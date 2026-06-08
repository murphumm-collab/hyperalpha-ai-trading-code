"""Discord Bot Service - Handle Discord bot lifecycle and message routing.

Architecture:
- Uses discord.py library (async, Gateway-based)
- Maintains persistent WebSocket connection to Discord
- Routes DM messages to Hyper AI service for processing
- Sends AI responses back to Discord DM
"""
import asyncio
import logging
import re
from typing import Dict, Optional, Callable, Any

logger = logging.getLogger(__name__)

_discord_clients: Dict[int, Any] = {}
_message_handlers: Dict[int, Callable] = {}
_discord_loops: Dict[int, asyncio.AbstractEventLoop] = {}


def _runtime_key(owner_user_id: Optional[int] = None) -> int:
    return int(owner_user_id or 0)


def _get_discord_module():
    """Lazy import discord to avoid startup errors if not installed."""
    try:
        import discord
        return discord
    except ImportError:
        logger.warning("discord.py not installed")
        return None


async def validate_discord_token(token: str) -> dict:
    """Validate a Discord bot token by attempting to login."""
    discord = _get_discord_module()
    if not discord:
        return {"valid": False, "error": "discord.py not installed"}

    try:
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            pass

        login_task = asyncio.create_task(client.login(token))
        await asyncio.wait_for(login_task, timeout=10)

        bot_user = client.user
        result = {
            "valid": True,
            "username": bot_user.name if bot_user else None,
            "bot_id": str(bot_user.id) if bot_user else None,
        }

        await client.close()
        return result
    except asyncio.TimeoutError:
        return {"valid": False, "error": "Connection timeout"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def _strip_markdown(text: str) -> str:
    """Strip Markdown formatting to produce clean plain text."""
    text = re.sub(r'```[\s\S]*?```', lambda m: m.group(0).strip('`').strip(), text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    return text


async def send_discord_message(token: str, user_id: int, text: str) -> bool:
    """Send a DM to a Discord user using REST API with proper formatting."""
    discord = _get_discord_module()
    if not discord:
        return False

    try:
        from services.message_formatter import format_for_discord

        intents = discord.Intents.default()
        client = discord.Client(intents=intents)
        await client.login(token)

        user = await client.fetch_user(user_id)
        if not user:
            await client.close()
            return False

        dm_channel = await user.create_dm()

        # Convert tables and chunk for Discord
        chunks = format_for_discord(text)
        for chunk in chunks:
            await dm_channel.send(chunk)

        await client.close()
        return True
    except Exception as e:
        logger.error(f"Failed to send Discord message: {e}")
        return False


async def send_discord_message_via_client(
    user_id: int,
    text: str,
    owner_user_id: Optional[int] = None,
) -> bool:
    """Send a DM using the running Gateway client (preferred for replies)."""
    key = _runtime_key(owner_user_id)
    client = _discord_clients.get(key)
    client_loop = _discord_loops.get(key)
    if not client or not client.is_ready():
        return False

    async def _send():
        try:
            from services.message_formatter import format_for_discord

            user = await client.fetch_user(user_id)
            if not user:
                return False

            dm_channel = await user.create_dm()

            # Convert tables and chunk for Discord
            chunks = format_for_discord(text)
            for chunk in chunks:
                await dm_channel.send(chunk)

            return True
        except Exception as e:
            logger.error(f"Failed to send Discord message via client: {e}")
            return False

    # If we're in the Discord event loop, run directly
    try:
        current_loop = asyncio.get_running_loop()
        if current_loop == client_loop:
            return await _send()
    except RuntimeError:
        pass

    # Otherwise, schedule on Discord's event loop
    if client_loop and client_loop.is_running():
        future = asyncio.run_coroutine_threadsafe(_send(), client_loop)
        try:
            return future.result(timeout=30)
        except Exception as e:
            logger.error(f"Failed to send Discord message (cross-thread): {e}")
            return False

    return False


def is_discord_client_running(owner_user_id: Optional[int] = None) -> bool:
    """Check if Discord Gateway client is running and connected."""
    if owner_user_id is not None:
        client = _discord_clients.get(_runtime_key(owner_user_id))
        return client is not None and client.is_ready()
    return any(client.is_ready() for client in _discord_clients.values())


def get_discord_client(owner_user_id: Optional[int] = None):
    """Get the running Discord client instance."""
    if owner_user_id is not None:
        return _discord_clients.get(_runtime_key(owner_user_id))
    return next(iter(_discord_clients.values()), None)


async def start_discord_gateway(
    token: str,
    message_callback: Callable,
    owner_user_id: Optional[int] = None,
):
    """
    Start the Discord Gateway client for receiving DM messages.

    Args:
        token: Bot token from Discord Developer Portal
        message_callback: Async function(user_id, username, display_name, text) -> response_text
    """
    discord = _get_discord_module()
    if not discord:
        print("[Discord] discord.py not installed, skipping Gateway startup", flush=True)
        return

    key = _runtime_key(owner_user_id)
    await stop_discord_gateway(owner_user_id)
    _message_handlers[key] = message_callback
    _discord_loops[key] = asyncio.get_event_loop()  # Store the event loop

    intents = discord.Intents.default()
    intents.message_content = True
    intents.dm_messages = True

    client = discord.Client(intents=intents)
    _discord_clients[key] = client

    @client.event
    async def on_ready():
        print(f"[Discord] Gateway connected for user={owner_user_id} as {client.user}", flush=True)

    @client.event
    async def on_message(message):
        if message.author.bot:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return

        user_id = message.author.id
        username = message.author.name
        display_name = message.author.display_name
        text = message.content

        print(f"[Discord] DM from {username} ({user_id}): {text[:50]}...", flush=True)

        message_handler = _message_handlers.get(key)
        if message_handler:
            try:
                response = await message_handler(user_id, username, display_name, text)
                if response:
                    if len(response) <= 2000:
                        await message.channel.send(response)
                    else:
                        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                        for chunk in chunks:
                            await message.channel.send(chunk)
            except Exception as e:
                logger.error(f"[Discord] Message handler error: {e}")
                await message.channel.send("Sorry, an error occurred while processing your message.")

    @client.event
    async def on_disconnect():
        print(f"[Discord] Gateway disconnected for user={owner_user_id}, will auto-reconnect...", flush=True)

    try:
        await client.start(token)
    except Exception as e:
        print(f"[Discord] Gateway error for user={owner_user_id}: {e}", flush=True)
        _discord_clients.pop(key, None)
        _message_handlers.pop(key, None)
        _discord_loops.pop(key, None)


async def stop_discord_gateway(owner_user_id: Optional[int] = None):
    """Stop one user's Discord Gateway client, or all clients when omitted."""
    keys = list(_discord_clients.keys()) if owner_user_id is None else [_runtime_key(owner_user_id)]
    for key in keys:
        client = _discord_clients.pop(key, None)
        _message_handlers.pop(key, None)
        _discord_loops.pop(key, None)
        if client:
            await client.close()
            print(f"[Discord] Gateway stopped for user_key={key}", flush=True)


# ============================================================================
# Discord Bot Adapter (implements BotAdapter interface)
# ============================================================================
class DiscordAdapter:
    """Discord bot adapter implementing the unified BotAdapter interface."""

    def __init__(self):
        self._token: Optional[str] = None
        self._message_callback: Optional[Callable] = None

    @property
    def platform(self) -> str:
        return "discord"

    def is_ready(self) -> bool:
        return is_discord_client_running()

    async def send_message(self, chat_id: str, content: str) -> bool:
        """Send message to Discord user via DM."""
        user_id = int(chat_id)
        return await send_discord_message_via_client(user_id, content)

    async def start(self, token: str) -> bool:
        """Start the Discord Gateway with the given token."""
        self._token = token
        # Gateway is started separately via start_discord_gateway()
        # This adapter just tracks the token
        logger.info(f"[DiscordAdapter] Token set, Gateway will be started separately")
        return True

    async def stop(self) -> None:
        """Stop the Discord Gateway."""
        await stop_discord_gateway()
        self._token = None
        logger.info(f"[DiscordAdapter] Stopped")

    def set_message_callback(self, callback: Callable):
        """Set the message handler callback."""
        self._message_callback = callback


# Global adapter instance
_discord_adapter: Optional[DiscordAdapter] = None


def get_discord_adapter() -> DiscordAdapter:
    """Get or create the global Discord adapter instance."""
    global _discord_adapter
    if _discord_adapter is None:
        _discord_adapter = DiscordAdapter()
    return _discord_adapter
