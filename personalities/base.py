"""Base class for AI personalities."""

import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from models.personality import PersonalityConfig


class LLMPersonality(ABC):
    """Abstract base class for all AI personalities."""
    
    def __init__(self, config: PersonalityConfig):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        self.internal_beliefs: Dict[str, Any] = {}  # Core beliefs about the topic
        self.belief_history: List[Dict[str, Any]] = []  # Track belief evolution
        self.current_question: Optional[str] = None
    
    @abstractmethod
    def generate_response(self, question: str, context: str = "", iteration: int = 0) -> str:
        """Generate a response to the debate question."""
        pass
    
    @abstractmethod
    def generate_vote(self, participants: List[str], debate_context: str) -> Dict[str, Any]:
        """Generate rankings for all participants based on debate quality."""
        pass
    
    @abstractmethod
    def generate_internal_belief(self, question: str) -> Dict[str, Any]:
        """Generate initial internal beliefs about the question."""
        pass
    
    @abstractmethod
    def update_beliefs(self, arguments: str, iteration: int) -> bool:
        """Update internal beliefs based on arguments. Returns True if beliefs changed."""
        pass
    
    def add_to_history(self, role: str, content: str):
        """Add an entry to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
    
    def _should_update_belief(self, evidence_strength: int) -> bool:
        """Determine if beliefs should be updated based on evidence strength."""
        # Higher belief_persistence requires stronger evidence
        threshold = self.config.belief_persistence * 10
        # Truth-seeking personalities have lower threshold
        threshold -= (self.config.truth_seeking * 5)
        return evidence_strength >= threshold
    
    def _save_belief_state(self, iteration: int):
        """Save current belief state to history."""
        self.belief_history.append({
            "iteration": iteration,
            "beliefs": self.internal_beliefs.copy(),
            "timestamp": time.time()
        })
    
    def _build_iteration_prompt(self, iteration: int, question: str, context: str) -> str:
        """Build prompt based on iteration number."""
        if iteration == 0:
            # First establish beliefs, then generate position
            return f"""Question: {question}

Based on your personality and expertise, provide your STRONGEST initial position on this question. 

Your goal is to WIN this debate by:
- Providing expert-level analysis that DEFEATS opposing viewpoints
- Drawing from relevant fields to build an UNASSAILABLE argument
- Being specific with principles and examples that PROVE your position
- Establishing intellectual dominance from the start

Remember: You're not here to explore ideas - you're here to CONVINCE others and WIN.
Provide a powerful position that reflects {self.config.reasoning_depth}/10 depth of analysis."""
        else:
            # Include internal beliefs in reasoning
            belief_context = ""
            if self.internal_beliefs:
                belief_context = f"\nYour current understanding: {json.dumps(self.internal_beliefs, indent=2)}\n"
            
            return f"""Question: {question}
{belief_context}
Current debate context:
{context}

This is iteration {iteration} of the debate. Your mission:
1. ATTACK at least 2 other participants' arguments - find their weaknesses and EXPLOIT them
2. If you disagree, DEMOLISH their position with superior evidence and reasoning
3. If you must agree, show how YOUR interpretation is BETTER and more complete
4. NEVER concede unless the evidence is overwhelming (belief persistence: {self.config.belief_persistence}/10)
5. Fight for your position - you're here to WIN, not to find compromise

Remember: This is a COMPETITION. Others are trying to defeat your arguments. DEFEND your position and ATTACK theirs.
Provide a response with {self.config.reasoning_depth}/10 depth that DOMINATES the debate."""
    
    def _build_voting_prompt(self, participants: List[str], debate_context: str) -> str:
        """Build prompt for voting on debate performance."""
        return f"""Based on the debate so far, rank all participants (including yourself) from best to worst based on:
1. Quality of arguments
2. Logic and reasoning
3. Ability to address others' points
4. Persuasiveness

Participants: {', '.join(participants)}

Debate context:
{debate_context}

Return your rankings as JSON in this format:
{{
    "rankings": ["participant1", "participant2", "participant3", "participant4"],
    "reasoning": "Brief explanation of your rankings"
}}

Be fair and objective, considering your personality traits:
- Fairness level: {self.config.voting_traits.fairness}/10
- Self-confidence: {self.config.voting_traits.self_confidence}/10"""