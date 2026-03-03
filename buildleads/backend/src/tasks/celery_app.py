"""Celery application with beat schedule for background tasks.

Schedule:
  02:00 daily      — collect BZP tenders
  02:30 daily      — collect GUNB building permits
  05:00 daily      — score unscored leads
  06:30 Mon-Fri    — morning digest emails (Phase 4)
  08:00 Mon        — weekly summary emails (Phase 4)
  09:00 daily      — check trial expiry
"""

from celery import Celery
from celery.schedules import crontab

from src.config import settings

app = Celery("buildleads", broker=settings.redis_url, backend=settings.redis_url)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Warsaw",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

app.conf.beat_schedule = {
    "collect-bzp-daily": {
        "task": "src.tasks.collect.collect_bzp",
        "schedule": crontab(hour=2, minute=0),
    },
    "collect-gunb-daily": {
        "task": "src.tasks.collect.collect_gunb",
        "schedule": crontab(hour=2, minute=30),
    },
    "score-new-leads": {
        "task": "src.tasks.scoring.score_unscored_leads",
        "schedule": crontab(hour=5, minute=0),
    },
    "check-trial-expiry": {
        "task": "src.tasks.maintenance.check_trial_expiry",
        "schedule": crontab(hour=9, minute=0),
    },
    # Phase 4 — uncomment when email system is ready:
    # "morning-digest": {
    #     "task": "src.tasks.emails.send_morning_digest",
    #     "schedule": crontab(hour=6, minute=30, day_of_week="1-5"),
    # },
    # "weekly-summary": {
    #     "task": "src.tasks.emails.send_weekly_summary",
    #     "schedule": crontab(hour=8, minute=0, day_of_week="1"),
    # },
}

# Auto-discover tasks in src.tasks package
app.autodiscover_tasks(["src.tasks"])
