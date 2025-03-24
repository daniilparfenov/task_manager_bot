import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import API_TOKEN
from handlers import register_handlers

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Регистрируем обработчики команд
register_handlers(dp)


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="tasks", description="Показать список задач"),
        BotCommand(command="add_task", description="Добавить новую задачу"),
        BotCommand(command="update_task", description="Изменить существующую задачу"),
        BotCommand(command="delete_task", description="Удалить задачу"),
        BotCommand(
            command="delete_tasks_by_deadline", description="Удалить задачи по дедлайну"
        ),
        BotCommand(command="add_notification", description="Создать напоминание"),
        BotCommand(command="delete_notification", description="Удалить напоминание"),
    ]
    await bot.set_my_commands(commands)


async def main():
    # Удаляем вебхук, если был установлен
    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)
    # Запускаем поллинг
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
