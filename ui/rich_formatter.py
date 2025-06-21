"""Rich terminal formatting utilities."""

from typing import Any, Dict, List, Optional

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text


class RichFormatter:
    """Handles all Rich terminal formatting for the debate app."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
    
    def display_header(self):
        """Display the application header."""
        header_text = Text()
        header_text.append("🤖 ", style="bold")
        header_text.append("ASS", style="bold red")
        header_text.append(" - ", style="bold")
        header_text.append("A", style="bold cyan")
        header_text.append("rgumentative ", style="cyan")
        header_text.append("S", style="bold magenta")
        header_text.append("ystem ", style="magenta")
        header_text.append("S", style="bold yellow")
        header_text.append("ervice", style="yellow")
        header_text.append(" 🤖", style="bold")
        
        panel = Panel(
            Align.center(header_text),
            subtitle="[italic]Watch AI personalities debate any topic[/italic]",
            border_style="bright_blue",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    def display_question(self, question: str):
        """Display the debate question prominently."""
        question_panel = Panel(
            f"[bold cyan]{question}[/bold cyan]",
            title="[bold]Today's Debate Question[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(question_panel)
        self.console.print()
    
    def display_participants(self, personalities: Dict[str, Any]):
        """Display the debate participants."""
        self.console.print("[bold]Debate Participants:[/bold]\n")
        
        for name, config in personalities.items():
            # Get color based on name
            colors = {
                "Philosopher": "blue",
                "Scientist": "green",
                "Artist": "magenta", 
                "Pragmatist": "yellow"
            }
            color = colors.get(name, "cyan")
            
            # Create participant info
            info_lines = [
                f"[{color}]Role:[/{color}] {config.get('role', 'Unknown')}",
                f"[{color}]Style:[/{color}] {config.get('debate_style', 'Unknown')}",
                f"[{color}]Perspective:[/{color}] {config.get('perspective', 'Unknown')}"
            ]
            
            panel = Panel(
                "\n".join(info_lines),
                title=f"[bold {color}]{name}[/bold {color}]",
                border_style=color,
                width=50
            )
            self.console.print(panel)
        
        self.console.print()
    
    def display_round_header(self, round_num: int, round_type: str = "Arguments"):
        """Display a round header."""
        self.console.print(f"\n[bold magenta]═══ Round {round_num} {round_type} ═══[/bold magenta]\n")
    
    def display_argument(self, speaker: str, argument: str, color: Optional[str] = None):
        """Display a single argument in a panel."""
        if not color:
            colors = {
                "Philosopher": "blue",
                "Scientist": "green",
                "Artist": "magenta",
                "Pragmatist": "yellow"
            }
            color = colors.get(speaker, "cyan")
        
        panel = Panel(
            argument,
            title=f"[bold {color}]{speaker}[/bold {color}]",
            border_style=color,
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    def display_judge_verdict(self, verdict: str, judge_name: str = "Judge"):
        """Display the judge's final verdict."""
        self.console.print("\n[bold red]═══ Final Verdict ═══[/bold red]\n")
        
        verdict_panel = Panel(
            verdict,
            title=f"[bold red]{judge_name}'s Decision[/bold red]",
            border_style="red",
            padding=(1, 2)
        )
        self.console.print(verdict_panel)
        self.console.print()
    
    def display_voting_table(self, votes: List[Dict[str, Any]]):
        """Display votes in a formatted table."""
        vote_table = Table(
            title="Individual Rankings",
            show_header=True,
            header_style="bold magenta"
        )
        
        vote_table.add_column("Voter", style="cyan", width=12)
        vote_table.add_column("1st Choice", style="green")
        vote_table.add_column("2nd Choice", style="yellow")
        vote_table.add_column("3rd Choice", style="orange1")
        vote_table.add_column("4th Choice", style="red")
        
        for vote in votes:
            row = [vote["voter"]]
            rankings = vote.get("rankings", [])
            
            for i in range(4):
                if i < len(rankings):
                    if i == 0:
                        row.append(f"[bold]{rankings[i]}[/bold]")
                    else:
                        row.append(rankings[i])
                else:
                    row.append("-")
            
            vote_table.add_row(*row)
        
        self.console.print(vote_table)
        self.console.print()
    
    def display_score_summary(
        self,
        scores: Dict[str, int],
        max_score: int,
        threshold_percentage: float
    ):
        """Display score summary with progress bars."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        threshold_score = max_score * threshold_percentage
        
        score_lines = []
        for participant, score in sorted_scores:
            percentage = (score / max_score) * 100
            bar_length = int(percentage / 5)  # 20 chars max
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            score_lines.append(
                f"{participant:<12} {bar} {score:>2} pts ({percentage:>5.1f}%)"
            )
        
        score_panel = Panel(
            "\n".join(score_lines),
            title="[bold]Point Totals[/bold]",
            border_style="cyan"
        )
        self.console.print(score_panel)
        
        # Display consensus status
        if sorted_scores:
            top_participant, top_score = sorted_scores[0]
            if top_score >= threshold_score:
                self.console.print(
                    f"\n[bold green]✓ CONSENSUS REACHED! Winner: {top_participant}[/bold green]"
                )
            else:
                needed = threshold_score - top_score
                self.console.print(
                    f"\n[yellow]✗ No consensus yet. "
                    f"Top scorer needs {needed:.0f} more points.[/yellow]"
                )
    
    def display_error(self, message: str):
        """Display an error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")
    
    def display_warning(self, message: str):
        """Display a warning message."""
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
    
    def display_success(self, message: str):
        """Display a success message."""
        self.console.print(f"[bold green]✓[/bold green] {message}")
    
    def display_info(self, message: str):
        """Display an info message."""
        self.console.print(f"[bold blue]ℹ[/bold blue] {message}")
    
    def create_progress(self, description: str) -> Progress:
        """Create a progress indicator."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        )