import re
import math
from collections import Counter

# Regex-based rules for detecting hardcoded secrets in code lines.
REGEX_PATTERNS = [
    (
        re.compile(
            r"""(?i)\b(password|pwd|pass|user_password)\b\s*=\s*["'][^"']{4,}["']"""
        ),
        "password assignment",
        "hardcoded_password",
    ),
    (
        re.compile(
            r"""(?i)\b(token|api_token|auth_token)\b\s*=\s*["'][A-Za-z0-9_\-=/+]{4,}["']"""
        ),
        "token assignment",
        "hardcoded_token",
    ),
    (
        re.compile(
            r"""(?i)\b(secret|secret_key|private_key)\b\s*=\s*["'][^"']{4,}["']"""
        ),
        "secret assignment",
        "hardcoded_secret",
    ),
]

def shannon_entropy(s: str) -> float:
    """
    Calculate Shannon entropy for a given string.
    Used to estimate how random a potential secret looks.
    """
    if not s:
        return 0.0

    counts = Counter(s)
    length = len(s)
    entropy = 0.0
    for count in counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy

def entropy_to_confidence(entropy: float) -> str:
    """
    Map entropy value to a simple confidence level: low / medium / high.
    """
    if entropy < 3.0:
        return "low"
    elif entropy < 4.0:
        return "medium"
    else:
        return "high"

def scan_text_for_passwords(
        text: str,
        file_path: str,
        commit_hash: str | None = None
) -> list[dict]:
    """
    Scan plain text (e.g. commit message) for potential secrets
    using the same regex + entropy rules as for diffs.

    `file_path` is used as an identifier in findings (e.g. "COMMIT_MESSAGE").
    """
    findings: list[dict] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        code_line = line.rstrip("\n")
        for regex, pattern_name, finding_type in REGEX_PATTERNS:
            if regex.search(code_line):
                entropy = shannon_entropy(code_line)
                confidence = entropy_to_confidence(entropy)

                finding = {
                    "commit_hash": commit_hash or "unknown",
                    "file_path": file_path,
                    "line": line_number,
                    "snippet": code_line,
                    "type": finding_type,
                    "confidence": confidence,
                    "rationale": (
                        f"Commit message line matches regex '{pattern_name}' "
                        f"(entropy: {entropy:.2f})"
                    ),
                }
                findings.append(finding)
                break
    return findings

def scan_file_for_passwords(file_path: str) -> list[dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return scan_text_for_passwords(text, file_path)

def scan_diff_for_passwords(diff_text: str, diff_source: str) -> list[dict]:
    """
    Scan a git diff text for potential hardcoded secrets using regex + entropy.
    Returns a list of finding dicts.
    """
    current_file = None
    findings: list[dict] = []
    for line_number, line in enumerate(diff_text.splitlines(), start=1):
        if line.startswith("+++ "):
            parts = line.split()
            if len(parts) >= 2:
                path = parts[1]
                if path.startswith("b/"):
                    path = path[2:]
                current_file = path
        stripped = line.strip()
        if stripped.startswith("+") and not stripped.startswith("+++"):
            code_line = stripped[1:]
            for regex, pattern_name, finding_type in REGEX_PATTERNS:
                if regex.search(code_line):
                    entropy = shannon_entropy(code_line)
                    confidence = entropy_to_confidence(entropy)

                    finding = {
                        "commit_hash": diff_source,
                        "file_path": current_file or "unknown",
                        "line": line_number,
                        "snippet": code_line,
                        "type": finding_type,
                        "confidence": confidence,
                        "rationale": (
                            f"Added line in diff matches regex '{pattern_name}' "
                            f"entropy= {entropy:.2f})"
                        )
                    }
                    findings.append(finding)
                    break
    return findings