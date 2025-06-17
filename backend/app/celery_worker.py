from celery import Celery
import os

# This environment variable setup is a standard Celery convention.
# It helps prevent circular imports when Celery discovers tasks.
os.environ.setdefault('FORKED_BY_CELERY', '1')

# Initialize the Celery application.
# The first argument "tasks" is the conventional name for the main module.
# The broker and backend URLs point to our new Redis container.
# `include=["app.tasks"]` is crucial: it tells Celery to look inside `app/tasks.py`
# to find any functions decorated as tasks.
celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.tasks"]
)

# Optional configuration to make tracking tasks easier.
celery_app.conf.update(
    task_track_started=True,
)