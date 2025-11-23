"""工程・タスク管理サービス"""
from datetime import date
from typing import Optional
from crm_core import get_db, Project, Milestone, Task, TimeEntry


class ScheduleService:
    """工程管理サービス"""

    @staticmethod
    def get_schedule(project_id: int) -> tuple[Optional[Project], list[Milestone]]:
        """案件の工程を取得"""
        with get_db() as db:
            project = db.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                return None, []
            milestones = db.query(Milestone).filter(
                Milestone.project_id == project_id
            ).order_by(Milestone.due_date).all()
            return project, milestones

    @staticmethod
    def add_milestone(
        project_id: int,
        milestone_name: str,
        due_date: date,
        description: str = ""
    ) -> Milestone:
        """マイルストーンを追加"""
        with get_db() as db:
            milestone = Milestone(
                project_id=project_id,
                milestone_name=milestone_name,
                due_date=due_date,
                description=description,
                status="pending"
            )
            db.add(milestone)
            db.flush()
            return milestone

    @staticmethod
    def update_milestone_status(milestone_id: int, status: str) -> Optional[Milestone]:
        """マイルストーンステータスを更新"""
        with get_db() as db:
            milestone = db.query(Milestone).filter(
                Milestone.milestone_id == milestone_id
            ).first()
            if milestone:
                milestone.status = status
                if status == "completed":
                    milestone.completed_date = date.today()
            return milestone


class TaskService:
    """タスク管理サービス"""

    @staticmethod
    def get_tasks(project_id: int) -> list[Task]:
        """案件のタスク一覧を取得"""
        with get_db() as db:
            return db.query(Task).filter(
                Task.project_id == project_id
            ).order_by(Task.sort_order, Task.due_date).all()

    @staticmethod
    def add_task(
        project_id: int,
        task_name: str,
        estimated_hours: float = None,
        due_date: date = None,
        description: str = "",
        milestone_id: int = None
    ) -> Task:
        """タスクを追加"""
        with get_db() as db:
            task = Task(
                project_id=project_id,
                task_name=task_name,
                estimated_hours=estimated_hours,
                due_date=due_date,
                description=description,
                milestone_id=milestone_id,
                status="todo"
            )
            db.add(task)
            db.flush()
            return task

    @staticmethod
    def update_task_status(task_id: int, status: str) -> Optional[Task]:
        """タスクステータスを更新"""
        with get_db() as db:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if task:
                task.status = status
                if status == "done":
                    task.completed_date = date.today()
            return task

    @staticmethod
    def log_time(task_id: int, hours: float, description: str = "") -> tuple[TimeEntry, float]:
        """工数を記録"""
        with get_db() as db:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                raise ValueError(f"Task {task_id} not found")

            entry = TimeEntry(
                task_id=task_id,
                project_id=task.project_id,
                hours=hours,
                description=description,
                work_date=date.today()
            )
            db.add(entry)

            # タスクの実績工数を更新
            total_hours = sum(float(e.hours) for e in task.time_entries) + hours
            task.actual_hours = total_hours
            db.flush()

            return entry, total_hours
