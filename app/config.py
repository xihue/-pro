import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load .env file from project root
load_dotenv(os.path.join(basedir, "..", ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # DeepSeek API — set via .env file or environment variable
    API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
    BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")

    # 游戏存储目录
    GAMES_DIR = os.path.join(basedir, "..", "storage", "games")
