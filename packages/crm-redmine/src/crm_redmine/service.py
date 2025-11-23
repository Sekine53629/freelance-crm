"""Redmine連携サービス"""
from datetime import datetime
from typing import Optional
from crm_core import get_db, Task, RedmineConfig
from .client import RedmineClient


class RedmineService:
    """Redmine連携サービス"""

    @staticmethod
    def setup_config(
        project_id: int,
        redmine_url: str,
        redmine_project_id: str,
        api_key: str
    ) -> tuple[bool, str]:
        """Redmine連携を設定"""
        # 接続テスト
        client = RedmineClient(redmine_url, api_key)
        if not client.test_connection():
            return False, "Redmineへの接続に失敗しました"

        # プロジェクト存在確認
        projects = client.get_projects()
        if not any(p["identifier"] == redmine_project_id for p in projects):
            return False, f"プロジェクト '{redmine_project_id}' が見つかりません"

        with get_db() as db:
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

        return True, "設定完了"

    @staticmethod
    def sync_task(task_id: int) -> tuple[bool, str, Optional[int]]:
        """タスクをRedmineに同期"""
        with get_db() as db:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                return False, "タスクが見つかりません", None

            config = db.query(RedmineConfig).filter(
                RedmineConfig.project_id == task.project_id
            ).first()
            if not config:
                return False, "Redmine連携が設定されていません", None

            client = RedmineClient(config.redmine_url, config.api_key)

            try:
                result = client.create_issue(
                    project_id=config.redmine_project_id,
                    subject=task.task_name,
                    description=task.description or "",
                    estimated_hours=float(task.estimated_hours) if task.estimated_hours else None,
                    due_date=task.due_date.isoformat() if task.due_date else None
                )
                issue_id = result["issue"]["id"]
                task.redmine_issue_id = issue_id
                config.last_sync_at = datetime.utcnow()

                return True, f"チケット #{issue_id} を作成しました", issue_id
            except Exception as e:
                return False, str(e), None

    @staticmethod
    def bulk_sync(project_id: int) -> list[tuple[str, bool, str]]:
        """案件の全タスクをRedmineに同期"""
        results = []
        with get_db() as db:
            config = db.query(RedmineConfig).filter(
                RedmineConfig.project_id == project_id
            ).first()
            if not config:
                return [("", False, "Redmine連携が設定されていません")]

            tasks = db.query(Task).filter(
                Task.project_id == project_id,
                Task.redmine_issue_id.is_(None)
            ).all()

            if not tasks:
                return [("", False, "同期対象のタスクがありません")]

            client = RedmineClient(config.redmine_url, config.api_key)

            for task in tasks:
                try:
                    result = client.create_issue(
                        project_id=config.redmine_project_id,
                        subject=task.task_name,
                        description=task.description or "",
                        estimated_hours=float(task.estimated_hours) if task.estimated_hours else None,
                        due_date=task.due_date.isoformat() if task.due_date else None
                    )
                    issue_id = result["issue"]["id"]
                    task.redmine_issue_id = issue_id
                    results.append((task.task_name, True, f"#{issue_id}"))
                except Exception as e:
                    results.append((task.task_name, False, str(e)))

            config.last_sync_at = datetime.utcnow()

        return results
