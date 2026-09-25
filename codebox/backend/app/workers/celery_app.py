from celery import Celery

from ..config import get_settings

settings = get_settings()

celery_app = Celery("codebox", broker=settings.redis_url, include=["app.workers.tasks"])
celery_app.conf.update(
    task_ignore_result=True,          # results are stored in PostgreSQL
    task_acks_late=True,              # re-deliver if a worker dies mid-job
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,     # jobs are long; don't hoard them
    task_time_limit=300,
    task_soft_time_limit=240,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=3,
    broker_transport_options={"visibility_timeout": 900},
    # Fail fast when Redis is down so the API can report it instead of hanging
    task_publish_retry_policy={"max_retries": 2, "interval_start": 0,
                               "interval_step": 0.5, "interval_max": 1},
    worker_hijack_root_logger=False,
)
