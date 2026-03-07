"""Personality-related Pydantic models with validation."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class PersonalityTraits(BaseModel):
    """Voting-related personality traits."""
    fairness: int = Field(
        default=7,
        ge=1,
        le=10,
        description="How fairly the personality evaluates others (1-10)"
    )
    self_confidence: int = Field(
        default=5,
        ge=1,
        le=10,
        description="How likely to rank themselves highly (1-10)"
    )
    strategic_thinking: int = Field(
        default=5,
        ge=1,
        le=10,
        description="How strategically they vote (1-10)"
    )
    empathy: int = Field(
        default=5,
        ge=1,
        le=10,
        description="How much they consider others' perspectives (1-10)"
    )


class PersonalityConfig(BaseModel):
    """Configuration for an AI personality."""
    name: str = Field(..., min_length=1, max_length=50, description="Display name")
    model_provider: str = Field(..., pattern="^(claude|openai|local)$", description="LLM provider")
    model_name: str = Field(..., min_length=1, description="Model identifier")
    system_prompt: str = Field(..., min_length=1, description="System prompt for the model")

    # Optional role/perspective/style - generated from system_prompt if not provided
    role: Optional[str] = Field(None, description="Role description")
    perspective: Optional[str] = Field(None, description="Unique perspective")
    debate_style: Optional[str] = Field(None, description="How they argue")

    # Advanced traits
    reasoning_depth: int = Field(
        default=7,
        ge=1,
        le=10,
        description="Depth of logical reasoning (1-10)"
    )
    agreeableness: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Tendency to agree with others (1-10)"
    )
    conviction: int = Field(
        default=7,
        ge=1,
        le=10,
        description="Strength of personal beliefs (1-10)"
    )
    openness: int = Field(
        default=6,
        ge=1,
        le=10,
        description="Openness to changing views (1-10)"
    )

    # Internal belief tracking
    truth_seeking: int = Field(
        default=8,
        ge=1,
        le=10,
        description="Commitment to finding truth (1-10)"
    )
    belief_persistence: int = Field(
        default=6,
        ge=1,
        le=10,
        description="How strongly beliefs persist (1-10)"
    )

    # Voting traits
    voting_traits: PersonalityTraits = Field(
        default_factory=PersonalityTraits,
        description="Traits affecting voting behavior"
    )

    # Local model configuration
    model_url: Optional[str] = Field(
        None,
        description="URL for local model server"
    )
    model_endpoint: Optional[str] = Field(
        default="/v1/chat/completions",
        description="Endpoint for local model"
    )
    auth_token: Optional[str] = Field(
        None,
        description="Authentication token for local model"
    )
    request_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name doesn't contain special characters."""
        if not v.replace(' ', '').replace('-', '').replace('_', '').isalnum():
            raise ValueError("Name can only contain letters, numbers, spaces, hyphens, and underscores")
        return v.strip()

    @model_validator(mode='after')
    def validate_trait_balance(self) -> 'PersonalityConfig':
        """Ensure personality traits are logically consistent."""
        if self.conviction >= 8 and self.openness >= 8:
            raise ValueError("High conviction (>=8) with high openness (>=8) is contradictory")
        if self.agreeableness <= 3 and self.voting_traits.empathy >= 8:
            raise ValueError("Low agreeableness (<=3) with high empathy (>=8) is contradictory")
        return self

    def to_system_prompt(self) -> str:
        """Generate a system prompt from the configuration."""
        if self.system_prompt:
            return self.system_prompt

        role_text = self.role or "a debate participant"
        return f"""You are {self.name}, {role_text}.

Your perspective: {self.perspective or "bringing unique insights to the debate"}
Your debate style: {self.debate_style or "thoughtful and analytical"}

Personality traits:
- Reasoning depth: {self.reasoning_depth}/10
- Agreeableness: {self.agreeableness}/10
- Conviction in beliefs: {self.conviction}/10
- Openness to new ideas: {self.openness}/10
- Truth-seeking: {self.truth_seeking}/10

When voting, consider:
- Fairness: {self.voting_traits.fairness}/10
- Self-confidence: {self.voting_traits.self_confidence}/10
- Strategic thinking: {self.voting_traits.strategic_thinking}/10
- Empathy: {self.voting_traits.empathy}/10"""
