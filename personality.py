from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List
import openai
import anthropic
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class PersonalityConfig:
    name: str
    model_provider: str  # "openai" or "claude"
    model_name: str
    system_prompt: str
    traits: Dict[str, Any]

class LLMPersonality(ABC):
    def __init__(self, config: PersonalityConfig):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
    
    @abstractmethod
    def generate_response(self, question: str, context: str = "") -> str:
        pass
    
    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

class ClaudePersonality(LLMPersonality):
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        self.client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
    
    def generate_response(self, question: str, context: str = "") -> str:
        messages = []
        
        if context:
            messages.append({
                "role": "user", 
                "content": f"Context from previous arguments: {context}\n\nOriginal question: {question}\n\nPlease respond according to your personality."
            })
        else:
            messages.append({
                "role": "user", 
                "content": f"Question: {question}\n\nPlease respond according to your personality."
            })
        
        response = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=500,
            system=self.config.system_prompt,
            messages=messages
        )
        
        return response.content[0].text

class OpenAIPersonality(LLMPersonality):
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def generate_response(self, question: str, context: str = "") -> str:
        messages = [{"role": "system", "content": self.config.system_prompt}]
        
        if context:
            messages.append({
                "role": "user", 
                "content": f"Context from previous arguments: {context}\n\nOriginal question: {question}\n\nPlease respond according to your personality."
            })
        else:
            messages.append({
                "role": "user", 
                "content": f"Question: {question}\n\nPlease respond according to your personality."
            })
        
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            max_tokens=500
        )
        
        return response.choices[0].message.content

def create_personality(config: PersonalityConfig) -> LLMPersonality:
    if config.model_provider == "claude":
        return ClaudePersonality(config)
    elif config.model_provider == "openai":
        return OpenAIPersonality(config)
    else:
        raise ValueError(f"Unsupported model provider: {config.model_provider}")