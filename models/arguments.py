"""Argument-related Pydantic models with validation."""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


class Argument(BaseModel):
    """Represents a single argument in a debate."""
    speaker: str = Field(..., min_length=1, description="Name of the speaker")
    content: str = Field(..., min_length=1, description="Argument content")
    iteration: int = Field(..., ge=0, description="Debate iteration number")
    timestamp: datetime = Field(default_factory=datetime.now)
    references: List[str] = Field(
        default_factory=list,
        description="References to other speakers' arguments"
    )
    argument_type: str = Field(
        default="general",
        pattern="^(opening|rebuttal|closing|general)$",
        description="Type of argument"
    )

    @field_validator('content')
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Ensure argument has meaningful content."""
        if len(v.strip()) < 10:
            raise ValueError("Argument content must be at least 10 characters")
        return v.strip()

    @field_validator('references')
    @classmethod
    def validate_references(cls, v: List[str]) -> List[str]:
        """Ensure references are non-empty strings."""
        return [ref.strip() for ref in v if ref.strip()]
