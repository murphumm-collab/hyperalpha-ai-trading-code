"""
Order Management API Routes
Provides functionality for creating, querying, and canceling orders
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import logging

from database.connection import SessionLocal
from database.models import User, Order, Account
from schemas.order import OrderCreate, OrderOut
from services.order_matching import create_order, check_and_execute_order, get_pending_orders, cancel_order, process_all_pending_orders
from repositories.user_repo import verify_user_password, user_has_password, set_user_password, verify_auth_session
from api.auth_utils import get_current_user_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class OrderCreateRequest(BaseModel):
    """Order creation request model"""
    user_id: int
    symbol: str
    name: str
    side: str  # BUY/SELL
    order_type: str  # MARKET/LIMIT
    price: Optional[float] = None
    quantity: float
    username: Optional[str] = None  # Username for verification (required if no session_token)
    password: Optional[str] = None  # Trading password (required if no session_token)
    session_token: Optional[str] = None  # Auth session token (alternative to username+password)


class OrderExecutionResult(BaseModel):
    order_id: int
    executed: bool
    message: str


class OrderProcessingResult(BaseModel):
    """Order processing result model"""
    executed_count: int
    total_checked: int
    message: str


def _ensure_order_owner(db: Session, order_id: int, user_id: int) -> Order:
    order = (
        db.query(Order)
        .join(Account, Order.account_id == Account.id)
        .filter(
            Order.id == order_id,
            Account.user_id == user_id,
            Account.is_deleted != True,
        )
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _load_order_request_user(db: Session, request: OrderCreateRequest, current_user: User) -> User:
    """
    Resolve the user allowed to create this order.

    The request body keeps user_id for legacy clients, but it is only accepted
    when it matches a verified body session token or the authenticated request
    user. This prevents the local/default user fallback from creating orders for
    arbitrary accounts in multi-user deployments.
    """
    if request.session_token:
        session_user_id = verify_auth_session(db, request.session_token)
        if not session_user_id or session_user_id != request.user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        if current_user.username != "default" and current_user.id != session_user_id:
            raise HTTPException(status_code=403, detail="Cannot create orders for another user")

        user = db.query(User).filter(User.id == session_user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Session user not found")
        return user

    if request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot create orders for another user")

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/create", response_model=OrderOut)
def create_new_order(
    request: OrderCreateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Create a new order
    
    Args:
        request: Order creation request
        db: Database session
        
    Returns:
        Created order information
    """
    try:
        user = _load_order_request_user(db, request, current_user)

        # Authentication: supports either session_token or username+password
        if request.session_token:
            # Already authenticated and matched to the resolved request user.
            pass
        elif request.username and request.password:
            # Authenticate using username and password
            if user.username != request.username:
                raise HTTPException(status_code=401, detail="Username does not match")
            
            # Password verification
            if not user_has_password(db, user.id):
                # First transaction, set password
                if len(request.password.strip()) < 4:
                    raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
                
                updated_user = set_user_password(db, user.id, request.password)
                if not updated_user:
                    raise HTTPException(status_code=500, detail="Failed to set trading password")
                
                logger.info(f"User {user.id} first transaction, trading password set")
            else:
                # Verify existing password
                if not verify_user_password(db, user.id, request.password):
                    raise HTTPException(status_code=401, detail="Incorrect trading password")
        else:
            raise HTTPException(status_code=400, detail="Please provide either session token or username+password")
        
        # Resolve trading account for the user (default user initialized in backend/main.py has at least one account)
        account = (
            db.query(Account)
            .filter(Account.user_id == user.id, Account.is_active == "true", Account.is_deleted != True)
            .first()
        )
        if not account:
            raise HTTPException(status_code=404, detail="Active trading account not found for user")

        # Create order (crypto-only)
        order = create_order(
            db=db,
            account=account,
            symbol=request.symbol,
            name=request.name,
            side=request.side,
            order_type=request.order_type,
            price=request.price,
            quantity=request.quantity
        )
        
        db.commit()
        db.refresh(order)
        
        logger.info(f"User {user.username} created order: {order.order_no}")
        return order
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")


@router.get("/pending", response_model=List[OrderOut])
def get_user_pending_orders(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Get pending orders
    
    Args:
        user_id: Optional current user ID filter for backwards compatibility
        db: Database session
        
    Returns:
        List of pending orders
    """
    try:
        if user_id is not None and user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot view another user's orders")

        orders = (
            db.query(Order)
            .join(Account, Order.account_id == Account.id)
            .filter(
                Account.user_id == current_user.id,
                Account.is_deleted != True,
                Order.status == "PENDING",
            )
            .order_by(Order.created_at)
            .all()
        )
        return orders
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pending orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending orders: {str(e)}")


@router.get("/user/{user_id}", response_model=List[OrderOut])
def get_user_orders(
    user_id: int,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Get all orders for a user
    
    Args:
        user_id: User ID
        status: Filter by order status (PENDING/FILLED/CANCELLED)
        db: Database session
        
    Returns:
        List of user's orders
    """
    try:
        if user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot view another user's orders")

        query = (
            db.query(Order)
            .join(Account, Order.account_id == Account.id)
            .filter(
                Account.user_id == current_user.id,
                Account.is_deleted != True,
            )
        )
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(Order.created_at.desc()).all()
        return orders
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user orders: {str(e)}")


@router.post("/execute/{order_id}", response_model=OrderExecutionResult)
def execute_order_manually(
    order_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Manually execute a specific order (check execution conditions)
    
    Args:
        order_id: Order ID
        db: Database session
        
    Returns:
        Order execution result
    """
    try:
        order = _ensure_order_owner(db, order_id, current_user.id)
        
        if order.status != "PENDING":
            return OrderExecutionResult(
                order_id=order_id,
                executed=False,
                message=f"Order status is {order.status}, cannot execute"
            )
        
        # Check and execute order
        executed = check_and_execute_order(db, order)
        
        if executed:
            return OrderExecutionResult(
                order_id=order_id,
                executed=True,
                message="Order executed successfully"
            )
        else:
            return OrderExecutionResult(
                order_id=order_id,
                executed=False,
                message="Order does not meet execution conditions"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute order: {str(e)}")


@router.post("/cancel/{order_id}")
def cancel_user_order(
    order_id: int,
    reason: str = "User cancelled",
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Cancel an order
    
    Args:
        order_id: Order ID
        reason: Reason for cancellation
        db: Database session
        
    Returns:
        Cancellation result
    """
    try:
        order = _ensure_order_owner(db, order_id, current_user.id)
        
        if order.status != "PENDING":
            raise HTTPException(status_code=400, detail=f"Order status is {order.status}, cannot be cancelled")
        
        success = cancel_order(db, order, reason)
        
        if success:
            return {"message": "Order cancelled successfully", "order_id": order_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to cancel order")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")


@router.post("/process-all", response_model=OrderProcessingResult)
def process_all_orders(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Process all pending orders
    
    Args:
        db: Database session
        
    Returns:
        Processing statistics
    """
    try:
        pending_orders = (
            db.query(Order)
            .join(Account, Order.account_id == Account.id)
            .filter(
                Account.user_id == current_user.id,
                Account.is_deleted != True,
                Order.status == "PENDING",
            )
            .order_by(Order.created_at)
            .all()
        )
        executed_count = 0
        for order in pending_orders:
            if check_and_execute_order(db, order):
                executed_count += 1
        total_checked = len(pending_orders)
        
        return OrderProcessingResult(
            executed_count=executed_count,
            total_checked=total_checked,
            message=f"Processing complete: Checked {total_checked} orders, executed {executed_count}"
        )
        
    except Exception as e:
        logger.error(f"Failed to process orders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process orders: {str(e)}")


@router.get("/order/{order_id}", response_model=OrderOut)
def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Get order details
    
    Args:
        order_id: Order ID
        db: Database session
        
    Returns:
        Order details
    """
    try:
        order = _ensure_order_owner(db, order_id, current_user.id)
        
        return order
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get order details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get order details: {str(e)}")


@router.get("/health")
def orders_health_check(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Order service health check
    
    Returns:
        Service status information
    """
    try:
        # Count orders by status
        base_query = (
            db.query(Order)
            .join(Account, Order.account_id == Account.id)
            .filter(
                Account.user_id == current_user.id,
                Account.is_deleted != True,
            )
        )
        total_orders = base_query.count()
        pending_orders = base_query.filter(Order.status == "PENDING").count()
        filled_orders = base_query.filter(Order.status == "FILLED").count()
        cancelled_orders = base_query.filter(Order.status == "CANCELLED").count()
        
        import time
        return {
            "status": "healthy",
            "timestamp": int(time.time() * 1000),
            "statistics": {
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "filled_orders": filled_orders,
                "cancelled_orders": cancelled_orders
            },
            "message": "Order service is running normally"
        }
        
    except Exception as e:
        logger.error(f"Order service health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": int(time.time() * 1000),
            "error": str(e),
            "message": "Order service exception"
        }
