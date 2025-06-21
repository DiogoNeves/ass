"""Voting-related Pydantic models with validation."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator


class Vote(BaseModel):
    """Represents a single vote from a personality."""
    voter: str = Field(..., min_length=1, description="Name of the voter")
    rankings: List[str] = Field(..., description="Ordered list from best to worst")
    reasoning: str = Field(..., min_length=1, description="Explanation for the rankings")
    iteration: int = Field(..., ge=0, description="Voting iteration number")
    
    @field_validator('rankings')
    @classmethod
    def validate_rankings(cls, v: List[str]) -> List[str]:
        """Ensure rankings have no duplicates and all entries are non-empty."""
        if not v:
            raise ValueError("Rankings cannot be empty")
        
        if len(v) != len(set(v)):
            raise ValueError("Rankings cannot contain duplicates")
        
        for participant in v:
            if not participant or not participant.strip():
                raise ValueError("Participant names cannot be empty")
        
        return v
    
    @model_validator(mode='after')
    def voter_in_rankings(self) -> 'Vote':
        """Ensure the voter is included in their own rankings."""
        if self.voter not in self.rankings:
            raise ValueError(f"Voter '{self.voter}' must be included in their own rankings")
        return self


class VotingConfig(BaseModel):
    """Configuration for the voting system."""
    point_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Percentage of max possible points for consensus"
    )
    scoring_system: Dict[int, int] = Field(
        default_factory=lambda: {1: 4, 2: 3, 3: 2, 4: 1},
        description="Rank position to points mapping"
    )
    min_iterations: int = Field(
        default=2,
        ge=1,
        description="Minimum iterations before voting can start"
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum iterations to prevent infinite loops"
    )
    
    @field_validator('scoring_system')
    @classmethod
    def validate_scoring_system(cls, v: Dict[int, int]) -> Dict[int, int]:
        """Ensure scoring system has sequential keys starting from 1."""
        if not v:
            raise ValueError("Scoring system cannot be empty")
        
        keys = sorted(v.keys())
        expected_keys = list(range(1, len(keys) + 1))
        
        if keys != expected_keys:
            raise ValueError(f"Scoring system must have sequential keys from 1 to {len(keys)}")
        
        # Ensure all values are positive
        for rank, points in v.items():
            if points <= 0:
                raise ValueError(f"Points for rank {rank} must be positive")
        
        return v
    
    @model_validator(mode='after')
    def validate_iterations(self) -> 'VotingConfig':
        """Ensure min_iterations <= max_iterations."""
        if self.min_iterations > self.max_iterations:
            raise ValueError("min_iterations cannot be greater than max_iterations")
        return self


class VotingResult(BaseModel):
    """Result of a voting round."""
    iteration: int = Field(..., ge=0)
    scores: Dict[str, int] = Field(..., description="Participant name to score mapping")
    sorted_rankings: List[Tuple[str, int]] = Field(..., description="Participants sorted by score")
    consensus_reached: bool = Field(..., description="Whether consensus was achieved")
    winner: Optional[str] = Field(None, description="Winner if consensus reached")
    threshold_score: float = Field(..., ge=0, description="Score needed for consensus")
    individual_votes: List[Vote] = Field(..., description="All votes cast this round")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @field_validator('sorted_rankings')
    @classmethod
    def validate_sorted_rankings(cls, v: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """Ensure rankings are properly sorted by score (descending)."""
        if len(v) > 1:
            scores = [score for _, score in v]
            if scores != sorted(scores, reverse=True):
                raise ValueError("Rankings must be sorted by score in descending order")
        return v
    
    @model_validator(mode='after')
    def validate_winner_consensus(self) -> 'VotingResult':
        """Ensure winner is only set when consensus is reached."""
        if self.consensus_reached and not self.winner:
            raise ValueError("Winner must be set when consensus is reached")
        if not self.consensus_reached and self.winner:
            raise ValueError("Winner cannot be set when consensus is not reached")
        return self