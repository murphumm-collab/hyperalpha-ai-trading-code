"""
System Log API Routes
提供系统日志查询接口
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from api.auth_utils import get_admin_user_dependency
from database.models import User
from services.system_logger import system_logger

router = APIRouter(prefix="/api/system-logs", tags=["System Logs"])

SYSTEM_LOG_CATEGORIES = ["price_update", "ai_decision", "system_error", "admin_audit"]
SYSTEM_LOG_LEVELS = ["INFO", "WARNING", "ERROR"]


@router.get("/")
async def get_system_logs(
    level: Optional[str] = Query(None, description="日志级别过滤: INFO, WARNING, ERROR"),
    category: Optional[str] = Query(None, description="日志分类过滤: price_update, ai_decision, system_error"),
    limit: int = Query(100, ge=1, le=500, description="返回的最大日志数量"),
    current_user: User = Depends(get_admin_user_dependency),
) -> Dict[str, Any]:
    """
    获取系统日志列表

    参数:
    - level: 过滤日志级别 (INFO, WARNING, ERROR)
    - category: 过滤日志分类 (price_update, ai_decision, system_error)
    - limit: 返回的最大日志数量 (1-500)

    返回:
    - logs: 日志列表
    - total: 返回的日志数量
    """
    min_level = None if level else "WARNING"
    logs = system_logger.get_logs(
        level=level,
        category=category,
        limit=limit,
        min_level=min_level,
    )
    return {
        "logs": logs,
        "total": len(logs)
    }


@router.get("/categories")
async def get_log_categories(
    current_user: User = Depends(get_admin_user_dependency),
) -> Dict[str, List[str]]:
    """
    获取可用的日志分类和级别

    返回:
    - categories: 日志分类列表
    - levels: 日志级别列表
    """
    return {
        "categories": SYSTEM_LOG_CATEGORIES,
        "levels": SYSTEM_LOG_LEVELS
    }


@router.delete("/")
async def clear_system_logs(
    current_user: User = Depends(get_admin_user_dependency),
) -> Dict[str, str]:
    """
    清空所有系统日志

    返回:
    - message: 操作结果消息
    """
    system_logger.clear_logs()
    return {"message": "All system logs cleared successfully"}


@router.get("/stats")
async def get_log_stats(
    current_user: User = Depends(get_admin_user_dependency),
) -> Dict[str, Any]:
    """
    获取日志统计信息

    返回:
    - total_logs: 总日志数量
    - by_level: 按级别分组的统计
    - by_category: 按分类分组的统计
    """
    all_logs = system_logger.get_logs(limit=500, min_level="WARNING")

    stats = {
        "total_logs": len(all_logs),
        "by_level": {
            level: 0 for level in SYSTEM_LOG_LEVELS
        },
        "by_category": {
            category: 0 for category in SYSTEM_LOG_CATEGORIES
        }
    }

    for log in all_logs:
        level = log.get("level", "INFO")
        category = log.get("category", "system_error")

        if level in stats["by_level"]:
            stats["by_level"][level] += 1
        if category in stats["by_category"]:
            stats["by_category"][category] += 1

    return stats
