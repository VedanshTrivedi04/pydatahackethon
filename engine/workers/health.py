"""
Celery Worker Health Check.

Reports worker stats: active tasks, queued tasks, worker status.
Used by the /api/v1/health/detailed endpoint to verify worker health.

Can also be run standalone:
    python -m engine.workers.health
"""

from engine.core.queue.celery_app import celery_app
from engine.utils.logging import get_logger

logger = get_logger(__name__)


def get_worker_stats() -> dict:
    """
    Inspect active Celery workers and return health status.

    Returns:
        Dict with worker_count, active_tasks, queued_tasks, worker_names.
    """
    try:
        inspect = celery_app.control.inspect(timeout=2.0)

        # Active tasks (currently executing)
        active = inspect.active() or {}
        active_task_count = sum(len(tasks) for tasks in active.values())

        # Registered workers
        workers = list(active.keys())

        # Reserved tasks (in worker memory, not yet executing)
        reserved = inspect.reserved() or {}
        reserved_count = sum(len(tasks) for tasks in reserved.values())

        return {
            "status": "healthy" if workers else "no_workers",
            "worker_count": len(workers),
            "worker_names": workers,
            "active_tasks": active_task_count,
            "reserved_tasks": reserved_count,
        }
    except Exception as e:
        logger.warning("worker.health_check_failed", error=str(e))
        return {
            "status": "unreachable",
            "worker_count": 0,
            "worker_names": [],
            "active_tasks": 0,
            "reserved_tasks": 0,
            "error": str(e),
        }


if __name__ == "__main__":
    import json
    stats = get_worker_stats()
    print(json.dumps(stats, indent=2))
