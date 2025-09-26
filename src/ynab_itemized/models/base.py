"""Base models and utilities."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, Field


class BaseModel(PydanticBaseModel):
    """Base model with common fields and utilities."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(validate_assignment=True, use_enum_values=True)

    def dict_for_db(self) -> Dict[str, Any]:
        """Return dictionary suitable for database storage."""
        data = self.model_dump()
        # SQLAlchemy handles datetime objects directly, no conversion needed
        return data

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()
