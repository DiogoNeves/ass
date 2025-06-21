"""File management service for saving and loading debates."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from pydantic import ValidationError
from rich.console import Console

from models.debate import DebateState


class FileManager:
    """Handles saving and loading debate files with AI-generated titles."""
    
    def __init__(self, save_directory: str = "debates", console: Optional[Console] = None):
        self.save_directory = Path(save_directory)
        self.console = console or Console()
        self.anthropic_client = None
        
        # Ensure save directory exists
        self.save_directory.mkdir(exist_ok=True)
    
    def _get_anthropic_client(self) -> Optional[Anthropic]:
        """Lazy load Anthropic client when needed."""
        if self.anthropic_client is None:
            try:
                self.anthropic_client = Anthropic()
            except Exception:
                return None
        return self.anthropic_client
    
    def generate_debate_title(self, question: str, debate_content: str = "") -> str:
        """Generate a concise title for the debate using AI."""
        client = self._get_anthropic_client()
        if not client:
            # Fallback to question-based title
            return self._create_fallback_title(question)
        
        try:
            prompt = f"""Generate a very concise, descriptive title for this debate.

Question: {question}

{f"Debate preview: {debate_content[:500]}..." if debate_content else ""}

Requirements:
- Maximum 50 characters
- Capture the essence of the debate topic
- Be specific and engaging
- No quotes or special formatting
- Use title case

Return only the title, nothing else."""

            response = client.messages.create(
                model="claude-3-5-sonnet-20241112",
                max_tokens=50,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            title = response.content[0].text.strip()
            # Ensure title isn't too long
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title
            
        except Exception as e:
            self.console.print(f"[yellow]Could not generate AI title: {e}[/yellow]")
            return self._create_fallback_title(question)
    
    def _create_fallback_title(self, question: str) -> str:
        """Create a fallback title from the question."""
        # Remove question mark and limit length
        title = question.replace("?", "").strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filename."""
        # Replace problematic characters
        sanitized = text.replace("/", "-").replace("\\", "-").replace(":", "-")
        sanitized = sanitized.replace("?", "").replace("*", "").replace('"', "")
        sanitized = sanitized.replace("<", "").replace(">", "").replace("|", "")
        
        # Replace spaces with underscores and remove multiple underscores
        sanitized = "_".join(sanitized.split())
        
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:97] + "..."
        
        return sanitized
    
    def save_debate(self, debate_data: Dict[str, Any], custom_filename: Optional[str] = None) -> str:
        """Save debate data to a JSON file.
        
        Args:
            debate_data: The debate data to save
            custom_filename: Optional custom filename (without extension)
            
        Returns:
            The path to the saved file
        """
        if custom_filename:
            filename = f"{custom_filename}.json"
        else:
            # Generate filename from timestamp and title
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Try to get AI title if not already present
            if "ai_generated_title" not in debate_data or not debate_data["ai_generated_title"]:
                debate_context = ""
                if "iterations" in debate_data and debate_data["iterations"]:
                    # Get first iteration arguments for context
                    first_iter = debate_data["iterations"][0]
                    if "arguments" in first_iter:
                        debate_context = " ".join(first_iter["arguments"].values())[:500]
                
                debate_data["ai_generated_title"] = self.generate_debate_title(
                    debate_data.get("question", "Unknown Topic"),
                    debate_context
                )
            
            title_part = self._sanitize_filename(debate_data["ai_generated_title"])
            filename = f"{timestamp}_{title_part}.json"
        
        filepath = self.save_directory / filename
        
        try:
            # Validate with Pydantic if possible
            if "question" in debate_data and "participants" in debate_data:
                try:
                    # This will validate the structure
                    DebateState.model_validate(debate_data)
                except ValidationError as e:
                    self.console.print(f"[yellow]Warning: Debate data validation failed: {e}[/yellow]")
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(debate_data, f, indent=2, ensure_ascii=False)
            
            self.console.print(f"\n[green]✓ Debate saved to: {filepath}[/green]")
            return str(filepath)
            
        except Exception as e:
            self.console.print(f"[red]Error saving debate: {e}[/red]")
            raise
    
    def load_debate(self, filename: str) -> Dict[str, Any]:
        """Load a debate from a JSON file.
        
        Args:
            filename: The filename (with or without path)
            
        Returns:
            The loaded debate data
        """
        # Handle both full paths and just filenames
        if os.path.isabs(filename):
            filepath = Path(filename)
        else:
            filepath = self.save_directory / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Debate file not found: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Try to validate with Pydantic
            try:
                DebateState.model_validate(data)
            except ValidationError as e:
                self.console.print(f"[yellow]Warning: Loaded debate has validation issues: {e}[/yellow]")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in debate file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading debate: {e}")
    
    def list_debates(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List available debate files.
        
        Args:
            limit: Maximum number of debates to return (most recent first)
            
        Returns:
            List of debate metadata
        """
        debates = []
        
        # Get all JSON files
        json_files = sorted(
            self.save_directory.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True  # Most recent first
        )
        
        if limit:
            json_files = json_files[:limit]
        
        for filepath in json_files:
            try:
                # Load just the metadata
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                debates.append({
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "question": data.get("question", "Unknown"),
                    "ai_title": data.get("ai_generated_title", ""),
                    "participants": data.get("participants", []),
                    "timestamp": data.get("start_time", ""),
                    "final_verdict": data.get("final_verdict") is not None,
                    "num_iterations": len(data.get("iterations", []))
                })
                
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not read {filepath.name}: {e}[/yellow]")
                continue
        
        return debates