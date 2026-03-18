# scripts/backup.py

import os
import subprocess
import logging
from datetime import datetime
from dotenv import load_dotenv

# Читаємо змінні з .env файлу
load_dotenv()

# Налаштовуємо логування
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

# Папка для зберігання резервних копій
BACKUPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backups")


def create_backup() -> tuple[bool, str]:
    """
    Створює резервну копію бази даних PostgreSQL за допомогою pg_dump.

    Як працює pg_dump:
    pg_dump підключається до БД і виводить всі дані у вигляді SQL команд.
    Цей файл можна використати для відновлення БД.

    Returns:
        tuple: (success, filepath або error message)
    """
    try:
        # Створюємо папку backups якщо не існує
        os.makedirs(BACKUPS_DIR, exist_ok=True)

        # Генеруємо назву файлу з датою та часом
        # Формат: backup_2025-01-24_153000.sql
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"backup_{timestamp}.sql"
        filepath = os.path.join(BACKUPS_DIR, filename)

        # Читаємо параметри підключення з .env
        db_name = os.getenv("DB_NAME", "images_db")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")

        # Встановлюємо пароль через змінну оточення
        # Це безпечніше ніж передавати пароль в командному рядку
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password

        # Формуємо команду pg_dump
        # pg_dump створює SQL файл з усіма даними БД
        command = [
            "pg_dump",
            "-h", db_host,
            "-p", db_port,
            "-U", db_user,
            "-d", db_name,
            "-f", filepath,
        ]

        logger.info(f"Creating backup: {filename}")

        # Запускаємо pg_dump як subprocess
        # subprocess.run() — запускає зовнішню команду і чекає результату
        result = subprocess.run(
            command,
            env=env,
            capture_output=True,  # захоплюємо stdout і stderr
            text=True             # повертаємо текст замість байтів
        )

        # Перевіряємо чи команда виконалась успішно
        # returncode=0 означає успіх
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return False, result.stderr

        logger.info(f"Backup created successfully: {filepath}")
        return True, filepath

    except FileNotFoundError:
        # pg_dump не знайдено — PostgreSQL не встановлений локально
        error = "pg_dump not found. Make sure PostgreSQL is installed."
        logger.error(error)
        return False, error

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False, str(e)


def list_backups() -> list:
    """
    Повертає список всіх резервних копій.

    Returns:
        list: список словників з інформацією про кожну копію
    """
    if not os.path.exists(BACKUPS_DIR):
        return []

    backups = []
    for filename in sorted(os.listdir(BACKUPS_DIR), reverse=True):
        if filename.endswith(".sql"):
            filepath = os.path.join(BACKUPS_DIR, filename)
            stat = os.stat(filepath)
            backups.append({
                "filename": filename,
                "filepath": filepath,
                "size_kb": round(stat.st_size / 1024, 1),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

    return backups


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🔄 Creating database backup...")

    success, result = create_backup()

    if success:
        print(f"✅ Backup created: {result}")

        # Показуємо список всіх копій
        backups = list_backups()
        print(f"\n📁 Total backups: {len(backups)}")
        for backup in backups:
            print(f"  - {backup['filename']} ({backup['size_kb']} KB) — {backup['created']}")
    else:
        print(f"❌ Backup failed: {result}")