"""
Celery Application Configuration.

Configures the Celery app with:
- Redis as the message broker
- Redis as the result backend
- Task serialization (JSON)
- Task routing by module type
- Retry policies
- Dead-letter queue support via a dedicated DLQ queue
- Worker concurrency and prefetch settings
- Task time limits
- Monitoring via Flower (optional)

This is the ONLY place Celery is configured — never instantiate
celery.Celery() anywhere else in the codebase.
"""

from celery import Celery
from celery.signals import task_failure, task_prerun, task_postrun, task_retry
from kombu import Exchange, Queue

from engine.config.settings import get_settings

settings = get_settings()


# =============================================================================
# Queue Definitions
# =============================================================================

# Exchange — all queues use the same direct exchange
default_exchange = Exchange("shipfaster", type="direct")

# Named queues per task priority/type
QUEUE_DEFAULT = "shipfaster.default"
QUEUE_HIGH_PRIORITY = "shipfaster.high"
QUEUE_LOW_PRIORITY = "shipfaster.low"
QUEUE_DLQ = "shipfaster.dlq"  # Dead Letter Queue

TASK_QUEUES = (
    Queue(QUEUE_HIGH_PRIORITY, default_exchange, routing_key="high"),
    Queue(QUEUE_DEFAULT, default_exchange, routing_key="default"),
    Queue(QUEUE_LOW_PRIORITY, default_exchange, routing_key="low"),
    Queue(QUEUE_DLQ, default_exchange, routing_key="dlq"),
)

# Module → Queue routing map
# Real-time / user-initiated jobs get high priority
# Webhook-triggered batch jobs get default priority
# Analytics/background jobs get low priority
MODULE_QUEUE_MAP: dict[str, str] = {
    "scaffolder": QUEUE_HIGH_PRIORITY,
    "test_generator": QUEUE_HIGH_PRIORITY,
    "docs_generator": QUEUE_DEFAULT,
    "changelog_generator": QUEUE_DEFAULT,
    "notebook_to_blog": QUEUE_LOW_PRIORITY,
}


# =============================================================================
# Celery App Factory
# =============================================================================

def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.

    Returns:
        Fully configured Celery instance.
    """
    app = Celery(
        "shipfaster",
        broker=settings.redis.url,
        backend=settings.redis.url,
        include=[
            "engine.workers.execute_module",
            "engine.workers.retry_handler",
        ],
    )

    # -----------------------------------------------------------------------
    # Core Configuration
    # -----------------------------------------------------------------------
    app.conf.update(
        # Serialization
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,

        # Result TTL — keep results for 24 hours
        result_expires=86400,

        # Task execution
        task_acks_late=True,         # Acknowledge AFTER task completes (not before)
        task_reject_on_worker_lost=True,  # Re-queue if worker crashes mid-task
        worker_prefetch_multiplier=1,    # One task at a time per worker slot (fair dispatch)
        task_always_eager=False,         # Never run synchronously (use celery.chord.apply in tests)

        # Time limits
        task_soft_time_limit=300,    # 5 min soft limit → raises SoftTimeLimitExceeded
        task_time_limit=360,         # 6 min hard limit → kills worker process

        # Queues
        task_queues=TASK_QUEUES,
        task_default_queue=QUEUE_DEFAULT,
        task_default_exchange="shipfaster",
        task_default_routing_key="default",

        # Task routing (module_name → queue)
        task_routes={
            "engine.workers.execute_module.execute_module_task": {
                "queue": QUEUE_DEFAULT,  # Overridden per-call based on module
            },
            "engine.workers.retry_handler.handle_dead_letter": {
                "queue": QUEUE_DLQ,
            },
        },

        # Beat scheduler (not used yet — placeholder for future scheduled jobs)
        beat_schedule={},

        # Worker settings
        worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory leak safety)
        worker_disable_rate_limits=False,
    )

    return app


# Singleton Celery app instance
celery_app = create_celery_app()


# =============================================================================
# Task Signal Handlers (Observability)
# =============================================================================

@task_prerun.connect
def on_task_prerun(task_id: str, task: object, args: tuple, kwargs: dict, **extra: object) -> None:
    """Log task start with task_id and job_id for observability."""
    from engine.utils.logging import get_logger
    logger = get_logger("celery.signals")
    job_id = kwargs.get("job_id", "unknown")
    logger.info(
        "celery.task_started",
        task_id=task_id,
        task_name=getattr(task, "name", "unknown"),
        job_id=job_id,
    )


@task_postrun.connect
def on_task_postrun(
    task_id: str, task: object, args: tuple, kwargs: dict,
    retval: object, state: str, **extra: object
) -> None:
    """Log task completion with final state."""
    from engine.utils.logging import get_logger
    logger = get_logger("celery.signals")
    job_id = kwargs.get("job_id", "unknown")
    logger.info(
        "celery.task_completed",
        task_id=task_id,
        task_name=getattr(task, "name", "unknown"),
        job_id=job_id,
        state=state,
    )


@task_failure.connect
def on_task_failure(
    task_id: str, exception: Exception, args: tuple,
    kwargs: dict, traceback: object, einfo: object, **extra: object
) -> None:
    """Log task failure with exception details."""
    from engine.utils.logging import get_logger
    logger = get_logger("celery.signals")
    job_id = kwargs.get("job_id", "unknown")
    logger.error(
        "celery.task_failed",
        task_id=task_id,
        job_id=job_id,
        exc_type=type(exception).__name__,
        exc_message=str(exception),
    )


@task_retry.connect
def on_task_retry(
    request: object, reason: object, einfo: object, **extra: object
) -> None:
    """Log task retry with reason."""
    from engine.utils.logging import get_logger
    logger = get_logger("celery.signals")
    logger.warning(
        "celery.task_retrying",
        task_id=getattr(request, "id", "unknown"),
        reason=str(reason),
        retries=getattr(request, "retries", 0),
    )
