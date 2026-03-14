# http.server — built-in Python module, no installation needed
# It provides BaseHTTPRequestHandler — a class that handles HTTP requests
from http.server import HTTPServer, BaseHTTPRequestHandler

# json — built-in module for converting Python objects to JSON format
# Example: {"status": "ok"} → '{"status": "ok"}'
import json

# os — built-in module for interacting with the operating system
# We use it to read environment variables from .env file
import os

# logging — built-in module for writing logs to a file
# Much better than print() because it adds timestamps automatically
import logging

# load_dotenv reads the .env file and puts variables into os.environ
# Without this line, os.getenv() would not see our .env variables
from dotenv import load_dotenv

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

        else:
            self._send_json(
                status_code=404,
                data={"error": "Route not found", "path": self.path}
            )
            logger.warning(f"404 Not Found: {self.path}")


    def _handle_home(self):
        """
        Handler for GET /
        Returns a welcome message with available routes.
        """
        response_data = {
            "message": "Welcome to Image Server!",
            "version": "1.0.0",
            "routes": {
                "GET  /": "This welcome message",
                "GET  /health": "Server health check",
                "POST /upload": "Upload an image (coming soon)",
            }
        }

        self._send_json(status_code=200, data=response_data)
        logger.info("GET / — home route accessed")

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
        # end_headers() sends an empty line — required by HTTP protocol
        self.end_headers()

        # Step 3: Send the actual response body
        # Відправляємо все в браузер
        self.wfile.write(body_bytes)

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
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))

    try:
        # HTTPServer creation is INSIDE try block
        # because this is where OSError happens if port is busy
        server = HTTPServer((host, port), ImageServerHandler)

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
