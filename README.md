# 🖼️ Image Hosting Server

Веб-сервіс для завантаження, зберігання та перегляду зображень.
Навчальний проект — спрощений аналог Dropbox, написаний на чистому Python без фреймворків.

---

## 🚀 Tech Stack

- **Backend**: Python 3.13 (`http.server`)
- **Database**: PostgreSQL 16 + psycopg2
- **Web Server**: Nginx
- **Containerization**: Docker & Docker Compose
- **Frontend**: HTML5, CSS3, JavaScript

---

## ✅ Features

- Завантаження зображень (`.jpg`, `.png`, `.gif`, до **5MB**)
- Валідація формату та розміру файлу через Pillow
- Зберігання метаданих в PostgreSQL
- Список зображень з пагінацією (10 шт/сторінка)
- Видалення зображень (файл + запис у БД)
- Логування всіх дій
- Резервне копіювання БД (pg_dump)

---

## 📂 Project Structure
```
image-hosting-server/
├── src/
│   ├── app.py           # HTTP сервер — головний файл
│   ├── database.py      # Робота з PostgreSQL
│   ├── validators.py    # Валідація зображень
│   ├── file_handler.py  # Збереження/видалення файлів
│   ├── templates/       # HTML сторінки
│   └── static/          # CSS, JS, зображення
├── config/
│   ├── nginx.conf       # Конфігурація Nginx
│   └── init.sql         # Ініціалізація БД
├── scripts/
│   └── backup.py        # Резервне копіювання
├── images/              # Завантажені зображення (volume)
├── logs/                # Логи (volume)
├── backups/             # Резервні копії БД
├── Dockerfile
├── compose.yaml
└── .env.example
```

---

## ⚡ Quick Start

### Docker Compose (Recommended)
```bash
git clone https://github.com/luchikm/image-hosting-server.git
cd image-hosting-server

# Створи .env файл
cp .env.example .env

# Запусти проект
docker compose up --build
```

Відкрий [http://localhost](http://localhost)

### Local Development (Without Docker)
```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python src/app.py
```

Відкрий [http://localhost:8000](http://localhost:8000)

---

## 🌐 API Routes

| Метод | Маршрут | Опис |
|---|---|---|
| GET | `/` | Головна сторінка |
| GET | `/upload` | Сторінка завантаження |
| POST | `/upload` | Завантажити зображення |
| GET | `/images-list` | Список зображень |
| GET | `/api/images?page=1` | JSON список з пагінацією |
| GET | `/images/<filename>` | Переглянути зображення |
| POST | `/delete/<id>` | Видалити зображення |
| GET | `/health` | Перевірка стану сервера |

---

## 🗄️ Database Backup
```bash
# Активуй virtual environment
source .venv/bin/activate

# Створи резервну копію
python scripts/backup.py
```

Резервні копії зберігаються в папці `backups/`:
```
backup_2026-03-18_164612.sql
```

---

## 🔧 Environment Variables

Створи `.env` файл в корені проекту (або скопіюй з `.env.example`):
```env
# Database Configuration
DB_HOST=db
DB_NAME=images_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_PORT=5432

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# PostgreSQL Docker Configuration
POSTGRES_DB=${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}

# Application settings
MAX_FILE_SIZE_MB=5
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif
UPLOAD_FOLDER=/images
LOG_FILE=/logs/app.log
```

---

## 🛑 Stop Project
```bash
# Зупинити контейнери
docker compose down

# Зупинити і видалити дані БД
docker compose down -v
```

---

## 🛠️ Requirements

- Python 3.13+
- Docker & Docker Compose
- PostgreSQL 16 (або через Docker)