"""
Backward compatibility module for personality imports.
The actual implementations have been moved to the personalities/ directory.
"""

# Import PersonalityConfig from models
from models.personality import PersonalityConfig

# Import everything from the new location for backward compatibility
from personalities import (
    ClaudePersonality,
    LLMPersonality,
    LocalModelPersonality,
    OpenAIPersonality,
    create_personality,
)

# For complete backward compatibility
__all__ = [
    "PersonalityConfig",
    "LLMPersonality", 
    "ClaudePersonality",
    "OpenAIPersonality",
    "LocalModelPersonality",
    "create_personality"
]