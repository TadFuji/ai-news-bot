# Contributing to AI News Bot

Thank you for your interest in contributing! This project welcomes bug reports, feature suggestions, and pull requests from the community.

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A [Google AI Studio API Key](https://aistudio.google.com/apikey)

### Development Setup

```bash
# Fork and clone
git clone https://github.com/<your-username>/ai-news-bot.git
cd ai-news-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY
```

### Running Locally

```bash
# Run the full pipeline
python collect_rss_gemini.py    # Stage 1
python curate_morning_brief.py  # Stage 2

# Launch admin dashboard
streamlit run app.py
```

## 📝 How to Contribute

### Reporting Bugs

1. Search [existing issues](https://github.com/TadFuji/ai-news-bot/issues) to avoid duplicates
2. Use the **Bug Report** template if available
3. Include: Python version, OS, error output, steps to reproduce

### Suggesting Features

Open an issue with the **Feature Request** label. Describe the problem, your proposed solution, and any alternatives you've considered.

### Submitting Changes

1. **Fork** this repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with clear, descriptive commits
4. Ensure your code follows the project's style (see below)
5. Push to your fork: `git push origin feature/amazing-feature`
6. Open a **Pull Request** against `main`

## 🎨 Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code
- Use descriptive variable names in English
- Write docstrings for all public functions
- Keep commits atomic and write meaningful commit messages

### Commit Message Convention

```
type: short description

Longer description if needed.
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## 🔍 Areas Where Help is Appreciated

| Area | Description |
|------|-------------|
| 🌐 RSS Sources | New feed URLs, especially non-English/non-Japanese media |
| 🧪 Testing | Unit tests for parsing, curation, and fallback logic |
| 🎨 Frontend | GitHub Pages UI improvements (dark mode, accessibility) |
| 📊 Analytics | Trend analysis dashboard using collected data |
| 🌍 i18n | Support for additional output languages |

## 📄 License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
