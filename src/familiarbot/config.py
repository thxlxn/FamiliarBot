import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_KEY = os.getenv('TELEGRAM_KEY')
GEMINI_KEY = os.getenv('GEMINI_KEY')
DB_NAME = os.getenv('DB_NAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')