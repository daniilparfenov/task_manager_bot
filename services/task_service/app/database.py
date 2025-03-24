from app.config import DB_NAME, MONGO_URI
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(MONGO_URI)
database = client[DB_NAME]
tasks_collection = database.get_collection("tasks")

# Создаем индекс по полю user_id для быстрой фильтрации
tasks_collection.create_index([("user_id", 1)])
