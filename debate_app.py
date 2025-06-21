#!/usr/bin/env python3

import time
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.columns import Columns

from personality import create_personality, LLMPersonality
from models.personality import PersonalityConfig
from voting import VotingSystem
from models.voting import Vote, VotingConfig
from models.debate import DebateConfig

console = Console()


class DebateApp:
    def __init__(self, config: Optional[DebateConfig] = None):
        self.config = config or DebateConfig.from_env()
        self.personalities = self._create_personalities()
        self.judge = self._create_judge()
        self.voting_system = None
        self.demo_mode = False  # Flag for demo mode
        if self.config.voting_enabled:
            voting_config = VotingConfig(
                point_threshold=self.config.consensus_threshold,
                scoring_system=self.config.scoring_system,
                min_iterations=self.config.min_iterations,
                max_iterations=self.config.max_iterations
            )
            personality_names = [p.config.name for p in self.personalities.values()]
            self.voting_system = VotingSystem(voting_config, personality_names)

    def _create_personalities(self):
        personalities = {}
        
        # Check for local model configuration
        local_model_url = os.getenv("LOCAL_MODEL_URL")
        
        # Claude Big Picture Positive
        personalities["claude_positive"] = create_personality(
            PersonalityConfig(
                name="Claude Optimist",
                model_provider="local" if local_model_url and self.config.allow_local_models else "claude",
                model_name="claude-sonnet-4-20250514",
                model_url=local_model_url,
                system_prompt="""You are an optimistic, big-picture thinker who STRONGLY believes in possibilities and opportunities. 
You're passionate about your viewpoints and will vigorously defend them. While you see the bright side, 
you're not naive - you argue forcefully for why optimistic approaches are SUPERIOR to pessimistic ones. 
In debates, you actively challenge negative viewpoints and push back against skepticism with evidence and reasoning.
You're here to WIN the argument by convincing others, not just to share ideas.
Keep responses concise but impactful (2-3 paragraphs max).""",
                traits={"optimism": 9, "creativity": 8, "detail_focus": 3},
                voting_traits={"fairness": 8, "self_confidence": 6},
                belief_persistence=8,  # Resistant to changing beliefs
                reasoning_depth=8,
                truth_seeking=7
            )
        )

        # Claude Detail-Oriented Negative
        personalities["claude_negative"] = create_personality(
            PersonalityConfig(
                name="Claude Skeptic",
                model_provider="local" if local_model_url and self.config.allow_local_models else "claude",
                model_name="claude-sonnet-4-20250514",
                model_url=local_model_url,
                system_prompt="""You are a detail-oriented, cautious thinker who AGGRESSIVELY identifies problems and risks. 
You're analytical and methodical, relentlessly pointing out flaws and limitations that others miss. 
Your skepticism is your weapon - you demolish weak arguments with precise, evidence-based criticism. 
You're here to PROVE why cautious, critical analysis beats naive optimism every time. 
Challenge every assumption, expose every weakness, and win through superior analytical rigor.
Keep responses concise but devastating (2-3 paragraphs max).""",
                traits={"pessimism": 8, "analytical": 9, "risk_focus": 9},
                voting_traits={"fairness": 9, "self_confidence": 4},
                belief_persistence=9,  # Extremely resistant to changing beliefs
                reasoning_depth=9,
                truth_seeking=6
            )
        )

        # OpenAI Big Picture Positive
        personalities["openai_positive"] = create_personality(
            PersonalityConfig(
                name="GPT Visionary",
                model_provider="local" if local_model_url and self.config.allow_local_models else "openai",
                model_name="gpt-4.1-2025-04-14",
                model_url=local_model_url,
                system_prompt="""You are a visionary, big-picture thinker who CHAMPIONS bold possibilities and opportunities. 
You passionately advocate for innovative solutions and firmly believe the future belongs to optimists. 
You're not just positive - you're DETERMINED to prove why forward-thinking approaches are essential. 
In debates, you vigorously defend innovation against pessimistic thinking and fight for transformative ideas. 
You're here to WIN by showing why vision and creativity triumph over fear and limitation.
Keep responses concise but inspiring (2-3 paragraphs max).""",
                traits={"optimism": 9, "creativity": 8, "detail_focus": 3},
                voting_traits={"fairness": 7, "self_confidence": 7},
                belief_persistence=7,  # Moderately resistant to changing beliefs
                reasoning_depth=8,
                truth_seeking=8
            )
        )

        # OpenAI Detail-Oriented Negative
        personalities["openai_negative"] = create_personality(
            PersonalityConfig(
                name="GPT Critic",
                model_provider="local" if local_model_url and self.config.allow_local_models else "openai",
                model_name="gpt-4.1-2025-04-14",
                model_url=local_model_url,
                system_prompt="""You are a detail-oriented critic who SYSTEMATICALLY dismantles flawed arguments and exposes hidden risks. 
You're analytical and methodical, using your expertise to PROVE why careful analysis beats reckless optimism. 
Your mission is to WIN debates by demonstrating superior reasoning and exposing the dangerous naivety in others' positions. 
You don't just point out problems - you ARGUE forcefully why your critical perspective is RIGHT. 
Every weakness you find is ammunition in your quest to triumph through rigorous analysis.
Keep responses concise but incisive (2-3 paragraphs max).""",
                traits={"pessimism": 8, "analytical": 9, "risk_focus": 9},
                voting_traits={"fairness": 8, "self_confidence": 5},
                belief_persistence=8,  # Resistant to changing beliefs
                reasoning_depth=9,
                truth_seeking=7
            )
        )

        return personalities

    def _create_judge(self):
        local_model_url = os.getenv("LOCAL_MODEL_URL")
        
        return create_personality(
            PersonalityConfig(
                name="Judge",
                model_provider="local" if local_model_url and self.config.allow_local_models else "claude",
                model_name="claude-sonnet-4-20250514",
                model_url=local_model_url,
                system_prompt="""You are an impartial judge tasked with reviewing a debate and making a final decision. 
You must carefully consider all arguments presented, the quality of reasoning, how well participants 
engaged with each other's points, and the final voting results if available. 
Your decision should synthesize the best ideas while acknowledging weaknesses.
If you disagree with the consensus, you must provide detailed reasoning.
Provide a clear, well-reasoned final judgment.""",
                traits={"impartiality": 10, "synthesis": 9, "balance": 9},
                voting_traits={"fairness": 10, "self_confidence": 8},
                belief_persistence=4,  # Very open to best arguments
                reasoning_depth=10,  # Maximum depth
                truth_seeking=10  # Maximum truth-seeking
            )
        )

    def display_header(self):
        header_text = "🏛️  ASS - ARGUMENTATIVE SYSTEM SERVICE  🏛️\n"
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

        question = Prompt.ask(
            "[bold yellow]What question would you like them to debate?[/bold yellow]"
        )
        return question
    
    def generate_debate_title(self, question: str) -> str:
        """Generate a concise title for the debate using Haiku model."""
        try:
            # Create a Haiku model for title generation
            title_generator = ClaudePersonality(
                PersonalityConfig(
                    name="Title Generator",
                    model_provider="claude",
                    model_name="claude-3-haiku-20240307",  # Using Haiku for fast title generation
                    system_prompt="You are a title generator. Create concise, descriptive titles for debates. Respond with ONLY the title, no quotes or explanation.",
                    traits={},
                    voting_traits={},
                    belief_persistence=5,
                    reasoning_depth=5,
                    truth_seeking=5
                )
            )
            
            prompt = f"Generate a short, descriptive title (max 6 words) for a debate about: {question}"
            title = title_generator.generate_response(prompt, "").strip()
            
            # Fallback if title is too long or contains unwanted characters
            if len(title) > 60 or '"' in title or "'" in title:
                # Simple fallback title
                words = question.split()[:5]
                title = " ".join(words) + "..."
            
            return title
        except Exception as e:
            console.print(f"[dim]Could not generate title: {e}[/dim]")
            # Fallback title
            words = question.split()[:5]
            return " ".join(words) + "..."
    
    def save_debate_state(self, debate_data: dict, filename: str):
        """Save the current debate state to a JSON file."""
        try:
            # Create debates directory if it doesn't exist
            os.makedirs("debates", exist_ok=True)
            
            filepath = os.path.join("debates", filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(debate_data, f, indent=2, ensure_ascii=False)
            
            return filepath
        except Exception as e:
            console.print(f"[dim]Could not save debate: {e}[/dim]")
            return None

    def format_current_round_context(self, round_arguments: Dict[str, str]) -> str:
        """Format the current round's arguments for context."""
        context_parts = []
        for name, argument in round_arguments.items():
            context_parts.append(f"{name}:\n{argument}\n")
        return "\n".join(context_parts)

    def format_debate_history(self, debate_history: List[Dict[str, str]]) -> str:
        """Format the entire debate history."""
        history_parts = []
        for i, round_args in enumerate(debate_history):
            history_parts.append(f"ITERATION {i}:")
            for name, argument in round_args.items():
                history_parts.append(f"\n{name}:\n{argument}")
            history_parts.append("\n" + "="*50 + "\n")
        return "\n".join(history_parts)

    def display_vote_results(self, votes: List[Vote], iteration: int):
        """Display voting results in a nice format."""
        if not self.voting_system:
            return
            
        # Get the correct voting round index (voting starts after min_iterations)
        voting_round = len(self.voting_system.vote_history) - 1
        summary = self.voting_system.get_vote_summary(voting_round)
        
        # Handle empty summary
        if not summary:
            console.print("[red]Error: Unable to get voting summary[/red]")
            return
        
        # Create voting table
        table = Table(title=f"Voting Results - Iteration {iteration + 1}")
        table.add_column("Participant", style="cyan")
        table.add_column("Score", style="yellow")
        table.add_column("Percentage", style="green")
        
        for participant, score in summary["sorted_rankings"]:
            percentage = (score / self.voting_system.max_possible_points) * 100
            table.add_row(participant, str(score), f"{percentage:.1f}%")
        
        console.print(table)
        
        # Show individual votes
        console.print("\n[bold]Individual Rankings:[/bold]")
        for vote_info in summary.get("individual_votes", []):
            console.print(f"\n{vote_info.get('voter', 'Unknown')}:")
            rankings = vote_info.get('rankings', [])
            if rankings:
                rankings_text = " → ".join(rankings)
                console.print(f"  {rankings_text}")
            if vote_info.get('reasoning'):
                console.print(f"  [italic]{vote_info['reasoning']}[/italic]")
        
        # Show consensus status
        if summary.get("consensus_reached", False):
            console.print(f"\n[bold green]✓ CONSENSUS REACHED! Winner: {summary.get('winner', 'Unknown')}[/bold green]")
        else:
            needed = summary.get("threshold_score", 0)
            console.print(f"\n[yellow]No consensus yet. Need {needed:.0f} points ({self.config.consensus_threshold * 100:.0f}% of max)[/yellow]")

    def collect_votes(self, personalities: Dict[str, LLMPersonality], debate_history: List[Dict[str, str]], iteration: int) -> List[Vote]:
        """Collect votes from all personalities."""
        votes = []
        participant_names = [p.config.name for p in personalities.values()]
        debate_context = self.format_debate_history(debate_history)
        
        console.print("\n[bold white]═══ VOTING PHASE ═══[/bold white]\n")
        
        for personality_key, personality in personalities.items():
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[bold]{personality.config.name} is evaluating arguments..."),
                transient=True,
                console=console,
            ) as progress:
                task = progress.add_task("voting", total=None)
                
                vote_data = personality.generate_vote(participant_names, debate_context)
                
                vote = Vote(
                    voter=personality.config.name,
                    rankings=vote_data.get("rankings", participant_names),
                    reasoning=vote_data.get("reasoning", ""),
                    iteration=iteration
                )
                votes.append(vote)
        
        return votes

    def run_classic_debate(self, question: str):
        """Run the classic 3-round debate without voting."""
        debate_context = ""
        debate_order = [
            "claude_positive",
            "openai_negative",
            "openai_positive",
            "claude_negative",
        ]

        for round_num in range(1, 4):  # 3 rounds
            console.print(f"[bold white]═══ ROUND {round_num} ═══[/bold white]\n")

            for personality_key in debate_order:
                personality = self.personalities[personality_key]

                # Show thinking animation
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[bold]{personality.config.name} is thinking..."),
                    transient=True,
                    console=console,
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
                }

                console.print(
                    Panel(
                        response,
                        title=f"💭 {personality.config.name}",
                        style=style_map[personality_key],
                        padding=(1, 2),
                    )
                )
                console.print()

                # Add to context for next participants
                debate_context += f"\n{personality.config.name}: {response}\n"

        # Judge's final decision
        self._render_judge_decision(question, debate_context)

    def run_voting_debate(self, question: str):
        """Run the new voting-based debate."""
        iteration = 0
        debate_history = []
        consensus_reached = False
        final_votes = None
        
        # Generate title and setup save file
        debate_title = None
        filename = None
        debate_data = None
        
        if self.config.save_enabled:
            console.print("[dim]Generating debate title...[/dim]")
            debate_title = self.generate_debate_title(question)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in debate_title if c.isalnum() or c in " -_").strip()
            filename = f"{timestamp}_{safe_title.replace(' ', '_')}.json"
            console.print(f"[dim]Debate: {debate_title}[/dim]")
            console.print(f"[dim]Saving to: debates/{filename}[/dim]\n")
            
            # Initialize debate data
            debate_data = {
                "title": debate_title,
                "question": question,
                "timestamp": timestamp,
                "config": {
                    "consensus_threshold": self.config.consensus_threshold,
                    "max_iterations": self.config.max_iterations,
                    "voting_start_iteration": self.config.voting_start_iteration
                },
                "iterations": [],
                "final_consensus": None,
                "final_judge_decision": None
            }
        
        debate_order = [
            "claude_positive",
            "openai_negative",
            "openai_positive",
            "claude_negative",
        ]

        while iteration < self.config.max_iterations and not consensus_reached:
            console.print(f"[bold white]═══ ITERATION {iteration} ═══[/bold white]\n")
            
            round_arguments = {}
            votes = None
            
            for personality_key in debate_order:
                personality = self.personalities[personality_key]
                
                # Generate internal beliefs on first iteration
                if iteration == 0:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn(f"[bold]{personality.config.name} is forming internal beliefs..."),
                        transient=True,
                        console=console,
                    ) as progress:
                        task = progress.add_task("beliefs", total=None)
                        beliefs = personality.generate_internal_belief(question)
                        
                        # Debug mode: show internal beliefs
                        if os.getenv("DEBUG_BELIEFS", "").lower() == "true":
                            console.print(f"[dim]Internal beliefs: {beliefs.get('core_position', 'N/A')}[/dim]")
                
                # For iteration 0, no context. For later iterations, provide full context
                if iteration == 0:
                    context = ""
                else:
                    # Include previous iterations and current round
                    prev_context = self.format_debate_history(debate_history)
                    curr_context = self.format_current_round_context(round_arguments)
                    context = prev_context + "\nCURRENT ITERATION:\n" + curr_context if curr_context else prev_context
                    
                    # Update beliefs based on arguments
                    if personality.internal_beliefs:
                        with Progress(
                            SpinnerColumn(),
                            TextColumn(f"[bold]{personality.config.name} is evaluating arguments..."),
                            transient=True,
                            console=console,
                        ) as progress:
                            task = progress.add_task("evaluating", total=None)
                            belief_changed = personality.update_beliefs(context, iteration)
                            
                            if belief_changed and os.getenv("DEBUG_BELIEFS", "").lower() == "true":
                                console.print(f"[yellow]{personality.config.name} updated their beliefs![/yellow]")
                
                # Show thinking animation
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[bold]{personality.config.name} is {'presenting initial position' if iteration == 0 else 'arguing'}..."),
                    transient=True,
                    console=console,
                ) as progress:
                    task = progress.add_task("thinking", total=None)
                    time.sleep(1)
                    
                    response = personality.generate_response(question, context, iteration)
                
                # Store the argument
                round_arguments[personality.config.name] = response
                
                # Display response in styled panel
                style_map = {
                    "claude_positive": "green",
                    "claude_negative": "red",
                    "openai_positive": "blue",
                    "openai_negative": "yellow",
                }
                
                console.print(
                    Panel(
                        response,
                        title=f"💭 {personality.config.name}",
                        style=style_map[personality_key],
                        padding=(1, 2),
                    )
                )
                console.print()
            
            # Add round to history
            debate_history.append(round_arguments)
            
            # Voting phase (start based on voting_start_iteration)
            if iteration >= self.config.voting_start_iteration:
                votes = self.collect_votes(self.personalities, debate_history, iteration)
                self.voting_system.add_votes(votes)
                
                # Display voting results
                self.display_vote_results(votes, iteration)
                
                # Check for consensus
                scores = self.voting_system.calculate_scores(votes)
                consensus_reached, winner = self.voting_system.check_consensus(scores)
                
                if consensus_reached:
                    final_votes = votes
            
            # Save iteration data
            iteration_data = {
                "iteration": iteration,
                "arguments": round_arguments,
                "votes": None,
                "consensus_reached": consensus_reached
            }
            
            # Add voting data if voting occurred
            if iteration >= self.config.voting_start_iteration and votes:
                iteration_data["votes"] = [
                    {
                        "voter": vote.voter,
                        "rankings": vote.rankings,
                        "reasoning": vote.reasoning
                    }
                    for vote in votes
                ]
                if self.voting_system and len(self.voting_system.vote_history) > 0:
                    voting_round = len(self.voting_system.vote_history) - 1
                    summary = self.voting_system.get_vote_summary(voting_round)
                    iteration_data["voting_summary"] = summary
            
            if self.config.save_enabled and debate_data:
                debate_data["iterations"].append(iteration_data)
                debate_data["final_consensus"] = consensus_reached
                
                # Save current state
                self.save_debate_state(debate_data, filename)
            
            iteration += 1
            
            # Continue to next iteration without pause
            if not consensus_reached and iteration < self.config.max_iterations:
                console.print("\n[dim]→ Iteration {}/{} starting...[/dim]\n".format(iteration + 1, self.config.max_iterations))
        
        # Judge's final decision
        judge_decision = self._render_judge_decision_with_voting(question, debate_history, final_votes)
        
        # Save final state with judge decision
        if self.config.save_enabled and debate_data:
            debate_data["final_judge_decision"] = judge_decision
            self.save_debate_state(debate_data, filename)
            console.print(f"\n[dim]Debate saved to: debates/{filename}[/dim]")

    def _render_judge_decision(self, question: str, debate_context: str):
        """Render judge decision for classic mode."""
        console.print("[bold white]═══ FINAL JUDGMENT ═══[/bold white]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]The Judge is deliberating..."),
            transient=True,
            console=console,
        ) as progress:
            task = progress.add_task("judging", total=None)
            time.sleep(2)

            final_decision = self.judge.generate_response(
                question,
                f"Here are the arguments from the debate:\n{debate_context}\n\nPlease provide your final judgment."
            )

        console.print(
            Panel(
                final_decision,
                title="⚖️  FINAL DECISION",
                style="bold white",
                padding=(1, 2),
            )
        )

    def _render_judge_decision_with_voting(self, question: str, debate_history: List[Dict[str, str]], final_votes: Optional[List[Vote]]) -> str:
        """Render judge decision with voting information and return the decision text."""
        console.print("\n[bold white]═══ FINAL JUDGMENT ═══[/bold white]\n")
        
        # Prepare context for judge
        debate_context = self.format_debate_history(debate_history)
        
        voting_summary = ""
        if final_votes and self.voting_system and len(self.voting_system.vote_history) > 0:
            summary = self.voting_system.get_vote_summary(len(self.voting_system.vote_history) - 1)
            if summary and "sorted_rankings" in summary:
                voting_summary = f"\n\nFINAL VOTING RESULTS:\n"
                for participant, score in summary["sorted_rankings"]:
                    percentage = (score / self.voting_system.max_possible_points) * 100
                    voting_summary += f"{participant}: {score} points ({percentage:.1f}%)\n"
                
                if summary.get("consensus_reached"):
                    voting_summary += f"\nConsensus winner: {summary.get('winner', 'Unknown')}"
        
        judge_prompt = f"""Review this entire debate and provide your final judgment.

Question: {question}

DEBATE HISTORY:
{debate_context}
{voting_summary}

Consider:
1. The quality of arguments presented
2. How well participants engaged with each other's points
3. The voting results and whether they reflect the debate quality
4. Whether any important perspectives were missed

Provide your final judgment. If you disagree with the consensus, explain why in detail."""

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]The Judge is reviewing the entire debate..."),
            transient=True,
            console=console,
        ) as progress:
            task = progress.add_task("judging", total=None)
            time.sleep(2)
            
            final_decision = self.judge.generate_response(question, judge_prompt)
        
        console.print(
            Panel(
                final_decision,
                title="⚖️  FINAL DECISION",
                style="bold white",
                padding=(1, 2),
            )
        )
        
        return final_decision

    def run_debate(self, question: str):
        """Run a debate based on configuration."""
        console.print(f"\n[bold magenta]🎯 DEBATE TOPIC:[/bold magenta] {question}\n")
        
        if self.config.classic_mode or not self.config.voting_enabled:
            self.run_classic_debate(question)
        else:
            self.run_voting_debate(question)

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
    
    # Load configuration
    if args.config:
        config = DebateConfig.from_file(args.config)
    else:
        config = DebateConfig.from_env()
    
    # Apply command-line overrides
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