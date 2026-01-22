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
git clone <YOUR_REPO_URL>
cd <YOUR_REPO_DIR>
# pip install -r requirements.txt  # optional, if you add dependencies later
```

## Configuration

The tool reads OpenAI settings from environment variables.
You can use .env file (not commited to Git) based on .env.example:

```dotenv
OPENAI_API_KEY=put_key_here
OPENAI_MODEL=gpt-4o-mini
```

By default, the code uses `gpt-4o-mini`, but you can override it via CLI.

## Usage

Basic usage with a local repository:

```bash
python3 main.py \
  --repo /path/to/local/repo \
  --n 5 \
  --out report.json
```

Usage with a remote Git URL:

```bash
--repo /path/to/local/repo \
  --n 5 \
  --min-confidence medium \
  --llm-model gpt-4o-mini \
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