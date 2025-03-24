from datetime import datetime

import redis
from celery.result import AsyncResult
from celery_tasks import (celery_app, send_notification_reminder,
                          send_overdue_deadline_reminder)
from config import REDIS_URL
from fastapi import FastAPI, HTTPException, Query

app = FastAPI()
redis_client = redis.from_url(REDIS_URL)


@app.post("/schedule_deadline_reminder")
async def schedule_deadline_reminder(
    user_id: str = Query(...),
    task_id: str = Query(...),
    title: str = Query(...),
    deadline: str = Query(...),
):
    """Добавляет задачу в очередь Celery с отложенным выполнением"""
    eta = datetime.fromisoformat(deadline)
    task = send_overdue_deadline_reminder.apply_async(
        args=[user_id, task_id, title], eta=eta
    )

    # Сохраняем соответствие task_id -> celery_task_id в Redis
    redis_client.set(f"deadline{task_id}", task.id)
    return {"status": "scheduled", "task_id": task.id}


@app.post("/cancel_deadline_reminder/{task_id}")
async def cancel_deadline_reminder(task_id: str):
    """Отмена задачи Celery по task_id"""

    celery_task_id = redis_client.get(f"deadline{task_id}")
    if not celery_task_id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    celery_task_id = celery_task_id.decode()
    result = AsyncResult(celery_task_id, app=celery_app)
    result.revoke(terminate=True)  # Принудительно отменяем задачу
    redis_client.delete(task_id)

    return {"status": "cancelled", "task_id": task_id}


@app.post("/cancel_notification_reminder/{task_id}")
async def cancel_notification_reminder(task_id: str):
    """Отмена задачи Celery по task_id"""

    celery_task_id = redis_client.get(f"notification{task_id}")
    if not celery_task_id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    celery_task_id = celery_task_id.decode()
    result = AsyncResult(celery_task_id, app=celery_app)
    result.revoke(terminate=True)  # Принудительно отменяем задачу
    redis_client.delete(task_id)

    return {"status": "cancelled", "task_id": task_id}


@app.post("/schedule_notification_reminder")
async def schedule_notification_reminder(
    user_id: str = Query(...),
    task_id: str = Query(...),
    title: str = Query(...),
    date: str = Query(...),
):
    """Добавляет задачу в очередь Celery с отложенным выполнением"""
    eta = datetime.fromisoformat(date)
    task = send_notification_reminder.apply_async(args=[user_id, title], eta=eta)

    # Сохраняем соответствие task_id -> celery_task_id в Redis
    redis_client.set(f"notification{task_id}", task.id)
    return {"status": "scheduled", "task_id": task.id}
