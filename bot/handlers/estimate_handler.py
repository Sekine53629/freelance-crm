"""見積もり機能ハンドラー"""
from datetime import datetime
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db
from models import Project, EstimateItem


def register_estimate_handlers(app):
    """見積もり関連のハンドラーを登録"""

    @app.message(re.compile(r"^見積\s+(\d+)$"))
    def handle_show_estimate(message, say, context):
        """案件の見積一覧を表示"""
        match = context["matches"]
        project_id = int(match[0])

        try:
            with get_db() as db:
                project = db.query(Project).filter(Project.project_id == project_id).first()
                if not project:
                    say(f"案件ID {project_id} が見つかりません")
                    return

                items = db.query(EstimateItem).filter(
                    EstimateItem.project_id == project_id
                ).order_by(EstimateItem.sort_order).all()

                blocks = build_estimate_blocks(project, items)
                say(text=f"見積書 - {project.project_name}", blocks=blocks)
        except Exception as e:
            say(f":x: エラー: {str(e)}")

    @app.command("/estimate")
    def handle_estimate_command(ack, body, client):
        """見積明細追加モーダルを開く"""
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=get_estimate_modal()
        )

    @app.view("estimate_submission")
    def handle_estimate_submission(ack, body, client, view):
        """見積明細登録処理"""
        ack()
        user_id = body["user"]["id"]
        values = view["state"]["values"]

        project_id = int(values["project_id_block"]["project_id"]["value"])
        item_name = values["item_name_block"]["item_name"]["value"]
        quantity = float(values["quantity_block"]["quantity"]["value"] or "1")
        unit = values["unit_block"]["unit"]["value"] or "式"
        unit_price = float(values["unit_price_block"]["unit_price"]["value"])
        description = values["description_block"]["description"]["value"] or ""

        try:
            with get_db() as db:
                # 明細追加
                item = EstimateItem(
                    project_id=project_id,
                    item_name=item_name,
                    quantity=quantity,
                    unit=unit,
                    unit_price=unit_price,
                    description=description
                )
                db.add(item)
                db.flush()

                # 案件の見積総額を更新
                total = db.query(EstimateItem).filter(
                    EstimateItem.project_id == project_id
                ).all()
                total_amount = sum(float(i.quantity) * float(i.unit_price) for i in total)

                project = db.query(Project).filter(Project.project_id == project_id).first()
                if project:
                    project.estimated_amount = total_amount

                item_id = item.item_id

            client.chat_postMessage(
                channel=user_id,
                text=f":white_check_mark: 見積明細を追加しました\n"
                     f"*項目:* {item_name}\n"
                     f"*数量:* {quantity} {unit}\n"
                     f"*単価:* ¥{unit_price:,.0f}\n"
                     f"*金額:* ¥{quantity * unit_price:,.0f}\n"
                     f"*見積総額:* ¥{total_amount:,.0f}"
            )
        except Exception as e:
            client.chat_postMessage(
                channel=user_id,
                text=f":x: 見積追加に失敗: {str(e)}"
            )

    @app.message(re.compile(r"^見積削除\s+(\d+)$"))
    def handle_delete_estimate_item(message, say, context):
        """見積明細を削除: 見積削除 [明細ID]"""
        match = context["matches"]
        item_id = int(match[0])

        try:
            with get_db() as db:
                item = db.query(EstimateItem).filter(EstimateItem.item_id == item_id).first()
                if not item:
                    say(f"明細ID {item_id} が見つかりません")
                    return

                project_id = item.project_id
                item_name = item.item_name
                db.delete(item)
                db.flush()

                # 見積総額を再計算
                remaining = db.query(EstimateItem).filter(
                    EstimateItem.project_id == project_id
                ).all()
                total_amount = sum(float(i.quantity) * float(i.unit_price) for i in remaining)

                project = db.query(Project).filter(Project.project_id == project_id).first()
                if project:
                    project.estimated_amount = total_amount

            say(f":wastebasket: 見積明細を削除しました\n"
                f"*削除項目:* {item_name}\n"
                f"*新しい見積総額:* ¥{total_amount:,.0f}")
        except Exception as e:
            say(f":x: 削除に失敗: {str(e)}")


def build_estimate_blocks(project, items):
    """見積表示用のブロックを構築"""
    client_name = project.client.company_name if project.client else "不明"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📄 見積書", "emoji": True}
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*案件:* {project.project_name}"},
                {"type": "mrkdwn", "text": f"*クライアント:* {client_name}"},
            ]
        },
        {"type": "divider"},
    ]

    if items:
        total = 0
        for item in items:
            amount = float(item.quantity) * float(item.unit_price)
            total += amount
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{item.item_name}*\n"
                           f"{item.quantity} {item.unit} × ¥{float(item.unit_price):,.0f} = *¥{amount:,.0f}*"
                },
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "削除"},
                    "action_id": f"delete_estimate_{item.item_id}",
                    "style": "danger"
                }
            })

        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*合計金額: ¥{total:,.0f}*"
            }
        })
    else:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_見積明細がありません_"}
        })

    return blocks


def get_estimate_modal():
    """見積明細追加モーダル"""
    return {
        "type": "modal",
        "callback_id": "estimate_submission",
        "title": {"type": "plain_text", "text": "見積明細追加"},
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
                "block_id": "item_name_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "item_name",
                    "placeholder": {"type": "plain_text", "text": "例: システム設計"}
                },
                "label": {"type": "plain_text", "text": "項目名"}
            },
            {
                "type": "input",
                "block_id": "quantity_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "quantity",
                    "placeholder": {"type": "plain_text", "text": "例: 1"}
                },
                "label": {"type": "plain_text", "text": "数量（デフォルト: 1）"}
            },
            {
                "type": "input",
                "block_id": "unit_block",
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": "unit",
                    "placeholder": {"type": "plain_text", "text": "例: 式, 人日, 時間"}
                },
                "label": {"type": "plain_text", "text": "単位（デフォルト: 式）"}
            },
            {
                "type": "input",
                "block_id": "unit_price_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "unit_price",
                    "placeholder": {"type": "plain_text", "text": "例: 100000"}
                },
                "label": {"type": "plain_text", "text": "単価（円）"}
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
