"""SQLAlchemy Models for Freelance CRM"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime,
    Numeric, ForeignKey, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class AcquisitionChannel(Base):
    """獲得チャネルマスタ"""
    __tablename__ = 'acquisition_channels'

    channel_id = Column(Integer, primary_key=True)
    channel_name = Column(String(100), unique=True, nullable=False)
    channel_category = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="acquisition_channel")


class Industry(Base):
    """業種マスタ"""
    __tablename__ = 'industries'

    industry_id = Column(Integer, primary_key=True)
    industry_name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    clients = relationship("Client", back_populates="industry")


class ProjectStatus(Base):
    """案件ステータスマスタ"""
    __tablename__ = 'project_statuses'

    status_id = Column(Integer, primary_key=True)
    status_name = Column(String(50), unique=True, nullable=False)
    status_order = Column(Integer, default=0)
    is_terminal = Column(Boolean, default=False)

    projects = relationship("Project", back_populates="status")


class Client(Base):
    """クライアント"""
    __tablename__ = 'clients'

    client_id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=False)
    industry_id = Column(Integer, ForeignKey('industries.industry_id'))
    company_size = Column(String(50))
    contact_person = Column(String(100))
    contact_email = Column(String(255))
    payment_due_day = Column(Integer)
    payment_terms = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    industry = relationship("Industry", back_populates="clients")
    projects = relationship("Project", back_populates="client")


class Project(Base):
    """案件"""
    __tablename__ = 'projects'

    project_id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.client_id'))
    project_name = Column(String(255), nullable=False)
    acquisition_channel_id = Column(Integer, ForeignKey('acquisition_channels.channel_id'))
    contact_method = Column(String(100))
    first_contact_date = Column(Date)
    request_date = Column(Date)
    deadline = Column(Date)
    estimated_hours = Column(Numeric(10, 2))
    status_id = Column(Integer, ForeignKey('project_statuses.status_id'))
    won_lost = Column(String(20))
    lost_reason = Column(Text)
    estimated_amount = Column(Numeric(12, 2))
    requirements = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="projects")
    acquisition_channel = relationship("AcquisitionChannel", back_populates="projects")
    status = relationship("ProjectStatus", back_populates="projects")


def init_db(database_url: str):
    """データベース初期化"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """セッション取得"""
    Session = sessionmaker(bind=engine)
    return Session()
