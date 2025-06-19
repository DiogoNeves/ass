from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import openai
import anthropic
from dotenv import load_dotenv
import os
import json
import requests

load_dotenv()

@dataclass
class PersonalityConfig:
    name: str
    model_provider: str  # "openai", "claude", or "local"
    model_name: str
    system_prompt: str
    traits: Dict[str, Any]
    voting_traits: Dict[str, Any] = field(default_factory=lambda: {"fairness": 7, "self_confidence": 5})
    # Local model configuration
    model_url: Optional[str] = None
    model_endpoint: Optional[str] = "/v1/chat/completions"
    auth_token: Optional[str] = None
    request_timeout: int = 30

class LLMPersonality(ABC):
    def __init__(self, config: PersonalityConfig):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
    
    @abstractmethod
    def generate_response(self, question: str, context: str = "", iteration: int = 0) -> str:
        pass
    
    @abstractmethod
    def generate_vote(self, participants: List[str], debate_context: str) -> Dict[str, Any]:
        """Generate rankings for all participants based on debate quality."""
        pass
    
    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
    
    def _build_iteration_prompt(self, iteration: int, question: str, context: str) -> str:
        """Build prompt based on iteration number."""
        if iteration == 0:
            return f"Question: {question}\n\nProvide your initial position on this question. Be concise but comprehensive."
        else:
            return f"""Question: {question}

Current debate context:
{context}

This is iteration {iteration} of the debate. You must:
1. Directly address at least 2 other participants' arguments
2. Either agree and build upon their points, or disagree with specific reasoning
3. Avoid simply restating your previous position
4. Be open to changing your mind if presented with compelling arguments

Respond according to your personality traits."""

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


def create_personality(config: PersonalityConfig) -> LLMPersonality:
    if config.model_provider == "claude":
        return ClaudePersonality(config)
    elif config.model_provider == "openai":
        return OpenAIPersonality(config)
    elif config.model_provider == "local":
        return LocalModelPersonality(config)
    else:
        raise ValueError(f"Unsupported model provider: {config.model_provider}")