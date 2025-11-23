"""案件登録ハンドラー - Slack対話型フォーム"""
from datetime import datetime
import sys
import os

# 親ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, Client, Project

# チャネル名マッピング
CHANNEL_MAP = {
    "1": "ランサーズ",
    "2": "クラウドワークス",
    "3": "ココナラ",
    "4": "Twitter/X",
    "5": "LinkedIn",
    "6": "紹介",
    "7": "直接営業",
    "8": "その他"
}


def register_project_handlers(app):
    """案件関連のハンドラーを登録"""

    @app.command("/project")
    def handle_project_command(ack, body, client):
        """案件登録モーダルを開く"""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=get_project_modal()
        )

    @app.view("project_submission")
    def handle_project_submission(ack, body, client, view):
        """案件登録フォームの送信処理"""
        ack()
        user_id = body["user"]["id"]
        values = view["state"]["values"]

        # フォームから値を取得
        project_name = values["project_name_block"]["project_name"]["value"]
        client_name = values["client_name_block"]["client_name"]["value"]
        channel_id = values["channel_block"]["channel"]["selected_option"]["value"]
        request_date = values["request_date_block"]["request_date"]["selected_date"]
        deadline = values["deadline_block"]["deadline"]["selected_date"]
        notes = values["notes_block"]["notes"]["value"] or ""

        channel_name = CHANNEL_MAP.get(channel_id, "その他")

        try:
            # データベースに保存
            with get_db() as db:
                # クライアント取得または作成
                db_client = db.query(Client).filter(
                    Client.company_name == client_name
                ).first()

                if not db_client:
                    db_client = Client(company_name=client_name)
                    db.add(db_client)
                    db.flush()

                # 案件作成
                project = Project(
                    project_name=project_name,
                    client_id=db_client.client_id,
                    acquisition_channel_id=int(channel_id),
                    request_date=datetime.strptime(request_date, "%Y-%m-%d").date() if request_date else None,
                    deadline=datetime.strptime(deadline, "%Y-%m-%d").date() if deadline else None,
                    notes=notes,
                    status_id=1  # 問い合わせ
                )
                db.add(project)
                db.flush()
                project_id = project.project_id

            # 成功メッセージを送信
            client.chat_postMessage(
                channel=user_id,
                text=f":white_check_mark: 案件を登録しました!\n"
                     f"*案件ID:* PRJ-{project_id:04d}\n"
                     f"*案件名:* {project_name}\n"
                     f"*クライアント:* {client_name}\n"
                     f"*獲得チャネル:* {channel_name}\n"
                     f"*依頼日:* {request_date}\n"
                     f"*納期:* {deadline}\n"
                     f"*メモ:* {notes if notes else '(なし)'}"
            )
        except Exception as e:
            # エラーメッセージを送信
            client.chat_postMessage(
                channel=user_id,
                text=f":x: 案件登録に失敗しました\nエラー: {str(e)}"
            )

    @app.message("案件登録")
    def handle_project_message(message, say, client):
        """メッセージで案件登録を開始"""
        say(
            text="案件を登録しますか?",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "案件を登録しますか?"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "登録する"},
                            "style": "primary",
                            "action_id": "open_project_modal"
                        }
                    ]
                }
            ]
        )

    @app.action("open_project_modal")
    def handle_open_modal(ack, body, client):
        """ボタンクリックでモーダルを開く"""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=get_project_modal()
        )

    @app.message("案件一覧")
    def handle_list_projects(message, say):
        """最近の案件一覧を表示"""
        try:
            with get_db() as db:
                projects = db.query(Project).order_by(
                    Project.created_at.desc()
                ).limit(10).all()

                if not projects:
                    say("登録されている案件はありません。")
                    return

                lines = ["*最近の案件一覧:*\n"]
                for p in projects:
                    client_name = p.client.company_name if p.client else "不明"
                    lines.append(
                        f"• PRJ-{p.project_id:04d}: {p.project_name} ({client_name})"
                    )

                say("\n".join(lines))
        except Exception as e:
            say(f"案件一覧の取得に失敗しました: {str(e)}")


def get_project_modal():
    """案件登録モーダルのビュー定義"""
    return {
        "type": "modal",
        "callback_id": "project_submission",
        "title": {"type": "plain_text", "text": "案件登録"},
        "submit": {"type": "plain_text", "text": "登録"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": [
            {
                "type": "input",
                "block_id": "project_name_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "project_name",
                    "placeholder": {"type": "plain_text", "text": "例: ECサイト在庫管理システム"}
                },
                "label": {"type": "plain_text", "text": "案件名"}
            },
            {
                "type": "input",
                "block_id": "client_name_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "client_name",
                    "placeholder": {"type": "plain_text", "text": "例: 株式会社〇〇"}
                },
                "label": {"type": "plain_text", "text": "クライアント名"}
            },
            {
                "type": "input",
                "block_id": "channel_block",
                "element": {
                    "type": "static_select",
                    "action_id": "channel",
                    "placeholder": {"type": "plain_text", "text": "選択してください"},
                    "options": [
                        {"text": {"type": "plain_text", "text": "ランサーズ"}, "value": "1"},
                        {"text": {"type": "plain_text", "text": "クラウドワークス"}, "value": "2"},
                        {"text": {"type": "plain_text", "text": "ココナラ"}, "value": "3"},
                        {"text": {"type": "plain_text", "text": "Twitter/X"}, "value": "4"},
                        {"text": {"type": "plain_text", "text": "LinkedIn"}, "value": "5"},
                        {"text": {"type": "plain_text", "text": "紹介"}, "value": "6"},
                        {"text": {"type": "plain_text", "text": "直接営業"}, "value": "7"},
                        {"text": {"type": "plain_text", "text": "その他"}, "value": "8"}
                    ]
                },
                "label": {"type": "plain_text", "text": "獲得チャネル"}
            },
            {
                "type": "input",
                "block_id": "request_date_block",
                "element": {
                    "type": "datepicker",
                    "action_id": "request_date",
                    "placeholder": {"type": "plain_text", "text": "日付を選択"}
                },
                "label": {"type": "plain_text", "text": "依頼日"}
            },
            {
                "type": "input",
                "block_id": "deadline_block",
                "element": {
                    "type": "datepicker",
                    "action_id": "deadline",
                    "placeholder": {"type": "plain_text", "text": "日付を選択"}
                },
                "label": {"type": "plain_text", "text": "納期"}
            },
            {
                "type": "input",
                "block_id": "notes_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "notes",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "備考やメモ"}
                },
                "label": {"type": "plain_text", "text": "メモ"}
            }
        ]
    }
