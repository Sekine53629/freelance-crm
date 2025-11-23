"""Redmine連携ハンドラー"""
from datetime import datetime
import re
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import Project, Task, RedmineConfig


class RedmineClient:
    """Redmine APIクライアント"""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-Redmine-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def create_issue(self, project_id: str, subject: str, description: str = "",
                     estimated_hours: float = None, due_date: str = None) -> dict:
        """Redmineにチケットを作成"""
        data = {
            "issue": {
                "project_id": project_id,
                "subject": subject,
                "description": description,
            }
        }
        if estimated_hours:
            data["issue"]["estimated_hours"] = estimated_hours
        if due_date:
            data["issue"]["due_date"] = due_date

        response = requests.post(
            f"{self.url}/issues.json",
            headers=self.headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def get_issue(self, issue_id: int) -> dict:
        """Redmineのチケットを取得"""
        response = requests.get(
            f"{self.url}/issues/{issue_id}.json",
            headers=self.headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def update_issue(self, issue_id: int, **kwargs) -> dict:
        """Redmineのチケットを更新"""
        data = {"issue": kwargs}
        response = requests.put(
            f"{self.url}/issues/{issue_id}.json",
            headers=self.headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return {"status": "updated"}

    def get_projects(self) -> list:
        """Redmineのプロジェクト一覧を取得"""
        response = requests.get(
            f"{self.url}/projects.json",
            headers=self.headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("projects", [])


def register_redmine_handlers(app):
    """Redmine連携のハンドラーを登録"""

    @app.command("/redmine-setup")
    def handle_redmine_setup(ack, body, client):
        """Redmine連携設定モーダルを開く"""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=get_redmine_setup_modal()
        )

    @app.view("redmine_setup_submission")
    def handle_redmine_setup_submission(ack, body, client, view):
        """Redmine連携設定を保存"""
        ack()
        user_id = body["user"]["id"]
        values = view["state"]["values"]

        project_id = int(values["project_id_block"]["project_id"]["value"])
        redmine_url = values["redmine_url_block"]["redmine_url"]["value"]
        redmine_project_id = values["redmine_project_id_block"]["redmine_project_id"]["value"]
        api_key = values["api_key_block"]["api_key"]["value"]

        try:
            # 接続テスト
            redmine = RedmineClient(redmine_url, api_key)
            projects = redmine.get_projects()
            project_exists = any(p["identifier"] == redmine_project_id for p in projects)

            if not project_exists:
                client.chat_postMessage(
                    channel=user_id,
                    text=f":warning: Redmineプロジェクト `{redmine_project_id}` が見つかりません"
                )
                return

            with get_db() as db:
                # 既存設定を確認
                config = db.query(RedmineConfig).filter(
                    RedmineConfig.project_id == project_id
                ).first()

                if config:
                    config.redmine_url = redmine_url
                    config.redmine_project_id = redmine_project_id
                    config.api_key = api_key
                else:
                    config = RedmineConfig(
                        project_id=project_id,
                        redmine_url=redmine_url,
                        redmine_project_id=redmine_project_id,
                        api_key=api_key,
                        sync_enabled=True
                    )
                    db.add(config)

            client.chat_postMessage(
                channel=user_id,
                text=f":white_check_mark: Redmine連携を設定しました\n"
                     f"*Redmine URL:* {redmine_url}\n"
                     f"*プロジェクト:* {redmine_project_id}"
            )
        except requests.RequestException as e:
            client.chat_postMessage(
                channel=user_id,
                text=f":x: Redmine接続エラー: {str(e)}"
            )
        except Exception as e:
            client.chat_postMessage(
                channel=user_id,
                text=f":x: 設定エラー: {str(e)}"
            )

    @app.message(re.compile(r"^Redmine登録\s+(\d+)$"))
    def handle_sync_to_redmine(message, say, context):
        """タスクをRedmineに登録: Redmine登録 [タスクID]"""
        match = context["matches"]
        task_id = int(match[0])

        try:
            with get_db() as db:
                task = db.query(Task).filter(Task.task_id == task_id).first()
                if not task:
                    say(f"タスクID {task_id} が見つかりません")
                    return

                config = db.query(RedmineConfig).filter(
                    RedmineConfig.project_id == task.project_id
                ).first()

                if not config:
                    say(":warning: この案件のRedmine連携が設定されていません\n"
                        "`/redmine-setup` で設定してください")
                    return

                redmine = RedmineClient(config.redmine_url, config.api_key)

                # チケット作成
                result = redmine.create_issue(
                    project_id=config.redmine_project_id,
                    subject=task.task_name,
                    description=task.description or "",
                    estimated_hours=float(task.estimated_hours) if task.estimated_hours else None,
                    due_date=task.due_date.isoformat() if task.due_date else None
                )

                issue_id = result["issue"]["id"]
                task.redmine_issue_id = issue_id
                config.last_sync_at = datetime.utcnow()

            say(f":white_check_mark: Redmineにチケットを作成しました\n"
                f"*タスク:* {task.task_name}\n"
                f"*Redmine Issue:* #{issue_id}\n"
                f"*URL:* {config.redmine_url}/issues/{issue_id}")
        except requests.RequestException as e:
            say(f":x: Redmine連携エラー: {str(e)}")
        except Exception as e:
            say(f":x: エラー: {str(e)}")

    @app.message(re.compile(r"^Redmine一括登録\s+(\d+)$"))
    def handle_bulk_sync_to_redmine(message, say, context):
        """案件の全タスクをRedmineに登録: Redmine一括登録 [案件ID]"""
        match = context["matches"]
        project_id = int(match[0])

        try:
            with get_db() as db:
                config = db.query(RedmineConfig).filter(
                    RedmineConfig.project_id == project_id
                ).first()

                if not config:
                    say(":warning: この案件のRedmine連携が設定されていません")
                    return

                tasks = db.query(Task).filter(
                    Task.project_id == project_id,
                    Task.redmine_issue_id.is_(None)
                ).all()

                if not tasks:
                    say("登録対象のタスクがありません（既に登録済み or タスクなし）")
                    return

                redmine = RedmineClient(config.redmine_url, config.api_key)
                created = []

                for task in tasks:
                    try:
                        result = redmine.create_issue(
                            project_id=config.redmine_project_id,
                            subject=task.task_name,
                            description=task.description or "",
                            estimated_hours=float(task.estimated_hours) if task.estimated_hours else None,
                            due_date=task.due_date.isoformat() if task.due_date else None
                        )
                        issue_id = result["issue"]["id"]
                        task.redmine_issue_id = issue_id
                        created.append(f"• {task.task_name} → #{issue_id}")
                    except Exception as e:
                        created.append(f"• {task.task_name} → :x: 失敗: {str(e)}")

                config.last_sync_at = datetime.utcnow()

            say(f":white_check_mark: Redmineへの一括登録完了\n\n" + "\n".join(created))
        except Exception as e:
            say(f":x: エラー: {str(e)}")


def get_redmine_setup_modal():
    """Redmine設定モーダル"""
    return {
        "type": "modal",
        "callback_id": "redmine_setup_submission",
        "title": {"type": "plain_text", "text": "Redmine連携設定"},
        "submit": {"type": "plain_text", "text": "設定"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": [
            {
                "type": "input",
                "block_id": "project_id_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "project_id",
                    "placeholder": {"type": "plain_text", "text": "CRM案件ID（数字）"}
                },
                "label": {"type": "plain_text", "text": "案件ID"}
            },
            {
                "type": "input",
                "block_id": "redmine_url_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "redmine_url",
                    "placeholder": {"type": "plain_text", "text": "例: https://redmine.example.com"}
                },
                "label": {"type": "plain_text", "text": "Redmine URL"}
            },
            {
                "type": "input",
                "block_id": "redmine_project_id_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "redmine_project_id",
                    "placeholder": {"type": "plain_text", "text": "例: my-project"}
                },
                "label": {"type": "plain_text", "text": "Redmineプロジェクト識別子"}
            },
            {
                "type": "input",
                "block_id": "api_key_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "api_key",
                    "placeholder": {"type": "plain_text", "text": "RedmineのAPIキー"}
                },
                "label": {"type": "plain_text", "text": "APIキー"}
            }
        ]
    }
