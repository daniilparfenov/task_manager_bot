# Используем Python как базовый образ
FROM python:3.13

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt /app/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота в контейнер
COPY . /app/

# Запускаем бот
CMD ["python", "bot.py"]
