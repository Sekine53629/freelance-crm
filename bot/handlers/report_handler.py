"""月次レポートハンドラー - Slack対話型"""
from datetime import datetime, date
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from reports.monthly_report import MonthlyReportGenerator


def register_report_handlers(app):
    """レポート関連のハンドラーを登録"""

    @app.command("/report")
    def handle_report_command(ack, body, client, respond):
        """月次レポートを生成して投稿"""
        ack()
        user_id = body["user"]["id"]

        # 引数から年月を取得（例: /report 2025 11）
        text = body.get("text", "").strip()
        year, month = parse_year_month(text)

        try:
            with get_db() as db:
                generator = MonthlyReportGenerator(db)
                stats, markdown, blocks = generator.generate(year, month)

            # Slackに投稿
            client.chat_postMessage(
                channel=user_id,
                text=f"月次レポート {stats.year}年{stats.month}月",
                blocks=blocks
            )

        except Exception as e:
            client.chat_postMessage(
                channel=user_id,
                text=f":x: レポート生成に失敗しました\nエラー: {str(e)}"
            )

    @app.message(re.compile(r"^(月次)?レポート(\s+\d{4}\s+\d{1,2})?$"))
    def handle_report_message(message, say, context):
        """メッセージで月次レポートを生成"""
        text = message.get("text", "")
        year, month = parse_year_month(text)

        try:
            with get_db() as db:
                generator = MonthlyReportGenerator(db)
                stats, markdown, blocks = generator.generate(year, month)

            say(
                text=f"月次レポート {stats.year}年{stats.month}月",
                blocks=blocks
            )

        except Exception as e:
            say(f":x: レポート生成に失敗しました: {str(e)}")

    @app.message("ヘルプ")
    def handle_help(message, say):
        """ヘルプメッセージを表示"""
        say(
            text="利用可能なコマンド一覧",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Freelance CRM コマンド一覧*"
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "*案件管理*\n"
                            "• `案件登録` - 新規案件を登録\n"
                            "• `/project` - 案件登録フォームを開く\n"
                            "• `案件一覧` - 最近の案件を表示\n\n"
                            "*レポート*\n"
                            "• `レポート` - 前月の月次レポートを生成\n"
                            "• `レポート 2025 11` - 指定月のレポートを生成\n"
                            "• `/report` - 月次レポートを生成\n"
                            "• `/report 2025 11` - 指定月のレポートを生成"
                        )
                    }
                }
            ]
        )


def parse_year_month(text: str) -> tuple[int | None, int | None]:
    """テキストから年月を抽出"""
    numbers = re.findall(r"\d+", text)
    if len(numbers) >= 2:
        year = int(numbers[0])
        month = int(numbers[1])
        if 2000 <= year <= 2100 and 1 <= month <= 12:
            return year, month
    return None, None
