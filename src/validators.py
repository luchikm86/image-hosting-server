
import os
import logging
from PIL import Image
import io

# Get logger for this module
# __name__ will be "validators" — visible in log output
logger = logging.getLogger(__name__)

# Набор дозволених розширень файлів
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

# Максимальний розмір: 5MB (в байтах)
# 5 * 1024 * 1024 = 5,242,880 bytes
MAX_FILE_SIZE = 5 * 1024 * 1024


def validate_extension(filename: str) -> tuple[bool, str]:
    """
    Перевіряємо чи дозволено використовувати файл з таким розширенням

    """

    # Отримуємо розширення з назви файлу
    # rsplit розбиваю праворуч, а maxsplit=1 вказує що розділення буде лише один раз
    # "photo.jpg" → ["photo", "jpg"] → "jpg"
    parts = filename.rsplit(".", maxsplit=1)

    # Перевіряємо чи у файла взагалі є розширення
    if len(parts) < 2:
        logger.warning(f"File has no extension: {filename}")
        return False, "File has no extension"

    # Отримуємо розширення файлу і переведення його в нижній регістр
    # "photo.JPG" → "jpg"
    extension = parts[1].lower()

    # Перевіярємо наявність розширення файлу в нашому наборі
    if extension not in ALLOWED_EXTENSIONS:
        logger.warning(f"Invalid extension: {extension} — file: {filename}")
        return False, f"File type '.{extension}' is not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

    return True, ""


def validate_size(file_size: int) -> tuple[bool, str]:
    """
    Перевіряємо розмір файлу, чи знаходиться він в межах дозволеного ліміту.

    """
    # Перевіряємо розмір файлу.
    # Якщо файл більше ніж 5 МБ, то ми заходимо в if
    if file_size > MAX_FILE_SIZE:
        # Перетворюємо байти в МБ, щоб видати помилку про те що розмір файлу більше ніж дозволено
        size_mb = file_size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        logger.warning(f"File too large: {size_mb:.1f}MB (max {max_mb}MB)")
        return False, f"File size {size_mb:.1f}MB exceeds maximum {max_mb:.0f}MB"

    return True, ""


def validate_image_content(file_bytes: bytes) -> tuple[bool, str]:
    """
    Перевірте, чи файл справді є справжнім зображенням, за допомогою Pillow.

    Навіщо це потрібно?
    Користувач може перейменувати "virus.exe" на "virus.jpg" та обійти перевірку розширення.
    Pillow фактично відкриває файл та перевіряє, чи містить він дійсні дані зображення.

    """
    try:
        # BytesIO обгортаю байти в файлоподібний об'єкт
        image_stream = io.BytesIO(file_bytes)

        # Image.open() — тільки читає заголовок файлу
        # Швидко, але не перевіряє весь файл
        image = Image.open(image_stream)

        # verify() сканує внутрішню структуру файлу.
        # Повертає помилку якщо файл пошкоджений або якщо це не справжнє зображення
        image.verify()

        return True, ""

    except Exception as e:
        logger.warning(f"File is not a valid image: {e}")
        return False, "File is not a valid image"


def validate_image(filename: str, file_size: int, file_bytes: bytes) -> tuple[bool, str]:
    """
    Головна функція — запускає всі три перевірки по черзі.

    На першій помилці зупиняється

    """
    # Check 1: Перевіряємо розширення файлу
    is_valid, error = validate_extension(filename)
    if not is_valid:
        return False, error

    # Check 2: Перевіряємо розмір файлу
    is_valid, error = validate_size(file_size)
    if not is_valid:
        return False, error

    # Check 3: Перевіряємо чи це справжнє фото (Pillow)
    is_valid, error = validate_image_content(file_bytes)
    if not is_valid:
        return False, error

    # Усі перевірки пройдено успішно
    logger.info(f"File validated successfully: {filename} ({file_size} bytes)")
    return True, ""