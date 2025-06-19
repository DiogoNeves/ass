from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import openai
import anthropic
from dotenv import load_dotenv
import os
import json
import requests
import time

load_dotenv()

@dataclass
class PersonalityConfig:
    name: str
    model_provider: str  # "openai", "claude", or "local"
    model_name: str
    system_prompt: str
    traits: Dict[str, Any]
    voting_traits: Dict[str, Any] = field(default_factory=lambda: {"fairness": 7, "self_confidence": 5})
    # Belief system traits
    belief_persistence: int = 7  # How resistant to changing beliefs (0-10)
    reasoning_depth: int = 8  # Quality of internal reasoning (0-10)
    truth_seeking: int = 6  # How much they value finding truth vs winning (0-10)
    # Local model configuration
    model_url: Optional[str] = None
    model_endpoint: Optional[str] = "/v1/chat/completions"
    auth_token: Optional[str] = None
    request_timeout: int = 30

class LLMPersonality(ABC):
    def __init__(self, config: PersonalityConfig):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        self.internal_beliefs: Dict[str, Any] = {}  # Core beliefs about the topic
        self.belief_history: List[Dict[str, Any]] = []  # Track belief evolution
        self.current_question: Optional[str] = None
    
    @abstractmethod
    def generate_response(self, question: str, context: str = "", iteration: int = 0) -> str:
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

class ClaudePersonality(LLMPersonality):
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        self.client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
    
    def generate_response(self, question: str, context: str = "", iteration: int = 0) -> str:
        prompt = self._build_iteration_prompt(iteration, question, context)
        
        messages = [{"role": "user", "content": prompt}]
        
        response = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=500,
            system=self.config.system_prompt,
            messages=messages
        )
        
        return response.content[0].text
    
    def generate_vote(self, participants: List[str], debate_context: str) -> Dict[str, Any]:
        vote_prompt = f"""Based on the debate so far, rank all participants (including yourself) from best to worst based on:
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
- Fairness level: {self.config.voting_traits.get('fairness', 7)}/10
- Self-confidence: {self.config.voting_traits.get('self_confidence', 5)}/10"""
        
        messages = [{"role": "user", "content": vote_prompt}]
        
        response = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=300,
            system="You are participating in a debate and must now rank all participants. Be objective but consider your personality traits.",
            messages=messages
        )
        
        try:
            return json.loads(response.content[0].text)
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
        
        messages = [{"role": "user", "content": belief_prompt}]
        
        response = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=400,
            system=f"You are an expert analyst with deep knowledge across multiple fields. Truth-seeking level: {self.config.truth_seeking}/10",
            messages=messages
        )
        
        try:
            beliefs = json.loads(response.content[0].text)
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
        
        messages = [{"role": "user", "content": update_prompt}]
        
        response = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=500,
            system="You are an expert analyst evaluating evidence to update your understanding of truth.",
            messages=messages
        )
        
        try:
            result = json.loads(response.content[0].text)
            
            if result.get("should_update", False) and self._should_update_belief(result.get("evidence_strength", 0)):
                self.internal_beliefs = result["updated_beliefs"]
                self._save_belief_state(iteration)
                return True
            return False
        except json.JSONDecodeError:
            return False

class OpenAIPersonality(LLMPersonality):
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def generate_response(self, question: str, context: str = "", iteration: int = 0) -> str:
        prompt = self._build_iteration_prompt(iteration, question, context)
        
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def generate_vote(self, participants: List[str], debate_context: str) -> Dict[str, Any]:
        vote_prompt = f"""Based on the debate so far, rank all participants (including yourself) from best to worst based on:
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
- Fairness level: {self.config.voting_traits.get('fairness', 7)}/10
- Self-confidence: {self.config.voting_traits.get('self_confidence', 5)}/10"""
        
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

class LocalModelPersonality(LLMPersonality):
    """Personality that connects to a local model server."""
    
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        if not config.model_url:
            raise ValueError("model_url is required for local model provider")
        
        self.base_url = config.model_url.rstrip('/')
        self.endpoint = config.model_endpoint
        self.headers = {"Content-Type": "application/json"}
        
        if config.auth_token:
            self.headers["Authorization"] = f"Bearer {config.auth_token}"
        
        self._test_connection()
    
    def _test_connection(self):
        """Test if the local model server is accessible."""
        try:
            test_url = f"{self.base_url}/health"  # Try health endpoint first
            response = requests.get(test_url, timeout=5)
            if response.status_code == 404:
                # Try the main endpoint with a minimal request
                test_url = f"{self.base_url}{self.endpoint}"
                response = requests.post(
                    test_url,
                    headers=self.headers,
                    json={"messages": [{"role": "user", "content": "test"}], "max_tokens": 1},
                    timeout=5
                )
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to connect to local model server at {self.base_url}: {e}")
    
    def generate_response(self, question: str, context: str = "", iteration: int = 0) -> str:
        prompt = self._build_iteration_prompt(iteration, question, context)
        
        payload = {
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                f"{self.base_url}{self.endpoint}",
                headers=self.headers,
                json=payload,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            # Support both OpenAI-style and simple response formats
            if "choices" in result:
                return result["choices"][0]["message"]["content"]
            elif "response" in result:
                return result["response"]
            else:
                return str(result)
                
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Local model request failed: {e}")
    
    def generate_vote(self, participants: List[str], debate_context: str) -> Dict[str, Any]:
        vote_prompt = f"""Based on the debate so far, rank all participants (including yourself) from best to worst based on:
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
- Fairness level: {self.config.voting_traits.get('fairness', 7)}/10
- Self-confidence: {self.config.voting_traits.get('self_confidence', 5)}/10"""
        
        payload = {
            "messages": [
                {"role": "system", "content": "You are participating in a debate and must now rank all participants. Return valid JSON."},
                {"role": "user", "content": vote_prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.3  # Lower temperature for more consistent JSON
        }
        
        try:
            response = requests.post(
                f"{self.base_url}{self.endpoint}",
                headers=self.headers,
                json=payload,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result:
                content = result["choices"][0]["message"]["content"]
            elif "response" in result:
                content = result["response"]
            else:
                content = str(result)
            
            return json.loads(content)
            
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            # Fallback if request or parsing fails
            return {
                "rankings": participants,
                "reasoning": f"Unable to generate vote: {str(e)}"
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
        
        payload = {
            "messages": [
                {"role": "system", "content": f"You are an expert analyst with deep knowledge across multiple fields. Truth-seeking level: {self.config.truth_seeking}/10"},
                {"role": "user", "content": belief_prompt}
            ],
            "max_tokens": 400,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                f"{self.base_url}{self.endpoint}",
                headers=self.headers,
                json=payload,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result:
                content = result["choices"][0]["message"]["content"]
            elif "response" in result:
                content = result["response"]
            else:
                content = str(result)
            
            beliefs = json.loads(content)
            self.internal_beliefs = beliefs
            self.current_question = question
            self._save_belief_state(0)
            return beliefs
            
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            # Fallback
            self.internal_beliefs = {"error": f"Failed to parse beliefs: {str(e)}"}
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
        
        payload = {
            "messages": [
                {"role": "system", "content": "You are an expert analyst evaluating evidence to update your understanding of truth."},
                {"role": "user", "content": update_prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                f"{self.base_url}{self.endpoint}",
                headers=self.headers,
                json=payload,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            
            result_json = response.json()
            if "choices" in result_json:
                content = result_json["choices"][0]["message"]["content"]
            elif "response" in result_json:
                content = result_json["response"]
            else:
                content = str(result_json)
            
            result = json.loads(content)
            
            if result.get("should_update", False) and self._should_update_belief(result.get("evidence_strength", 0)):
                self.internal_beliefs = result["updated_beliefs"]
                self._save_belief_state(iteration)
                return True
            return False
            
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            return False


def create_personality(config: PersonalityConfig) -> LLMPersonality:
    if config.model_provider == "claude":
        return ClaudePersonality(config)
    elif config.model_provider == "openai":
        return OpenAIPersonality(config)
    elif config.model_provider == "local":
        return LocalModelPersonality(config)
    else:
        raise ValueError(f"Unsupported model provider: {config.model_provider}")