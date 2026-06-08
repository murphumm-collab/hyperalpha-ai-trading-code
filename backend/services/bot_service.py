"""Bot Integration Service - Manage Telegram/Discord bot configurations"""
import logging
import secrets
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from database.models import BotConfig
from utils.encryption import encrypt_private_key, decrypt_private_key

logger = logging.getLogger(__name__)


def _new_webhook_secret() -> str:
    return secrets.token_urlsafe(32)


def _ensure_webhook_secret(db: Session, config: BotConfig) -> str:
    if config.webhook_secret:
        return config.webhook_secret

    while True:
        candidate = _new_webhook_secret()
        exists = db.query(BotConfig).filter(
            BotConfig.webhook_secret == candidate
        ).first()
        if not exists:
            config.webhook_secret = candidate
            return candidate


def _bot_config_query(db: Session, platform: str, user_id: Optional[int] = None):
    query = db.query(BotConfig).filter(BotConfig.platform == platform)
    if user_id is not None:
        query = query.filter(BotConfig.user_id == user_id)
    return query


def _config_payload(db: Session, config: BotConfig) -> Dict[str, Any]:
    webhook_secret = _ensure_webhook_secret(db, config)
    return {
        "id": config.id,
        "user_id": config.user_id,
        "platform": config.platform,
        "bot_username": config.bot_username,
        "bot_app_id": config.bot_app_id,
        "status": config.status,
        "error_message": config.error_message,
        "has_token": bool(config.bot_token_encrypted),
        "webhook_secret": webhook_secret,
        "webhook_path": f"/api/bot/{config.platform}/webhook/{webhook_secret}",
        "webhook_url": config.webhook_url,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


def get_bot_config(db: Session, platform: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get bot configuration for a platform."""
    config = _bot_config_query(db, platform, user_id).first()
    if not config:
        return None
    payload = _config_payload(db, config)
    db.commit()
    return payload


def get_bot_config_by_webhook_secret(
    db: Session,
    platform: str,
    webhook_secret: str,
) -> Optional[BotConfig]:
    """Resolve a bot configuration from a public webhook secret."""
    if not webhook_secret:
        return None
    return db.query(BotConfig).filter(
        BotConfig.platform == platform,
        BotConfig.webhook_secret == webhook_secret,
    ).first()


def get_all_bot_configs(db: Session, user_id: Optional[int] = None) -> list:
    """Get all bot configurations."""
    query = db.query(BotConfig)
    if user_id is not None:
        query = query.filter(BotConfig.user_id == user_id)
    configs = query.all()
    payload = [
        {
            "id": c.id,
            "user_id": c.user_id,
            "platform": c.platform,
            "bot_username": c.bot_username,
            "status": c.status,
            "has_token": bool(c.bot_token_encrypted),
            "webhook_secret": _ensure_webhook_secret(db, c),
            "webhook_path": f"/api/bot/{c.platform}/webhook/{c.webhook_secret}",
            "webhook_url": c.webhook_url,
        }
        for c in configs
    ]
    db.commit()
    return payload


def save_bot_config(
    db: Session,
    platform: str,
    bot_token: str,
    bot_username: Optional[str] = None,
    bot_app_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Save or update bot configuration."""
    config = _bot_config_query(db, platform, user_id).first()

    encrypted_token = encrypt_private_key(bot_token) if bot_token else None

    if config:
        if user_id is not None and config.user_id is None:
            config.user_id = user_id
        config.bot_token_encrypted = encrypted_token
        if bot_username:
            config.bot_username = bot_username
        if bot_app_id:
            config.bot_app_id = bot_app_id
        config.status = "configured"
        config.error_message = None
        _ensure_webhook_secret(db, config)
    else:
        config = BotConfig(
            user_id=user_id,
            platform=platform,
            bot_token_encrypted=encrypted_token,
            bot_username=bot_username,
            bot_app_id=bot_app_id,
            webhook_secret=_new_webhook_secret(),
            status="configured"
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    return get_bot_config(db, platform, user_id)


def get_decrypted_bot_token(db: Session, platform: str, user_id: Optional[int] = None) -> Optional[str]:
    """Get decrypted bot token for internal use."""
    config = _bot_config_query(db, platform, user_id).first()
    if not config or not config.bot_token_encrypted:
        return None
    return decrypt_private_key(config.bot_token_encrypted)


def get_decrypted_bot_token_for_config(config: BotConfig) -> Optional[str]:
    """Decrypt the token from a resolved BotConfig row."""
    if not config or not config.bot_token_encrypted:
        return None
    return decrypt_private_key(config.bot_token_encrypted)


def update_bot_status(
    db: Session,
    platform: str,
    status: str,
    error_message: Optional[str] = None,
    user_id: Optional[int] = None,
) -> bool:
    """Update bot connection status."""
    config = _bot_config_query(db, platform, user_id).first()
    if not config:
        return False

    config.status = status
    config.error_message = error_message
    db.commit()
    return True


def delete_bot_config(db: Session, platform: str, user_id: Optional[int] = None) -> bool:
    """Delete bot configuration."""
    config = _bot_config_query(db, platform, user_id).first()
    if not config:
        return False

    db.delete(config)
    db.commit()
    return True
