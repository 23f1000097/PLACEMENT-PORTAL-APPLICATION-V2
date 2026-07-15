from celery import Celery
from celery.schedules import crontab

from config import Config


celery = Celery(
    "placement_portal",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
    include=["tasks"],
)

celery.conf.update(
    timezone="Asia/Kolkata",
    enable_utc=False,
    beat_schedule={
        "daily-deadline-reminders": {
            "task": "tasks.send_daily_deadline_reminders",
            "schedule": crontab(minute="*/5"),
        },
        "monthly-placement-report": {
            "task": "tasks.generate_monthly_activity_report",
            "schedule": crontab(day_of_month=1, hour=8, minute=0),
        },
    },
)
