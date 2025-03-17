from fastapi import APIRouter, HTTPException, Query
from app.database import tasks_collection
from app.models import TaskModel
from bson import ObjectId
from datetime import datetime

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
    }


# Получение списка всех задач заданного пользователя
@router.get("/tasks")
async def get_tasks(user_id: int = Query(...)):
    tasks = await tasks_collection.find({"user_id": user_id}).to_list(None)
    return [task_serializer(task) for task in tasks]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    tasks = await tasks_collection.find({"_id": ObjectId(task_id)}).to_list(None)
    return [task_serializer(task) for task in tasks][0]


# Создание новой задачи
@router.post("/tasks")
async def create_task(task: TaskModel):
    task_data = task.dict()
    task_data["created_at"] = datetime.utcnow()
    result = await tasks_collection.insert_one(task_data)
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

    return {"message": "Задача обновлена"}


# Удаление задачи
@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    result = await tasks_collection.delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"message": "Задача удалена"}
