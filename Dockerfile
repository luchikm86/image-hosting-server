# ─────────────────────────────────────────────
# Stage 1: Builder
# Встановлюємо залежності окремо від фінального образу
# Це зменшує розмір фінального образу
# ─────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Встановлюємо робочу директорію
WORKDIR /app

# Встановлюємо системні залежності для psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо тільки requirements.txt спочатку
# Docker кешує цей шар — якщо requirements.txt не змінився,
# pip install не запускається знову (швидша збірка)
COPY requirements.txt .

# Встановлюємо залежності в окрему папку
# --no-cache-dir — не зберігаємо кеш pip (менший розмір)
# --prefix=/install — встановлюємо в /install замість системної папки
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────
# Stage 2: Final image
# Копіюємо тільки потрібне з builder
# ─────────────────────────────────────────────
FROM python:3.13-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Встановлюємо libpq для runtime (psycopg2 потребує її)
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо встановлені залежності з builder
COPY --from=builder /install /usr/local

# Копіюємо код застосунку
COPY src/ ./src/

# Створюємо папки для файлів і логів
# Вони будуть перезаписані Docker Volumes але потрібні для запуску
RUN mkdir -p /images /logs

# Вказуємо порт який слухає застосунок
EXPOSE 8000

# Команда запуску сервера
CMD ["python", "src/app.py"]