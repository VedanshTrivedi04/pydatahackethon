"""
Background Scheduler (Mock Demo Implementation).

Replaces Celery Beat for the demo. Runs inside the FastAPI event loop
to simulate cron tasks like resetting limits or cleaning up old jobs.
"""

import asyncio
from typing import NoReturn

from engine.utils.logging import get_logger

logger = get_logger(__name__)

async def run_scheduler() -> NoReturn:
    """
    Infinite loop that runs background maintenance tasks periodically.
    """
    logger.info("Demo Background Scheduler started.")
    
    while True:
        try:
            # Simulate a 24-hour cron that runs every 60 seconds in the demo
            await asyncio.sleep(60)
            
            logger.info("Scheduler: Running mock nightly maintenance...")
            
            # Example tasks that would run here:
            # - Reset token buckets for Rate Limiting
            # - Sync limits from Stripe/Billing
            # - Cleanup orphaned Sandbox containers
            # - Database nightly backup trigger
            
            logger.info("Scheduler: Nightly maintenance completed.")
            
        except asyncio.CancelledError:
            logger.info("Demo Background Scheduler shutting down.")
            raise
        except Exception as e:
            logger.error("Scheduler encountered an error", error=str(e))
            # Sleep briefly to avoid tight crash loops
            await asyncio.sleep(5)
