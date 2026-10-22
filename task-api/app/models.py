from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), default="")
    status = Column(String(20), default="pending", nullable=False)
    priority = Column(String(20), default="medium", nullable=False)
    assignee = Column(String(100), default="")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
