# Git Secret Scanner

This is a small CLI tool that scans the last **N** Git commits for hardcoded secrets (passwords, tokens, secret keys).  
It analyzes Git diffs and commit messages using simple regex rules and entropy-based heuristics and writes the results to a JSON report.

## Requirements

- Python 3.10+  
- `git` installed and available in your `$PATH`

## Installation

Clone the repository and install Python dependencies (if any):

```bash
git clone <YOUR_REPO_URL>
cd <YOUR_REPO_DIR>
# pip install -r requirements.txt  # optional, if you add dependencies later
```

## Usage

Run the tool from the command line:

```bash
python3 main.py --repo <path_to_repo> --n <number_of_commits> --out <report_path>
```

Example:

```bash
python3 main.py --repo git_test_scanner --n 3 --out report.json
```

Arguments:

- `--repo` – path to the local Git repository to scan  
- `--n` – how many last commits to scan (must be > 0)  
- `--out` – path to the JSON report file (default: `report.json`)

## Output format

The tool writes a single JSON file with the following structure:

```json
{
  "repository": "git_test_scanner",
  "scanned_commits": 3,
  "findings": [
    {
      "commit_hash": "da17cc5efef46b8302802f81d7e5c185fe417516",
      "file_path": "testik.txt",
      "line": 18,
      "snippet": "password = \"123456\"",
      "type": "hardcoded_password",
      "confidence": "medium",
      "rationale": "Added line in diff matches regex 'password assignment' (entropy= 3.93)"
    }
  ]
}
```

Each finding contains:

- `commit_hash` – Git commit hash where the secret was found  
- `file_path` – file path or `"COMMIT_MESSAGE"` for commit messages  
- `line` – line number in the diff or text  
- `snippet` – the exact line with a potential secret  
- `type` – type of secret (for example, `hardcoded_password`, `hardcoded_token`)  
- `confidence` – `low`, `medium` or `high` based on entropy  
- `rationale` – short explanation of why this line was flagged

## Future work (LLM integration)

Right now the tool only uses regex and entropy-based heuristics.  
Next steps:

- send suspicious lines to an LLM for deeper analysis  
- reduce false positives  
- classify findings by severity