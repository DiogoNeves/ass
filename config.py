from dataclasses import dataclass, field
from typing import Dict, Optional
import json
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DebateConfig:
    """Configuration for the debate system."""
    
    # Voting configuration
    voting_enabled: bool = True
    consensus_threshold: float = 0.75  # 75% of max points needed
    min_iterations: int = 2  # Minimum rounds before voting (deprecated, use voting_start_iteration)
    voting_start_iteration: int = 2  # Which iteration voting starts (0-indexed, so 2 means 3rd iteration)
    max_iterations: int = 10  # Maximum rounds to prevent infinite loops
    
    # Scoring system - rank position to points
    scoring_system: Dict[int, int] = field(default_factory=lambda: {1: 4, 2: 3, 3: 2, 4: 1})
    
    # Judge configuration
    judge_can_override: bool = True
    override_threshold: float = 0.9  # Judge needs 90% conviction to override
    
    # Model configuration
    allow_local_models: bool = True
    local_model_timeout: int = 30
    
    # Classic mode (3 rounds, no voting)
    classic_mode: bool = False
    
    # File saving
    save_enabled: bool = True
    
    # Personality voting traits
    default_voting_traits: Dict[str, int] = field(
        default_factory=lambda: {"fairness": 7, "self_confidence": 5}
    )
    
    @classmethod
    def from_file(cls, config_path: str) -> "DebateConfig":
        """Load configuration from a JSON file."""
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        return cls(**config_data)
    
    @classmethod
    def from_env(cls) -> "DebateConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if they exist
        if os.getenv("DEBATE_VOTING_ENABLED") is not None:
            config.voting_enabled = os.getenv("DEBATE_VOTING_ENABLED").lower() == "true"
        
        if os.getenv("DEBATE_CONSENSUS_THRESHOLD"):
            config.consensus_threshold = float(os.getenv("DEBATE_CONSENSUS_THRESHOLD"))
        
        if os.getenv("DEBATE_MAX_ITERATIONS"):
            config.max_iterations = int(os.getenv("DEBATE_MAX_ITERATIONS"))
        
        if os.getenv("DEBATE_CLASSIC_MODE"):
            config.classic_mode = os.getenv("DEBATE_CLASSIC_MODE").lower() == "true"
        
        if os.getenv("LOCAL_MODEL_URL"):
            config.allow_local_models = True
        
        if os.getenv("DEBATE_SAVE_ENABLED") is not None:
            config.save_enabled = os.getenv("DEBATE_SAVE_ENABLED").lower() == "true"
        
        return config
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            "voting_enabled": self.voting_enabled,
            "consensus_threshold": self.consensus_threshold,
            "min_iterations": self.min_iterations,
            "max_iterations": self.max_iterations,
            "scoring_system": self.scoring_system,
            "judge_can_override": self.judge_can_override,
            "override_threshold": self.override_threshold,
            "allow_local_models": self.allow_local_models,
            "local_model_timeout": self.local_model_timeout,
            "classic_mode": self.classic_mode,
            "default_voting_traits": self.default_voting_traits,
            "save_enabled": self.save_enabled,
            "voting_start_iteration": self.voting_start_iteration
        }
    
    def save_to_file(self, config_path: str):
        """Save configuration to a JSON file."""
        with open(config_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)