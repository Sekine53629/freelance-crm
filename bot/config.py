"""Configuration for Freelance CRM Bot"""
import os
from dotenv import load_dotenv

load_dotenv()

# Slack設定
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")

# データベース設定
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://freelance_user:password@localhost:5432/freelance_crm"
)

# アプリ設定
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
