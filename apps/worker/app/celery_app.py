"""Celery application with task autodiscovery."""

import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery("potencjal_worker")

app.config_from_object({
    "broker_url": REDIS_URL,
    "result_backend": REDIS_URL,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "Europe/Warsaw",
    "task_routes": {
        "app.tasks.lookup.*": {"queue": "lookups"},
        "app.tasks.embeddings.*": {"queue": "embeddings"},
        "app.tasks.alerts.*": {"queue": "default"},
    },
    "beat_schedule": {
        "cleanup-expired-snapshots": {
            "task": "app.tasks.maintenance.cleanup_expired_snapshots",
            "schedule": crontab(hour=3, minute=0),
        },
        "refresh-watchlist-companies": {
            "task": "app.tasks.lookup.refresh_watchlist",
            "schedule": crontab(hour=6, minute=0),
        },
    },
})

app.autodiscover_tasks(["app.tasks"])
