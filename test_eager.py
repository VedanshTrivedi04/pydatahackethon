import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from engine.core.queue.celery_app import celery_app
print("task_always_eager:", celery_app.conf.task_always_eager)
