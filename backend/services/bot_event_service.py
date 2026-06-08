"""Bot Event Service - System event queue for Bot conversations.

Events (signal triggers, AI decisions) are saved as assistant messages
to the Bot conversation and pushed to all bound channels.
Push = broadcast to ALL bound channels; Reply = unicast to originating channel.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from database.models import HyperAiConversation, HyperAiMessage, BotConfig

logger = logging.getLogger(__name__)


def _format_money(value: Any) -> Optional[str]:
    if not isinstance(value, (int, float)):
        return None
    abs_value = abs(float(value))
    if abs_value >= 1000:
        return f"${value:,.0f}"
    if abs_value >= 1:
        return f"${value:,.2f}"
    return f"${value:,.4f}"


def _format_price(value: Any) -> Optional[str]:
    if not isinstance(value, (int, float)):
        return None
    return f"{float(value):,.6f}".rstrip("0").rstrip(".")


def _wallet_action_label(action: Any) -> Optional[str]:
    mapping = {
        "open": "Opened",
        "add": "Increased",
        "reduce": "Reduced",
        "close": "Closed",
        "flip": "Flipped",
        "update": "Updated",
    }
    if not isinstance(action, str):
        return None
    return mapping.get(action.strip().lower(), action.strip().replace("_", " ").title())


def _wallet_direction_label(direction: Any) -> Optional[str]:
    mapping = {
        "long": "Long",
        "short": "Short",
        "flat": "Flat",
    }
    if not isinstance(direction, str):
        return None
    return mapping.get(direction.strip().lower(), direction.strip().replace("_", " ").title())


def _wallet_event_type_label(event_type: Any) -> Optional[str]:
    mapping = {
        "position_change": "Position Change",
        "equity_change": "Equity Change",
        "fill": "Trade Fill",
        "funding": "Funding",
        "transfer": "Transfer",
        "liquidation": "Liquidation",
    }
    if not isinstance(event_type, str):
        return None
    return mapping.get(event_type.strip().lower(), event_type.strip().replace("_", " ").title())


def get_bot_conversations(db: Session, user_id: Optional[int] = None) -> List[HyperAiConversation]:
    """Get Bot conversations, optionally scoped to one user."""
    query = db.query(HyperAiConversation).filter(
        HyperAiConversation.is_bot_conversation == True
    )
    if user_id is not None:
        query = query.filter(HyperAiConversation.user_id == user_id)
    return query.all()


def get_or_create_bot_conversation(db: Session, user_id: int) -> HyperAiConversation:
    """Get or create the shared bot conversation for one user."""
    conv = db.query(HyperAiConversation).filter(
        HyperAiConversation.user_id == user_id,
        HyperAiConversation.is_bot_conversation == True,
    ).first()
    if conv:
        return conv

    conv = HyperAiConversation(
        user_id=user_id,
        title="Hyper AI Bot",
        is_bot_conversation=True,
    )
    db.add(conv)
    db.flush()
    return conv


def get_connected_bot_configs(db: Session) -> List[BotConfig]:
    """Get all connected bot configurations."""
    return db.query(BotConfig).filter(
        BotConfig.status == "connected"
    ).all()


def enqueue_system_event(
    db: Session,
    event_type: str,
    event_data: Dict[str, Any],
    format_message: bool = True,
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Enqueue a system event to all Bot conversations.

    Args:
        db: Database session
        event_type: Type of event (signal_triggered, ai_decision, etc.)
        event_data: Event payload
        format_message: If True, format event_data into readable message

    Returns:
        List of dicts with conversation_id, message_id, platform for push
    """
    # Format event into readable message
    if format_message:
        content = _format_event_message(event_type, event_data)
    else:
        content = event_data.get("message", str(event_data))

    results = []
    if user_id is not None:
        bot_convs = [get_or_create_bot_conversation(db, user_id)]
    else:
        bot_convs = get_bot_conversations(db)

    for conv in bot_convs:
        # Save as assistant message (Bot-initiated)
        message = HyperAiMessage(
            conversation_id=conv.id,
            role="assistant",
            content=content,
            is_complete=True
        )
        db.add(message)
        db.flush()

        results.append({
            "conversation_id": conv.id,
            "message_id": message.id,
            "platform": conv.bot_platform,
            "user_id": conv.user_id,
            "content": content
        })

    db.commit()
    return results


def _format_event_message(event_type: str, data: Dict[str, Any]) -> str:
    """Format event data into human-readable message."""
    header = "【🤖 Hyper AI Notification】\n\n"

    if event_type == "signal_triggered":
        pool_name = data.get('pool_name', 'Unknown')
        symbol = data.get('symbol', 'N/A')
        wallet_event = data.get('wallet_event')
        if isinstance(wallet_event, dict):
            event_type_name = _wallet_event_type_label(wallet_event.get('event_type')) or "Wallet Event"
            summary = wallet_event.get('summary') or 'Wallet event triggered'
            detail = wallet_event.get('detail') if isinstance(wallet_event.get('detail'), dict) else {}
            address = str(wallet_event.get('address', ''))[:6]
            address_tail = str(wallet_event.get('address', ''))[-4:]
            short_address = f"{address}...{address_tail}" if address and address_tail else "N/A"
            action = _wallet_action_label(detail.get("action"))
            direction = _wallet_direction_label(detail.get("direction"))
            notional_value = _format_money(detail.get("notional_value"))
            entry_price = _format_price(detail.get("entry_price"))
            leverage = detail.get("leverage")
            unrealized_pnl = _format_money(detail.get("unrealized_pnl"))
            liquidation_price = _format_price(detail.get("liquidation_price"))
            closed_pnl = _format_money(detail.get("closed_pnl"))
            average_price = _format_price(detail.get("average_price"))

            extra_lines = []
            if action:
                if direction and direction != "Flat":
                    extra_lines.append(f"Action: {action} {direction}")
                else:
                    extra_lines.append(f"Action: {action}")
            elif direction:
                extra_lines.append(f"Direction: {direction}")

            extra_lines.append(f"Type: {event_type_name}")
            extra_lines.append(f"Wallet: {short_address}")
            extra_lines.append(f"Symbol: {symbol}")
            if notional_value:
                extra_lines.append(f"Notional: {notional_value}")
            if entry_price:
                extra_lines.append(f"Entry Price: {entry_price}")
            if leverage is not None:
                extra_lines.append(f"Leverage: {leverage}")
            if unrealized_pnl:
                extra_lines.append(f"Unrealized PnL: {unrealized_pnl}")
            if liquidation_price:
                extra_lines.append(f"Liquidation Price: {liquidation_price}")
            if closed_pnl:
                extra_lines.append(f"Realized PnL: {closed_pnl}")
            if average_price:
                extra_lines.append(f"Avg Price: {average_price}")

            return (
                f"{header}"
                f"🔔 【{pool_name}】 Wallet signal triggered\n"
                f"{summary}\n"
                f"{chr(10).join(extra_lines)}"
            )
        triggered = data.get('triggered_signals', [])
        signals_text = ", ".join(
            f"{s.get('signal_name', s.get('metric', 'N/A'))}={s.get('current_value', 'N/A'):.4f}"
            if isinstance(s.get('current_value'), (int, float))
            else f"{s.get('signal_name', s.get('metric', 'N/A'))}={s.get('current_value', 'N/A')}"
            for s in triggered[:3]
        ) if triggered else "N/A"
        return (
            f"{header}"
            f"🔔 【{pool_name}】 {symbol} triggered\n"
            f"{signals_text}"
        )
    elif event_type == "ai_decision":
        trader = data.get('trader_name', 'AI Trader')
        op = data.get('operation', 'HOLD')
        symbol = data.get('symbol', 'N/A')
        portion = data.get('target_portion', 'N/A')
        reason = data.get('reason', '')
        return (
            f"{header}"
            f"🤖 【{trader}】 {op} {symbol} {portion}\n"
            f"{reason}"
        )
    elif event_type == "program_decision":
        program = data.get('program_name', 'Program')
        op = data.get('operation', 'HOLD')
        symbol = data.get('symbol', 'N/A')
        size = data.get('size_usd', 'N/A')
        leverage = data.get('leverage', '')
        reason = data.get('reason', '')
        return (
            f"{header}"
            f"⚙️ 【{program}】 {op} {symbol} {size} {leverage}\n"
            f"{reason}"
        )
    elif event_type == "trade_executed":
        return (
            f"{header}"
            f"✅ **Trade Executed**\n"
            f"Symbol: {data.get('symbol', 'N/A')}\n"
            f"Side: {data.get('side', 'N/A')}\n"
            f"Size: {data.get('size', 'N/A')}\n"
            f"Price: {data.get('price', 'N/A')}"
        )
    else:
        return f"{header}📢 {event_type}: {data.get('message', str(data))}"


async def push_event_to_all_channels(
    db: Session,
    event_results: List[Dict[str, Any]]
):
    """
    Push broadcast: send event notification to ALL bound channels on ALL connected platforms.
    Called after enqueue_system_event to notify users on Telegram/Discord/etc.

    Uses adapter pattern - automatically works with any registered platform adapter.
    """
    from database.models import BotChatBinding
    from services.bot_adapter import get_adapter
    from services.bot_service import get_decrypted_bot_token
    from services.discord_bot_service import send_discord_message
    from services.telegram_bot_service import send_telegram_message

    if not event_results:
        return

    # Get content from first result (all results have the same content)
    content = event_results[0].get("content", "")
    if not content:
        return

    user_ids = {
        result.get("user_id")
        for result in event_results
        if result.get("user_id") is not None
    }

    # Query active bindings for the event owner only. Legacy global events with
    # no user_id keep the previous broadcast behavior.
    bindings_query = db.query(BotChatBinding).filter(
        BotChatBinding.is_active == True
    )
    if user_ids:
        bindings_query = bindings_query.filter(BotChatBinding.user_id.in_(user_ids))
    bindings = bindings_query.all()

    for binding in bindings:
        if binding.platform == "telegram":
            token = get_decrypted_bot_token(db, "telegram", binding.user_id)
            if not token:
                logger.debug(f"Telegram token missing for user {binding.user_id}, skipping push")
                continue
            try:
                await send_telegram_message(token, int(binding.chat_id), content)
            except Exception as e:
                logger.error(f"Failed to push to Telegram chat {binding.chat_id}: {e}")
            continue

        if binding.platform == "discord":
            token = get_decrypted_bot_token(db, "discord", binding.user_id)
            if not token:
                logger.debug(f"Discord token missing for user {binding.user_id}, skipping push")
                continue
            try:
                await send_discord_message(token, int(binding.chat_id), content)
            except Exception as e:
                logger.error(f"Failed to push to Discord user {binding.chat_id}: {e}")
            continue

        adapter = get_adapter(binding.platform)
        if not adapter:
            logger.warning(f"No adapter registered for platform: {binding.platform}")
            continue

        if not adapter.is_ready():
            logger.debug(f"Adapter {binding.platform} not ready, skipping push to {binding.chat_id}")
            continue

        try:
            await adapter.send_message(binding.chat_id, content)
        except Exception as e:
            logger.error(f"Failed to push to {binding.platform} chat {binding.chat_id}: {e}")


# Legacy functions kept for backward compatibility during transition
# These can be removed once all callers use the adapter pattern

async def _push_to_telegram(db: Session, content: str):
    """[DEPRECATED] Use adapter pattern instead. Push message to all known Telegram chat_ids."""
    from services.bot_adapter import get_adapter
    from database.models import BotChatBinding

    adapter = get_adapter("telegram")
    if not adapter or not adapter.is_ready():
        return

    bindings = db.query(BotChatBinding).filter(
        BotChatBinding.platform == "telegram",
        BotChatBinding.is_active == True
    ).all()

    for binding in bindings:
        try:
            await adapter.send_message(binding.chat_id, content)
        except Exception as e:
            logger.error(f"Failed to push to Telegram chat {binding.chat_id}: {e}")


async def _push_to_discord(db: Session, content: str):
    """[DEPRECATED] Use adapter pattern instead. Push message to all known Discord user_ids."""
    from services.bot_adapter import get_adapter
    from database.models import BotChatBinding

    adapter = get_adapter("discord")
    if not adapter or not adapter.is_ready():
        logger.warning("Discord adapter not ready, skipping push")
        return

    bindings = db.query(BotChatBinding).filter(
        BotChatBinding.platform == "discord",
        BotChatBinding.is_active == True
    ).all()

    for binding in bindings:
        try:
            await adapter.send_message(binding.chat_id, content)
        except Exception as e:
            logger.error(f"Failed to push to Discord user {binding.chat_id}: {e}")
