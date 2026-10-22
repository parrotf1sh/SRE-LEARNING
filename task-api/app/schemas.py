from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    pending = "pending"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    status: TaskStatus = TaskStatus.pending
    priority: TaskPriority = TaskPriority.medium
    assignee: str = Field(default="", max_length=100)


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    assignee: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CacheMeta(BaseModel):
    hit: bool
    ttl: int


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
    cache: CacheMeta
