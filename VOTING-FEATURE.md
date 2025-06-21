Extend the existing AI personality debate project to include a preferential voting system with the following requirements:

VOTING MECHANISM:
- Replace fixed iterations with consensus-driven stopping
- At the end of each iteration, each AI personality ranks ALL participants (including themselves) from best to worst based on answer quality
- Use ranked-choice voting where ranks are converted to points (e.g., 1st place = N points, 2nd = N-1 points, etc.)
- Continue iterations until a configurable point threshold is reached indicating consensus

DEBATE DYNAMICS:
- Each iteration concludes when all personalities have answered and argued
- Personalities should actively debate and challenge each other's points unless already in agreement
- Personalities can change their minds only when presented with truly convincing arguments
- Some personalities may agree with each other from the start

CONSENSUS & TERMINATION:
- Stop when the voting reaches a configurable agreement threshold (measured in total points)
- After consensus, a judge reviews the entire debate history, all arguments, and final vote rankings
- Judge can override consensus only in extreme cases and must provide detailed reasoning

CONFIGURATION NEEDS:
- Configurable point threshold for consensus
- Configurable scoring system for ranked votes
- Judge override conditions and logging

UPDATE REQUIREMENTS:
- Modify existing personality prompts to include voting behavior
- Add voting instructions and ranking criteria
- Update the debate flow to include ranking phases
- Implement the judge review system

Please analyze the existing codebase structure and implement these changes while maintaining backward compatibility where possible.