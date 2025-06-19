# Claude AI Assistant Guide for ASS Project

## Project Overview
ASS (Argumentative System Service) is a Python CLI application that simulates AI debates between four distinct personalities using Claude and OpenAI models. This guide helps Claude understand the project structure and conventions for effective assistance.

## Quick Context
- **Language**: Python 3.9+
- **Package Manager**: UV (modern Python package/project manager)
- **Key Dependencies**: anthropic, openai, rich, python-dotenv
- **Main Branch**: main (currently on: voting)
- **License**: MIT

## Key Files to Know
- `debate_app.py` - Main interactive application entry point
- `personality.py` - Core personality system with LLMPersonality base class
- `demo.py` - Simple demo runner for quick testing
- `pyproject.toml` - Project configuration and dependencies

## Development Commands
Please commit between phases.

```bash
# Install/update dependencies
uv sync

# Run interactive debate
uv run python debate_app.py

# Run demo
uv run python demo.py

# Add new dependency
uv add <package-name>
```

## Code Conventions
1. **Personality System**: Use abstract base class pattern, implement `create_personality()` factory
2. **Configuration**: Use dataclasses (e.g., `PersonalityConfig`) for structured config
3. **UI**: Use Rich library for terminal output (panels, colors, animations)
4. **Error Handling**: Graceful handling of API errors with user-friendly messages
5. **Environment**: API keys in `.env` file (never commit!)

## Architecture Patterns
- **Factory Pattern**: For creating personalities based on configuration
- **Context Accumulation**: Each personality maintains conversation history
- **Provider Agnostic**: Support multiple LLM providers through abstract interfaces
- **Structured Debate**: 3-round format (opening � rebuttals � final positions)

## Common Tasks
### Adding a New Personality Type
1. Create new class inheriting from `LLMPersonality` in `personality.py`
2. Implement required methods: `generate_argument()`, `_format_history()`
3. Update `create_personality()` factory function
4. Add configuration in `PersonalityConfig`

### Modifying Debate Structure
1. Edit debate flow in `debate_app.py`
2. Update round structure in the main debate loop
3. Adjust judge synthesis logic if needed

### Testing Changes
1. Use `demo.py` for quick testing with pre-set questions
2. Run interactive mode to test user input handling
3. Check Rich formatting displays correctly in terminal

## Important Notes
- Always use UV commands (not pip) for dependency management
- Maintain compatibility with both Claude and OpenAI APIs
- Keep personality responses distinct and in-character
- Ensure Rich terminal UI remains clean and readable
- Follow existing code style and patterns

## API Model Identifiers
- Claude: "claude-3-5-sonnet-20241112"
- OpenAI: "gpt-4o-20250117"

## Project Philosophy
This project demonstrates creative AI integration while maintaining clean, extensible code. It's both a functional debate simulator and a showcase of modern Python development practices with AI APIs.