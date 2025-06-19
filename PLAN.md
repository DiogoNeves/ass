Implementation Plan: Voting System & Local Model Support

    Overview

    Implement a preferential voting system where personalities debate until reaching consensus, with the first round
     for initial opinions and subsequent rounds for argumentation. Also add support for local model servers.

    Phase 1: Core Architecture Changes

    1.1 Create Voting System Module (voting.py)

    - VotingConfig dataclass:
      - point_threshold: Consensus threshold (e.g., 75% of max possible points)
      - scoring_system: Dict mapping ranks to points (e.g., {1: 4, 2: 3, 3: 2, 4: 1})
      - min_iterations: Minimum rounds before voting can start (default: 2)
      - max_iterations: Safety limit (default: 10)
    - Vote dataclass:
      - voter: Personality name
      - rankings: Ordered list of all participants
      - reasoning: Brief explanation for rankings
      - iteration: Which iteration this vote is from
    - VotingSystem class:
      - calculate_scores(): Convert rankings to points
      - check_consensus(): Determine if threshold is met
      - get_vote_summary(): Format voting results
      - track_vote_history(): Monitor voting trends

    1.2 Update Personality System (personality.py)

    - Modify generate_response() to accept iteration number:
      - Iteration 0: Initial opinion (no argumentation)
      - Iteration 1+: Must engage with and respond to other arguments
    - Add generate_vote() method:
      - Analyze all arguments from current iteration
      - Rank participants based on argument quality
      - Return structured rankings with reasoning
    - Update prompts to emphasize:
      - Direct engagement with other personalities' points
      - Ability to change mind when presented with compelling arguments
      - Constructive debate rather than just restating positions

    Phase 2: Debate Flow Modifications

    2.1 Redesign DebateApp Flow (debate_app.py)

    # Pseudo-code for new flow
    iteration = 0
    debate_history = []
    consensus_reached = False

    while iteration < max_iterations and not consensus_reached:
        # Round of arguments
        round_arguments = {}

        # Iteration 0: Initial opinions (no context)
        # Iteration 1+: Full debate context provided
        for personality in personalities:
            if iteration == 0:
                response = personality.generate_response(question, context="")
            else:
                # Provide full context of current iteration
                context = format_current_round(round_arguments)
                response = personality.generate_response(question, context)

            round_arguments[personality.name] = response
            # Display response immediately so others can see it

        debate_history.append(round_arguments)

        # Voting phase (skip on first iteration)
        if iteration > 0:
            votes = collect_votes(personalities, debate_history)
            scores = voting_system.calculate_scores(votes)
            consensus_reached = voting_system.check_consensus(scores)
            display_voting_results(scores, votes)

        iteration += 1

    # Judge reviews everything
    judge_decision = judge.review_debate(debate_history, final_scores, votes)

    2.2 Context Management

    - Iteration 0: Each personality gives initial position
    - Iteration 1+: Each personality sees:
      - All previous iterations' arguments
      - Current iteration's arguments (as they're made)
      - Must directly address at least 2 other personalities' points
    - Format context to highlight:
      - Who said what
      - Key points of disagreement
      - Areas of emerging consensus

    Phase 3: Enhanced Argumentation

    3.1 Update Personality Prompts

    Add iteration-specific instructions:
    Iteration 0: "Present your initial position on the question."
    Iteration 1+: "Review the arguments made by others. Directly address their points,
                  either agreeing and building upon them or disagreeing with specific reasoning.
                  You must engage with at least 2 other personalities' arguments."

    3.2 Argument Tracking

    - Track which arguments each personality has addressed
    - Ensure diversity in engagement (not always arguing with same personality)
    - Monitor for repetition and encourage new angles

    Phase 4: Local Model Support

    4.1 Create LocalModelPersonality class

    class LocalModelPersonality(LLMPersonality):
        def __init__(self, config: PersonalityConfig):
            super().__init__(config)
            self.base_url = config.model_url
            self.endpoint = config.model_endpoint or "/v1/chat/completions"
            self.headers = self._build_headers(config)
            self._test_connection()

        def generate_response(self, question: str, context: str = "", iteration: int = 0) -> str:
            # Implementation for HTTP requests to local model
            # Support OpenAI-compatible format

    4.2 Configuration Support

    - Environment variables:
      - LOCAL_MODEL_URL: Base URL
      - LOCAL_MODEL_AUTH: Optional auth token
      - LOCAL_MODEL_TIMEOUT: Request timeout
    - PersonalityConfig additions:
      - model_url: For local models
      - model_endpoint: Specific API endpoint
      - request_timeout: Timeout in seconds

    Phase 5: Judge System Enhancement

    5.1 Comprehensive Judge Review

    Judge receives:
    - Complete debate history (all iterations)
    - Voting results from each iteration
    - Final consensus scores
    - Personality engagement metrics

    Judge evaluates:
    - Quality of arguments
    - How well personalities engaged with each other
    - Whether consensus was reached genuinely or through fatigue
    - Any personalities that dominated or were ignored

    5.2 Override Mechanism

    - Judge can override only with detailed reasoning
    - Must identify specific flaws in consensus
    - Override triggers logged with full context
    - Optional: Trigger one more debate round after override

    Phase 6: Configuration & CLI

    6.1 Config Module (config.py)

    @dataclass
    class DebateConfig:
        # Voting configuration
        voting_enabled: bool = True
        consensus_threshold: float = 0.75
        min_iterations: int = 2
        max_iterations: int = 10

        # Scoring system
        scoring_system: Dict[int, int] = None  # Default: {1: 4, 2: 3, 3: 2, 4: 1}

        # Judge configuration
        judge_can_override: bool = True
        override_threshold: float = 0.9  # Judge needs strong conviction

        # Model configuration
        allow_local_models: bool = False
        local_model_timeout: int = 30

    6.2 CLI Updates

    # New flags
    --voting-threshold FLOAT     # Set consensus threshold
    --min-iterations INT         # Minimum debate rounds
    --max-iterations INT         # Maximum debate rounds
    --local-model-url URL        # Use local model server
    --classic-mode              # Use original 3-round format
    --config FILE               # Load config from JSON/YAML

    Implementation Order

    1. Update personality.py - Add iteration awareness and voting
    2. Create voting.py - Core voting logic
    3. Refactor debate_app.py - New iteration-based flow
    4. Add local model support - LocalModelPersonality class
    5. Enhance judge system - Comprehensive review capabilities
    6. Create config.py - Centralized configuration
    7. Update CLI - New command-line options
    8. Update demos - Show new features in action

    Key Design Decisions

    - First iteration is special: No argumentation, just initial positions
    - Real-time visibility: Personalities see arguments as they're made within each iteration
    - Mandatory engagement: Must address others' points in iterations 1+
    - Flexible consensus: Configurable thresholds and scoring
    - Backward compatibility: --classic-mode preserves original behavior
    - Local model support: OpenAI-compatible API format for maximum compatibility

    This ensures genuine debate and argumentation rather than parallel monologues.