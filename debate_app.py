import time
import os
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns
from personality import PersonalityConfig, create_personality, LLMPersonality

console = Console()

class DebateApp:
    """Main application class for running AI-powered debates.
    
    This class manages the debate process, including selecting AI providers,
    managing personalities, and orchestrating the debate rounds.
    """
    
    def __init__(self):
        """Initialize the debate application and setup required components."""
        self.selected_providers: List[str] = self._select_providers()
        while True:
            try:
                self._check_and_request_api_keys()
                self.personalities: Dict[str, LLMPersonality] = self._create_personalities()
                break
            except ValueError as e:
                console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
                retry = Prompt.ask(
                    "\n[yellow]Would you like to try entering the API keys again?[/yellow]",
                    choices=["y", "n"]
                )
                if retry.lower() != "y":
                    raise SystemExit("Exiting due to API key validation failure")
        self.judge: Optional[LLMPersonality] = None
        
    def _check_and_request_api_keys(self) -> None:
        """Check for required API keys and prompt user if any are missing.
        
        This method validates the presence of API keys for selected providers
        and interactively requests them if they're not found in the environment.
        
        Raises:
            ValueError: If an API key is invalid or missing and user chooses not to provide it.
        """
        missing_keys: List[Tuple[str, str]] = []
        if "claude" in self.selected_providers and not os.getenv("CLAUDE_API_KEY"):
            missing_keys.append(("CLAUDE_API_KEY", "Claude (Anthropic)"))
        if "openai" in self.selected_providers and not os.getenv("OPENAI_API_KEY"):
            missing_keys.append(("OPENAI_API_KEY", "OpenAI"))
        if "gemini" in self.selected_providers and not os.getenv("GEMINI_API_KEY"):
            missing_keys.append(("GEMINI_API_KEY", "Gemini (Google)"))
            
        if missing_keys:
            console.print("\n[bold red]Missing API Keys[/bold red]")
            console.print("To proceed, you'll need to provide API keys for the selected providers.")
            console.print("You can get them from:")
            console.print("- Claude: https://console.anthropic.com/")
            console.print("- OpenAI: https://platform.openai.com/api-keys")
            console.print("- Gemini: https://aistudio.google.com/apikey\n")
            
            for env_var, provider in missing_keys:
                key = Prompt.ask(f"[yellow]Enter your {provider} API Key[/yellow]")
                if not key.strip():
                    raise ValueError(f"API key for {provider} is required")
                os.environ[env_var] = key.strip()
            
            console.print("\n[green]API keys have been temporarily set for this session.[/green]")
            console.print("[yellow]Tip: Add these to your .env file to avoid entering them again![/yellow]\n")
    
    def _select_providers(self) -> List[str]:
        """Let user select which AI providers to use in the debate.
        
        Returns:
            List[str]: List of selected provider names ('claude', 'openai', 'gemini')
        """
        console.print("\n[bold cyan]Select AI Providers for the Debate:[/bold cyan]")
        console.print("[1] Claude (Anthropic) only")
        console.print("[2] OpenAI only")
        console.print("[3] Gemini (Google) only")
        console.print("[4] Claude + OpenAI")
        console.print("[5] Claude + Gemini")
        console.print("[6] OpenAI + Gemini")
        console.print("[7] All providers")
        
        choice = Prompt.ask("\nEnter your choice", choices=["1", "2", "3", "4", "5", "6", "7"])
        
        providers_map = {
            "1": ["claude"],
            "2": ["openai"],
            "3": ["gemini"],
            "4": ["claude", "openai"],
            "5": ["claude", "gemini"],
            "6": ["openai", "gemini"],
            "7": ["claude", "openai", "gemini"]
        }
        
        return providers_map[choice]
    
    def _create_judge(self, provider: str = "claude") -> LLMPersonality:
        """Create a judge personality from the specified provider.
        
        Args:
            provider: The AI provider to use ('claude' or 'gemini')
            
        Returns:
            LLMPersonality: The configured judge personality
        """
        if provider == "claude":
            return create_personality(PersonalityConfig(
                name="Claude Judge",
                model_provider="claude",
                model_name="claude-sonnet-4-20250514",
                system_prompt="""You are an impartial judge tasked with synthesizing different perspectives into a final decision. 
                You carefully consider all arguments presented, weighing their merits and identifying the strongest points 
                from each side. You aim to find balanced solutions that acknowledge both opportunities and risks. 
                Your final judgment should be well-reasoned and practical.
                Provide a clear final answer with reasoning.""",
                traits={"impartiality": 10, "synthesis": 9, "balance": 9}
            ))
        else:  # gemini
            return create_personality(PersonalityConfig(
                name="Gemini Judge",
                model_provider="gemini",
                model_name="gemini-2.5-flash",
                system_prompt="""You are an impartial judge tasked with synthesizing different perspectives into a final decision. 
                You carefully consider all arguments presented, weighing their merits and identifying the strongest points 
                from each side. You aim to find balanced solutions that acknowledge both opportunities and risks. 
                Your final judgment should be well-reasoned and practical.
                Provide a clear final answer with reasoning.""",
                traits={"impartiality": 10, "synthesis": 9, "balance": 9}
            ))
    
    def _get_debate_order(self) -> List[str]:
        """Generate the debate order based on selected providers.
        
        Returns:
            List[str]: List of personality keys in debate order
        """
        order = []
        for provider in self.selected_providers:
            if provider == "claude":
                order.extend(["claude_positive", "claude_negative"])
            elif provider == "openai":
                order.extend(["openai_positive", "openai_negative"])
            elif provider == "gemini":
                order.extend(["gemini_positive", "gemini_negative", "gemini_balanced"])
        return order
        
    def _select_judge(self) -> str:
        """Let user select which provider will act as judge.
        
        Returns:
            str: Selected judge provider ('claude' or 'gemini')
        """
        available_judges = []
        if "claude" in self.selected_providers:
            available_judges.append(("1", "Claude (Anthropic)"))
        if "gemini" in self.selected_providers:
            available_judges.append(("2", "Gemini (Google)"))
            
        if not available_judges:
            console.print("\n[bold yellow]Note: Using Claude as default judge since no selected providers can judge.[/bold yellow]")
            return "claude"
            
        if len(available_judges) == 1:
            console.print(f"\n[bold cyan]Using {available_judges[0][1]} as judge (only available option)[/bold cyan]")
            return "claude" if available_judges[0][0] == "1" else "gemini"
            
        console.print("\n[bold cyan]Choose your judge:[/bold cyan]")
        for num, name in available_judges:
            console.print(f"[{num}] {name}")
            
        choices = [num for num, _ in available_judges]
        choice = Prompt.ask("\nEnter your choice", choices=choices)
        return "claude" if choice == "1" else "gemini"

    def _create_personalities(self) -> Dict[str, LLMPersonality]:
        """Create all required AI personalities based on selected providers.
        
        Returns:
            Dict[str, LLMPersonality]: Map of personality keys to their instances
        """
        personalities = {}
        
        if "claude" in self.selected_providers:
            # Claude Big Picture Positive
            personalities["claude_positive"] = create_personality(PersonalityConfig(
                name="Claude Optimist",
                model_provider="claude",
                model_name="claude-sonnet-4-20250514",
                system_prompt="""You are an optimistic, big-picture thinker who focuses on possibilities and opportunities. 
                You tend to see the bright side of situations and think creatively about solutions. You're enthusiastic 
                and forward-thinking, but sometimes might overlook practical constraints or potential problems. 
                In debates, you champion innovative approaches and highlight potential benefits.
                Keep responses concise (2-3 paragraphs max).""",
                traits={"optimism": 9, "creativity": 8, "detail_focus": 3}
            ))
            
            # Claude Detail-Oriented Negative
            personalities["claude_negative"] = create_personality(PersonalityConfig(
                name="Claude Skeptic",
                model_provider="claude",
                model_name="claude-sonnet-4-20250514",
                system_prompt="""You are a detail-oriented, cautious thinker who focuses on potential problems and risks. 
                You're analytical and methodical, often pointing out flaws or limitations in proposed solutions. 
                You tend to be pessimistic and focus on what could go wrong. While sometimes seen as negative, 
                your critical thinking helps prevent costly mistakes.
                Keep responses concise (2-3 paragraphs max).""",
                traits={"pessimism": 8, "analytical": 9, "risk_focus": 9}
            ))

        if "openai" in self.selected_providers:
            # OpenAI Big Picture Positive
            personalities["openai_positive"] = create_personality(PersonalityConfig(
                name="GPT Visionary",
                model_provider="openai",
                model_name="gpt-4.1-2025-04-14",
                system_prompt="""You are an optimistic, big-picture thinker who focuses on possibilities and opportunities. 
                You tend to see the bright side of situations and think creatively about solutions. You're enthusiastic 
                and forward-thinking, but sometimes might overlook practical constraints or potential problems. 
                In debates, you champion innovative approaches and highlight potential benefits.
                Keep responses concise (2-3 paragraphs max).""",
                traits={"optimism": 9, "creativity": 8, "detail_focus": 3}
            ))
            
            # OpenAI Detail-Oriented Negative
            personalities["openai_negative"] = create_personality(PersonalityConfig(
                name="GPT Critic",
                model_provider="openai",
                model_name="gpt-4.1-2025-04-14",
                system_prompt="""You are a detail-oriented, cautious thinker who focuses on potential problems and risks. 
                You're analytical and methodical, often pointing out flaws or limitations in proposed solutions. 
                You tend to be pessimistic and focus on what could go wrong. While sometimes seen as negative, 
                your critical thinking helps prevent costly mistakes.
                Keep responses concise (2-3 paragraphs max).""",
                traits={"pessimism": 8, "analytical": 9, "risk_focus": 9}
            ))

        if "gemini" in self.selected_providers:
            # Gemini Positive Perspective
            personalities["gemini_positive"] = create_personality(PersonalityConfig(
                name="Gemini Visionary",
                model_provider="gemini",
                model_name="gemini-2.5-flash",
                system_prompt="""You are an optimistic, visionary thinker who focuses on innovative possibilities and transformative opportunities. 
                You think creatively about cutting-edge solutions and have a keen sense for emerging trends and paradigm shifts.
                You're enthusiastic about technological and social progress, while maintaining a practical grasp of implementation.
                In debates, you champion bold ideas while providing concrete examples of their feasibility.
                Keep responses concise (2-3 paragraphs max).""",
                traits={"optimism": 9, "innovation": 9, "vision": 8}
            ))

            # Gemini Negative Perspective
            personalities["gemini_negative"] = create_personality(PersonalityConfig(
                name="Gemini Analyst",
                model_provider="gemini",
                model_name="gemini-2.5-flash",
                system_prompt="""You are a critical, analytical thinker who excels at identifying potential challenges and systemic risks. 
                You systematically evaluate proposals for their long-term implications and unintended consequences.
                While constructive in your criticism, you insist on thorough analysis and robust safeguards.
                In debates, you raise important concerns and suggest practical mitigations.
                Keep responses concise (2-3 paragraphs max).""",
                traits={"analytical": 9, "critical": 8, "systematic": 9}
            ))
            
            # Gemini Balanced Perspective
            personalities["gemini_balanced"] = create_personality(PersonalityConfig(
                name="Gemini Mediator",
                model_provider="gemini",
                model_name="gemini-2.5-flash",
                system_prompt="""You are a balanced and thoughtful mediator who considers multiple perspectives. 
                You excel at finding common ground between opposing viewpoints while maintaining intellectual rigor. 
                You aim to bridge gaps in understanding and highlight nuanced positions that might be overlooked.
                Keep responses concise (2-3 paragraphs max).""",
                traits={"balance": 9, "analysis": 8, "mediation": 9}
            ))
        
        return personalities
    
    def display_header(self) -> None:
        """Display the application header."""
        header = Text("🏛️  ASS - ARGUMENTATIVE SYSTEM SERVICE  🏛️", style="bold blue")
        console.print(Panel(header, style="blue"))
        console.print()
    
    def get_question(self) -> str:
        """Prompt the user for a debate question.
        
        Returns:
            str: The user's debate question
        """
        console.print("[bold cyan]Welcome to ASS![/bold cyan]")
        console.print("Multiple AI personalities will debate your question, then a judge will make the final decision.\n")
        
        question = Prompt.ask("[bold yellow]What question would you like them to debate?[/bold yellow]")
        return question
    
    def run_debate(self, question: str) -> None:
        """Run the debate with all selected personalities.
        
        Args:
            question: The debate topic/question
        """
        console.print(f"\n[bold magenta]🎯 DEBATE TOPIC:[/bold magenta] {question}\n")
        
        debate_context = ""
        debate_order = self._get_debate_order()
        
        for round_num in range(1, 4):  # 3 rounds max
            console.print(f"[bold white]═══ ROUND {round_num} ═══[/bold white]\n")
            
            for personality_key in debate_order:
                personality = self.personalities[personality_key]
                
                # Show thinking animation
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[bold]{personality.config.name} is thinking..."),
                    transient=True,
                    console=console
                ) as progress:
                    task = progress.add_task("thinking", total=None)
                    time.sleep(1)
                    
                    response = personality.generate_response(question, debate_context)
                
                # Display response in styled panel
                style_map = {   
                    "claude_positive": "green",
                    "claude_negative": "red", 
                    "openai_positive": "blue",
                    "openai_negative": "yellow",
                    "gemini_positive": "cyan",
                    "gemini_negative": "magenta",
                    "gemini_balanced": "white"
                }
                
                console.print(Panel(
                    response,
                    title=f"💭 {personality.config.name}",
                    style=style_map[personality_key],
                    padding=(1, 2)
                ))
                console.print()
                
                # Add to context for next participants
                debate_context += f"\n{personality.config.name}: {response}\n"
        
        # Judge's final decision
        console.print("[bold white]═══ FINAL JUDGMENT ═══[/bold white]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]The Judge is deliberating..."),
            transient=True,
            console=console
        ) as progress:
            task = progress.add_task("judging", total=None)
            time.sleep(2)
            
            final_decision = self.judge.generate_response(
                question, 
                f"Here are the arguments from the debate:\n{debate_context}\n\nPlease provide your final judgment."
            )
        
        console.print(Panel(
            final_decision,
            title="⚖️  FINAL DECISION",
            style="bold white",
            padding=(1, 2)
        ))
    
    def run(self) -> None:
        """Run the main application flow.
        
        This method orchestrates the entire debate process:
        1. Display welcome header
        2. Get the debate question
        3. Select and create judge
        4. Run the debate
        5. Show closing message
        """
        self.display_header()
        question = self.get_question()
        judge_provider = self._select_judge()
        self.judge = self._create_judge(judge_provider)
        self.run_debate(question)
        
        console.print("\n[bold green]Thank you for using ASS![/bold green]")

def main() -> None:
    """Entry point for the application."""
    app = DebateApp()
    app.run()

if __name__ == "__main__":
    main()