"""Bot Integration Service - Manage Telegram/Discord bot configurations"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from database.models import BotConfig
from utils.encryption import encrypt_private_key, decrypt_private_key

logger = logging.getLogger(__name__)


def _bot_config_query(db: Session, platform: str, user_id: Optional[int] = None):
    query = db.query(BotConfig).filter(BotConfig.platform == platform)
    if user_id is not None:
        query = query.filter(BotConfig.user_id == user_id)
    return query


def get_bot_config(db: Session, platform: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Get bot configuration for a platform."""
    config = _bot_config_query(db, platform, user_id).first()
    if not config:
        return None
    return {
        "id": config.id,
        "user_id": config.user_id,
        "platform": config.platform,
        "bot_username": config.bot_username,
        "bot_app_id": config.bot_app_id,
        "status": config.status,
        "error_message": config.error_message,
        "has_token": bool(config.bot_token_encrypted),
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


def get_all_bot_configs(db: Session, user_id: Optional[int] = None) -> list:
    """Get all bot configurations."""
    query = db.query(BotConfig)
    if user_id is not None:
        query = query.filter(BotConfig.user_id == user_id)
    configs = query.all()
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "platform": c.platform,
            "bot_username": c.bot_username,
            "status": c.status,
            "has_token": bool(c.bot_token_encrypted),
        }
        for c in configs
    ]


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
    else:
        config = BotConfig(
            user_id=user_id,
            platform=platform,
            bot_token_encrypted=encrypted_token,
            bot_username=bot_username,
            bot_app_id=bot_app_id,
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
