import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("TOKEN")

# Путь к базе данных
DB_PATH = "data/database.db"

# Админы (ID пользователей через запятую)
ADMINS = [int(admin_id) for admin_id in os.getenv("ADMINS", "").split(",") if admin_id]

# Пути к папкам
COVERS_PATH = "covers"
DATA_PATH = "data"
