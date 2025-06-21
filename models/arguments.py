"""Argument-related Pydantic models with validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

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
    
    def extract_key_points(self) -> List[str]:
        """Extract key points from the argument (placeholder for NLP)."""
        # Simple implementation - split by sentences
        sentences = self.content.split('.')
        return [s.strip() for s in sentences if len(s.strip()) > 20]


class ArgumentHistory(BaseModel):
    """Tracks the history of arguments for a participant."""
    participant: str = Field(..., min_length=1, description="Participant name")
    arguments: List[Argument] = Field(
        default_factory=list,
        description="Chronological list of arguments"
    )
    total_word_count: int = Field(default=0, ge=0, description="Total words spoken")
    key_themes: List[str] = Field(
        default_factory=list,
        description="Key themes in arguments"
    )
    stance_evolution: Dict[str, Any] = Field(
        default_factory=dict,
        description="How stance evolved over time"
    )
    
    def add_argument(self, argument: Argument) -> None:
        """Add a new argument to the history."""
        if argument.speaker != self.participant:
            raise ValueError(
                f"Argument speaker '{argument.speaker}' doesn't match "
                f"participant '{self.participant}'"
            )
        
        self.arguments.append(argument)
        self.total_word_count += len(argument.content.split())
    
    def get_arguments_by_type(self, arg_type: str) -> List[Argument]:
        """Get all arguments of a specific type."""
        return [arg for arg in self.arguments if arg.argument_type == arg_type]
    
    def get_latest_position(self) -> Optional[str]:
        """Get the most recent stated position."""
        if not self.arguments:
            return None
        return self.arguments[-1].content
    
    @field_validator('arguments')
    @classmethod
    def validate_arguments_consistency(cls, v: List[Argument]) -> List[Argument]:
        """Ensure arguments are from the same speaker."""
        if not v:
            return v
        
        speakers = {arg.speaker for arg in v}
        if len(speakers) > 1:
            raise ValueError("All arguments must be from the same speaker")
        
        return v


class DebateContext(BaseModel):
    """Context for generating new arguments."""
    current_iteration: int = Field(..., ge=0, description="Current debate iteration")
    previous_arguments: Dict[str, List[Argument]] = Field(
        default_factory=dict,
        description="Previous arguments by participant"
    )
    question: str = Field(..., min_length=1, description="Debate question")
    debate_phase: str = Field(
        default="main",
        pattern="^(opening|main|closing|voting)$",
        description="Current phase of debate"
    )
    key_contentions: List[str] = Field(
        default_factory=list,
        description="Main points of contention"
    )
    
    def get_recent_arguments(self, limit: int = 3) -> List[Argument]:
        """Get the most recent arguments from all participants."""
        all_args = []
        for participant_args in self.previous_arguments.values():
            all_args.extend(participant_args)
        
        # Sort by timestamp and return most recent
        sorted_args = sorted(all_args, key=lambda x: x.timestamp, reverse=True)
        return sorted_args[:limit]
    
    def get_participant_history(self, participant: str) -> List[Argument]:
        """Get all arguments from a specific participant."""
        return self.previous_arguments.get(participant, [])
    
    def summarize_for_participant(self, participant: str) -> str:
        """Create a summary of the debate for a participant."""
        summary_parts = [f"Debate Question: {self.question}"]
        summary_parts.append(f"Current Phase: {self.debate_phase}")
        summary_parts.append(f"Iteration: {self.current_iteration + 1}")
        
        if self.key_contentions:
            summary_parts.append("\nKey Points of Contention:")
            for contention in self.key_contentions:
                summary_parts.append(f"- {contention}")
        
        # Add recent arguments from others
        recent = self.get_recent_arguments()
        other_args = [arg for arg in recent if arg.speaker != participant]
        
        if other_args:
            summary_parts.append("\nRecent Arguments:")
            for arg in other_args[:3]:
                summary_parts.append(f"\n{arg.speaker}: {arg.content[:200]}...")
        
        return "\n".join(summary_parts)