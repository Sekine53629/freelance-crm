"""月次レポート生成モジュール"""
from datetime import datetime, date
from calendar import monthrange
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Project, Client, AcquisitionChannel


@dataclass
class MonthlyStats:
    """月次統計データ"""
    year: int
    month: int
    total_projects: int
    new_projects: int
    won_projects: int
    lost_projects: int
    in_progress: int
    total_estimated: float
    won_amount: float
    win_rate: float
    channel_breakdown: dict
    status_breakdown: dict
    top_clients: list


class MonthlyReportGenerator:
    """月次レポート生成クラス"""

    # ステータスマッピング
    STATUS_MAP = {
        1: "問い合わせ", 2: "見積中", 3: "見積提出済", 4: "交渉中", 5: "受注確定",
        6: "進行中", 7: "レビュー中", 8: "納品済", 9: "完了", 10: "失注", 11: "キャンセル"
    }

    CHANNEL_MAP = {
        1: "ランサーズ", 2: "クラウドワークス", 3: "ココナラ", 4: "Twitter/X",
        5: "LinkedIn", 6: "紹介", 7: "直接営業", 8: "その他"
    }

    # 受注系ステータス
    WON_STATUSES = {5, 6, 7, 8, 9}  # 受注確定〜完了
    LOST_STATUSES = {10, 11}  # 失注、キャンセル
    TERMINAL_STATUSES = {9, 10, 11}  # 完了、失注、キャンセル

    def __init__(self, db: Session):
        self.db = db

    def get_month_range(self, year: int, month: int) -> tuple[date, date]:
        """月の開始日と終了日を取得"""
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        return start_date, end_date

    def collect_stats(self, year: int, month: int) -> MonthlyStats:
        """月次統計を収集"""
        start_date, end_date = self.get_month_range(year, month)

        # 当月に作成された案件
        new_projects = self.db.query(Project).filter(
            and_(
                func.date(Project.created_at) >= start_date,
                func.date(Project.created_at) <= end_date
            )
        ).all()

        # 全案件（進行中含む）
        all_projects = self.db.query(Project).all()

        # 当月の新規案件数
        new_count = len(new_projects)

        # 受注・失注カウント（当月作成分）
        won_count = sum(1 for p in new_projects if p.status_id in self.WON_STATUSES)
        lost_count = sum(1 for p in new_projects if p.status_id in self.LOST_STATUSES)

        # 進行中案件（全体）
        in_progress = sum(1 for p in all_projects if p.status_id not in self.TERMINAL_STATUSES)

        # 金額集計
        total_estimated = sum(
            float(p.estimated_amount or 0) for p in new_projects
        )
        won_amount = sum(
            float(p.estimated_amount or 0) for p in new_projects
            if p.status_id in self.WON_STATUSES
        )

        # 受注率計算
        decided = won_count + lost_count
        win_rate = (won_count / decided * 100) if decided > 0 else 0.0

        # チャネル別内訳
        channel_breakdown = {}
        for p in new_projects:
            ch_name = self.CHANNEL_MAP.get(p.acquisition_channel_id, "その他")
            if ch_name not in channel_breakdown:
                channel_breakdown[ch_name] = {"count": 0, "amount": 0}
            channel_breakdown[ch_name]["count"] += 1
            channel_breakdown[ch_name]["amount"] += float(p.estimated_amount or 0)

        # ステータス別内訳
        status_breakdown = {}
        for p in new_projects:
            st_name = self.STATUS_MAP.get(p.status_id, "不明")
            status_breakdown[st_name] = status_breakdown.get(st_name, 0) + 1

        # トップクライアント（当月案件数順）
        client_counts = {}
        for p in new_projects:
            if p.client:
                name = p.client.company_name
                if name not in client_counts:
                    client_counts[name] = {"count": 0, "amount": 0}
                client_counts[name]["count"] += 1
                client_counts[name]["amount"] += float(p.estimated_amount or 0)

        top_clients = sorted(
            client_counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:5]

        return MonthlyStats(
            year=year,
            month=month,
            total_projects=len(all_projects),
            new_projects=new_count,
            won_projects=won_count,
            lost_projects=lost_count,
            in_progress=in_progress,
            total_estimated=total_estimated,
            won_amount=won_amount,
            win_rate=win_rate,
            channel_breakdown=channel_breakdown,
            status_breakdown=status_breakdown,
            top_clients=top_clients
        )

    def generate_markdown(self, stats: MonthlyStats) -> str:
        """Markdown形式のレポートを生成"""
        lines = [
            f"# 月次営業レポート {stats.year}年{stats.month}月",
            "",
            "## サマリー",
            "",
            "| 指標 | 値 |",
            "|------|-----|",
            f"| 新規案件数 | {stats.new_projects}件 |",
            f"| 受注数 | {stats.won_projects}件 |",
            f"| 失注数 | {stats.lost_projects}件 |",
            f"| 受注率 | {stats.win_rate:.1f}% |",
            f"| 進行中案件 | {stats.in_progress}件 |",
            f"| 見積総額 | ¥{stats.total_estimated:,.0f} |",
            f"| 受注金額 | ¥{stats.won_amount:,.0f} |",
            "",
        ]

        # チャネル別
        if stats.channel_breakdown:
            lines.extend([
                "## チャネル別実績",
                "",
                "| チャネル | 件数 | 金額 |",
                "|----------|------|------|",
            ])
            for ch, data in sorted(stats.channel_breakdown.items(), key=lambda x: x[1]["count"], reverse=True):
                lines.append(f"| {ch} | {data['count']}件 | ¥{data['amount']:,.0f} |")
            lines.append("")

        # ステータス別
        if stats.status_breakdown:
            lines.extend([
                "## ステータス別内訳",
                "",
                "| ステータス | 件数 |",
                "|------------|------|",
            ])
            for st, count in sorted(stats.status_breakdown.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"| {st} | {count}件 |")
            lines.append("")

        # トップクライアント
        if stats.top_clients:
            lines.extend([
                "## トップクライアント",
                "",
                "| クライアント | 案件数 | 金額 |",
                "|--------------|--------|------|",
            ])
            for name, data in stats.top_clients:
                lines.append(f"| {name} | {data['count']}件 | ¥{data['amount']:,.0f} |")
            lines.append("")

        lines.extend([
            "---",
            f"*生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        ])

        return "\n".join(lines)

    def generate_slack_blocks(self, stats: MonthlyStats) -> list:
        """Slack Block Kit形式のレポートを生成"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 月次営業レポート {stats.year}年{stats.month}月",
                    "emoji": True
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📈 サマリー*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*新規案件*\n{stats.new_projects}件"},
                    {"type": "mrkdwn", "text": f"*受注*\n{stats.won_projects}件"},
                    {"type": "mrkdwn", "text": f"*失注*\n{stats.lost_projects}件"},
                    {"type": "mrkdwn", "text": f"*受注率*\n{stats.win_rate:.1f}%"},
                ]
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*進行中*\n{stats.in_progress}件"},
                    {"type": "mrkdwn", "text": f"*見積総額*\n¥{stats.total_estimated:,.0f}"},
                    {"type": "mrkdwn", "text": f"*受注金額*\n¥{stats.won_amount:,.0f}"},
                ]
            },
        ]

        # チャネル別
        if stats.channel_breakdown:
            channel_text = "\n".join([
                f"• {ch}: {data['count']}件 (¥{data['amount']:,.0f})"
                for ch, data in sorted(stats.channel_breakdown.items(), key=lambda x: x[1]["count"], reverse=True)
            ])
            blocks.extend([
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📡 チャネル別*\n{channel_text}"
                    }
                }
            ])

        # トップクライアント
        if stats.top_clients:
            client_text = "\n".join([
                f"• {name}: {data['count']}件"
                for name, data in stats.top_clients[:3]
            ])
            blocks.extend([
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🏢 トップクライアント*\n{client_text}"
                    }
                }
            ])

        blocks.extend([
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                ]
            }
        ])

        return blocks

    def generate(self, year: Optional[int] = None, month: Optional[int] = None) -> tuple[MonthlyStats, str, list]:
        """レポートを生成して統計、Markdown、Slackブロックを返す"""
        if year is None or month is None:
            today = date.today()
            # 前月のレポートを生成
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

        stats = self.collect_stats(year, month)
        markdown = self.generate_markdown(stats)
        blocks = self.generate_slack_blocks(stats)

        return stats, markdown, blocks
