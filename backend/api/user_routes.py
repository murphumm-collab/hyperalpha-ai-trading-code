"""
User authentication API routes
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import logging

from database.connection import SessionLocal
from database.models import User, UserExchangeConfig, UserSubscription
from api.auth_utils import get_admin_user_dependency, get_current_user_dependency, is_admin_user
from repositories.user_repo import (
    create_user, get_user, get_user_by_username,
    update_user, create_auth_session, verify_auth_session,
    verify_user_password
)
from datetime import datetime
from pydantic import BaseModel
from schemas.user import (
    UserCreate, UserUpdate, UserOut, UserLogin, UserAuthResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", response_model=UserOut)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if username exists
        existing = get_user_by_username(db, user_data.username)
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Create new user
        user = create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password
        )
        
        return UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active == "true"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"User registration failed: {str(e)}")


@router.post("/login", response_model=UserAuthResponse)
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = get_user_by_username(db, login_data.username)
        if not user or not verify_user_password(db, user.id, login_data.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create auth session
        session = create_auth_session(db, user.id)
        if not session:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        return UserAuthResponse(
            user=UserOut(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active == "true"
            ),
            session_token=session.session_token,
            expires_at=session.expires_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User login failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"User login failed: {str(e)}")


@router.get("/profile", response_model=UserOut)
async def get_user_profile(session_token: str, db: Session = Depends(get_db)):
    try:
        user_id = verify_auth_session(db, session_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active == "true"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")


@router.put("/profile", response_model=UserOut)
async def update_user_profile(
    session_token: str, 
    user_data: UserUpdate, 
    db: Session = Depends(get_db)
):
    try:
        user_id = verify_auth_session(db, session_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        # Check if new username is taken (if provided)
        if user_data.username:
            existing = get_user_by_username(db, user_data.username)
            if existing and existing.id != user_id:
                raise HTTPException(status_code=400, detail="Username already exists")
        
        user = update_user(
            db=db,
            user_id=user_id,
            username=user_data.username,
            email=user_data.email
        )
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active == "true"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update user profile: {str(e)}")


@router.get("/", response_model=List[UserOut])
async def list_users(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    try:
        return [UserOut(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            is_active=current_user.is_active == "true"
        )]
        
    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@router.get("/exchange-config")
async def get_exchange_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Get current exchange configuration for the resolved request user."""
    try:
        config = db.query(UserExchangeConfig).filter(UserExchangeConfig.user_id == current_user.id).first()
        if not config:
            # Return default if no config exists
            return {"selected_exchange": "hyperliquid"}
        return {"selected_exchange": config.selected_exchange}
    except Exception as e:
        logger.error(f"Failed to get exchange config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get exchange config: {str(e)}")


@router.post("/exchange-config")
async def set_exchange_config(
    exchange_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """Set exchange configuration for the resolved request user."""
    try:
        selected_exchange = exchange_data.get("selected_exchange")
        if not selected_exchange or selected_exchange not in ["hyperliquid", "binance", "aster"]:
            raise HTTPException(status_code=400, detail="Invalid exchange selection")

        config = db.query(UserExchangeConfig).filter(UserExchangeConfig.user_id == current_user.id).first()
        if config:
            config.selected_exchange = selected_exchange
        else:
            config = UserExchangeConfig(user_id=current_user.id, selected_exchange=selected_exchange)
            db.add(config)

        db.commit()
        return {"selected_exchange": selected_exchange, "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set exchange config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set exchange config: {str(e)}")


class MembershipSyncRequest(BaseModel):
    """Request model for syncing membership info from www.akooi.com"""
    username: str
    status: str | None  # "ACTIVE" or None
    current_period_end: str | None  # ISO datetime string


class AdminUserOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    role: str
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None


class AdminRoleUpdateRequest(BaseModel):
    role: str


ADMIN_MANAGED_ROLES = {"user", "admin", "operator"}


def _admin_user_payload(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role or "user",
        is_active=user.is_active == "true",
        created_at=user.created_at.isoformat() if user.created_at else None,
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


def _count_admin_users(db: Session, exclude_user_id: int | None = None) -> int:
    query = db.query(User).filter(User.role.in_(["admin", "operator"]))
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    env_admins = [
        user for user in query.all()
        if is_admin_user(user)
    ]
    return len(env_admins)


@router.get("/admin/users", response_model=List[AdminUserOut])
async def admin_list_users(
    current_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db),
):
    """List all users for admin role management."""
    try:
        users = db.query(User).order_by(User.id.asc()).all()
        return [_admin_user_payload(user) for user in users]
    except Exception as e:
        logger.error(f"Failed to list admin users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@router.patch("/admin/users/{user_id}/role", response_model=AdminUserOut)
async def admin_update_user_role(
    user_id: int,
    request: AdminRoleUpdateRequest,
    current_user: User = Depends(get_admin_user_dependency),
    db: Session = Depends(get_db),
):
    """Update a user's role. Prevent removing the final admin/operator."""
    new_role = (request.role or "").strip().lower()
    if new_role not in ADMIN_MANAGED_ROLES:
        raise HTTPException(status_code=400, detail="Role must be one of: user, admin, operator")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = (user.role or "user").lower()
    if old_role in {"admin", "operator"} and new_role == "user":
        if _count_admin_users(db, exclude_user_id=user.id) <= 0:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin user")

    user.role = new_role
    db.commit()
    db.refresh(user)
    return _admin_user_payload(user)


@router.post("/sync-membership")
async def sync_membership_info(
    sync_data: MembershipSyncRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Sync membership information from www.akooi.com to local database

    This endpoint is called by frontend after successfully fetching membership
    info from www.akooi.com/api/membership/me. It updates the local UserSubscription
    table to keep it in sync, preventing accidental usage of stale local data.

    Important: This only updates the current request user's subscription.
    Never clear or overwrite other users' subscriptions from a frontend sync.
    """
    try:
        # Step 1: Clear only the current user's existing subscription.
        deleted = db.query(UserSubscription).filter(
            UserSubscription.user_id == current_user.id
        ).delete()
        logger.info(
            "Cleared %s subscription(s) for current user %s (ID: %s)",
            deleted,
            current_user.username,
            current_user.id,
        )

        # Step 2: Determine subscription type based on status from the trusted
        # membership lookup that the authenticated frontend just performed.
        subscription_type = "premium" if sync_data.status == "ACTIVE" else "free"

        # Parse expiry date if provided
        expires_at = None
        if sync_data.current_period_end:
            try:
                expires_at = datetime.fromisoformat(sync_data.current_period_end.replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Failed to parse expiry date: {e}")

        # Step 3: Create subscription for current request user.
        subscription = UserSubscription(
            user_id=current_user.id,
            subscription_type=subscription_type,
            expires_at=expires_at,
            max_sampling_depth=60 if subscription_type == "premium" else 10
        )
        db.add(subscription)
        logger.info(
            "Created subscription for current user %s (ID: %s): %s",
            current_user.username,
            current_user.id,
            subscription_type,
        )

        db.commit()

        return {
            "status": "success",
            "message": f"Membership synced for {current_user.username}",
            "subscription_type": subscription_type,
            "max_sampling_depth": subscription.max_sampling_depth
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to sync membership info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync membership info: {str(e)}"
        )


@router.post("/clear-membership")
async def clear_membership(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Clear membership subscription for the current request user.
    Called when user logs out to ensure premium status is removed.
    """
    try:
        deleted_count = db.query(UserSubscription).filter(
            UserSubscription.user_id == current_user.id
        ).delete()

        db.commit()
        logger.info(
            "Cleared %s subscription(s) on logout for current user %s (ID: %s)",
            deleted_count,
            current_user.username,
            current_user.id,
        )

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "username": current_user.username,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to clear membership: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear membership: {str(e)}"
        )
