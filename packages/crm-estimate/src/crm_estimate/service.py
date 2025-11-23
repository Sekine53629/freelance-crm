"""見積サービス"""
from typing import Optional
from crm_core import get_db, Project, EstimateItem


class EstimateService:
    """見積管理サービス"""

    @staticmethod
    def get_estimate(project_id: int) -> tuple[Optional[Project], list[EstimateItem]]:
        """案件の見積を取得"""
        with get_db() as db:
            project = db.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                return None, []
            items = db.query(EstimateItem).filter(
                EstimateItem.project_id == project_id
            ).order_by(EstimateItem.sort_order).all()
            return project, items

    @staticmethod
    def add_item(
        project_id: int,
        item_name: str,
        unit_price: float,
        quantity: float = 1,
        unit: str = "式",
        description: str = ""
    ) -> EstimateItem:
        """見積明細を追加"""
        with get_db() as db:
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

            # 見積総額を更新
            total = sum(
                float(i.quantity) * float(i.unit_price)
                for i in db.query(EstimateItem).filter(
                    EstimateItem.project_id == project_id
                ).all()
            )
            project = db.query(Project).filter(Project.project_id == project_id).first()
            if project:
                project.estimated_amount = total

            return item

    @staticmethod
    def delete_item(item_id: int) -> tuple[bool, float]:
        """見積明細を削除し、新しい合計を返す"""
        with get_db() as db:
            item = db.query(EstimateItem).filter(EstimateItem.item_id == item_id).first()
            if not item:
                return False, 0

            project_id = item.project_id
            db.delete(item)
            db.flush()

            # 見積総額を再計算
            remaining = db.query(EstimateItem).filter(
                EstimateItem.project_id == project_id
            ).all()
            total = sum(float(i.quantity) * float(i.unit_price) for i in remaining)

            project = db.query(Project).filter(Project.project_id == project_id).first()
            if project:
                project.estimated_amount = total

            return True, total

    @staticmethod
    def calculate_total(project_id: int) -> float:
        """見積合計を計算"""
        with get_db() as db:
            items = db.query(EstimateItem).filter(
                EstimateItem.project_id == project_id
            ).all()
            return sum(float(i.quantity) * float(i.unit_price) for i in items)
