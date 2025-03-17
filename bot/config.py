import os

# Получаем токен бота из переменных окружения
API_TOKEN = os.getenv("TELEGRAM_TOKEN")

# URL для взаимодействия с сервисом задач (API task_service)
TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL")

# URL для подключения к Redis (если нужно для очередей/отложенных задач)
REDIS_URL = os.getenv("REDIS_URL")
