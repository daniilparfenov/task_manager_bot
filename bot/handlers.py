import requests
import logging
from aiogram import Router, types
from aiogram.filters import Command
from datetime import datetime, timedelta
from config import TASK_SERVICE_URL
import pytz
from models import TaskModel
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


router = Router()
MOSCOW_TZ = pytz.timezone("Europe/Moscow")


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я твой помощник для управления задачами. Используй команды для взаимодействия."
    )


@router.message(Command("tasks"))
async def cmd_get_tasks(message: types.Message):
    """Получить список задач"""
    try:
        user_id = message.from_user.id
        response = requests.get(
            f"{TASK_SERVICE_URL}/tasks", params={"user_id": user_id}
        )

        response.raise_for_status()  # Проверяем HTTP-ошибки

        tasks_data = response.json()

        now = datetime.now(tz=MOSCOW_TZ)
        overdue_count = 0  # Счетчик просроченных задач

        logging.exception(
            f"\n\n{tasks_data}\n\n"
        )

        if tasks_data:
            task_list = []  # Список строк с задачами
            for task in tasks_data:
                task_id = task.get("id", "N/A")
                title = task.get("title", "Без названия")
                description = task.get("description", "Без описания")
                isCompleted = task.get("completed", False)

                deadline = datetime.fromisoformat(task["deadline"]).astimezone(
                    MOSCOW_TZ
                )
                deadline_str = deadline.strftime("%Y-%m-%d %H:%M")
                if isCompleted:
                    time_left = "🎉 Выполнено, дедлайн уже не важен ;)"
                elif deadline < now:
                    overdue_count += 1
                    time_left = "❌ Просрочено"
                else:
                    days_left = int((deadline - now).total_seconds() // 86400)
                    hours_left = int(((deadline - now).total_seconds() % 86400) // 3600)
                    time_left = f"Осталось: {days_left} д. {hours_left} ч."

                status = "Выполнено" if isCompleted else "Не выполнено"

                task_info = (
                    f"🆔 {task_id} | \n📌 {title}\n"
                    f"📄 {description}\n"
                    f"⏳ {deadline_str}\n"
                    f"⏱ {time_left}\n"
                    f"✅ {status}"
                )

                task_list.append(task_info)
            # Добавляем в начало сообщение о количестве просроченных задач
            deadline_summary = (
                f"❗️Количество просроченных задач: {overdue_count}.\n\n"
                if overdue_count > 0
                else ""
            )
            final_message = deadline_summary + "\n\n".join(task_list)
            await message.answer(final_message)
        else:
            await message.answer("✅ У тебя нет активных задач!")

    except requests.exceptions.RequestException as e:
        await message.answer("❌ Ошибка сервера. Попробуй позже.")
        logging.error(f"Ошибка запроса: {e}")

    except Exception as e:
        await message.answer("❌ Ошибка обработки данных.")
        logging.error(f"Ошибка: {e}")


# Определяем состояние
class TaskForm(StatesGroup):
    title = State()  # Ожидаем название
    user_id = State()  # Ожидаем user_id
    deadline = State()  # Ожидаем дедлайн
    description = State()  # Ожидаем описание задачи


@router.message(Command("add_task"))
async def cmd_add_task(message: types.Message, state: FSMContext):
    """Добавить задачу"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Используйте формат: /add_task task_title deadline (YYYY-MM-DD HH:MM)"
        )
        return

    ans = args[1]
    parts = ans.rsplit(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Используйте формат: /add_task task_title deadline (YYYY-MM-DD HH:MM)"
        )
        return

    task_title, task_deadline = parts[0], parts[1] + " " + parts[2]
    try:
        task_deadline = datetime.strptime(task_deadline, "%Y-%m-%d %H:%M")
        task_deadline = MOSCOW_TZ.localize(task_deadline).astimezone(pytz.UTC)
    except ValueError:
        await message.answer("Неверный формат даты. Используйте: YYYY-MM-DD HH:MM")
        return

    # Сохраняем название и дедлайн в состоянии
    await state.update_data(
        title=task_title, deadline=task_deadline, user_id=message.from_user.id
    )

    # Запрашиваем у пользователя описание
    await message.answer("Отлично! Теперь пришли описание задачи:")
    await state.set_state(TaskForm.description)  # Переключаем состояние


# Обработчик для получения описания задачи
@router.message(TaskForm.description)
async def process_description(message: types.Message, state: FSMContext):
    """Получение описания и отправка в API"""
    task_description = message.text.strip()

    # Получаем сохранённые данные
    user_data = await state.get_data()
    task_title = user_data["title"]
    task_deadline = user_data["deadline"]

    # Отправка данных в API
    task_data = {
        "title": task_title,
        "user_id": user_data["user_id"],
        "description": task_description,
        "deadline": task_deadline.isoformat(),
        "completed": False,
    }

    try:
        response = requests.post(f"{TASK_SERVICE_URL}/tasks", json=task_data)
        if response.status_code == 200:
            await message.answer(f"✅ Задача '{task_title}' добавлена!")
        else:
            await message.answer("❌ Ошибка при добавлении задачи.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

    # Завершаем процесс и очищаем состояние
    await state.clear()


@router.message(Command("delete_task"))
async def cmd_delete_task(message: types.Message):
    """Удалить задачу по ID"""
    try:
        task_id = message.text.removeprefix("/delete_task ").strip()
        response = requests.delete(f"{TASK_SERVICE_URL}/tasks/{task_id}")
        if response.status_code == 200:
            await message.answer(f"Задача с ID {task_id} удалена.")
        else:
            await message.answer(
                "Не удалось удалить задачу. Возможно, такого ID не существует."
            )
    except ValueError:
        await message.answer("Неверный формат ID. Пожалуйста, укажи ID задачи.")
    except Exception as e:
        await message.answer("Ошибка при удалении задачи.")
        logging.error(e)


class UpdateTaskForm(StatesGroup):
    task_id = State()  # ID задачи
    field = State()  # Выбранное поле
    new_value = State()  # Новое значение


@router.message(Command("update_task"))
async def cmd_update_task(message: types.Message, state: FSMContext):
    """Запросить ID задачи"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Используйте формат: /update_task task_id")
        return

    task_id = args[1]

    await state.update_data(task_id=task_id)

    # Создаём inline-клавиатуру с вариантами выбора
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Название", callback_data="title")],
            [types.InlineKeyboardButton(text="Описание", callback_data="description")],
            [types.InlineKeyboardButton(text="Дедлайн", callback_data="deadline")],
            [types.InlineKeyboardButton(text="Статус", callback_data="completed")],
        ]
    )

    await message.answer("Выберите, что хотите изменить:", reply_markup=keyboard)
    await state.set_state(UpdateTaskForm.field)


@router.callback_query(UpdateTaskForm.field)
async def process_field_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора поля"""
    selected_field = callback.data

    await state.update_data(field=selected_field)

    if selected_field == "completed":
        user_data = await state.get_data()
        task_id = user_data["task_id"]
        response = requests.get(f"{TASK_SERVICE_URL}/tasks/{task_id}")
        if response.status_code != 200:
            callback.message.answer(
                "Ошибка при обновлении задач (completed status getting error)"
            )
            return
        task = response.json()
        new_value = not task["completed"]
        update_data = {selected_field: new_value}
        try:
            response = requests.put(
                f"{TASK_SERVICE_URL}/tasks/{task_id}", json=update_data
            )
            if response.status_code == 200:
                await callback.message.answer(f"✅ Задача {task_id} успешно обновлена!")
            else:
                await callback.message.answer("❌ Ошибка при обновлении задачи.")
        except Exception as e:
            await callback.message.answer(f"❌ Ошибка: {str(e)}")

        await state.clear()  # Очистка состояния

    else:
        await callback.message.answer(f"Введите новое значение для {selected_field}:")
        await state.set_state(UpdateTaskForm.new_value)
    await callback.answer()  # Закрываем инлайн-клавиатуру


@router.message(UpdateTaskForm.new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    """Получение нового значения и обновление задачи"""
    user_data = await state.get_data()
    task_id = user_data["task_id"]
    field = user_data["field"]
    new_value = message.text.strip()
    if field == "deadline":
        try:
            new_value = datetime.strptime(new_value, "%Y-%m-%d %H:%M")

            new_value = MOSCOW_TZ.localize(new_value).astimezone(pytz.UTC).isoformat()
        except ValueError:
            await message.answer("Неверный формат даты. Используйте: YYYY-MM-DD HH:MM")
            return

    # Формируем данные для обновления
    update_data = {field: new_value}

    try:
        response = requests.put(f"{TASK_SERVICE_URL}/tasks/{task_id}", json=update_data)
        if response.status_code == 200:
            await message.answer(f"✅ Задача {task_id} успешно обновлена!")
        else:
            await message.answer("❌ Ошибка при обновлении задачи.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

    await state.clear()  # Очистка состояния


def register_handlers(dp):
    """Регистрируем все обработчики команд."""
    dp.include_router(router)


@router.message(Command("delete_task_by_time"))
async def delete_task_by_deadline(message: types.Message):
    """Удаление задачи по указанному дедлайну."""
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    ans = args[1]
    parts = ans.rsplit(maxsplit=2)
    if len(parts) != 1:
        await message.answer(
            "Используйте формат: /add_task task_title deadline (YYYY-MM-DD)"
        )
        return
    try:
        deadline_str = parts[0]
        resp = requests.delete(
            f"{TASK_SERVICE_URL}/tasks", params={"user_id": user_id, "deadline_time": deadline_str}
        )
        if resp.status_code == 200:
            await message.reply(f"Задачи с дедлайном в {deadline_str} удалены.")
        elif resp.status_code == 404:
            await message.reply("Задач с таким дедлайном не найдено.")
        else:
            await message.reply("Произошла ошибка при попытке удаления задачи.")
    except ValueError:
        await message.reply("Неверный формат даты. Используйте формат YYYY-MM-DD")
    except Exception as e:
        await message.answer("Ошибка при удалении задачи.")
        logging.error(e)
