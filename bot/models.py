"""SQLAlchemy Models for Freelance CRM"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime,
    Numeric, ForeignKey, create_engine, Computed
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
    start_date = Column(Date)
    deadline = Column(Date)
    actual_end_date = Column(Date)
    estimated_hours = Column(Numeric(10, 2))
    actual_hours = Column(Numeric(10, 2))
    status_id = Column(Integer, ForeignKey('project_statuses.status_id'))
    won_lost = Column(String(20))
    lost_reason = Column(Text)
    estimated_amount = Column(Numeric(12, 2))
    final_amount = Column(Numeric(12, 2))
    requirements = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="projects")
    acquisition_channel = relationship("AcquisitionChannel", back_populates="projects")
    status = relationship("ProjectStatus", back_populates="projects")
    estimate_items = relationship("EstimateItem", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    time_entries = relationship("TimeEntry", back_populates="project", cascade="all, delete-orphan")
    redmine_config = relationship("RedmineConfig", back_populates="project", uselist=False, cascade="all, delete-orphan")


class EstimateItem(Base):
    """見積明細"""
    __tablename__ = 'estimate_items'

    item_id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.project_id', ondelete='CASCADE'))
    item_name = Column(String(255), nullable=False)
    description = Column(Text)
    quantity = Column(Numeric(10, 2), default=1)
    unit = Column(String(50), default='式')
    unit_price = Column(Numeric(12, 2), nullable=False)
    amount = Column(Numeric(12, 2), Computed('quantity * unit_price'))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="estimate_items")


class Milestone(Base):
    """マイルストーン（工期管理）"""
    __tablename__ = 'milestones'

    milestone_id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.project_id', ondelete='CASCADE'))
    milestone_name = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(Date, nullable=False)
    completed_date = Column(Date)
    status = Column(String(50), default='pending')
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="milestones")
    tasks = relationship("Task", back_populates="milestone")


class Task(Base):
    """作業工程"""
    __tablename__ = 'tasks'

    task_id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.project_id', ondelete='CASCADE'))
    milestone_id = Column(Integer, ForeignKey('milestones.milestone_id', ondelete='SET NULL'))
    task_name = Column(String(255), nullable=False)
    description = Column(Text)
    assigned_to = Column(String(100))
    estimated_hours = Column(Numeric(10, 2))
    actual_hours = Column(Numeric(10, 2))
    start_date = Column(Date)
    due_date = Column(Date)
    completed_date = Column(Date)
    status = Column(String(50), default='todo')
    priority = Column(Integer, default=5)
    redmine_issue_id = Column(Integer)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    milestone = relationship("Milestone", back_populates="tasks")
    time_entries = relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan")


class TimeEntry(Base):
    """工数記録"""
    __tablename__ = 'time_entries'

    entry_id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.task_id', ondelete='CASCADE'))
    project_id = Column(Integer, ForeignKey('projects.project_id', ondelete='CASCADE'))
    hours = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    work_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="time_entries")
    project = relationship("Project", back_populates="time_entries")


class RedmineConfig(Base):
    """Redmine設定"""
    __tablename__ = 'redmine_config'

    config_id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.project_id', ondelete='CASCADE'), unique=True)
    redmine_url = Column(String(500), nullable=False)
    redmine_project_id = Column(String(100), nullable=False)
    api_key = Column(String(255))
    sync_enabled = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="redmine_config")


def init_db(database_url: str):
    """データベース初期化"""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """セッション取得"""
    Session = sessionmaker(bind=engine)
    return Session()
