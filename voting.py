from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import json


@dataclass
class VotingConfig:
    """Configuration for the voting system."""
    point_threshold: float = 0.75  # Percentage of max possible points for consensus
    scoring_system: Dict[int, int] = field(default_factory=lambda: {1: 4, 2: 3, 3: 2, 4: 1})
    min_iterations: int = 2  # Minimum iterations before voting can start
    max_iterations: int = 10  # Maximum iterations to prevent infinite loops


@dataclass
class Vote:
    """Represents a single vote from a personality."""
    voter: str
    rankings: List[str]  # Ordered list from best to worst
    reasoning: str
    iteration: int


class VotingSystem:
    """Manages the voting process and consensus determination."""
    
    def __init__(self, config: VotingConfig, participants: List[str]):
        self.config = config
        self.participants = participants
        self.vote_history: List[List[Vote]] = []
        self.max_possible_points = self._calculate_max_points()
    
    def _calculate_max_points(self) -> int:
        """Calculate maximum possible points a participant can receive."""
        # If everyone ranks a participant first
        return len(self.participants) * self.config.scoring_system[1]
    
    def add_votes(self, votes: List[Vote]):
        """Add a round of votes to the history."""
        self.vote_history.append(votes)
    
    def calculate_scores(self, votes: List[Vote]) -> Dict[str, int]:
        """Convert rankings to point scores."""
        scores = defaultdict(int)
        
        for vote in votes:
            for rank, participant in enumerate(vote.rankings, 1):
                if rank in self.config.scoring_system:
                    scores[participant] += self.config.scoring_system[rank]
        
        return dict(scores)
    
    def check_consensus(self, scores: Dict[str, int]) -> Tuple[bool, Optional[str]]:
        """
        Check if consensus has been reached.
        Returns (consensus_reached, winner_name)
        """
        if not scores:
            return False, None
        
        # Find the top scorer
        top_participant = max(scores.items(), key=lambda x: x[1])
        top_score = top_participant[1]
        
        # Check if top score meets threshold
        threshold_score = self.max_possible_points * self.config.point_threshold
        consensus_reached = top_score >= threshold_score
        
        return consensus_reached, top_participant[0] if consensus_reached else None
    
    def get_vote_summary(self, iteration: int) -> Dict[str, any]:
        """Get a summary of voting results for a specific iteration."""
        if iteration >= len(self.vote_history):
            return {}
        
        votes = self.vote_history[iteration]
        scores = self.calculate_scores(votes)
        consensus_reached, winner = self.check_consensus(scores)
        
        # Sort participants by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "iteration": iteration,
            "scores": scores,
            "sorted_rankings": sorted_scores,
            "consensus_reached": consensus_reached,
            "winner": winner,
            "threshold_score": self.max_possible_points * self.config.point_threshold,
            "individual_votes": [
                {
                    "voter": vote.voter,
                    "rankings": vote.rankings,
                    "reasoning": vote.reasoning
                }
                for vote in votes
            ]
        }
    
    def get_voting_trends(self) -> Dict[str, List[int]]:
        """Track how scores changed over iterations."""
        trends = defaultdict(list)
        
        for iteration_votes in self.vote_history:
            scores = self.calculate_scores(iteration_votes)
            for participant in self.participants:
                trends[participant].append(scores.get(participant, 0))
        
        return dict(trends)
    
    def format_vote_table(self, votes: List[Vote]) -> str:
        """Format votes as a readable table."""
        lines = []
        scores = self.calculate_scores(votes)
        
        lines.append("VOTING RESULTS")
        lines.append("=" * 50)
        
        # Individual votes
        for vote in votes:
            lines.append(f"\n{vote.voter}'s Rankings:")
            for rank, participant in enumerate(vote.rankings, 1):
                points = self.config.scoring_system.get(rank, 0)
                lines.append(f"  {rank}. {participant} ({points} points)")
            if vote.reasoning:
                lines.append(f"  Reasoning: {vote.reasoning}")
        
        # Total scores
        lines.append("\nTOTAL SCORES:")
        lines.append("-" * 30)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for participant, score in sorted_scores:
            percentage = (score / self.max_possible_points) * 100
            lines.append(f"{participant}: {score} points ({percentage:.1f}% of max)")
        
        # Consensus status
        consensus, winner = self.check_consensus(scores)
        lines.append(f"\nConsensus threshold: {self.config.point_threshold * 100:.0f}% of max points")
        if consensus:
            lines.append(f"✓ CONSENSUS REACHED! Winner: {winner}")
        else:
            lines.append("✗ No consensus yet")
        
        return "\n".join(lines)