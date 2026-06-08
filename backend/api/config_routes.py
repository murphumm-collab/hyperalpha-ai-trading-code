"""
System config API routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from database.connection import SessionLocal
from database.models import SystemConfig, GlobalSamplingConfig, User
from api.auth_utils import get_authenticated_user_dependency, get_current_user_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])
ALLOWED_SYSTEM_CONFIG_UPDATE_KEYS = {"ui_language"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ConfigUpdateRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = None


def _get_effective_sampling_values(db: Session) -> tuple[int, int]:
    configs = db.query(GlobalSamplingConfig).filter(GlobalSamplingConfig.user_id != None).all()
    if not configs:
        global_config = db.query(GlobalSamplingConfig).filter(GlobalSamplingConfig.user_id == None).first()
        if global_config:
            return global_config.sampling_interval or 18, global_config.sampling_depth or 10
        return 18, 10

    intervals = [
        config.sampling_interval
        for config in configs
        if config.sampling_interval is not None
    ]
    depths = [
        config.sampling_depth
        for config in configs
        if config.sampling_depth is not None
    ]
    return min(intervals) if intervals else 18, max(depths) if depths else 10


def _sync_effective_global_sampling_config(db: Session) -> GlobalSamplingConfig:
    effective_interval, effective_depth = _get_effective_sampling_values(db)
    config = db.query(GlobalSamplingConfig).filter(GlobalSamplingConfig.user_id == None).first()
    if not config:
        config = GlobalSamplingConfig(
            user_id=None,
            sampling_interval=effective_interval,
            sampling_depth=effective_depth,
        )
        db.add(config)
    else:
        config.sampling_interval = effective_interval
        config.sampling_depth = effective_depth
    db.flush()
    return config


@router.get("/check-required")
async def check_required_configs(db: Session = Depends(get_db)):
    """Check if required configs are set"""
    try:
        return {
            "has_required_configs": True,
            "missing_configs": []
        }
    except Exception as e:
        logger.error(f"Failed to check required configs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check required configs: {str(e)}")


@router.get("/global-sampling")
async def get_global_sampling_config(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """Get current user's sampling preference, falling back to effective global config."""
    try:
        config = db.query(GlobalSamplingConfig).filter(
            GlobalSamplingConfig.user_id == current_user.id
        ).first()
        if not config:
            config = _sync_effective_global_sampling_config(db)
            db.commit()

        return {
            "sampling_interval": config.sampling_interval,
            "sampling_depth": config.sampling_depth
        }
    except Exception as e:
        logger.error(f"Failed to get global sampling config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get global sampling config: {str(e)}")


@router.put("/global-sampling")
async def update_global_sampling_config(
    payload: dict,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """Update current user's sampling preference and refresh effective global pool config."""
    try:
        sampling_interval = payload.get("sampling_interval")
        sampling_depth = payload.get("sampling_depth")

        # Validate sampling_interval if provided
        if sampling_interval is not None:
            if not isinstance(sampling_interval, int) or sampling_interval < 5 or sampling_interval > 60:
                raise HTTPException(
                    status_code=400,
                    detail="sampling_interval must be between 5 and 60 seconds"
                )

        # Validate sampling_depth if provided
        if sampling_depth is not None:
            if not isinstance(sampling_depth, int) or sampling_depth < 10 or sampling_depth > 60:
                raise HTTPException(
                    status_code=400,
                    detail="sampling_depth must be between 10 and 60"
                )

        config = db.query(GlobalSamplingConfig).filter(
            GlobalSamplingConfig.user_id == current_user.id
        ).first()
        if not config:
            config = GlobalSamplingConfig(
                user_id=current_user.id,
                sampling_interval=sampling_interval or 18,
                sampling_depth=sampling_depth or 10
            )
            db.add(config)
        else:
            if sampling_interval is not None:
                config.sampling_interval = sampling_interval
            if sampling_depth is not None:
                config.sampling_depth = sampling_depth

        effective_config = _sync_effective_global_sampling_config(db)
        db.commit()
        db.refresh(config)
        db.refresh(effective_config)

        # Trigger sampling pool reconfiguration (use watchlist if available)
        try:
            print(f"[DEBUG] Starting sampling pool update to effective depth={effective_config.sampling_depth}")
            from services.sampling_pool import sampling_pool
            from services.trading_commands import AI_TRADING_SYMBOLS
            from services.hyperliquid_symbol_service import get_selected_symbols as get_hyperliquid_selected_symbols

            symbols = get_hyperliquid_selected_symbols() or AI_TRADING_SYMBOLS
            for symbol in symbols:
                sampling_pool.set_max_samples(symbol, effective_config.sampling_depth)

            print(f"[DEBUG] Sampling pool updated: depth={effective_config.sampling_depth} for {len(symbols)} symbols")
            logger.info(f"Sampling pool updated: depth={effective_config.sampling_depth} for {len(symbols)} symbols")
        except Exception as pool_err:
            print(f"[ERROR] Failed to update sampling pool: {pool_err}")
            logger.warning(f"Failed to update sampling pool: {pool_err}")

        return {
            "sampling_interval": config.sampling_interval,
            "sampling_depth": config.sampling_depth,
            "effective_sampling_interval": effective_config.sampling_interval,
            "effective_sampling_depth": effective_config.sampling_depth,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update global sampling config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update global sampling config: {str(e)}")


# Generic system config update - must be after specific routes to avoid path conflicts
class ConfigValueRequest(BaseModel):
    value: str


@router.put("/{key}")
async def update_system_config(
    key: str,
    payload: ConfigValueRequest,
    current_user: User = Depends(get_authenticated_user_dependency),
    db: Session = Depends(get_db),
):
    """Update an allowed system config value by key."""
    if key not in ALLOWED_SYSTEM_CONFIG_UPDATE_KEYS:
        raise HTTPException(status_code=403, detail="System config key is not user-editable")

    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if config:
        config.value = payload.value
    else:
        config = SystemConfig(key=key, value=payload.value)
        db.add(config)
    db.commit()
    return {"success": True, "key": key, "value": payload.value}
