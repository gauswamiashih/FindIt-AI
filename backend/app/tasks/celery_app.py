"""
Celery Application Initialization
Configures Celery with Redis broker and result backend.
"""

from celery import Celery
from app.core.config import settings
import logging

logger = logging.getLogger("findit.celery")

redis_url = settings.REDIS_URL or "redis://localhost:6379/0"

celery_app = Celery(
    "findit_tasks",
    broker=redis_url,
    backend=redis_url,
    include=["app.tasks.matching_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300, # 5 minutes max
    result_expires=3600, # 1 hour
)
