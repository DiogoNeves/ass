"""Debate engine that yields structured events for any frontend (CLI, web, etc.)."""

import os
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from config import DebateConfig
from models.personality import PersonalityConfig
from models.voting import Vote, VotingConfig
from personality import LLMPersonality, create_personality
from services.file_manager import FileManager
from voting import VotingSystem


# Event type constants
EVENT_DEBATE_START = "debate_start"
EVENT_ITERATION_START = "iteration_start"
EVENT_BELIEF_FORMING = "belief_forming"
EVENT_BELIEF_FORMED = "belief_formed"
EVENT_BELIEF_UPDATING = "belief_updating"
EVENT_BELIEF_UPDATED = "belief_updated"
EVENT_THINKING = "thinking"
EVENT_RESPONSE = "response"
EVENT_VOTING_START = "voting_start"
EVENT_VOTING_PERSONALITY = "voting_personality"
EVENT_VOTE_RESULTS = "vote_results"
EVENT_CONSENSUS = "consensus"
EVENT_NEXT_ITERATION = "next_iteration"
EVENT_JUDGE_THINKING = "judge_thinking"
EVENT_JUDGE_DECISION = "judge_decision"
EVENT_DEBATE_END = "debate_end"

STYLE_MAP = {
    "claude_positive": "green",
    "claude_negative": "red",
    "openai_positive": "blue",
    "openai_negative": "yellow",
}

DEBATE_ORDER = [
    "claude_positive",
    "openai_negative",
    "openai_positive",
    "claude_negative",
]


class DebateEngine:
    """Provider-agnostic debate orchestrator that yields events."""

    def __init__(self, config: Optional[DebateConfig] = None):
        self.config = config or DebateConfig.from_env()
        self.personalities = self._create_personalities()
        self.judge = self._create_judge()
        self.voting_system = None
        self.file_manager = FileManager() if self.config.save_enabled else None

        if self.config.voting_enabled:
            voting_config = VotingConfig(
                point_threshold=self.config.consensus_threshold,
                scoring_system=self.config.scoring_system,
                min_iterations=self.config.min_iterations,
                max_iterations=self.config.max_iterations,
            )
            personality_names = [p.config.name for p in self.personalities.values()]
            self.voting_system = VotingSystem(voting_config, personality_names)

    def _create_personalities(self):
        personalities = {}
        local_model_url = os.getenv("LOCAL_MODEL_URL")

        configs = {
            "claude_positive": PersonalityConfig(
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
                voting_traits={"fairness": 8, "self_confidence": 6},
                belief_persistence=8,
                reasoning_depth=8,
                truth_seeking=7,
            ),
            "claude_negative": PersonalityConfig(
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
                voting_traits={"fairness": 9, "self_confidence": 4},
                belief_persistence=9,
                reasoning_depth=9,
                truth_seeking=6,
            ),
            "openai_positive": PersonalityConfig(
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
                voting_traits={"fairness": 7, "self_confidence": 7},
                belief_persistence=7,
                reasoning_depth=8,
                truth_seeking=8,
            ),
            "openai_negative": PersonalityConfig(
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
                voting_traits={"fairness": 8, "self_confidence": 5},
                belief_persistence=8,
                reasoning_depth=9,
                truth_seeking=7,
            ),
        }

        for key, cfg in configs.items():
            personalities[key] = create_personality(cfg)

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
                voting_traits={"fairness": 10, "self_confidence": 8},
                belief_persistence=4,
                reasoning_depth=10,
                truth_seeking=10,
            )
        )

    @staticmethod
    def format_current_round_context(round_arguments: Dict[str, str]) -> str:
        context_parts = []
        for name, argument in round_arguments.items():
            context_parts.append(f"{name}:\n{argument}\n")
        return "\n".join(context_parts)

    @staticmethod
    def format_debate_history(debate_history: List[Dict[str, str]]) -> str:
        history_parts = []
        for i, round_args in enumerate(debate_history):
            history_parts.append(f"ITERATION {i}:")
            for name, argument in round_args.items():
                history_parts.append(f"\n{name}:\n{argument}")
            history_parts.append("\n" + "=" * 50 + "\n")
        return "\n".join(history_parts)

    def run_debate(self, question: str) -> Generator[Dict[str, Any], None, None]:
        """Run a debate, yielding events. Delegates to classic or voting mode."""
        yield {"type": EVENT_DEBATE_START, "question": question,
               "voting_enabled": self.config.voting_enabled,
               "classic_mode": self.config.classic_mode}

        if self.config.classic_mode or not self.config.voting_enabled:
            yield from self._run_classic_debate(question)
        else:
            yield from self._run_voting_debate(question)

        yield {"type": EVENT_DEBATE_END}

    def _run_classic_debate(self, question: str) -> Generator[Dict[str, Any], None, None]:
        debate_context = ""

        for round_num in range(1, 4):
            yield {"type": EVENT_ITERATION_START, "iteration": round_num - 1,
                   "label": f"ROUND {round_num}"}

            for personality_key in DEBATE_ORDER:
                personality = self.personalities[personality_key]

                yield {"type": EVENT_THINKING, "personality": personality.config.name,
                       "personality_key": personality_key}

                response = personality.generate_response(question, debate_context)

                yield {"type": EVENT_RESPONSE, "personality": personality.config.name,
                       "personality_key": personality_key,
                       "style": STYLE_MAP[personality_key],
                       "text": response}

                debate_context += f"\n{personality.config.name}: {response}\n"

        # Judge
        yield from self._judge_classic(question, debate_context)

    def _run_voting_debate(self, question: str) -> Generator[Dict[str, Any], None, None]:
        iteration = 0
        debate_history: List[Dict[str, str]] = []
        consensus_reached = False
        final_votes = None

        # File saving setup
        debate_title = None
        filename = None
        debate_data = None

        if self.config.save_enabled and self.file_manager:
            debate_title = self.file_manager.generate_debate_title(question)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = self.file_manager._sanitize_filename(debate_title)
            filename = f"{timestamp}_{safe_title}.json"
            debate_data = {
                "title": debate_title,
                "question": question,
                "timestamp": timestamp,
                "config": {
                    "consensus_threshold": self.config.consensus_threshold,
                    "max_iterations": self.config.max_iterations,
                    "voting_start_iteration": self.config.voting_start_iteration,
                },
                "iterations": [],
                "final_consensus": None,
                "final_judge_decision": None,
            }

        while iteration < self.config.max_iterations and not consensus_reached:
            yield {"type": EVENT_ITERATION_START, "iteration": iteration,
                   "label": f"ITERATION {iteration}",
                   "max_iterations": self.config.max_iterations}

            round_arguments: Dict[str, str] = {}
            votes = None

            for personality_key in DEBATE_ORDER:
                personality = self.personalities[personality_key]

                # Internal beliefs on first iteration
                if iteration == 0:
                    yield {"type": EVENT_BELIEF_FORMING,
                           "personality": personality.config.name,
                           "personality_key": personality_key}
                    beliefs = personality.generate_internal_belief(question)
                    yield {"type": EVENT_BELIEF_FORMED,
                           "personality": personality.config.name,
                           "personality_key": personality_key,
                           "beliefs": beliefs}

                # Build context
                if iteration == 0:
                    context = ""
                else:
                    prev_context = self.format_debate_history(debate_history)
                    curr_context = self.format_current_round_context(round_arguments)
                    context = prev_context + ("\nCURRENT ITERATION:\n" + curr_context if curr_context else "")

                    # Update beliefs
                    if personality.internal_beliefs:
                        yield {"type": EVENT_BELIEF_UPDATING,
                               "personality": personality.config.name,
                               "personality_key": personality_key}
                        belief_changed = personality.update_beliefs(context, iteration)
                        yield {"type": EVENT_BELIEF_UPDATED,
                               "personality": personality.config.name,
                               "personality_key": personality_key,
                               "changed": belief_changed}

                # Generate response
                yield {"type": EVENT_THINKING, "personality": personality.config.name,
                       "personality_key": personality_key,
                       "action": "presenting initial position" if iteration == 0 else "arguing"}

                response = personality.generate_response(question, context, iteration)
                round_arguments[personality.config.name] = response

                yield {"type": EVENT_RESPONSE, "personality": personality.config.name,
                       "personality_key": personality_key,
                       "style": STYLE_MAP[personality_key],
                       "text": response, "iteration": iteration}

            debate_history.append(round_arguments)

            # Voting phase
            if iteration >= self.config.voting_start_iteration:
                yield {"type": EVENT_VOTING_START, "iteration": iteration}

                participant_names = [p.config.name for p in self.personalities.values()]
                debate_context = self.format_debate_history(debate_history)
                votes = []

                for personality_key, personality in self.personalities.items():
                    yield {"type": EVENT_VOTING_PERSONALITY,
                           "personality": personality.config.name,
                           "personality_key": personality_key}

                    vote_data = personality.generate_vote(participant_names, debate_context)
                    vote = Vote(
                        voter=personality.config.name,
                        rankings=vote_data.get("rankings", participant_names),
                        reasoning=vote_data.get("reasoning", ""),
                        iteration=iteration,
                    )
                    votes.append(vote)

                self.voting_system.add_votes(votes)
                scores = self.voting_system.calculate_scores(votes)
                consensus_reached, winner = self.voting_system.check_consensus(scores)

                voting_round = len(self.voting_system.vote_history) - 1
                summary = self.voting_system.get_vote_summary(voting_round)

                yield {"type": EVENT_VOTE_RESULTS, "iteration": iteration,
                       "votes": votes, "scores": scores, "summary": summary,
                       "consensus_reached": consensus_reached, "winner": winner,
                       "max_possible_points": self.voting_system.max_possible_points,
                       "threshold": self.config.consensus_threshold}

                if consensus_reached:
                    final_votes = votes
                    yield {"type": EVENT_CONSENSUS, "winner": winner, "iteration": iteration}

            # Save iteration data
            if self.config.save_enabled and debate_data and self.file_manager:
                iteration_data = {
                    "iteration": iteration,
                    "arguments": round_arguments,
                    "votes": None,
                    "consensus_reached": consensus_reached,
                }
                if iteration >= self.config.voting_start_iteration and votes:
                    iteration_data["votes"] = [
                        {"voter": v.voter, "rankings": v.rankings, "reasoning": v.reasoning}
                        for v in votes
                    ]
                    if self.voting_system and len(self.voting_system.vote_history) > 0:
                        vr = len(self.voting_system.vote_history) - 1
                        iteration_data["voting_summary"] = self.voting_system.get_vote_summary(vr)
                debate_data["iterations"].append(iteration_data)
                debate_data["final_consensus"] = consensus_reached
                self.file_manager.save_debate(debate_data, custom_filename=filename.replace(".json", ""))

            iteration += 1

            if not consensus_reached and iteration < self.config.max_iterations:
                yield {"type": EVENT_NEXT_ITERATION,
                       "next_iteration": iteration,
                       "max_iterations": self.config.max_iterations}

        # Judge decision
        yield from self._judge_with_voting(question, debate_history, final_votes)

        # Save final state
        if self.config.save_enabled and debate_data and self.file_manager:
            debate_data["final_judge_decision"] = self._last_judge_decision
            self.file_manager.save_debate(debate_data, custom_filename=filename.replace(".json", ""))

    def _judge_classic(self, question: str, debate_context: str) -> Generator[Dict[str, Any], None, None]:
        yield {"type": EVENT_JUDGE_THINKING}
        final_decision = self.judge.generate_response(
            question,
            f"Here are the arguments from the debate:\n{debate_context}\n\nPlease provide your final judgment.",
        )
        self._last_judge_decision = final_decision
        yield {"type": EVENT_JUDGE_DECISION, "text": final_decision}

    def _judge_with_voting(
        self,
        question: str,
        debate_history: List[Dict[str, str]],
        final_votes: Optional[List[Vote]],
    ) -> Generator[Dict[str, Any], None, None]:
        yield {"type": EVENT_JUDGE_THINKING}

        debate_context = self.format_debate_history(debate_history)
        voting_summary = ""
        if final_votes and self.voting_system and len(self.voting_system.vote_history) > 0:
            summary = self.voting_system.get_vote_summary(len(self.voting_system.vote_history) - 1)
            if summary and "sorted_rankings" in summary:
                voting_summary = "\n\nFINAL VOTING RESULTS:\n"
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

        final_decision = self.judge.generate_response(question, judge_prompt)
        self._last_judge_decision = final_decision
        yield {"type": EVENT_JUDGE_DECISION, "text": final_decision}
