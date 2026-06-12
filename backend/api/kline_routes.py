"""
K线数据管理API路由
"""

import asyncio
import re
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging

from api.auth_utils import get_current_user_dependency
from database.connection import SessionLocal
from database.models import CryptoKline, KlineCollectionTask, User
from services.kline_data_service import kline_service
from services.kline_backfill_manager import BackfillManager, SAFE_BACKFILL_ERROR_MESSAGE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/klines", tags=["klines"])
VALID_KLINE_PERIODS = {
    "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "8h", "12h", "1d", "3d", "1w", "1M"
}
_SAFE_SYMBOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:_./-]{0,39}$")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic模型
class BackfillRequest(BaseModel):
    exchange: Optional[str] = None  # 如果不指定，使用当前配置的交易所
    symbols: List[str]
    start_time: datetime
    end_time: datetime
    period: str = "1m"


class BackfillTaskResponse(BaseModel):
    task_id: int
    exchange: str
    symbol: str
    start_time: datetime
    end_time: datetime
    period: str
    status: str
    progress: int
    total_records: int
    collected_records: int
    error_message: Optional[str]
    created_at: datetime


class CoverageResponse(BaseModel):
    exchange: str
    symbol: str
    period: str
    earliest_time: Optional[int]
    latest_time: Optional[int]
    total_records: int
    time_span_seconds: Optional[int]
    coverage_percentage: Optional[float]


def _resolve_exchange(db: Session, current_user: User, requested_exchange: Optional[str] = None) -> str:
    try:
        return kline_service.resolve_exchange_for_user(db, current_user.id, requested_exchange)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unsupported exchange") from exc


def _task_response(task: KlineCollectionTask) -> BackfillTaskResponse:
    return BackfillTaskResponse(
        task_id=task.id,
        exchange=task.exchange,
        symbol=task.symbol,
        start_time=task.start_time,
        end_time=task.end_time,
        period=task.period,
        status=task.status,
        progress=task.progress,
        total_records=task.total_records or 0,
        collected_records=task.collected_records or 0,
        error_message=SAFE_BACKFILL_ERROR_MESSAGE if task.error_message else None,
        created_at=task.created_at,
    )


def _normalize_ts(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if value < 0:
        raise HTTPException(status_code=400, detail="timestamp must be non-negative")
    return int(value // 1000) if value > 10_000_000_000 else int(value)


def _safe_symbol_candidates(symbol: str) -> list[str]:
    raw = (symbol or "").strip()
    if not raw or not _SAFE_SYMBOL_RE.match(raw):
        raise HTTPException(status_code=400, detail="Invalid symbol")

    candidates = [raw, raw.upper()]
    if ":" in raw:
        dex, asset = raw.split(":", 1)
        candidates.append(f"{dex.lower()}:{asset.upper()}")

    ordered: list[str] = []
    for item in candidates:
        if item not in ordered:
            ordered.append(item)
    return ordered


def _normalize_request_symbol(symbol: str) -> str:
    candidates = _safe_symbol_candidates(symbol)
    raw = candidates[0]
    if ":" in raw:
        dex, asset = raw.split(":", 1)
        return f"{dex.lower()}:{asset.upper()}"
    return raw.upper()


@router.get("/coverage", response_model=List[CoverageResponse])
async def get_data_coverage(
    symbols: Optional[str] = None,  # 逗号分隔的交易对列表
    exchange: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """获取K线数据覆盖情况"""
    try:
        # 确保服务已初始化
        await kline_service.initialize()
        resolved_exchange = _resolve_exchange(db, current_user, exchange)

        # 解析交易对参数
        symbol_list = None
        if symbols:
            symbol_list = [_normalize_request_symbol(s.strip()) for s in symbols.split(",") if s.strip()]

        # 获取覆盖情况
        coverage_data = await kline_service.get_data_coverage(
            symbol_list,
            exchange=resolved_exchange,
        )

        return [CoverageResponse(**item) for item in coverage_data]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get data coverage: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to get data coverage")


@router.get("/backfill-tasks")
async def get_backfill_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """获取补漏任务列表"""
    try:
        tasks = db.query(KlineCollectionTask).filter(
            KlineCollectionTask.user_id == current_user.id
        ).order_by(KlineCollectionTask.created_at.desc()).limit(50).all()
        return {
            "tasks": [
                {
                    "task_id": t.id,
                    "exchange": t.exchange,
                    "symbol": t.symbol,
                    "status": t.status,
                    "progress": t.progress or 0,
                    "total_records": t.total_records or 0,
                    "collected_records": t.collected_records or 0,
                }
                for t in tasks
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get backfill tasks: {e}")
        return {"tasks": []}

@router.get("/data")
async def get_kline_data(
    symbol: str,
    period: str = "1m",
    limit: int = Query(1000, ge=1, le=5000),
    exchange: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    environment: str = Query("mainnet", pattern="^(mainnet|testnet|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """获取本地已采集的 K 线数据，不触发外部交易所请求。"""
    try:
        if period not in VALID_KLINE_PERIODS:
            raise HTTPException(status_code=400, detail="Unsupported period")

        resolved_exchange = _resolve_exchange(db, current_user, exchange)
        symbol_candidates = _safe_symbol_candidates(symbol)
        start_seconds = _normalize_ts(start_ts)
        end_seconds = _normalize_ts(end_ts)
        if start_seconds is not None and end_seconds is not None and start_seconds > end_seconds:
            raise HTTPException(status_code=400, detail="start_ts must be <= end_ts")

        query = db.query(CryptoKline).filter(
            CryptoKline.exchange == resolved_exchange,
            CryptoKline.symbol.in_(symbol_candidates),
            CryptoKline.period == period,
        )
        if environment != "all":
            query = query.filter(CryptoKline.environment == environment)
        if start_seconds is not None:
            query = query.filter(CryptoKline.timestamp >= start_seconds)
        if end_seconds is not None:
            query = query.filter(CryptoKline.timestamp <= end_seconds)

        rows = query.order_by(CryptoKline.timestamp.desc()).limit(limit).all()
        rows = list(reversed(rows))
        data = [
            {
                "timestamp": int(row.timestamp),
                "datetime": row.datetime_str,
                "datetime_str": row.datetime_str,
                "open": float(row.open_price) if row.open_price is not None else None,
                "high": float(row.high_price) if row.high_price is not None else None,
                "low": float(row.low_price) if row.low_price is not None else None,
                "close": float(row.close_price) if row.close_price is not None else None,
                "volume": float(row.volume) if row.volume is not None else None,
                "amount": float(row.amount) if row.amount is not None else None,
                "change": float(row.change) if row.change is not None else None,
                "percent": float(row.percent) if row.percent is not None else None,
                "exchange": row.exchange,
                "symbol": row.symbol,
                "period": row.period,
                "environment": row.environment,
            }
            for row in rows
        ]

        return {
            "success": True,
            "source": "local_db",
            "exchange": resolved_exchange,
            "requested_symbol": symbol,
            "matched_symbol": data[-1]["symbol"] if data else None,
            "period": period,
            "environment": environment,
            "count": len(data),
            "data": data,
            "message": "ok" if data else "No local K-line data found",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get K-line data for local DB request: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to get K-line data")

@router.post("/backfill", response_model=Dict[str, Any])
async def create_backfill_task(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """创建补漏任务"""
    try:
        # 确保服务已初始化
        await kline_service.initialize()

        # 使用显式交易所或当前用户配置的交易所
        exchange = _resolve_exchange(db, current_user, request.exchange)
        if request.period not in VALID_KLINE_PERIODS:
            raise HTTPException(status_code=400, detail="Unsupported period")

        # 验证时间范围
        if request.start_time >= request.end_time:
            raise HTTPException(status_code=400, detail="start_time must be before end_time")

        # 限制时间范围（最多30天）
        max_days = 30
        if (request.end_time - request.start_time).days > max_days:
            raise HTTPException(
                status_code=400,
                detail=f"Time range too large. Maximum {max_days} days allowed."
            )

        # 检查是否有任何任务正在运行（全局只允许一个任务）
        existing_active_task = db.query(KlineCollectionTask).filter(
            KlineCollectionTask.status.in_(["pending", "running"])
        ).first()

        if existing_active_task:
            raise HTTPException(
                status_code=400,
                detail="A backfill task is already running. Please wait for it to complete."
            )

        # 创建补漏任务记录
        task_ids = []
        skipped_symbols = []
        for symbol in request.symbols:
            symbol_upper = _normalize_request_symbol(symbol)

            # 检查是否有相同 symbol 的任务正在运行
            existing_task = db.query(KlineCollectionTask).filter(
                KlineCollectionTask.exchange == exchange,
                KlineCollectionTask.symbol == symbol_upper,
                KlineCollectionTask.status.in_(["pending", "running"])
            ).first()

            if existing_task:
                skipped_symbols.append(symbol_upper)
                continue

            task = KlineCollectionTask(
                user_id=current_user.id,
                exchange=exchange,
                symbol=symbol_upper,
                start_time=request.start_time,
                end_time=request.end_time,
                period=request.period,
                status="pending"
            )
            db.add(task)
            db.flush()  # 获取ID
            task_ids.append(task.id)

        db.commit()

        # 启动后台补漏任务
        backfill_manager = BackfillManager()
        for task_id in task_ids:
            background_tasks.add_task(backfill_manager.process_task, task_id)

        message = f"Created {len(task_ids)} backfill tasks"
        if skipped_symbols:
            message += f". Skipped {len(skipped_symbols)} symbols with existing tasks: {', '.join(skipped_symbols)}"

        return {
            "message": message,
            "task_ids": task_ids,
            "skipped_symbols": skipped_symbols,
            "exchange": exchange,
            "symbols": request.symbols,
            "time_range": f"{request.start_time} to {request.end_time}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create backfill task: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to create backfill task")


@router.get("/backfill/status/{task_id}", response_model=BackfillTaskResponse)
async def get_backfill_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """获取补漏任务状态"""
    try:
        task = db.query(KlineCollectionTask).filter(
            KlineCollectionTask.id == task_id,
            KlineCollectionTask.user_id == current_user.id,
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return _task_response(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task status: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to get task status")


@router.get("/backfill/tasks", response_model=List[BackfillTaskResponse])
async def list_backfill_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """获取补漏任务列表"""
    try:
        query = db.query(KlineCollectionTask).filter(
            KlineCollectionTask.user_id == current_user.id
        )

        if status:
            query = query.filter(KlineCollectionTask.status == status)

        tasks = query.order_by(KlineCollectionTask.created_at.desc()).limit(limit).all()

        return [_task_response(task) for task in tasks]

    except Exception as e:
        logger.error("Failed to list tasks: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to list tasks")


@router.delete("/backfill-tasks/{task_id}")
async def delete_backfill_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """删除补漏任务"""
    try:
        task = db.query(KlineCollectionTask).filter(
            KlineCollectionTask.id == task_id,
            KlineCollectionTask.user_id == current_user.id,
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        db.delete(task)
        db.commit()

        return {"message": f"Task {task_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")


@router.get("/gaps/{symbol}")
async def detect_data_gaps(
    symbol: str,
    days: int = 7,  # 检查最近几天的数据
    exchange: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """检测指定交易对的数据缺失"""
    try:
        # 确保服务已初始化
        await kline_service.initialize()
        resolved_exchange = _resolve_exchange(db, current_user, exchange)

        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # 检测缺失范围
        missing_ranges = await kline_service.detect_missing_ranges(
            symbol.upper(),
            start_time,
            end_time,
            "1m",
            exchange=resolved_exchange,
        )

        return {
            "symbol": symbol.upper(),
            "exchange": resolved_exchange,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "missing_ranges": [
                {
                    "start": range_start.isoformat(),
                    "end": range_end.isoformat(),
                    "duration_minutes": int((range_end - range_start).total_seconds() / 60)
                }
                for range_start, range_end in missing_ranges
            ],
            "total_missing_minutes": sum(
                int((range_end - range_start).total_seconds() / 60)
                for range_start, range_end in missing_ranges
            )
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect gaps for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to detect gaps: {str(e)}")


@router.get("/supported-symbols")
async def get_supported_symbols(
    exchange: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_dependency),
):
    """获取当前交易所支持的交易对"""
    try:
        await kline_service.initialize()
        resolved_exchange = _resolve_exchange(db, current_user, exchange)
        symbols = kline_service.get_supported_symbols(exchange=resolved_exchange)

        return {
            "exchange": resolved_exchange,
            "symbols": symbols,
            "count": len(symbols)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get supported symbols: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get supported symbols: {str(e)}")
