#!/usr/bin/env python3
"""
Demo of the voting system without requiring API keys.
This simulates how the voting works in the debate system.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from voting import Vote, VotingConfig, VotingSystem
from config import DebateConfig

console = Console()

def main():
    console.print(Panel("🗳️  VOTING SYSTEM DEMO  🗳️", style="bold blue"))
    console.print("\nThis demo shows how the voting system works without requiring API keys.\n")
    
    # Setup
    config = DebateConfig()
    voting_config = VotingConfig(
        point_threshold=config.consensus_threshold,
        scoring_system=config.scoring_system,
        min_iterations=2,
        max_iterations=5
    )
    
    participants = ["Claude Optimist", "Claude Skeptic", "GPT Visionary", "GPT Critic"]
    voting_system = VotingSystem(voting_config, participants)
    
    console.print(f"[bold]Configuration:[/bold]")
    console.print(f"- Consensus threshold: {config.consensus_threshold * 100}%")
    console.print(f"- Scoring: 1st={config.scoring_system[1]}pts, 2nd={config.scoring_system[2]}pts, 3rd={config.scoring_system[3]}pts, 4th={config.scoring_system[4]}pts")
    console.print(f"- Participants: {', '.join(participants)}\n")
    
    # Simulate multiple rounds
    rounds = [
        # Round 1: No clear winner
        {
            "description": "Initial positions - personalities stick to their biases",
            "votes": [
                Vote("Claude Optimist", ["Claude Optimist", "GPT Visionary", "Claude Skeptic", "GPT Critic"], 
                     "I believe my optimistic approach was most compelling", 0),
                Vote("Claude Skeptic", ["Claude Skeptic", "GPT Critic", "Claude Optimist", "GPT Visionary"], 
                     "The critical analysis was more thorough", 0),
                Vote("GPT Visionary", ["GPT Visionary", "Claude Optimist", "GPT Critic", "Claude Skeptic"], 
                     "Innovation-focused arguments were strongest", 0),
                Vote("GPT Critic", ["GPT Critic", "Claude Skeptic", "GPT Visionary", "Claude Optimist"], 
                     "Risk analysis was most important", 0)
            ]
        },
        # Round 2: Some convergence
        {
            "description": "After debate - some minds are changing",
            "votes": [
                Vote("Claude Optimist", ["GPT Visionary", "Claude Optimist", "Claude Skeptic", "GPT Critic"], 
                     "GPT Visionary made excellent points about balanced innovation", 1),
                Vote("Claude Skeptic", ["GPT Visionary", "Claude Skeptic", "GPT Critic", "Claude Optimist"], 
                     "The visionary approach addressed my concerns well", 1),
                Vote("GPT Visionary", ["GPT Visionary", "Claude Optimist", "Claude Skeptic", "GPT Critic"], 
                     "My position remains strong with growing support", 1),
                Vote("GPT Critic", ["GPT Visionary", "GPT Critic", "Claude Skeptic", "Claude Optimist"], 
                     "The visionary balanced innovation with practical considerations", 1)
            ]
        },
        # Round 3: Near consensus
        {
            "description": "Approaching consensus - most agree on the winner",
            "votes": [
                Vote("Claude Optimist", ["GPT Visionary", "Claude Optimist", "GPT Critic", "Claude Skeptic"], 
                     "GPT Visionary has proven their case convincingly", 2),
                Vote("Claude Skeptic", ["GPT Visionary", "GPT Critic", "Claude Skeptic", "Claude Optimist"], 
                     "I must admit the visionary approach is most sound", 2),
                Vote("GPT Visionary", ["GPT Visionary", "Claude Optimist", "GPT Critic", "Claude Skeptic"], 
                     "Grateful for the recognition of my balanced approach", 2),
                Vote("GPT Critic", ["GPT Visionary", "GPT Critic", "Claude Optimist", "Claude Skeptic"], 
                     "The visionary has addressed all major concerns effectively", 2)
            ]
        }
    ]
    
    # Run simulation
    for i, round_data in enumerate(rounds):
        console.print(f"\n[bold white]═══ ITERATION {i} ═══[/bold white]")
        console.print(f"[italic]{round_data['description']}[/italic]\n")
        
        # Add votes
        voting_system.add_votes(round_data['votes'])
        
        # Calculate and display results
        scores = voting_system.calculate_scores(round_data['votes'])
        consensus, winner = voting_system.check_consensus(scores)
        
        # Create results table
        table = Table(title=f"Voting Results - Iteration {i}")
        table.add_column("Participant", style="cyan")
        table.add_column("Score", style="yellow")
        table.add_column("Percentage", style="green")
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for participant, score in sorted_scores:
            percentage = (score / voting_system.max_possible_points) * 100
            table.add_row(participant, str(score), f"{percentage:.1f}%")
        
        console.print(table)
        
        # Show individual votes
        console.print("\n[bold]How they voted:[/bold]")
        for vote in round_data['votes']:
            console.print(f"\n{vote.voter}:")
            console.print(f"  Rankings: {' → '.join(vote.rankings[:2])}...")
            console.print(f"  [italic dim]{vote.reasoning}[/italic dim]")
        
        # Consensus status
        if consensus:
            console.print(f"\n[bold green]✓ CONSENSUS REACHED! Winner: {winner}[/bold green]")
            console.print("\nIn a real debate, this would trigger the judge's final review.")
            break
        else:
            threshold_score = voting_system.max_possible_points * config.consensus_threshold
            console.print(f"\n[yellow]No consensus yet. Need {threshold_score:.0f} points ({config.consensus_threshold * 100:.0f}% of max)[/yellow]")
            if i < len(rounds) - 1:
                console.print("[dim]The debate would continue to the next iteration...[/dim]")
    
    # Show trends
    console.print("\n[bold]Score Progression:[/bold]")
    trends = voting_system.get_voting_trends()
    for participant, scores in trends.items():
        trend = " → ".join(map(str, scores))
        console.print(f"{participant}: {trend}")
    
    console.print("\n[bold green]Demo complete![/bold green]")
    console.print("\nIn the actual system:")
    console.print("- AI personalities would generate real arguments")
    console.print("- Votes would be based on actual debate quality")
    console.print("- The judge would review everything before final decision")

if __name__ == "__main__":
    main()