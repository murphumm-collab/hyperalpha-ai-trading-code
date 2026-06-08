from sqlalchemy.orm import Session
from database.models import Account, Position
from typing import List, Optional


def list_positions(
    db: Session,
    account_id: int,
    owner_user_id: Optional[int] = None,
) -> List[Position]:
    query = db.query(Position).filter(Position.account_id == account_id)
    if owner_user_id is not None:
        query = (
            query.join(Account, Position.account_id == Account.id)
            .filter(
                Account.user_id == owner_user_id,
                Account.is_deleted != True,
            )
        )
    return query.all()


def get_position(
    db: Session,
    account_id: int,
    symbol: str,
    market: str,
    owner_user_id: Optional[int] = None,
) -> Optional[Position]:
    query = db.query(Position).filter(
        Position.account_id == account_id,
        Position.symbol == symbol,
        Position.market == market,
    )
    if owner_user_id is not None:
        query = (
            query.join(Account, Position.account_id == Account.id)
            .filter(
                Account.user_id == owner_user_id,
                Account.is_deleted != True,
            )
        )
    return query.first()


def upsert_position(db: Session, position: Position) -> Position:
    db.add(position)
    db.commit()
    db.refresh(position)
    return position
