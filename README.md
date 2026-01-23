# Git Secret Scanner

Small CLI tool that scans the last N Git commits for potential hardcoded secrets (passwords, tokens, secrets) using regex + entropy and an LLm for secondary review.

## Features

- Scans last **N commits** (diffs + commit messages)
- Detects potential secrets using:
    - regex-based rules
    - Shannon entropy to estimate randomness
- Optionally sends low/medium confidence findings to an LLM for re-classification
- Works with:
    - local Git repositories
    - remote Git URLs (via `git clone` into a temporary directory)
- Produces a JSON report with all findings

## Requirements

- Python 3.10+  
- `git` installed and available in your `$PATH`
- OpenAI API key (for real LLM classification)

## Installation

Clone the repository and install Python dependencies (if any):

```bash
git clone https://github.com/kandera37/git-secret-scanner.git
cd git-secret-scanner

# (optional) create venv
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate

# install dependencies
pip install -r requirements.txt
```

## Configuration

The tool uses OpenAI API for LLM-powered classification.

Create a `.env` file in the project root (you can copy from .env.example):

```bash
cp .env.example .env
```

```dotenv
OPENAI_API_KEY=put_key_here
OPENAI_MODEL=gpt-4o-mini
```

## Usage

Scan last 3 commits of a local repo:

```bash
python3 main.py \
  --repo /path/to/repo \
  --n 3 \
  --out report.json
```

Scan a remote git URL:

```bash
python3 main.py \
  --repo https://github.com/user/repo.git \
  --n 5 \
  --out report.json
```

Control which findings go to LLM:

```bash
python main.py \
  --repo . \
  --n 10 \
  --min-confidence low \
  --out report.json
```

Where:

- `--min-confidence` — minimal confidence level **to skip** LLM review.
    - Findings with `confidence` <= `min-confidence` are sent to the LLM.
    - Valid values: low, medium, high.
- `--llm-model` — OpenAI model name (default: gpt-4o-mini).

## Output format

The tool writes a JSON report like:

```json
{
  "repository": "https://github.com/user/repo.git",
  "scanned_commits": 3,
  "findings": [
    {
      "commit_hash": "da17cc5...",
      "file_path": "src/app.py",
      "line": 42,
      "snippet": "password = \"123456\"",
      "type": "hardcoded_password",
      "confidence": "medium",
      "rationale": "Added line in diff matches regex 'password assignment' (entropy= 3.93)",
      "llm_is_secret": true,
      "llm_type": "hardcoded_password",
      "llm_confidence": "high",
      "llm_comment": "Looks like a real hardcoded password."
    }
  ]
}
```

Fields:
- `type / confidence / rationale` — raw detector output (regex + entropy).
- `llm_*` — additional classification from the LLM (if enabled).

Project structure:
- `main.py` — CLI entry point, argument parsing, report writing
- `git_utils.py` — Git interaction (log, show, clone, commit messages)
- `scanner.py` — regex + entropy-based detectors for diffs and text
- `llm_utils.py` — candidate selection, LLM payload building, OpenAI call, merging results
- `.env.example` — example of environment configuration
- `requirements.txt` — Python dependencies