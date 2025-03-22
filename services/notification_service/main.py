from fastapi import FastAPI, Query, HTTPException
from celery.result import AsyncResult
import redis
from config import REDIS_URL
from datetime import datetime
from celery_tasks import send_overdue_deadline_reminder, celery_app

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
    redis_client.set(task_id, task.id)
    return {"status": "scheduled", "task_id": task.id}


@app.post("/cancel_deadline_reminder/{task_id}")
async def cancel_deadline_reminder(task_id: str):
    """Отмена задачи Celery по task_id"""

    celery_task_id = redis_client.get(task_id)
    if not celery_task_id:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    celery_task_id = celery_task_id.decode()
    result = AsyncResult(celery_task_id, app=celery_app)
    result.revoke(terminate=True)  # Принудительно отменяем задачу
    redis_client.delete(task_id)

    return {"status": "cancelled", "task_id": task_id}
