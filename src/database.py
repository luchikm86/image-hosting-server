# src/database.py

import os
import logging
import psycopg2
from dotenv import load_dotenv

# Читаємо змінні з .env файлу
load_dotenv()

# Створюємо об'єкт logger для цього модуля
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────────

def get_connection():
    """
    Створює і повертає підключення до PostgreSQL локально.

    """
    return psycopg2.connect(
        dbname=os.getenv("POSTGRES_DB", "images_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )


def test_connection() -> bool:
    """
    Перевіряє чи є підключення до PostgreSQL.
    Викликається при старті сервера.

    Returns:
        True якщо підключення успішне, False якщо ні
    """
    try:
        conn = get_connection()
        conn.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


# ─────────────────────────────────────────────
# TABLE INITIALIZATION
# ─────────────────────────────────────────────

def init_db():
    """
    Створює таблицю images якщо вона ще не існує.
    Викликається при старті сервера.

    IF NOT EXISTS — безпечно запускати кілька разів,
    таблиця не буде перестворена якщо вже існує.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Створюємо таблицю images
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id            SERIAL PRIMARY KEY,
                filename      TEXT    NOT NULL,
                original_name TEXT    NOT NULL,
                size          INTEGER NOT NULL,
                upload_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_type     TEXT    NOT NULL
            )
        """)

        # Зберігаємо зміни в БД
        conn.commit()

        cursor.close()
        conn.close()

        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


# ─────────────────────────────────────────────
# IMAGE METADATA OPERATIONS
# ─────────────────────────────────────────────

def save_image_metadata(
    filename: str,
    original_name: str,
    size: int,
    file_type: str
) -> int | None:
    """
    Зберігає метадані зображення в БД після збереження файлу.

    Args:
        filename:      унікальна назва файлу (згенерована uuid)
        original_name: оригінальна назва від користувача
        size:          розмір файлу в байтах
        file_type:     розширення файлу (jpg, png, gif)

    Returns:
        id новго запису або None якщо помилка
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # INSERT і одразу повертаємо id нового запису
        # RETURNING id — PostgreSQL повертає id після вставки
        cursor.execute("""
            INSERT INTO images (filename, original_name, size, file_type)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (filename, original_name, size, file_type))

        # fetchone() повертає перший рядок результату
        # result = (42,) — кортеж з одним елементом
        result = cursor.fetchone()
        image_id = result[0]

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Metadata saved: id={image_id} filename={filename}")
        return image_id

    except Exception as e:
        logger.error(f"Failed to save metadata: {e}")
        return None


def get_images(page: int = 1, per_page: int = 10) -> tuple[list, int]:
    """
    Повертає список зображень з пагінацією.

    Args:
        page:     номер сторінки (починається з 1)
        per_page: кількість зображень на сторінці

    Returns:
        tuple: (список зображень, загальна кількість)

    Як працює пагінація:
        page=1 → OFFSET=0  → перші 10 записів
        page=2 → OFFSET=10 → записи 11-20
        page=3 → OFFSET=20 → записи 21-30
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Рахуємо загальну кількість зображень
        cursor.execute("SELECT COUNT(*) FROM images")
        total = cursor.fetchone()[0]

        # Рахуємо offset для пагінації
        # page=1 → offset=0
        # page=2 → offset=10
        offset = (page - 1) * per_page

        # Отримуємо зображення для поточної сторінки
        cursor.execute("""
            SELECT id, filename, original_name, size, upload_time, file_type
            FROM images
            ORDER BY upload_time DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

        # Перетворюємо рядки в список словників
        # cursor.fetchall() → [(1, "a1b2.jpg", "photo.jpg", 1024, ...), ...]
        rows = cursor.fetchall()
        images = []
        for row in rows:
            images.append({
                "id":            row[0],
                "filename":      row[1],
                "original_name": row[2],
                "size":          row[3],
                "upload_time":   row[4].strftime("%Y-%m-%d %H:%M:%S"),
                "file_type":     row[5],
                "url":           f"/images/{row[1]}"
            })

        cursor.close()
        conn.close()

        return images, total

    except Exception as e:
        logger.error(f"Failed to get images: {e}")
        return [], 0


def delete_image_metadata(image_id: int) -> tuple[bool, str]:
    """
    Видаляє метадані зображення з БД по id.
    Фізичний файл видаляє file_handler.py окремо.

    Args:
        image_id: id запису в таблиці images

    Returns:
        tuple: (success, filename або error)
        filename потрібен щоб file_handler знав який файл видалити
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Спочатку отримуємо filename щоб потім видалити файл
        cursor.execute(
            "SELECT filename FROM images WHERE id = %s",
            (image_id,)
        )
        result = cursor.fetchone()

        # Якщо запис не знайдено — повертаємо помилку
        if not result:
            cursor.close()
            conn.close()
            return False, f"Image with id={image_id} not found"

        filename = result[0]

        # Видаляємо запис з БД
        cursor.execute(
            "DELETE FROM images WHERE id = %s",
            (image_id,)
        )

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Metadata deleted: id={image_id} filename={filename}")
        return True, filename

    except Exception as e:
        logger.error(f"Failed to delete metadata: {e}")
        return False, str(e)


if __name__ == "__main__":
    # Налаштовуємо логування для тесту
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s"
    )

    print("Testing database connection...")
    if test_connection():
        print("✅ Connection OK")
        init_db()
        print("✅ Table created")
    else:
        print("❌ Connection failed")