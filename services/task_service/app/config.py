import os
from dotenv import load_dotenv

load_dotenv()

# MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:password@mongodb:27017/")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "task_db")
REDIS_URL = os.getenv("REDIS_URL")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL")