from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List
import openai
import anthropic
import google.generativeai as genai 
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class PersonalityConfig:
    name: str
    model_provider: str  # "openai" or "claude" or "gemini"
    model_name: str
    system_prompt: str
    traits: Dict[str, Any]

class LLMPersonality(ABC):
    def __init__(self, config: PersonalityConfig):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        self._validate_api_key()
    
    @abstractmethod
    def generate_response(self, question: str, context: str = "") -> str:
        pass
    
    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
    
    @abstractmethod
    def _validate_api_key(self) -> None:
        """Validate that the API key is present and valid."""
        pass

class ClaudePersonality(LLMPersonality):
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        self.client = None  # Initialize after validation
    
    def _validate_api_key(self) -> None:
        api_key = os.getenv("CLAUDE_API_KEY")
        if not api_key:
            raise ValueError("CLAUDE_API_KEY environment variable is not set")
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            # Try a simple API call to validate the key
            self.client.messages.create(
                model="claude-instant-1.2",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        except Exception as e:
            raise ValueError(f"Invalid Claude API key: {str(e)}")

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
        self.client = None  # Initialize after validation
    
    def _validate_api_key(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        try:
            self.client = openai.OpenAI(api_key=api_key)
            # Try a simple API call to validate the key
            self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1
            )
        except Exception as e:
            raise ValueError(f"Invalid OpenAI API key: {str(e)}")

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

class GeminiAIPersonality(LLMPersonality):
    def __init__(self, config: PersonalityConfig):
        super().__init__(config)
        self.model = None
        self.chat = None
    
    def _validate_api_key(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-pro")
            # Try a simple API call to validate the key
            self.model.generate_content("Hi")
        except Exception as e:
            raise ValueError(f"Invalid Gemini API key: {str(e)}")
        self.chat = self.model.start_chat(history=[])
        self.chat.send_message(self.config.system_prompt)  # Set personality

    def generate_response(self, question: str, context: str = "") -> str:
        prompt = question
        if context:
            prompt = f"Context from previous arguments: {context}\n\nOriginal question: {question}\n\nPlease respond according to your personality."
        else:
            prompt = f"Question: {question}\n\nPlease respond according to your personality."

        response = self.chat.send_message(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=500,
                temperature=0.7
            )
        )

        return response.text

def create_personality(config: PersonalityConfig) -> LLMPersonality:
    if config.model_provider == "claude":
        return ClaudePersonality(config)
    elif config.model_provider == "openai":
        return OpenAIPersonality(config)
    elif config.model_provider == "gemini":
        return GeminiAIPersonality(config)
    else:
        raise ValueError(f"Unsupported model provider: {config.model_provider}")