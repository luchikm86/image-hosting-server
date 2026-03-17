from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import os
import logging
import email
import email.parser
from dotenv import load_dotenv
from validators import validate_image
from file_handler import save_image
from database import init_db, save_image_metadata, get_images, delete_image_metadata

# Load environment variables from .env file RIGHT NOW
# Must be called before any os.getenv() calls
# Читаємо файл .env для роботи з ним
load_dotenv()


# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────

# Get log file path from .env, fallback to local file if not set
LOG_FILE = os.getenv("LOG_FILE", "../logs/app.log")

# Create logs directory if it doesn't exist yet
# exist_ok=True means: don't raise error if folder already exists
# Створюємо директорію. Якщо вона була створена і exist_ok=True, тоді не виникає помилки
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configure the logging system:
# - level=INFO means: write INFO, WARNING, ERROR (skip DEBUG)
# - format: how each log line looks
# - handlers: write to BOTH file and terminal simultaneously
# Налаштовуємо систему логування
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        # FileHandler writes logs to app.log file
        # Записуємо logs у файл app.log
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        # StreamHandler prints logs to terminal (useful during development)
        # Виводимо logs у термінал
        logging.StreamHandler(),
    ],
)

# Create a logger object for this module
# __name__ will be "app" — helps identify which file wrote the log
# Створює іменований об'єкт логера для цього файлу, щоб в логах було видно звідки прийшло кожне повідомлення
# __name__ - це вбудована змінна Python яка містить назву поточного модуля.
# В даному випадку __name__ буде "app"
logger = logging.getLogger(__name__)

# Base directory where app.py is located: src/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Templates directory: src/templates/
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Static files directory: src/static/
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ─────────────────────────────────────────────
# REQUEST HANDLER
# ─────────────────────────────────────────────

class ImageServerHandler(BaseHTTPRequestHandler):
    """
    Main HTTP request handler for the Image Server.

    This class inherits from BaseHTTPRequestHandler.
    For every HTTP method (GET, POST) we define a method:
        do_GET()  → handles all GET requests
        do_POST() → handles all POST requests (added later)

    self.path     → the URL path, e.g. "/" or "/upload"
    self.command  → HTTP method, e.g. "GET" or "POST"
    """

    def do_GET(self):
        # Route: static files (CSS, JS, images)
        # Any path starting with /static/ goes here
        if self.path.startswith("/static/"):
            # Remove "/static/" prefix to get relative path
            # "/static/css/style.css" → "css/style.css"
            static_path = self.path[len("/static/"):]
            self._serve_static(static_path)

        elif self.path == "/":
            self._serve_html("index.html")

        elif self.path == "/upload":
            self._serve_html("upload.html")

        elif self.path == "/images-list":
            self._serve_html("images.html")

        elif self.path == "/health":
            self._handle_health()

        # Route: GET /api/images
        # Повертає JSON список всіх завантажених зображень
        elif self.path.startswith("/api/images"):
            self._handle_images_list()

        # Route: GET /images/<filename>
        # Роздає фізичний файл зображення
        elif self.path.startswith("/images/"):
            filename = self.path[len("/images/"):]
            self._serve_image(filename)

        else:
            self._send_json(
                status_code=404,
                data={"error": "Route not found", "path": self.path}
            )
            logger.warning(f"404 Not Found: {self.path}")

    def do_POST(self):
        """
        Обробляє POST запити.
        Зараз підтримує тільки маршрут /upload.
        """
        if self.path == "/upload":
            self._handle_upload()
        elif self.path.startswith("/delete/"):
            # Отримуємо назву файлу з URL
            # "/delete/a1b2c3.jpg" → "a1b2c3.jpg"
            image_id = self.path[len("/delete/"):]
            self._handle_delete(image_id)
        else:
            self._send_json(
                status_code=404,
                data={"error": "Route not found", "path": self.path}
            )
            logger.warning(f"404 Not Found: {self.path}")

    def _handle_upload(self):
        """
        Обробляє завантаження зображення.
        Використовує email.parser для парсингу multipart/form-data
        замість застарілого модуля cgi.
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

            # Крок 3: Зберігаємо метадані в БД  ← НОВИЙ КРОК
            file_type = original_filename.rsplit(".", 1)[1].lower()
            image_id = save_image_metadata(
                filename=result,
                original_name=original_filename,
                size=file_size,
                file_type=file_type
            )

            if image_id is None:
                logger.warning("File saved but metadata not saved to DB")

            # Крок 4: Повертаємо успішну відповідь ← ЦЕ БУЛО ВІДСУТНЄ!
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
        """
        # Отримуємо номер сторінки з URL
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

        # Отримуємо зображення з БД
        images, total = get_images(page=page, per_page=10)

        # Рахуємо загальну кількість сторінок
        import math
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

        Args:
            filename: назва файлу, наприклад "a1b2c3d4.jpg"
        """
        # Захист від path traversal атаки
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
        Handler for GET /health
        Returns server status. Docker uses this to check if container is alive.
        """
        self._send_json(
            status_code=200,
            data={"status": "ok", "server": "ImageServer/1.0"}
        )
        logger.info("GET /health — health check passed")

    def _send_json(self, status_code: int, data:dict):
        """
        Helper method to send a JSON response.

        Why a helper? Because every response needs the same 3 steps:
        1. Send status code (200, 404, etc.)
        2. Send headers (Content-Type: application/json)
        3. Send body (the actual JSON data)

        Args:
            status_code: HTTP status code (200, 404, 500...)
            data: Python dict that will be converted to JSON
        """
        # Convert Python dict to JSON string, ensure_ascii=False for Unicode
        # Перетворюємо dict в JSON рядок
        body = json.dumps(data, ensure_ascii=False, indent=2)

        # Encode string to bytes — HTTP works with bytes, not strings
        # Перетворюємо JSON рядок в байти (string → bytes)
        body_bytes = body.encode("utf-8")

        # Step 1: Send the status code line: "HTTP/1.1 200 OK"
        self.send_response(status_code)

        # Step 2: Send headers
        # Content-Type tells the browser: "this is JSON, not HTML"
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # Content-Length tells the browser how many bytes to expect
        self.send_header("Content-Length", str(len(body_bytes)))
        # Говоримо браузеру що після відповіді з'єднання закривається
        self.send_header("Connection", "close")
        # end_headers() sends an empty line — required by HTTP protocol
        self.end_headers()

        # Step 3: Send the actual response body
        # Відправляємо все в браузер
        self.wfile.write(body_bytes)
        # Примусово відправляємо всі байти з буфера
        self.wfile.flush()

    def _serve_html(self, filename: str):
        """
        Reads an HTML file from templates directory and sends it to browser.

        Args:
            filename: HTML filename, e.g. "index.html"
        """
        # Build full path to the HTML file
        # Example: /Users/.../src/templates/index.html
        filepath = os.path.join(TEMPLATES_DIR, filename)

        # Check if file exists — if not, return 404
        if not os.path.exists(filepath):
            self._send_json(
                status_code=404,
                data={"error": f"Template {filename} not found"}
            )
            logger.warning(f"Template not found: {filepath}")
            return

        # Read HTML file as bytes
        # "rb" = read binary — we need bytes for HTTP
        with open(filepath, "rb") as f:
            content = f.read()

        # Send response
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

        logger.info(f"GET {self.path} — served {filename}")

    def _serve_static(self, filepath: str):
        """
        Serves static files: CSS, JS, images.
        Automatically detects content type by file extension.

        Args:
            filepath: path after /static/, e.g. "css/style.css"
        """
        # Build full path to static file
        full_path = os.path.join(STATIC_DIR, filepath)

        # Check if file exists
        if not os.path.exists(full_path):
            self._send_json(
                status_code=404,
                data={"error": f"Static file not found: {filepath}"}
            )
            logger.warning(f"Static file not found: {full_path}")
            return

        # Detect content type by file extension
        # Browser needs to know: "is this CSS or JS or image?"
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
        # Fallback to binary stream if extension is unknown
        content_type = content_types.get(extension, "application/octet-stream")

        # Read file as bytes
        with open(full_path, "rb") as f:
            content = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        """
        Override the default BaseHTTPRequestHandler logger.
        By default it prints to stderr in an ugly format.
        We silence it here because we handle logging ourselves.
        """
        pass  # Our logger handles all output


# ─────────────────────────────────────────────
# SERVER STARTUP
# ─────────────────────────────────────────────

def run_server():
    """
    Creates and starts the HTTP server.
    Reads host and port from environment variables.
    """
    # Read server config from .env file
    # If not set — use sensible defaults
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", "8000"))

    try:
        # HTTPServer creation is INSIDE try block
        # because this is where OSError happens if port is busy
        server = ThreadingHTTPServer((host, port), ImageServerHandler)

        # Ініціалізуємо БД при старті
        logger.info("Initializing database...")
        init_db()

        logger.info(f"Server started at http://{host}:{port}")
        logger.info("Press Ctrl+C to stop")

        # serve_forever() — starts an infinite loop, listens for requests
        # Blocks here until Ctrl+C is pressed
        server.serve_forever()

    except KeyboardInterrupt:
        # Ctrl+C pressed — graceful shutdown
        logger.info("Server stopped by user")
        server.server_close()

    except OSError as e:
        # errno 48 = "Address already in use" on macOS
        # errno 98 = same error on Linux
        if e.errno in (48, 98):
            logger.error(f"Port {port} is already in use!")
            logger.error(f"Run: lsof -i :{port} | xargs kill -9")
        else:
            logger.error(f"Failed to start server: {e}")

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

# This block runs ONLY when you execute: python app.py
# It does NOT run when this file is imported by another module
if __name__ == "__main__":
    run_server()
