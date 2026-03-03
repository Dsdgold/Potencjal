"""Celery app configuration — will be activated in Phase 2 when Redis is added.

Schedule:
  02:00       — collect BZP
  02:30       — collect GUNB
  03:00 Mon   — collect TED
  03:30 Mon   — collect KRS
  04:00       — collect portals
  05:00       — qualify new leads (Ollama)
  06:30 Mon-Fri — morning digest emails
  08:00 Mon   — weekly summary emails
  09:00       — check trial expiry
"""

# Placeholder — Celery will be configured when Redis is added to docker-compose.
#
# from celery import Celery
# from celery.schedules import crontab
#
# app = Celery("buildleads")
# app.config_from_object("src.config")
#
# app.conf.beat_schedule = {
#     "collect-bzp": {
#         "task": "src.tasks.collect.collect_bzp",
#         "schedule": crontab(hour=2, minute=0),
#     },
#     ...
# }
