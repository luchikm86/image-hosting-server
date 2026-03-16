import os
import uuid
import logging

# Створюєио об'єкт logger для логування
# __name__ буде "file_handler" — відображатиметься в журналі логування
logger = logging.getLogger(__name__)


# Базовий каталог де знаходиться file_handler.py: src/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Директорія для зображень: на один рівень вище від src/, потім images/
# src/file_handler.py → src/ → project_root/ → images/
IMAGES_DIR = os.path.join(BASE_DIR, "..", "images")


def save_image(file_bytes: bytes, original_filename: str) -> tuple[bool, str]:
    """
    Зберігає файл зображення в каталозі /images з унікальною назвою.

    Чому унікальна назва?

    Якщо два користувачі завантажують "photo.jpg" — другий користувач перезапише першого.
    UUID гарантує, що кожен файл має унікальну назву.

    """
    try:
        # Перевіряємо що каталог зображень існує
        # exist_ok=True — без помилок, якщо каталог вже існує
        os.makedirs(IMAGES_DIR, exist_ok=True)

        # Отримуємо розширення файлу і приводимо до нижнього регістру
        # "my.photo.jpg" → "jpg"
        extension = original_filename.rsplit(".", maxsplit=1)[1].lower()

        # Генеруємо унікальне ім'я файлу за допомогою UUID
        # uuid4() → "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        # hex - повертає унікальне ім'я, але уже без дефісів
        unique_name = uuid.uuid4().hex  # → "a1b2c3d4e5f67890abcdef1234567890"
        filename = f"{unique_name}.{extension}"  # → "a1b2c3d4....jpg"

        # Створюємо повний шлях до файлу
        # Приклад: /project/images/a1b2c3d4....jpg
        filepath = os.path.join(IMAGES_DIR, filename)

        # Запис байті файлу на диск
        # "wb" = write binary
        with open(filepath, "wb") as f:
            f.write(file_bytes)

        logger.info(f"File saved: {filename} (original: {original_filename})")
        return True, filename

    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        return False, f"Failed to save file: {e}"


def delete_image(filename: str) -> tuple[bool, str]:
    """
    Видаляє файл зображення з каталогу /images

    """
    try:
        # Створюємо повний шлях до файлу
        filepath = os.path.join(IMAGES_DIR, filename)

        # Перевіряємо чи існує файл, перш ніж видалити
        if not os.path.exists(filepath):
            logger.warning(f"File not found for deletion: {filename}")
            return False, f"File not found: {filename}"

        # Видаляємо файл
        os.remove(filepath)

        logger.info(f"File deleted: {filename}")
        return True, f"File {filename} deleted successfully"

    except Exception as e:
        logger.error(f"Failed to delete file: {e}")
        return False, f"Failed to delete file: {e}"


def get_image_path(filename: str) -> str | None:
    """
    Повертає повний шлях до зображення, якщо воно існує.

    """
    filepath = os.path.join(IMAGES_DIR, filename)

    # Якщо файл існує, то повертаємо шлях до нього
    if os.path.exists(filepath):
        return filepath

    return None