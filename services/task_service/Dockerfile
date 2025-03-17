# Используем Python 3.13
FROM python:3.13

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы
COPY pyproject.toml poetry.lock ./
COPY app ./app

# Устанавливаем Poetry
RUN pip install poetry

# Устанавливаем зависимости
RUN poetry install --no-root

# Запускаем FastAPI
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
