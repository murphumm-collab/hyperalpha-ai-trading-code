from sqlalchemy.orm import Session
from database.models import Account, Order
from typing import List, Optional


def create_order(db: Session, order: Order) -> Order:
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def list_orders(
    db: Session,
    account_id: int,
    owner_user_id: Optional[int] = None,
) -> List[Order]:
    query = db.query(Order).filter(Order.account_id == account_id)
    if owner_user_id is not None:
        query = (
            query.join(Account, Order.account_id == Account.id)
            .filter(
                Account.user_id == owner_user_id,
                Account.is_deleted != True,
            )
        )
    return query.order_by(Order.created_at.desc()).all()


def get_order_by_no(
    db: Session,
    order_no: str,
    owner_user_id: Optional[int] = None,
) -> Optional[Order]:
    query = db.query(Order).filter(Order.order_no == order_no)
    if owner_user_id is not None:
        query = (
            query.join(Account, Order.account_id == Account.id)
            .filter(
                Account.user_id == owner_user_id,
                Account.is_deleted != True,
            )
        )
    return query.first()
