import logging
from datetime import datetime, timedelta

import requests
from app.database import tasks_collection
from app.models import TaskModel
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from .config import NOTIFICATION_SERVICE_URL

router = APIRouter()

from bson import ObjectId


def task_serializer(task) -> dict:
    return {
        "id": str(task["_id"]),
        "user_id": str(task["user_id"]),
        "title": task["title"],
        "description": task.get("description", ""),
        "deadline": task.get("deadline"),
        "completed": task.get("completed", False),
        "notification": task.get("notification", None),
    }


# Получение списка всех задач заданного пользователя
@router.get("/tasks")
async def get_tasks(user_id: int = Query(...)):
    tasks = await tasks_collection.find({"user_id": user_id}).to_list(None)
    logging.exception(f"\n\n{tasks}\n\n")
    return [task_serializer(task) for task in tasks]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    tasks = await tasks_collection.find({"_id": ObjectId(task_id)}).to_list(None)
    logging.exception(f"\n\n{tasks}\n\n")
    return [task_serializer(task) for task in tasks][0]


# Создание новой задачи
@router.post("/tasks")
async def create_task(task: TaskModel):
    task_data = task.dict()
    task_data["created_at"] = datetime.utcnow()
    result = await tasks_collection.insert_one(task_data)
    await schedule_reminder(
        user_id=task_data["user_id"],
        task_id=str(task_data["_id"]),
        title=task_data["title"],
        deadline=str(task_data["deadline"]),
    )
    return {"id": str(result.inserted_id)}


# Обновление задачи
@router.put("/tasks/{task_id}")
async def update_task(task_id: str, update_dict: dict):
    if not update_dict:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    result = await tasks_collection.update_one(
        {"_id": ObjectId(task_id)}, {"$set": update_dict}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    try:
        found = await tasks_collection.find({"_id": ObjectId(task_id)}).to_list(None)

        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/cancel_deadline_reminder/{task_id}"
        )
        response.raise_for_status()

        task = found[0]
        await schedule_reminder(
            task["user_id"], task_id, task["title"], update_dict["deadline"]
        )
    except requests.RequestException as e:
        print("Ошибка отмены уведомления о дедлайне в celery")

    return {"message": "Задача обновлена"}


# Создание напоминания пользователя
@router.post("/notification_reminder")
async def create_notification(task_id: str, user_id: str, title: str, date: str):

    result = tasks_collection.update_one(
        {"_id": ObjectId(task_id)}, {"$set": {"notification": date}}
    )

    payload = {
        "user_id": user_id,
        "task_id": task_id,
        "title": title,
        "date": date,
    }

    try:
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/schedule_notification_reminder", params=payload
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logging.exception(
            f"\nОшибка при отправке запроса в notification_service: {e}\n"
        )


@router.post("/delete_notification_reminder")
async def delete_notification(
    task_id: str,
):

    result = tasks_collection.update_one(
        {"_id": ObjectId(task_id)}, {"$unset": {"notification": "None"}}
    )

    payload = {
        "task_id": task_id,
    }

    try:
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/cancel_notification_reminder/{task_id}",
            params=payload,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logging.exception(
            f"\nОшибка при отправке запроса в notification_service: {e}\n"
        )


# Удаление задачи
@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    logging.exception(f"\n\n{task}\n\n")
    try:
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/cancel_deadline_reminder/{task_id}"
        )
        response.raise_for_status()
        resp = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/cancel_notification_reminder/{task_id}"
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        print("Ошибка отмены уведомления о дедлайне в celery")
    result = await tasks_collection.delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"message": "Задача удалена"}


# Отправляет запрос в notification_service для установки напоминания
async def schedule_reminder(user_id: str, task_id: str, title: str, deadline: str):
    """Отправка запроса в notification_service на напоминание"""
    payload = {
        "user_id": user_id,
        "task_id": task_id,
        "title": title,
        "deadline": deadline,
    }
    try:
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/schedule_deadline_reminder", params=payload
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Ошибка при отправке запроса в notification_service: {e}")


# Пролонгировать задачу
@router.post("/extend_task/{task_id}")
async def extend_task(task_id: str, day_count: int = Query(...)):
    """Продлевает задачу на 1 день после дедлайна"""
    task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    new_deadline = datetime.utcnow() + timedelta(days=day_count)

    await tasks_collection.update_one(
        {"_id": ObjectId(task_id)}, {"$set": {"deadline": new_deadline}}
    )

    # Перезапускаем напоминание для обновленного дедлайна
    await schedule_reminder(
        task["user_id"], task_id, task["title"], new_deadline.isoformat()
    )

    return {"message": f"Дедлайн задачи {task_id} продлен до {new_deadline}"}


@router.delete("/tasks")
async def delete_task_by_deadline(
    user_id: int = Query(...), deadline_time: str = Query(...)
):
    logging.exception(f"user_id: {user_id} \n deadline: {deadline_time}")
    target_date = datetime.strptime(deadline_time, "%Y-%m-%d")
    start_day = datetime(
        target_date.year, target_date.month, target_date.day, 0, 0, 0
    ) - timedelta(hours=3)
    end_day = datetime(
        target_date.year, target_date.month, target_date.day, 23, 59, 59
    ) - timedelta(hours=3)
    logging.exception(f"\n\nstart_day={start_day}, end_day={end_day}\n\n")
    result = await tasks_collection.find(
        {"user_id": user_id, "deadline": {"$gte": start_day, "$lte": end_day}}
    ).to_list()
    for task in result:
        try:
            response = requests.post(
                f"{NOTIFICATION_SERVICE_URL}/cancel_deadline_reminder/{task["_id"]}"
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print("Ошибка отмены уведомления о дедлайне в celery")
    for task in result:
        if "notification" in task:
            try:
                response = requests.post(
                    f"{NOTIFICATION_SERVICE_URL}/cancel_notification_reminder/{task["_id"]}"
                )
                response.raise_for_status()
            except requests.RequestException as e:
                print("Ошибка отмены уведомления о дедлайне в celery")

    logging.exception(f"\n\n{result}\n\n")
    result = await tasks_collection.delete_many(
        {"user_id": user_id, "deadline": {"$gte": start_day, "$lte": end_day}}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"message": "Задачи удалены"}
