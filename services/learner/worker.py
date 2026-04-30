import os
from celery import Celery

redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
app = Celery("learner", broker=redis_url, backend=redis_url)
app.conf.task_routes = {
    "trigger_learning": {"queue": "learning"},
}
