import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_TO_SEND_MESSAGE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL")
