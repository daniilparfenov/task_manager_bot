from celery import Celery
import requests
import os
from config import REDIS_URL, TELEGRAM_API_TO_SEND_MESSAGE_URL, TASK_SERVICE_URL

# Настройка Celery
celery_app = Celery(
    " ",
    broker=REDIS_URL,
)


@celery_app.task
def send_overdue_deadline_reminder(user_id: str, task_id: str, title: str):
    """Отправка напоминания пользователю через Telegram API"""

    extend_task_response = requests.post(
        f"{TASK_SERVICE_URL}/extend_task/{task_id}", params={"day_count": 1}
    )
    if extend_task_response.status_code != 200:
        raise Exception("Ошибка продления дедлайна задачи")
        return

    text = (
        f'🔔 Дедлайн по задаче "{title}" подошел к концу! Пролонгировано на 1 день'
    )
    payload = {"chat_id": user_id, "text": text}
    try:
        response = requests.post(TELEGRAM_API_TO_SEND_MESSAGE_URL, json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Ошибка при отправке напоминания в Telegram: {e}")
