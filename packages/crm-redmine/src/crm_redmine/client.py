"""Redmine API Client"""
import requests
from typing import Optional


class RedmineClient:
    """Redmine APIクライアント"""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-Redmine-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def create_issue(
        self,
        project_id: str,
        subject: str,
        description: str = "",
        estimated_hours: float = None,
        due_date: str = None
    ) -> dict:
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
        """チケットを取得"""
        response = requests.get(
            f"{self.url}/issues/{issue_id}.json",
            headers=self.headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def update_issue(self, issue_id: int, **kwargs) -> dict:
        """チケットを更新"""
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
        """プロジェクト一覧を取得"""
        response = requests.get(
            f"{self.url}/projects.json",
            headers=self.headers,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("projects", [])

    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            self.get_projects()
            return True
        except requests.RequestException:
            return False
