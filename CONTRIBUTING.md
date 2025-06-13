# Contributing to ASS

Thank you for your interest in contributing to ASS (Argumentative System Service)! We welcome all kinds of contributions.

## 🚀 Quick Start

1. **Fork the repository**
2. **Clone your fork:**
   ```bash
   git clone https://github.com/yourusername/ass.git
   cd ass
   ```
3. **Set up development environment:**
   ```bash
   uv sync
   cp .env.example .env
   # Add your API keys to .env
   ```

## 🎭 Types of Contributions

### 🤖 New Personalities
Add personalities with unique traits and perspectives:
- Scientists, artists, philosophers, comedians
- Different cultural perspectives
- Specialized domain experts

### 🎪 Enhanced Debate Formats
- Tournament brackets
- Team debates (2v2)
- Audience voting
- Time-limited rapid-fire rounds

### 🔌 Additional LLM Providers
- Gemini
- Claude-3 Opus
- Open-source models (Llama, Mistral)

### 🎨 UI/UX Improvements
- Better visualizations
- Export debate transcripts
- Save/replay debates
- Web interface

## 🛠️ Development Guidelines

### Code Style
- Follow PEP 8
- Use type hints where possible
- Keep functions focused and small
- Add docstrings to public functions

### Testing
```bash
# Run existing tests
uv run pytest

# Add tests for new personalities
# Add integration tests for new features
```

### Documentation
- Update README.md for new features
- Add docstrings to new functions
- Include example usage

## 🎯 Submitting Changes

1. **Create a branch:** `git checkout -b feature/my-feature`
2. **Make your changes**
3. **Test thoroughly**
4. **Commit with clear message:** `git commit -m "Add economist personality"`
5. **Push:** `git push origin feature/my-feature`
6. **Create Pull Request**

### Pull Request Guidelines
- Clear title describing the change
- Detailed description of what was added/changed
- Screenshots/examples if relevant
- Link any related issues

## 🔒 Security

- **NEVER commit API keys or secrets**
- Use `.env` for sensitive data
- Validate all user inputs
- Follow responsible AI practices

## 🐛 Bug Reports

Use GitHub Issues with:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)

## 💡 Feature Requests

We love new ideas! Please include:
- Clear description of the feature
- Why it would be useful
- Potential implementation approach

## 🎉 Recognition

Contributors will be:
- Added to README acknowledgments
- Credited in release notes
- Invited to join the maintainer team (for significant contributions)

## 📝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers get started
- Keep discussions on-topic

## ❓ Questions?

- Open a GitHub Issue
- Start a Discussion
- Reach out to maintainers

Thank you for helping make ASS better! 🎭