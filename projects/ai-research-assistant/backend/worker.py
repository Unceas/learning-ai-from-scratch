"""Background worker entrypoint for document indexing and outbox event dispatching."""

import logging
import signal
import time

from backend.config import get_settings
from backend.database import SessionLocal
from backend.events.dispatcher import default_dispatcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("research_assistant.worker")

_running = True


def _handle_signal(signum, frame):
    global _running
    logger.info("Shutdown signal received (%s), terminating worker...", signum)
    _running = False


def run_worker_loop():
    """Main worker loop handling outbox dispatch and RQ background tasks."""
    global _running
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    settings = get_settings()
    logger.info("Starting AI Research Assistant background worker (env=%s)...", settings.environment)

    # Check if RQ worker can be spawned
    if settings.redis_url and settings.use_distributed_queue:
        try:
            from backend.jobs.queue import get_redis_connection
            conn = get_redis_connection()
            if conn:
                logger.info("Connected to Redis broker at %s", settings.redis_url)
        except Exception as exc:
            logger.warning("Could not connect to Redis broker: %s", exc)

    logger.info("Worker loop initialized. Ready to process background jobs.")

    while _running:
        try:
            db = SessionLocal()
            try:
                stats = default_dispatcher.dispatch_batch(db, batch_size=20)
                if stats["published"] > 0 or stats["retried"] > 0 or stats["dead_letter"] > 0:
                    logger.info("Dispatched outbox batch: %s", stats)
            finally:
                db.close()
        except Exception as exc:
            logger.error("Error in outbox dispatcher cycle: %s", exc)

        # Sleep with responsive exit
        for _ in range(20):
            if not _running:
                break
            time.sleep(0.1)

    logger.info("Worker shut down cleanly.")


if __name__ == "__main__":
    run_worker_loop()
