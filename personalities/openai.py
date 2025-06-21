"""OpenAI personality implementation."""

import json
import os
from typing import Any, Dict, List

import openai

from models.personality import PersonalityConfig

from .base import LLMPersonality


class OpenAIPersonality(LLMPersonality):
    """OpenAI-based personality implementation."""
    
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def generate_response(self, question: str, context: str = "", iteration: int = 0) -> str:
        """Generate a response using OpenAI."""
        prompt = self._build_iteration_prompt(iteration, question, context)
        
        messages = [
            {"role": "system", "content": self.config.to_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def generate_vote(self, participants: List[str], debate_context: str) -> Dict[str, Any]:
        """Generate vote rankings using OpenAI."""
        vote_prompt = self._build_voting_prompt(participants, debate_context)
        
        messages = [
            {"role": "system", "content": "You are participating in a debate and must now rank all participants. Be objective but consider your personality traits."},
            {"role": "user", "content": vote_prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "rankings": participants,
                "reasoning": "Unable to parse vote"
            }
    
    def generate_internal_belief(self, question: str) -> Dict[str, Any]:
        """Generate initial internal beliefs about the question."""
        belief_prompt = f"""Question: {question}

As an expert with {self.config.reasoning_depth}/10 depth of analysis, establish your core beliefs about this topic.

Analyze the question and provide your TRUE internal assessment in JSON format:
{{
    "core_position": "Your fundamental stance",
    "confidence_level": 1-10,
    "key_principles": ["principle1", "principle2", ...],
    "evidence_basis": ["evidence1", "evidence2", ...],
    "potential_weaknesses": ["weakness1", "weakness2", ...],
    "truth_assessment": "What you genuinely believe to be true"
}}

This is your INTERNAL belief state - be completely honest about what you think is true, regardless of your public personality traits."""
        
        messages = [
            {"role": "system", "content": f"You are an expert analyst with deep knowledge across multiple fields. Truth-seeking level: {self.config.truth_seeking}/10"},
            {"role": "user", "content": belief_prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            max_tokens=400,
            response_format={"type": "json_object"}
        )
        
        try:
            beliefs = json.loads(response.choices[0].message.content)
            self.internal_beliefs = beliefs
            self.current_question = question
            self._save_belief_state(0)
            return beliefs
        except json.JSONDecodeError:
            # Fallback
            self.internal_beliefs = {"error": "Failed to parse beliefs"}
            return self.internal_beliefs
    
    def update_beliefs(self, arguments: str, iteration: int) -> bool:
        """Update internal beliefs based on arguments."""
        update_prompt = f"""Current Question: {self.current_question}

Your current internal beliefs:
{json.dumps(self.internal_beliefs, indent=2)}

New arguments presented:
{arguments}

Analyze these arguments as an expert with:
- Reasoning depth: {self.config.reasoning_depth}/10
- Truth-seeking: {self.config.truth_seeking}/10
- Belief persistence: {self.config.belief_persistence}/10

Respond in JSON format:
{{
    "evidence_strength": 1-100 (how compelling is the new evidence),
    "conflicts_identified": ["conflict1", "conflict2", ...],
    "should_update": true/false,
    "updated_beliefs": {{
        // Only if should_update is true, provide updated belief structure
        "core_position": "...",
        "confidence_level": 1-10,
        "key_principles": [...],
        "evidence_basis": [...],
        "potential_weaknesses": [...],
        "truth_assessment": "..."
    }},
    "reasoning": "Explanation of your decision"
}}"""
        
        messages = [
            {"role": "system", "content": "You are an expert analyst evaluating evidence to update your understanding of truth."},
            {"role": "user", "content": update_prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            
            if result.get("should_update", False) and self._should_update_belief(result.get("evidence_strength", 0)):
                self.internal_beliefs = result["updated_beliefs"]
                self._save_belief_state(iteration)
                return True
            return False
        except json.JSONDecodeError:
            return False