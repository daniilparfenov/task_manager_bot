from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI)
database = client[DB_NAME]
tasks_collection = database.get_collection("tasks")

# Создаем индекс по полю user_id для быстрой фильтрации
tasks_collection.create_index([("user_id", 1)])
