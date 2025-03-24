from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskModel(BaseModel):
    title: str = Field(..., example="Купить продукты")
    user_id: int = Field(..., example="my_id")
    description: Optional[str] = Field(None, example="Купить хлеб, молоко и яйца")
    deadline: datetime = Field(..., example="2025-03-12T15:00:00")
    completed: bool = Field(default=False)
