"""Freelance CRM Slack Bot - Main Application"""
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, DEBUG
from handlers.project_handler import register_project_handlers
from handlers.report_handler import register_report_handlers

# ログ設定
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Slack App初期化
app = App(token=SLACK_BOT_TOKEN)


# ======================
# 基本コマンド
# ======================
@app.message("こんにちは")
def greet(message, say):
    """挨拶に応答"""
    user = message["user"]
    say(f"こんにちは <@{user}>さん! 営業CRMボットです。")


@app.event("app_mention")
def handle_mention(event, say):
    """メンション時の応答"""
    user_id = event['user']
    say(f"<@{user_id}> お呼びですか?\n`ヘルプ` と送信すると使い方を確認できます。")


@app.event("message")
def handle_message_events(body, logger):
    """その他のメッセージイベント（ログ用）"""
    logger.debug(f"Message event: {body}")


# ======================
# ハンドラー登録
# ======================
register_project_handlers(app)
register_report_handlers(app)


# ======================
# メイン
# ======================
def main():
    """アプリケーション起動"""
    logger.info("Starting Freelance CRM Bot...")

    if not SLACK_BOT_TOKEN or not SLACK_APP_TOKEN:
        logger.error("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set")
        return

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)

    try:
        logger.info("Bot is running! Press Ctrl+C to stop.")
        handler.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
