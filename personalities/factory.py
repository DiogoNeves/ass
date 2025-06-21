"""Factory function for creating personality instances."""

from typing import Optional

from .base import LLMPersonality
from .claude import ClaudePersonality
from .openai import OpenAIPersonality
from .local import LocalModelPersonality
from models.personality import PersonalityConfig


def create_personality(config: PersonalityConfig) -> LLMPersonality:
    """Create a personality instance based on the configuration.
    
    Args:
        config: PersonalityConfig with model provider and settings
        
    Returns:
        LLMPersonality instance
        
    Raises:
        ValueError: If model provider is not supported
    """
    if config.model_provider == "claude":
        return ClaudePersonality(config)
    elif config.model_provider == "openai":
        return OpenAIPersonality(config)
    elif config.model_provider == "local":
        return LocalModelPersonality(config)
    else:
        raise ValueError(f"Unknown model provider: {config.model_provider}")