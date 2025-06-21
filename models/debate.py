"""Debate-related Pydantic models with validation."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class DebateConfig(BaseModel):
    """Configuration for the debate system."""
    # Voting configuration
    voting_enabled: bool = Field(default=True, description="Enable voting system")
    consensus_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Percentage of max points needed for consensus"
    )
    voting_start_iteration: int = Field(
        default=2,
        ge=0,
        description="Which iteration voting starts (0-indexed)"
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum rounds to prevent infinite loops"
    )
    
    # Scoring system
    scoring_system: Dict[int, int] = Field(
        default_factory=lambda: {1: 4, 2: 3, 3: 2, 4: 1},
        description="Rank position to points mapping"
    )
    
    # Judge configuration
    judge_can_override: bool = Field(
        default=True,
        description="Whether judge can override voting consensus"
    )
    override_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Judge conviction needed to override"
    )
    
    # Model configuration
    allow_local_models: bool = Field(
        default=True,
        description="Allow use of local LLM models"
    )
    local_model_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout for local model requests in seconds"
    )
    
    # Mode configuration
    classic_mode: bool = Field(
        default=False,
        description="Use classic 3-round format without voting"
    )
    
    # File saving
    save_enabled: bool = Field(
        default=True,
        description="Enable automatic debate saving"
    )
    save_directory: str = Field(
        default="debates",
        description="Directory to save debate files"
    )
    
    # Personality voting traits defaults
    default_voting_traits: Dict[str, int] = Field(
        default_factory=lambda: {"fairness": 7, "self_confidence": 5},
        description="Default voting trait values"
    )
    
    @field_validator('scoring_system')
    @classmethod
    def validate_scoring_system(cls, v: Dict[int, int]) -> Dict[int, int]:
        """Ensure scoring system is valid."""
        if not v:
            raise ValueError("Scoring system cannot be empty")
        
        # Check for sequential keys
        keys = sorted(v.keys())
        if keys != list(range(1, len(keys) + 1)):
            raise ValueError("Scoring system must have sequential keys starting from 1")
        
        # Ensure positive points
        for rank, points in v.items():
            if points <= 0:
                raise ValueError(f"Points for rank {rank} must be positive")
        
        return v
    
    @model_validator(mode='after')
    def validate_thresholds(self) -> 'DebateConfig':
        """Ensure thresholds are logical."""
        if self.override_threshold < self.consensus_threshold:
            raise ValueError("Judge override threshold should be >= consensus threshold")
        return self


class DebateIteration(BaseModel):
    """Data for a single debate iteration."""
    iteration_number: int = Field(..., ge=0, description="Iteration index")
    question: str = Field(..., min_length=1, description="Debate question")
    arguments: Dict[str, str] = Field(..., description="Participant name to argument mapping")
    timestamp: datetime = Field(default_factory=datetime.now)
    votes: Optional[List[Dict[str, Any]]] = Field(None, description="Votes cast this iteration")
    consensus_reached: bool = Field(default=False, description="Whether consensus was achieved")
    winner: Optional[str] = Field(None, description="Winner if consensus reached")
    
    @field_validator('arguments')
    @classmethod
    def validate_arguments(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Ensure all arguments are non-empty."""
        if not v:
            raise ValueError("Arguments cannot be empty")
        
        for participant, argument in v.items():
            if not participant.strip():
                raise ValueError("Participant name cannot be empty")
            if not argument.strip():
                raise ValueError(f"Argument for {participant} cannot be empty")
        
        return v
    
    @model_validator(mode='after')
    def validate_voting_consistency(self) -> 'DebateIteration':
        """Ensure voting data is consistent."""
        if self.consensus_reached and not self.winner:
            raise ValueError("Winner must be specified when consensus is reached")
        
        if self.votes and len(self.votes) != len(self.arguments):
            raise ValueError("Number of votes must match number of participants")
        
        return self


class DebateState(BaseModel):
    """Complete state of a debate."""
    debate_id: str = Field(..., min_length=1, description="Unique debate identifier")
    question: str = Field(..., min_length=1, description="Main debate question")
    participants: List[str] = Field(..., min_length=2, description="List of participant names")
    iterations: List[DebateIteration] = Field(default_factory=list, description="All debate iterations")
    config: DebateConfig = Field(default_factory=DebateConfig, description="Debate configuration")
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = Field(None)
    final_verdict: Optional[str] = Field(None, description="Judge's final verdict")
    ai_generated_title: Optional[str] = Field(None, description="AI-generated debate title")
    
    @field_validator('participants')
    @classmethod
    def validate_participants(cls, v: List[str]) -> List[str]:
        """Ensure participant list is valid."""
        if len(v) < 2:
            raise ValueError("Debate requires at least 2 participants")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Participant names must be unique")
        
        # Ensure non-empty names
        for name in v:
            if not name.strip():
                raise ValueError("Participant names cannot be empty")
        
        return v
    
    @model_validator(mode='after')
    def validate_state_consistency(self) -> 'DebateState':
        """Ensure debate state is internally consistent."""
        # If ended, must have end_time
        if self.final_verdict and not self.end_time:
            self.end_time = datetime.now()
        
        # Validate iteration participants match debate participants
        for iteration in self.iterations:
            arg_participants = set(iteration.arguments.keys())
            expected_participants = set(self.participants)
            
            if arg_participants != expected_participants:
                raise ValueError(
                    f"Iteration {iteration.iteration_number} participants "
                    f"don't match debate participants"
                )
        
        return self
    
    def to_save_format(self) -> Dict[str, Any]:
        """Convert to format suitable for JSON saving."""
        return {
            "debate_id": self.debate_id,
            "question": self.question,
            "participants": self.participants,
            "iterations": [
                {
                    "iteration": iter.iteration_number,
                    "arguments": iter.arguments,
                    "votes": iter.votes,
                    "consensus_reached": iter.consensus_reached,
                    "winner": iter.winner,
                    "timestamp": iter.timestamp.isoformat()
                }
                for iter in self.iterations
            ],
            "config": self.config.model_dump(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "final_verdict": self.final_verdict,
            "ai_generated_title": self.ai_generated_title
        }