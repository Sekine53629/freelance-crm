"""Database connection and operations"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import DATABASE_URL
from models import Base, Client, Project, AcquisitionChannel, Industry, ProjectStatus

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_db() -> Session:
    """データベースセッションのコンテキストマネージャー"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_database():
    """テーブル作成"""
    Base.metadata.create_all(engine)


# ======================
# クライアント操作
# ======================
def create_client(
    company_name: str,
    industry_id: int = None,
    company_size: str = None,
    contact_person: str = None
) -> Client:
    """クライアント作成"""
    with get_db() as db:
        client = Client(
            company_name=company_name,
            industry_id=industry_id,
            company_size=company_size,
            contact_person=contact_person
        )
        db.add(client)
        db.flush()
        return client


def get_client_by_name(company_name: str) -> Client:
    """会社名でクライアント検索"""
    with get_db() as db:
        return db.query(Client).filter(
            Client.company_name.ilike(f"%{company_name}%")
        ).first()


def get_or_create_client(company_name: str) -> tuple[Client, bool]:
    """クライアント取得または作成"""
    with get_db() as db:
        client = db.query(Client).filter(
            Client.company_name == company_name
        ).first()
        if client:
            return client, False
        client = Client(company_name=company_name)
        db.add(client)
        db.flush()
        return client, True


# ======================
# 案件操作
# ======================
def create_project(
    project_name: str,
    client_id: int = None,
    acquisition_channel_id: int = None,
    request_date=None,
    deadline=None,
    status_id: int = 1
) -> Project:
    """案件作成"""
    with get_db() as db:
        project = Project(
            project_name=project_name,
            client_id=client_id,
            acquisition_channel_id=acquisition_channel_id,
            request_date=request_date,
            deadline=deadline,
            status_id=status_id
        )
        db.add(project)
        db.flush()
        return project


def get_recent_projects(limit: int = 10) -> list[Project]:
    """最近の案件取得"""
    with get_db() as db:
        return db.query(Project).order_by(
            Project.created_at.desc()
        ).limit(limit).all()


def update_project_status(project_id: int, status_id: int) -> Project:
    """案件ステータス更新"""
    with get_db() as db:
        project = db.query(Project).filter(
            Project.project_id == project_id
        ).first()
        if project:
            project.status_id = status_id
        return project


# ======================
# マスタデータ取得
# ======================
def get_all_channels() -> list[AcquisitionChannel]:
    """全獲得チャネル取得"""
    with get_db() as db:
        return db.query(AcquisitionChannel).filter(
            AcquisitionChannel.is_active == True
        ).all()


def get_all_industries() -> list[Industry]:
    """全業種取得"""
    with get_db() as db:
        return db.query(Industry).all()


def get_all_statuses() -> list[ProjectStatus]:
    """全ステータス取得"""
    with get_db() as db:
        return db.query(ProjectStatus).order_by(
            ProjectStatus.status_order
        ).all()
