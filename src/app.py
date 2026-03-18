from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import math
import os
import logging
import email
import email.parser
from dotenv import load_dotenv
from validators import validate_image
from file_handler import save_image
from database import init_db, save_image_metadata, get_images, delete_image_metadata

# Читаємо файл .env для роботи з ним
load_dotenv()


# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────

# Шлях до log файла з .env, значення за замовчуванням якщо шлях буде відсутній
LOG_FILE = os.getenv("LOG_FILE", "../logs/app.log")

# Створюємо директорію. Якщо вона була створена і exist_ok=True, тоді не виникає помилки
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Налаштовуємо систему логування:
# - level=INFO: пише INFO, WARNING, ERROR (пропускає DEBUG)
# - format: як буде виглядати рядок нашого журналу логування
# - handlers: одночасно пише в журнал логування та дублює в термінал
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        # FileHandler записує logs у файл app.log
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        # StreamHandler виводить логи в термінал
        logging.StreamHandler(),
    ],
)

# Створює іменований об'єкт логера для цього файлу, щоб в логах було видно звідки прийшло кожне повідомлення
# __name__ - це вбудована змінна Python яка містить назву поточного модуля.
# В даному випадку __name__ буде "app"
logger = logging.getLogger(__name__)

# Базовий каталог, де знаходиться app.py: src/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Каталог шаблонів: src/templates/
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Каталог статичних файлів: src/static/
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ─────────────────────────────────────────────
# REQUEST HANDLER
# ─────────────────────────────────────────────

class ImageServerHandler(BaseHTTPRequestHandler):
    """
    Головний обробник HTTP запитів для сервера зображень

    Цей клас успадковується від BaseHTTPRequestHandler.
    Для кожного методу HTTP (GET, POST) ми визначаємо метод:
        do_GET()  → обробляє всі GET запити
        do_POST() → обробляє всі POST запити

    """

    def do_GET(self):
        """
        Обробляє всі GET запити від браузера.
        Визначає який марршрут викликати по self.path.
        """
        # Якщо URL починається з /static/, то відправляємо файл браузеру у відповідь на запит (css, js, img)
        # Видаляємо префікс /static/, щоб отримати відносний шлях до файлу.
        # Приклад "/static/css/style.css" → "css/style.css"
        if self.path.startswith("/static/"):
            static_path = self.path[len("/static/"):]
            self._serve_static(static_path)

        # Головна сторінка
        elif self.path == "/":
            self._serve_html("index.html")

        # Сторінка завантаження зображень
        elif self.path == "/upload":
            self._serve_html("upload.html")

        # Сторінка списку зображень
        elif self.path == "/images-list":
            self._serve_html("images.html")

        # Перевірка стану сервера (використовуємо інструмент Docker Healthcheck)
        elif self.path == "/health":
            self._handle_health()

        # API маршрут, який повертає список всіх зображень з БД
        elif self.path.startswith("/api/images"):
            self._handle_images_list()

        # Роздає фізичний файл зображення з папки /images
        # Приклад: "/images/a1b2c3.jpg" → "a1b2c3.jpg"
        elif self.path.startswith("/images/"):
            filename = self.path[len("/images/"):]
            self._serve_image(filename)

        # Якщо маршрут невідомий, то повертаємо 404
        else:
            self._send_json(
                status_code=404,
                data={"error": "Route not found", "path": self.path}
            )
            logger.warning(f"404 Not Found: {self.path}")

    def do_POST(self):
        """
        Функція обробляє POST запити від браузера.
        POST використовується для дій, які змінюють дані сервера:
            - POST /upload      →   завантаження зображення
            - POST /delete/id   →   видалення зображення
        """
        # Завантажуємо нове зображення на сервер
        if self.path == "/upload":
            self._handle_upload()

        # Видаляємо зображення по id
        # Приклад "/delete/12" → image_id = "12"
        elif self.path.startswith("/delete/"):
            image_id = self.path[len("/delete/"):]
            self._handle_delete(image_id)
        # Якщо маршрут невідомий, то повертаємо 404
        else:
            self._send_json(
                status_code=404,
                data={"error": "Route not found", "path": self.path}
            )
            logger.warning(f"404 Not Found: {self.path}")

    def _handle_upload(self):
        """
        Обробляє завантаження зображення на сервер.

        Кроки обробки:
            1. Парсимо multipart/form-data запит через email.parser
            2. Валідуємо файл (розширення, розмір, вміст)
            3. Зберігаємо файл на диск
            4. Зберігаємо метадані в PostgreSQL
            5. Повертаємо JSON відповідь з URL файлу
        Використовує email.parser для парсингу multipart/form-data
        """
        try:
            # Читаємо Content-Type з заголовків запиту
            # Приклад: "multipart/form-data; boundary=----WebKitBoundary123"
            content_type = self.headers.get("Content-Type", "")

            # Перевіряємо що запит містить файл (multipart)
            if "multipart/form-data" not in content_type:
                self._send_json(
                    status_code=400,
                    data={"error": "Expected multipart/form-data request"}
                )
                logger.warning("Upload attempt without multipart/form-data")
                return

            # Читаємо розмір тіла запиту з заголовків
            # Content-Length каже скільки байтів очікувати
            content_length = int(self.headers.get("Content-Length", 0))

            # Читаємо тіло запиту (сирі байти)
            body = self.rfile.read(content_length)

            # email.parser парсить multipart дані
            # Додаємо Content-Type як заголовок щоб парсер знав boundary
            msg = email.message_from_bytes(
                b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + body
            )

            # Шукаємо поле "file" серед всіх частин multipart
            file_data = None
            original_filename = None

            for part in msg.walk():
                # Отримуємо Content-Disposition заголовок частини
                # Приклад: 'form-data; name="file"; filename="photo.jpg"'
                disposition = part.get("Content-Disposition", "")

                # Шукаємо частину з name="file"
                if 'name="file"' in disposition:
                    # Отримуємо назву файлу
                    # filename="photo.jpg" → "photo.jpg"
                    for param in disposition.split(";"):
                        param = param.strip()
                        if param.startswith("filename="):
                            original_filename = param.split("=", 1)[1].strip('"')

                    # Отримуємо байти файлу
                    file_data = part.get_payload(decode=True)
                    break

            # Перевіряємо чи знайшли поле file
            if file_data is None or original_filename is None:
                self._send_json(
                    status_code=400,
                    data={"error": "No file field found in request"}
                )
                logger.warning("Upload attempt without file field")
                return

            # Перевіряємо чи файл не порожній
            if not original_filename:
                self._send_json(
                    status_code=400,
                    data={"error": "No file selected"}
                )
                return

            file_bytes = file_data
            file_size = len(file_bytes)

            # Крок 1: Валідація файлу
            is_valid, error = validate_image(original_filename, file_size, file_bytes)
            if not is_valid:
                self._send_json(status_code=400, data={"error": error})
                logger.warning(f"Validation failed: {error}")
                return

            # Крок 2: Зберігаємо файл на диск
            success, result = save_image(file_bytes, original_filename)
            if not success:
                self._send_json(status_code=500, data={"error": result})
                logger.error(f"Save failed: {result}")
                return

            # Крок 3: Зберігаємо метадані в БД
            file_type = original_filename.rsplit(".", 1)[1].lower()
            image_id = save_image_metadata(
                filename=result,
                original_name=original_filename,
                size=file_size,
                file_type=file_type
            )

            if image_id is None:
                logger.warning("File saved but metadata not saved to DB")

            # Крок 4: Повертаємо успішну відповідь з URL файлу
            file_url = f"/images/{result}"
            self._send_json(
                status_code=200,
                data={
                    "message": "Image uploaded successfully",
                    "filename": result,
                    "original_name": original_filename,
                    "url": file_url,
                    "size": file_size
                }
            )
            logger.info(f"Upload success: {result} (original: {original_filename})")

        except Exception as e:
            logger.error(f"Upload error: {e}")
            self._send_json(
                status_code=500,
                data={"error": "Internal server error"}
            )

    def _handle_images_list(self):
        """
        Повертає JSON список зображень з БД з пагінацією.

        Підтримує параметр page в URL:
            GET /api/images        → сторінка 1
            GET /api/images?page=2 → сторінка 2
        """
        # Отримуємо номер сторінки з URL параметра ?page=N
        # Якщо параметр відсутній або невалідний — використовуємо сторінку 1
        # /api/images?page=2 → page=2
        page = 1
        if "?" in self.path:
            query = self.path.split("?")[1]
            for param in query.split("&"):
                if param.startswith("page="):
                    try:
                        page = int(param.split("=")[1])
                    except ValueError:
                        page = 1

        # Отримуємо зображення з БД для поточної сторінки
        images, total = get_images(page=page, per_page=10)

        # Рахуємо загальну кількість сторінок
        # math.ceil округлює вгору: 11 зображень / 10 = 1.1 → 2 сторінки
        total_pages = math.ceil(total / 10) if total > 0 else 1

        self._send_json(status_code=200, data={
            "images": images,
            "page": page,
            "total": total,
            "total_pages": total_pages
        })
        logger.info(f"GET /api/images?page={page} — returned {len(images)}/{total}")

    def _serve_image(self, filename: str):
        """
        Роздає фізичний файл зображення з папки /images.
        Захист від path traversal атаки
        """

        # "../../../etc/passwd" → відхиляємо ❌
        if ".." in filename or "/" in filename:
            self._send_json(status_code=400, data={"error": "Invalid filename"})
            return

        images_dir = os.path.join(BASE_DIR, "..", "images")
        filepath = os.path.join(images_dir, filename)

        # Перевіряємо чи файл існує
        if not os.path.exists(filepath):
            self._send_json(status_code=404, data={"error": "Image not found"})
            logger.warning(f"Image not found: {filename}")
            return

        # Визначаємо тип контенту по розширенню
        extension = filename.rsplit(".", 1)[-1].lower()
        content_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
        }
        content_type = content_types.get(extension, "application/octet-stream")

        # Читаємо і відправляємо файл
        with open(filepath, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

        logger.info(f"GET /images/{filename} — served")

    def _handle_delete(self, image_id: str):
        """
        Видаляє зображення з БД і з диску по id.
        Спочатку видаляє метадані з БД, потім фізичний файл.
        """
        # Перевіряємо що id — це число
        try:
            image_id = int(image_id)
        except ValueError:
            self._send_json(status_code=400, data={"error": "Invalid image id"})
            return

        # Крок 1: Видаляємо метадані з БД і отримуємо filename
        success, result = delete_image_metadata(image_id)
        if not success:
            self._send_json(status_code=404, data={"error": result})
            return

        # Крок 2: Видаляємо фізичний файл
        filename = result
        from file_handler import delete_image
        success, message = delete_image(filename)
        if not success:
            logger.warning(f"Metadata deleted but file not found: {filename}")

        self._send_json(status_code=200, data={"message": f"Image {image_id} deleted"})
        logger.info(f"Deleted image id={image_id} filename={filename}")

    def _handle_health(self):
        """
        Перевірка стану сервера.
        Docker використовує цей маршрут для healthcheck контейнера.
        """
        self._send_json(
            status_code=200,
            data={"status": "ok", "server": "ImageServer/1.0"}
        )
        logger.info("GET /health — health check passed")

    def _send_json(self, status_code: int, data:dict):
        """
        Допоміжний метод для відправки JSON відповіді браузеру.
        Кожна відповідь складається з трьох кроків:
            1. Статус код (200, 404, 500...)
            2. Заголовки (Content-Type, Content-Length)
            3. Тіло відповіді (JSON дані)
        """
        # Перетворюємо dict в JSON рядок
        body = json.dumps(data, ensure_ascii=False, indent=2)

        # Перетворюємо JSON рядок в байти (string → bytes)
        body_bytes = body.encode("utf-8")

        # Step 1: Відправляємо статус код: "HTTP/1.1 200 OK"
        self.send_response(status_code)

        # Step 2: Відправка headers
        # Content-Type повідомляє браузеру: "це JSON, а не HTML"
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # Content-Length повідомляє браузеру скільки очікувати байтів
        self.send_header("Content-Length", str(len(body_bytes)))
        # Говоримо браузеру що після відповіді з'єднання закривається
        self.send_header("Connection", "close")
        # end_headers() відправляємо порожній рядок - цього вимагає HTTP протокол
        self.end_headers()

        # Step 3: Відправляємо відповідь в браузер
        self.wfile.write(body_bytes)
        # Примусово відправляємо всі байти з буфера
        self.wfile.flush()

    def _serve_html(self, filename: str):
        """
        Читає HTML файл з папки templates і відправляє браузеру.
        """
        # Створюємо повний шлях до HTML файлу
        # Приклад: /Users/.../src/templates/index.html
        filepath = os.path.join(TEMPLATES_DIR, filename)

        # Перевіряємо чи файл існує. Якщо файл відсутній, то повертаємо 404
        if not os.path.exists(filepath):
            self._send_json(
                status_code=404,
                data={"error": f"Template {filename} not found"}
            )
            logger.warning(f"Template not found: {filepath}")
            return

        # Читаємо HTML файл по байтам
        # "rb" = читаємо бінарний файл
        with open(filepath, "rb") as f:
            content = f.read()

        # Надсилаємо відповідь
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

        logger.info(f"GET {self.path} — served {filename}")

    def _serve_static(self, filepath: str):
        """
        Роздає статичні файли: CSS, JS, зображення.
        Автоматично визначає Content-Type по розширенню файлу.
        """
        # Створюємо повний шлях до статичного файлу
        full_path = os.path.join(STATIC_DIR, filepath)

        # Перевіряємо чи файл існує
        if not os.path.exists(full_path):
            self._send_json(
                status_code=404,
                data={"error": f"Static file not found: {filepath}"}
            )
            logger.warning(f"Static file not found: {full_path}")
            return

        # DВизначаємо тип контексту за розширенням файлу
        # Браузеру потрібно знати: "це CSS, JS чи image?"
        extension = filepath.split(".")[-1].lower()
        content_types = {
            "css": "text/css",
            "js": "application/javascript",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "ico": "image/x-icon",
        }
        # Провертаємось до бінарного потоку, якщо розширення невідоме
        content_type = content_types.get(extension, "application/octet-stream")

        # Читаємо файл по байтам
        with open(full_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        """
        Перевизначаємо дефолтний логер BaseHTTPRequestHandler.
        За замовчуванням він виводить некрасивий формат в stderr.
        Замовчуємо його — наш logger обробляє весь вивід.
        """
        pass  # Наш logger обробляє всі вихідні дані


# ─────────────────────────────────────────────
# SERVER STARTUP
# ─────────────────────────────────────────────

def run_server():
    """
    Створює та запускає HTTP сервер.
    Читає host і port з змінних оточення (.env файлу).
    """
    # Беремо данні для сервера з файлу .env
    # Якщо данні відсутні, то беремо значення за замовчуванням
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))

    try:
        # Створення HTTPServer відбувається в середину блоку try
        # тому, що може виникнути помилка OSError якщо порт зайнятий
        server = ThreadingHTTPServer((host, port), ImageServerHandler)

        # Ініціалізуємо БД при старті
        logger.info("Initializing database...")
        init_db()

        logger.info(f"Server started at http://{host}:{port}")
        logger.info("Press Ctrl+C to stop")

        # serve_forever() — запуск безкінечного циклу, очікує запити
        # блокується поки не буде натиснено Ctrl+C
        server.serve_forever()

    except KeyboardInterrupt:
        # Натискаємо Ctrl+C і завершаємо роботу
        logger.info("Server stopped by user")
        server.server_close()

    except OSError as e:
        # errno 48 - якщо зайнятий порт на macOS
        # errno 98 - якщо зайнятий порт на Linux
        # errno 10048 - якщо зайнятий порт на Windows
        if e.errno in (48, 98, 10048):
            logger.error(f"Port {port} is already in use!")
            logger.error(f"Run: lsof -i :{port} | xargs kill -9")
        else:
            logger.error(f"Failed to start server: {e}")

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

# Цей блок виконується тільки коли викнонується python app.py
if __name__ == "__main__":
    run_server()
