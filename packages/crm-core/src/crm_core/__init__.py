"""CRM Core - Models and Database"""
from .models import (
    Base,
    AcquisitionChannel,
    Industry,
    ProjectStatus,
    Client,
    Project,
    EstimateItem,
    Milestone,
    Task,
    TimeEntry,
    RedmineConfig,
)
from .database import get_db, init_database, get_engine

__all__ = [
    "Base",
    "AcquisitionChannel",
    "Industry",
    "ProjectStatus",
    "Client",
    "Project",
    "EstimateItem",
    "Milestone",
    "Task",
    "TimeEntry",
    "RedmineConfig",
    "get_db",
    "init_database",
    "get_engine",
]
