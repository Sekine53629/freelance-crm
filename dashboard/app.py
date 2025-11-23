"""Freelance CRM Dashboard - Streamlit App"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
import os
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# プロジェクトルートを取得
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "bot"))

from models import Client, Project

# データベース接続
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://freelance_user:freelance_pass@localhost:5432/freelance_crm")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ページ設定
st.set_page_config(
    page_title="Freelance CRM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# カスタムCSS - ダークモード対応 & コンパクトUI
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    /* KPIカード - ダークモード対応 */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
        padding: 1rem;
        border-radius: 0.75rem;
        border: 1px solid #3d7ab5;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    [data-testid="stMetric"] label {
        color: #a0c4e8 !important;
        font-size: 0.9rem !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.8rem !important;
        font-weight: bold;
    }
    /* 見出し */
    h5 {
        color: #e0e0e0 !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# マッピング
CHANNEL_MAP = {1: "ランサーズ", 2: "クラウドワークス", 3: "ココナラ", 4: "Twitter/X",
               5: "LinkedIn", 6: "紹介", 7: "直接営業", 8: "その他"}
STATUS_MAP = {1: "問い合わせ", 2: "見積中", 3: "見積提出済", 4: "交渉中", 5: "受注確定",
              6: "進行中", 7: "レビュー中", 8: "納品済", 9: "完了", 10: "失注", 11: "キャンセル"}


def load_data():
    with get_db() as db:
        projects = db.query(Project).all()
        data = []
        for p in projects:
            data.append({
                "project_id": p.project_id,
                "project_name": p.project_name,
                "client_name": p.client.company_name if p.client else "不明",
                "channel_id": p.acquisition_channel_id,
                "channel_name": CHANNEL_MAP.get(p.acquisition_channel_id, "その他"),
                "status_id": p.status_id,
                "status_name": STATUS_MAP.get(p.status_id, "不明"),
                "request_date": p.request_date,
                "deadline": p.deadline,
                "estimated_amount": float(p.estimated_amount) if p.estimated_amount else 0,
                "created_at": p.created_at
            })
        return pd.DataFrame(data)


def main():
    # タイトル行 - スタイリッシュなヘッダー
    st.markdown("""
    <div style="
        background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        padding: 1rem 2rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    ">
        <h1 style="
            color: white;
            margin: 0;
            font-size: 1.8rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        ">
            ⚡ FREELANCE CRM
            <span style="font-size: 1rem; font-weight: 400; opacity: 0.9; margin-left: 1rem;">
                Sales Analytics Dashboard
            </span>
        </h1>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()

    if df.empty:
        st.info("案件がありません。Slackで `/project` を使って登録してください。")
        return

    # ===== 上段: KPI =====
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("総案件数", len(df))
    with col2:
        st.metric("進行中", len(df[~df["status_id"].isin([9, 10, 11])]))
    with col3:
        st.metric("クライアント", df["client_name"].nunique())
    with col4:
        st.metric("見積総額", f"¥{df['estimated_amount'].sum():,.0f}")

    # ===== 中段: グラフ2つ + テーブル =====
    col_chart1, col_chart2, col_table = st.columns([1, 1, 2])

    with col_chart1:
        st.markdown("##### チャネル別")
        channel_counts = df["channel_name"].value_counts().reset_index()
        channel_counts.columns = ["チャネル", "件数"]
        fig1 = px.pie(channel_counts, values="件数", names="チャネル", hole=0.5,
                      color_discrete_sequence=px.colors.qualitative.Set2)
        fig1.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0')
        )
        fig1.update_traces(textposition='inside', textinfo='percent+label', textfont_size=11)
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        st.markdown("##### ステータス別")
        status_counts = df["status_name"].value_counts().reset_index()
        status_counts.columns = ["ステータス", "件数"]
        fig2 = px.bar(status_counts, x="ステータス", y="件数", color="ステータス",
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(
            margin=dict(t=10, b=50, l=10, r=10),
            height=300,
            showlegend=False,
            xaxis_tickangle=-45,
            xaxis_title="",
            yaxis_title="",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0'),
            xaxis=dict(gridcolor='#444'),
            yaxis=dict(gridcolor='#444')
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_table:
        st.markdown("##### 案件一覧")
        display_df = df[["project_id", "project_name", "client_name", "channel_name", "status_name", "deadline"]].copy()
        display_df.columns = ["ID", "案件名", "クライアント", "チャネル", "ステータス", "納期"]
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=300)

    # ===== 下段: 月別推移（あれば） =====
    if df["request_date"].notna().any():
        df_date = df[df["request_date"].notna()].copy()
        df_date["month"] = pd.to_datetime(df_date["request_date"]).dt.to_period("M").astype(str)
        monthly = df_date.groupby("month").size().reset_index(name="件数")

        st.markdown("##### 月別案件推移")
        fig3 = px.line(monthly, x="month", y="件数", markers=True,
                       line_shape='spline', color_discrete_sequence=['#4fc3f7'])
        fig3.update_layout(
            margin=dict(t=10, b=30, l=40, r=10),
            height=180,
            xaxis_title="",
            yaxis_title="",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e0e0e0'),
            xaxis=dict(gridcolor='#444'),
            yaxis=dict(gridcolor='#444')
        )
        st.plotly_chart(fig3, use_container_width=True)

    # フッター
    st.caption(f"更新: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
