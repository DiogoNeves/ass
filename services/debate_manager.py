"""Core debate orchestration service."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from models.arguments import Argument, DebateContext
from models.debate import DebateConfig, DebateIteration, DebateState
from models.voting import Vote
from personality import LLMPersonality
from voting import VotingSystem


class DebateManager:
    """Manages the core debate flow and orchestration."""
    
    def __init__(self, config: DebateConfig, console: Optional[Console] = None):
        self.config = config
        self.console = console or Console()
        self.debate_state: Optional[DebateState] = None
        
    def initialize_debate(self, question: str, personalities: Dict[str, LLMPersonality]) -> DebateState:
        """Initialize a new debate state."""
        self.debate_state = DebateState(
            debate_id=str(uuid.uuid4()),
            question=question,
            participants=list(personalities.keys()),
            config=self.config,
            start_time=datetime.now()
        )
        return self.debate_state
    
    def format_current_round_context(self, round_arguments: Dict[str, str]) -> str:
        """Format the current round's arguments for display."""
        context_parts = []
        for speaker, argument in round_arguments.items():
            context_parts.append(f"{speaker}:\n{argument}\n")
        return "\n".join(context_parts)
    
    def format_debate_history(self, debate_history: List[Dict[str, str]]) -> str:
        """Format the entire debate history."""
        if not debate_history:
            return "No previous arguments."
        
        history_text = []
        for i, round_args in enumerate(debate_history):
            history_text.append(f"\n--- Round {i + 1} ---")
            history_text.append(self.format_current_round_context(round_args))
        
        return "\n".join(history_text)
    
    def create_debate_context(
        self, 
        iteration: int, 
        debate_history: List[Dict[str, str]],
        phase: str = "main"
    ) -> DebateContext:
        """Create a DebateContext for argument generation."""
        context = DebateContext(
            current_iteration=iteration,
            question=self.debate_state.question,
            debate_phase=phase
        )
        
        # Convert history to Arguments
        for round_idx, round_args in enumerate(debate_history):
            for speaker, content in round_args.items():
                arg = Argument(
                    speaker=speaker,
                    content=content,
                    iteration=round_idx
                )
                
                if speaker not in context.previous_arguments:
                    context.previous_arguments[speaker] = []
                context.previous_arguments[speaker].append(arg)
        
        return context
    
    def collect_arguments(
        self,
        personalities: Dict[str, LLMPersonality],
        context: DebateContext,
        show_progress: bool = True
    ) -> Dict[str, str]:
        """Collect arguments from all personalities for current round."""
        arguments = {}
        
        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                for name, personality in personalities.items():
                    task = progress.add_task(f"[cyan]{name} is thinking...", total=None)
                    
                    # Generate argument
                    argument = personality.generate_response(
                        self.debate_state.question,
                        context.summarize_for_participant(name),
                        context.current_iteration
                    )
                    
                    arguments[name] = argument
                    progress.remove_task(task)
        else:
            # Without progress display
            for name, personality in personalities.items():
                arguments[name] = personality.generate_response(
                    self.debate_state.question,
                    context.summarize_for_participant(name),
                    context.current_iteration
                )
        
        return arguments
    
    def display_arguments(self, arguments: Dict[str, str], iteration: int):
        """Display arguments in formatted panels."""
        self.console.print(f"\n[bold magenta]═══ Round {iteration + 1} Arguments ═══[/bold magenta]\n")
        
        for speaker, argument in arguments.items():
            # Create styled panel based on speaker
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
            self.console.print()  # Space between panels
    
    def collect_votes(
        self,
        personalities: Dict[str, LLMPersonality],
        voting_system: VotingSystem,
        debate_context: str,
        iteration: int
    ) -> List[Vote]:
        """Collect votes from all personalities."""
        votes = []
        participant_names = list(personalities.keys())
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            for name, personality in personalities.items():
                task = progress.add_task(f"[cyan]{name} is voting...", total=None)
                
                try:
                    vote_data = personality.generate_vote(participant_names, debate_context)
                    
                    vote = Vote(
                        voter=personality.config.name,
                        rankings=vote_data.get("rankings", participant_names),
                        reasoning=vote_data.get("reasoning", "No reasoning provided"),
                        iteration=iteration
                    )
                    
                    votes.append(vote)
                    
                except Exception as e:
                    self.console.print(f"[red]Error getting vote from {name}: {e}[/red]")
                    # Create a default vote
                    vote = Vote(
                        voter=name,
                        rankings=participant_names,
                        reasoning="Error generating vote",
                        iteration=iteration
                    )
                    votes.append(vote)
                
                progress.remove_task(task)
        
        return votes
    
    def display_vote_results(self, votes: List[Vote], voting_system: VotingSystem, iteration: int):
        """Display voting results in a formatted table."""
        self.console.print(f"\n[bold cyan]═══ Voting Results - Round {iteration + 1} ═══[/bold cyan]\n")
        
        # Create a table for individual votes
        vote_table = Table(title="Individual Rankings", show_header=True, header_style="bold magenta")
        vote_table.add_column("Voter", style="cyan", width=12)
        vote_table.add_column("1st Choice", style="green")
        vote_table.add_column("2nd Choice", style="yellow") 
        vote_table.add_column("3rd Choice", style="orange1")
        vote_table.add_column("4th Choice", style="red")
        
        for vote in votes:
            row = [vote.voter]
            for i, ranked in enumerate(vote.rankings[:4]):
                if i == 0:
                    row.append(f"[bold]{ranked}[/bold]")
                else:
                    row.append(ranked)
            vote_table.add_row(*row)
        
        self.console.print(vote_table)
        self.console.print()
        
        # Calculate and display scores
        scores = voting_system.calculate_scores(votes)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Create score summary panel
        score_lines = []
        max_score = voting_system.max_possible_points
        threshold_score = max_score * voting_system.config.point_threshold
        
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
        
        # Check for consensus
        consensus, winner = voting_system.check_consensus(scores)
        
        if consensus:
            self.console.print(f"\n[bold green]✓ CONSENSUS REACHED! Winner: {winner}[/bold green]")
            self.console.print(f"[green]Achieved {scores[winner]} points (threshold: {threshold_score:.0f})[/green]")
        else:
            top_score = sorted_scores[0][1] if sorted_scores else 0
            needed = threshold_score - top_score
            self.console.print(f"\n[yellow]✗ No consensus yet. Top scorer needs {needed:.0f} more points.[/yellow]")
        
        # Show reasoning
        self.console.print("\n[bold]Voter Reasoning:[/bold]")
        for vote in votes:
            self.console.print(f"\n[cyan]{vote.voter}:[/cyan] {vote.reasoning}")
    
    def record_iteration(
        self,
        iteration: int,
        arguments: Dict[str, str],
        votes: Optional[List[Vote]] = None,
        consensus_reached: bool = False,
        winner: Optional[str] = None
    ):
        """Record an iteration in the debate state."""
        iteration_data = DebateIteration(
            iteration_number=iteration,
            question=self.debate_state.question,
            arguments=arguments,
            votes=[vote.model_dump() for vote in votes] if votes else None,
            consensus_reached=consensus_reached,
            winner=winner
        )
        
        self.debate_state.iterations.append(iteration_data)
    
    def finalize_debate(self, final_verdict: Optional[str] = None):
        """Finalize the debate state."""
        self.debate_state.end_time = datetime.now()
        self.debate_state.final_verdict = final_verdict
    
    def get_debate_summary(self) -> Dict[str, Any]:
        """Get a summary of the debate for saving."""
        if not self.debate_state:
            return {}
        
        return self.debate_state.to_save_format()