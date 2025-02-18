FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Создаем и активируем виртуальное окружение
RUN python -m venv --copies /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем файлы проекта
WORKDIR /app
COPY requirements.txt .
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем бота
CMD ["python", "main.py"] 