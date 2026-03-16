#!/usr/bin/env python3

import os
import time
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.table import Table

from config import DebateConfig
from debate_engine import (
    EVENT_BELIEF_FORMED,
    EVENT_BELIEF_FORMING,
    EVENT_BELIEF_UPDATED,
    EVENT_BELIEF_UPDATING,
    EVENT_CONSENSUS,
    EVENT_DEBATE_END,
    EVENT_DEBATE_START,
    EVENT_ITERATION_START,
    EVENT_JUDGE_DECISION,
    EVENT_JUDGE_THINKING,
    EVENT_NEXT_ITERATION,
    EVENT_RESPONSE,
    EVENT_THINKING,
    EVENT_VOTE_RESULTS,
    EVENT_VOTING_PERSONALITY,
    EVENT_VOTING_START,
    DebateEngine,
)

console = Console()


class DebateApp:
    def __init__(self, config: Optional[DebateConfig] = None):
        self.config = config or DebateConfig.from_env()
        self.engine = DebateEngine(self.config)

    def display_header(self):
        header_text = "\U0001f3db\ufe0f  ASS - ARGUMENTATIVE SYSTEM SERVICE  \U0001f3db\ufe0f\n"
        header_text += "Voting Mode Enabled" if self.config.voting_enabled else "Classic Mode"
        console.print(Panel(header_text, style="blue"))
        console.print()

    def get_question(self):
        console.print("[bold cyan]Welcome to ASS![/bold cyan]")
        if self.config.voting_enabled:
            console.print(
                "AI personalities will debate until reaching consensus through voting.\n"
                "[dim]Press Ctrl+C at any time to stop the debate.[/dim]\n"
            )
        else:
            console.print(
                "Four AI personalities will debate your question for 3 rounds.\n"
                "[dim]Press Ctrl+C at any time to stop the debate.[/dim]\n"
            )
        return Prompt.ask("[bold yellow]What question would you like them to debate?[/bold yellow]")

    def _render_event(self, event):
        """Render a single debate engine event to the Rich terminal."""
        event_type = event["type"]

        if event_type == EVENT_DEBATE_START:
            console.print(f"\n[bold magenta]\U0001f3af DEBATE TOPIC:[/bold magenta] {event['question']}\n")

        elif event_type == EVENT_ITERATION_START:
            console.print(f"[bold white]\u2550\u2550\u2550 {event['label']} \u2550\u2550\u2550[/bold white]\n")

        elif event_type == EVENT_BELIEF_FORMING:
            self._start_spinner = Progress(
                SpinnerColumn(),
                TextColumn(f"[bold]{event['personality']} is forming internal beliefs..."),
                transient=True, console=console,
            )
            self._start_spinner.start()
            self._start_spinner.add_task("beliefs", total=None)

        elif event_type == EVENT_BELIEF_FORMED:
            if hasattr(self, '_start_spinner'):
                self._start_spinner.stop()
            if os.getenv("DEBUG_BELIEFS", "").lower() == "true":
                beliefs = event.get("beliefs", {})
                console.print(f"[dim]Internal beliefs: {beliefs.get('core_position', 'N/A')}[/dim]")

        elif event_type == EVENT_BELIEF_UPDATING:
            self._start_spinner = Progress(
                SpinnerColumn(),
                TextColumn(f"[bold]{event['personality']} is evaluating arguments..."),
                transient=True, console=console,
            )
            self._start_spinner.start()
            self._start_spinner.add_task("evaluating", total=None)

        elif event_type == EVENT_BELIEF_UPDATED:
            if hasattr(self, '_start_spinner'):
                self._start_spinner.stop()
            if event.get("changed") and os.getenv("DEBUG_BELIEFS", "").lower() == "true":
                console.print(f"[yellow]{event['personality']} updated their beliefs![/yellow]")

        elif event_type == EVENT_THINKING:
            action = event.get("action", "thinking")
            self._start_spinner = Progress(
                SpinnerColumn(),
                TextColumn(f"[bold]{event['personality']} is {action}..."),
                transient=True, console=console,
            )
            self._start_spinner.start()
            self._start_spinner.add_task("thinking", total=None)
            time.sleep(1)

        elif event_type == EVENT_RESPONSE:
            if hasattr(self, '_start_spinner'):
                self._start_spinner.stop()
            console.print(Panel(
                event["text"],
                title=f"\U0001f4ad {event['personality']}",
                style=event["style"],
                padding=(1, 2),
            ))
            console.print()

        elif event_type == EVENT_VOTING_START:
            console.print("\n[bold white]\u2550\u2550\u2550 VOTING PHASE \u2550\u2550\u2550[/bold white]\n")

        elif event_type == EVENT_VOTING_PERSONALITY:
            self._start_spinner = Progress(
                SpinnerColumn(),
                TextColumn(f"[bold]{event['personality']} is evaluating arguments..."),
                transient=True, console=console,
            )
            self._start_spinner.start()
            self._start_spinner.add_task("voting", total=None)

        elif event_type == EVENT_VOTE_RESULTS:
            if hasattr(self, '_start_spinner'):
                self._start_spinner.stop()
            self._display_vote_results(event)

        elif event_type == EVENT_CONSENSUS:
            pass  # Already shown in vote results

        elif event_type == EVENT_NEXT_ITERATION:
            console.print(
                f"\n[dim]\u2192 Iteration {event['next_iteration'] + 1}/{event['max_iterations']} starting...[/dim]\n"
            )

        elif event_type == EVENT_JUDGE_THINKING:
            self._start_spinner = Progress(
                SpinnerColumn(),
                TextColumn("[bold]The Judge is reviewing the entire debate..."),
                transient=True, console=console,
            )
            self._start_spinner.start()
            self._start_spinner.add_task("judging", total=None)
            time.sleep(2)

        elif event_type == EVENT_JUDGE_DECISION:
            if hasattr(self, '_start_spinner'):
                self._start_spinner.stop()
            console.print("\n[bold white]\u2550\u2550\u2550 FINAL JUDGMENT \u2550\u2550\u2550[/bold white]\n")
            console.print(Panel(
                event["text"],
                title="\u2696\ufe0f  FINAL DECISION",
                style="bold white",
                padding=(1, 2),
            ))

        elif event_type == EVENT_DEBATE_END:
            pass

    def _display_vote_results(self, event):
        """Display voting results from a vote_results event."""
        summary = event.get("summary", {})
        iteration = event.get("iteration", 0)
        max_points = event.get("max_possible_points", 16)
        threshold = event.get("threshold", 0.75)

        if not summary:
            console.print("[red]Error: Unable to get voting summary[/red]")
            return

        table = Table(title=f"Voting Results - Iteration {iteration + 1}")
        table.add_column("Participant", style="cyan")
        table.add_column("Score", style="yellow")
        table.add_column("Percentage", style="green")

        for participant, score in summary.get("sorted_rankings", []):
            percentage = (score / max_points) * 100
            table.add_row(participant, str(score), f"{percentage:.1f}%")

        console.print(table)

        console.print("\n[bold]Individual Rankings:[/bold]")
        for vote_info in summary.get("individual_votes", []):
            console.print(f"\n{vote_info.get('voter', 'Unknown')}:")
            rankings = vote_info.get("rankings", [])
            if rankings:
                arrow = ' \u2192 '
                console.print(f"  {arrow.join(rankings)}")
            if vote_info.get("reasoning"):
                console.print(f"  [italic]{vote_info['reasoning']}[/italic]")

        if summary.get("consensus_reached", False):
            console.print(
                f"\n[bold green]\u2713 CONSENSUS REACHED! Winner: {summary.get('winner', 'Unknown')}[/bold green]"
            )
        else:
            needed = summary.get("threshold_score", 0)
            console.print(
                f"\n[yellow]No consensus yet. Need {needed:.0f} points ({threshold * 100:.0f}% of max)[/yellow]"
            )

    def run_debate(self, question: str):
        """Run a debate by consuming events from the engine."""
        for event in self.engine.run_debate(question):
            self._render_event(event)

    def run(self):
        self.display_header()
        question = self.get_question()
        self.run_debate(question)
        console.print("\n[bold green]Thank you for using ASS![/bold green]")
        if self.config.voting_enabled:
            console.print("[dim]Tip: Use --classic-mode to run the original 3-round format[/dim]")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ASS - Argumentative System Service")
    parser.add_argument("--classic-mode", action="store_true", help="Use classic 3-round format")
    parser.add_argument("--no-voting", action="store_true", help="Disable voting system")
    parser.add_argument("--voting-threshold", type=float, help="Consensus threshold (0-1)")
    parser.add_argument("--max-iterations", type=int, help="Maximum debate iterations")
    parser.add_argument("--min-iterations", type=int, help="Minimum iterations before voting")
    parser.add_argument("--local-model-url", help="URL for local model server")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--no-save", action="store_true", help="Disable saving debates to files")

    args = parser.parse_args()

    if args.config:
        config = DebateConfig.from_file(args.config)
    else:
        config = DebateConfig.from_env()

    if args.classic_mode:
        config.classic_mode = True
    if args.no_voting:
        config.voting_enabled = False
    if args.voting_threshold is not None:
        config.consensus_threshold = args.voting_threshold
    if args.max_iterations is not None:
        config.max_iterations = args.max_iterations
    if args.min_iterations is not None:
        config.min_iterations = args.min_iterations
    if args.local_model_url:
        os.environ["LOCAL_MODEL_URL"] = args.local_model_url
        config.allow_local_models = True
    if args.no_save:
        config.save_enabled = False

    app = DebateApp(config)
    app.run()


if __name__ == "__main__":
    main()
