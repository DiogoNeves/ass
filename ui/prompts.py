"""User input and prompting utilities."""

from typing import List, Optional

from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table


class PromptHandler:
    """Handles user input and prompting."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        
        # Predefined debate questions
        self.sample_questions = [
            "Should AI systems have rights and legal protections?",
            "Is universal basic income necessary in an automated future?",
            "Should we prioritize Mars colonization or Earth restoration?",
            "Is social media doing more harm than good to society?",
            "Should genetic engineering be used to enhance human capabilities?",
            "Is nuclear energy the solution to climate change?",
            "Should we ban autonomous weapons systems?",
            "Is cryptocurrency the future of money?",
            "Should there be limits on wealth accumulation?",
            "Is privacy dead in the digital age?",
            "Should we have a global government?",
            "Is free will an illusion?",
            "Should animals have the same rights as humans?",
            "Is democracy the best form of government?",
            "Should we upload human consciousness to computers?",
            "Is capitalism compatible with environmental sustainability?",
            "Should parents be required to vaccinate their children?",
            "Is cultural appropriation always wrong?",
            "Should we have designer babies?",
            "Is the simulation hypothesis likely to be true?"
        ]
    
    def get_debate_question(self) -> str:
        """Get a debate question from the user or provide samples."""
        self.console.print("\n[bold]Choose a debate topic:[/bold]")
        self.console.print("1. Enter your own question")
        self.console.print("2. Choose from sample questions")
        self.console.print("3. Random surprise topic")
        
        choice = Prompt.ask(
            "\nYour choice",
            choices=["1", "2", "3"],
            default="2"
        )
        
        if choice == "1":
            # Custom question
            question = Prompt.ask("\n[bold cyan]Enter your debate question[/bold cyan]")
            
            # Ensure it ends with a question mark
            if not question.strip().endswith("?"):
                question = question.strip() + "?"
            
            return question.strip()
            
        elif choice == "2":
            # Show sample questions
            return self._choose_sample_question()
            
        else:
            # Random question
            import random
            question = random.choice(self.sample_questions)
            self.console.print(f"\n[bold green]Random topic selected![/bold green]")
            return question
    
    def _choose_sample_question(self) -> str:
        """Let user choose from sample questions."""
        # Create a table of questions
        table = Table(
            title="Sample Debate Questions",
            show_header=True,
            header_style="bold magenta"
        )
        table.add_column("#", style="cyan", width=3)
        table.add_column("Question", style="white")
        
        # Add questions to table
        for i, question in enumerate(self.sample_questions, 1):
            table.add_row(str(i), question)
        
        self.console.print(table)
        
        # Get user choice
        choice = IntPrompt.ask(
            "\nSelect a question number",
            default=1,
            show_default=True
        )
        
        # Validate choice
        if 1 <= choice <= len(self.sample_questions):
            return self.sample_questions[choice - 1]
        else:
            self.console.print("[yellow]Invalid choice, using first question[/yellow]")
            return self.sample_questions[0]
    
    def confirm_action(self, message: str, default: bool = True) -> bool:
        """Ask user to confirm an action."""
        return Confirm.ask(message, default=default)
    
    def get_save_filename(self, default: Optional[str] = None) -> Optional[str]:
        """Get a filename for saving."""
        if not self.confirm_action("\nDo you want to save this debate?", default=True):
            return None
        
        if default:
            use_default = self.confirm_action(
                f"Use suggested filename: {default}?",
                default=True
            )
            if use_default:
                return default
        
        filename = Prompt.ask("Enter filename (without extension)")
        return filename.strip() if filename.strip() else None
    
    def get_debate_mode(self) -> str:
        """Get the debate mode from user."""
        self.console.print("\n[bold]Select debate mode:[/bold]")
        self.console.print("1. Classic (3 rounds, no voting)")
        self.console.print("2. Consensus (with voting system)")
        
        choice = Prompt.ask(
            "\nYour choice",
            choices=["1", "2"],
            default="2"
        )
        
        return "classic" if choice == "1" else "consensus"
    
    def get_personality_count(self, min_count: int = 2, max_count: int = 6) -> int:
        """Get the number of personalities to include."""
        return IntPrompt.ask(
            f"\nHow many personalities should debate? ({min_count}-{max_count})",
            default=4,
            show_default=True
        )
    
    def select_personalities(self, available: List[str], count: int) -> List[str]:
        """Let user select which personalities to include."""
        if count >= len(available):
            return available[:count]
        
        self.console.print(f"\n[bold]Select {count} personalities:[/bold]")
        
        # Show available personalities
        for i, name in enumerate(available, 1):
            self.console.print(f"{i}. {name}")
        
        selected = []
        while len(selected) < count:
            choice = IntPrompt.ask(
                f"\nSelect personality {len(selected) + 1}",
                default=len(selected) + 1
            )
            
            if 1 <= choice <= len(available):
                name = available[choice - 1]
                if name not in selected:
                    selected.append(name)
                else:
                    self.console.print("[yellow]Already selected, choose another[/yellow]")
            else:
                self.console.print("[yellow]Invalid choice[/yellow]")
        
        return selected
    
    def display_loading(self, message: str = "Loading..."):
        """Display a loading message."""
        with self.console.status(message, spinner="dots"):
            yield
    
    def pause_for_user(self, message: str = "Press Enter to continue..."):
        """Pause and wait for user input."""
        Prompt.ask(f"\n[dim]{message}[/dim]", default="", show_default=False)