"""Local model personality implementation."""

import json
from typing import Any, Dict, List

import requests

from models.personality import PersonalityConfig

from .base import LLMPersonality


class LocalModelPersonality(LLMPersonality):
    """Personality that connects to a local model server."""
    
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        # Use fields from PersonalityConfig
        self.base_url = config.model_url or 'http://localhost:8000'
        self.endpoint = config.model_endpoint
        self.headers = {"Content-Type": "application/json"}
        
        if config.auth_token:
            self.headers["Authorization"] = f"Bearer {config.auth_token}"
        
        self.request_timeout = config.request_timeout
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
        """Generate a response using local model."""
        prompt = self._build_iteration_prompt(iteration, question, context)
        
        payload = {
            "messages": [
                {"role": "system", "content": self.config.to_system_prompt()},
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
                timeout=self.request_timeout
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
        """Generate vote rankings using local model."""
        vote_prompt = self._build_voting_prompt(participants, debate_context)
        
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
                timeout=self.request_timeout
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
                timeout=self.request_timeout
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
                timeout=self.request_timeout
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