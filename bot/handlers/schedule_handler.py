"""工期管理・見積もり・タスク管理ハンドラー"""
from datetime import datetime, date
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import Project, Milestone, Task, EstimateItem, TimeEntry


def register_schedule_handlers(app):
    """工期管理・タスク関連のハンドラーを登録"""

    @app.message(re.compile(r"^工程\s+(\d+)$"))
    def handle_show_schedule(message, say, context):
        """案件の工程・マイルストーンを表示"""
        match = context["matches"]
        project_id = int(match[0])

        try:
            with get_db() as db:
                project = db.query(Project).filter(Project.project_id == project_id).first()
                if not project:
                    say(f"案件ID {project_id} が見つかりません")
                    return

                blocks = build_schedule_blocks(project, db)
                say(text=f"案件 {project.project_name} の工程", blocks=blocks)
        except Exception as e:
            say(f":x: エラー: {str(e)}")

    @app.message(re.compile(r"^タスク一覧\s+(\d+)$"))
    def handle_list_tasks(message, say, context):
        """案件のタスク一覧を表示"""
        match = context["matches"]
        project_id = int(match[0])

        try:
            with get_db() as db:
                tasks = db.query(Task).filter(
                    Task.project_id == project_id
                ).order_by(Task.sort_order, Task.due_date).all()

                if not tasks:
                    say(f"案件ID {project_id} にタスクがありません")
                    return

                blocks = build_task_list_blocks(tasks, project_id)
                say(text=f"タスク一覧", blocks=blocks)
        except Exception as e:
            say(f":x: エラー: {str(e)}")

    @app.command("/milestone")
    def handle_milestone_command(ack, body, client):
        """マイルストーン追加モーダルを開く"""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=get_milestone_modal()
        )

    @app.view("milestone_submission")
    def handle_milestone_submission(ack, body, client, view):
        """マイルストーン登録処理"""
        ack()
        user_id = body["user"]["id"]
        values = view["state"]["values"]

        project_id = int(values["project_id_block"]["project_id"]["value"])
        milestone_name = values["milestone_name_block"]["milestone_name"]["value"]
        due_date_str = values["due_date_block"]["due_date"]["selected_date"]
        description = values["description_block"]["description"]["value"] or ""

        try:
            with get_db() as db:
                milestone = Milestone(
                    project_id=project_id,
                    milestone_name=milestone_name,
                    due_date=datetime.strptime(due_date_str, "%Y-%m-%d").date(),
                    description=description,
                    status="pending"
                )
                db.add(milestone)
                db.flush()
                milestone_id = milestone.milestone_id

            client.chat_postMessage(
                channel=user_id,
                text=f":white_check_mark: マイルストーンを追加しました\n"
                     f"*ID:* MS-{milestone_id}\n"
                     f"*名前:* {milestone_name}\n"
                     f"*期限:* {due_date_str}"
            )
        except Exception as e:
            client.chat_postMessage(
                channel=user_id,
                text=f":x: マイルストーン追加に失敗: {str(e)}"
            )

    @app.command("/task")
    def handle_task_command(ack, body, client):
        """タスク追加モーダルを開く"""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=get_task_modal()
        )

    @app.view("task_submission")
    def handle_task_submission(ack, body, client, view):
        """タスク登録処理"""
        ack()
        user_id = body["user"]["id"]
        values = view["state"]["values"]

        project_id = int(values["project_id_block"]["project_id"]["value"])
        task_name = values["task_name_block"]["task_name"]["value"]
        estimated_hours = values["estimated_hours_block"]["estimated_hours"]["value"]
        due_date_str = values["due_date_block"]["due_date"]["selected_date"]
        description = values["description_block"]["description"]["value"] or ""

        try:
            with get_db() as db:
                task = Task(
                    project_id=project_id,
                    task_name=task_name,
                    estimated_hours=float(estimated_hours) if estimated_hours else None,
                    due_date=datetime.strptime(due_date_str, "%Y-%m-%d").date() if due_date_str else None,
                    description=description,
                    status="todo"
                )
                db.add(task)
                db.flush()
                task_id = task.task_id

            client.chat_postMessage(
                channel=user_id,
                text=f":white_check_mark: タスクを追加しました\n"
                     f"*ID:* TASK-{task_id}\n"
                     f"*名前:* {task_name}\n"
                     f"*見積工数:* {estimated_hours}h"
            )
        except Exception as e:
            client.chat_postMessage(
                channel=user_id,
                text=f":x: タスク追加に失敗: {str(e)}"
            )

    @app.message(re.compile(r"^工数記録\s+(\d+)\s+([\d.]+)(?:\s+(.+))?$"))
    def handle_time_entry(message, say, context):
        """工数を記録: 工数記録 [タスクID] [時間] [説明]"""
        match = context["matches"]
        task_id = int(match[0])
        hours = float(match[1])
        description = match[2] if len(match) > 2 else ""

        try:
            with get_db() as db:
                task = db.query(Task).filter(Task.task_id == task_id).first()
                if not task:
                    say(f"タスクID {task_id} が見つかりません")
                    return

                entry = TimeEntry(
                    task_id=task_id,
                    project_id=task.project_id,
                    hours=hours,
                    description=description,
                    work_date=date.today()
                )
                db.add(entry)

                # タスクの実績工数を更新
                total_hours = sum(
                    float(e.hours) for e in task.time_entries
                ) + hours
                task.actual_hours = total_hours
                db.flush()

            say(f":clock3: 工数を記録しました\n"
                f"*タスク:* {task.task_name}\n"
                f"*記録時間:* {hours}h\n"
                f"*累計:* {total_hours}h")
        except Exception as e:
            say(f":x: 工数記録に失敗: {str(e)}")


def build_schedule_blocks(project, db):
    """工程表示用のブロックを構築"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📋 {project.project_name}", "emoji": True}
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*開始日:* {project.start_date or '未設定'}"},
                {"type": "mrkdwn", "text": f"*納期:* {project.deadline or '未設定'}"},
                {"type": "mrkdwn", "text": f"*見積工数:* {project.estimated_hours or 0}h"},
                {"type": "mrkdwn", "text": f"*実績工数:* {project.actual_hours or 0}h"},
            ]
        },
    ]

    milestones = db.query(Milestone).filter(
        Milestone.project_id == project.project_id
    ).order_by(Milestone.due_date).all()

    if milestones:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*🎯 マイルストーン*"}
        })

        for ms in milestones:
            status_emoji = {
                "pending": "⬜",
                "in_progress": "🔵",
                "completed": "✅",
                "delayed": "🔴"
            }.get(ms.status, "⬜")

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} *{ms.milestone_name}*\n期限: {ms.due_date}"
                }
            })

    return blocks


def build_task_list_blocks(tasks, project_id):
    """タスク一覧用のブロックを構築"""
    status_emoji = {
        "todo": "⬜",
        "in_progress": "🔵",
        "review": "🟡",
        "done": "✅"
    }

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📝 タスク一覧 (PRJ-{project_id:04d})", "emoji": True}
        },
        {"type": "divider"},
    ]

    for task in tasks:
        emoji = status_emoji.get(task.status, "⬜")
        hours_info = ""
        if task.estimated_hours:
            actual = task.actual_hours or 0
            hours_info = f" ({actual}/{task.estimated_hours}h)"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{task.task_name}*{hours_info}\n"
                       f"期限: {task.due_date or '未設定'} | ID: TASK-{task.task_id}"
            }
        })

    return blocks


def get_milestone_modal():
    """マイルストーン追加モーダル"""
    return {
        "type": "modal",
        "callback_id": "milestone_submission",
        "title": {"type": "plain_text", "text": "マイルストーン追加"},
        "submit": {"type": "plain_text", "text": "追加"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": [
            {
                "type": "input",
                "block_id": "project_id_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "project_id",
                    "placeholder": {"type": "plain_text", "text": "案件ID（数字）"}
                },
                "label": {"type": "plain_text", "text": "案件ID"}
            },
            {
                "type": "input",
                "block_id": "milestone_name_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "milestone_name",
                    "placeholder": {"type": "plain_text", "text": "例: 設計完了"}
                },
                "label": {"type": "plain_text", "text": "マイルストーン名"}
            },
            {
                "type": "input",
                "block_id": "due_date_block",
                "element": {
                    "type": "datepicker",
                    "action_id": "due_date",
                    "placeholder": {"type": "plain_text", "text": "期限日"}
                },
                "label": {"type": "plain_text", "text": "期限"}
            },
            {
                "type": "input",
                "block_id": "description_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "説明"}
                },
                "label": {"type": "plain_text", "text": "説明"}
            }
        ]
    }


def get_task_modal():
    """タスク追加モーダル"""
    return {
        "type": "modal",
        "callback_id": "task_submission",
        "title": {"type": "plain_text", "text": "タスク追加"},
        "submit": {"type": "plain_text", "text": "追加"},
        "close": {"type": "plain_text", "text": "キャンセル"},
        "blocks": [
            {
                "type": "input",
                "block_id": "project_id_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "project_id",
                    "placeholder": {"type": "plain_text", "text": "案件ID（数字）"}
                },
                "label": {"type": "plain_text", "text": "案件ID"}
            },
            {
                "type": "input",
                "block_id": "task_name_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "task_name",
                    "placeholder": {"type": "plain_text", "text": "例: API設計"}
                },
                "label": {"type": "plain_text", "text": "タスク名"}
            },
            {
                "type": "input",
                "block_id": "estimated_hours_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "estimated_hours",
                    "placeholder": {"type": "plain_text", "text": "例: 8"}
                },
                "label": {"type": "plain_text", "text": "見積工数（時間）"}
            },
            {
                "type": "input",
                "block_id": "due_date_block",
                "optional": True,
                "element": {
                    "type": "datepicker",
                    "action_id": "due_date",
                    "placeholder": {"type": "plain_text", "text": "期限日"}
                },
                "label": {"type": "plain_text", "text": "期限"}
            },
            {
                "type": "input",
                "block_id": "description_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "詳細説明"}
                },
                "label": {"type": "plain_text", "text": "説明"}
            }
        ]
    }
