"""Database connection and session management"""
import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from .models import Base

# .envファイルを読み込み
load_dotenv()

_engine = None
_SessionLocal = None


def get_engine():
    """データベースエンジンを取得（シングルトン）"""
    global _engine
    if _engine is None:
        database_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://freelance_user:freelance_pass@localhost:5432/freelance_crm"
        )
        _engine = create_engine(database_url)
    return _engine


def get_session_factory():
    """セッションファクトリを取得"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """データベースセッションのコンテキストマネージャー"""
    SessionLocal = get_session_factory()
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
    Base.metadata.create_all(get_engine())
