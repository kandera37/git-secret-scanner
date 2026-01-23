import os
import subprocess
import tempfile

from scanner import scan_diff_for_passwords, scan_text_for_passwords

def get_last_commit_hash(repo_path: str) -> str:
    """
    Return the hash of the last commit in the given git repository.
    """
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%H"],
        capture_output=True,
        text=True,
        cwd=repo_path,
        check=True,
    )
    commit_hash = result.stdout.strip()
    return commit_hash

def get_last_n_commit_hashes(repo_path: str, n: int) -> list[str]:
    """
    Return a list of hashes for the last n commits from the given repo.
    """

    if n <= 0:
        return []
    result = subprocess.run(
        ["git", "log", "-n", str(n), "--pretty=format:%H"],
        capture_output=True,
        text=True,
        cwd=repo_path,
        check=True,
    )
    commits= result.stdout.strip().splitlines()
    return commits

def get_commit_diff(repo_path: str, commit_hash: str) -> str:
    """
    Return diff text for a specific commit hash in the given repo.
    """
    result= subprocess.run(
        ["git", "show", "--format=", "--patch", commit_hash],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    diff_text = result.stdout
    return diff_text

def get_last_commit_diff(repo_path: str) -> tuple[str, str]:
    """
    Returns (commit_hash, diff_text) for the last commit in the given repo.
    """
    commit_hash = get_last_commit_hash(repo_path)
    diff_text = get_commit_diff(repo_path, commit_hash)
    return commit_hash, diff_text

def analyze_last_commit(repo_path: str) -> list[dict]:
    """
    Analyze the last commit in the given repo and returns findings.
    """
    commit_hash, diff_text = get_last_commit_diff(repo_path)
    findings = scan_diff_for_passwords(diff_text, diff_source=commit_hash)
    return findings

def analyze_last_n_commits(repo_path: str, n: int) -> list[dict]:
    """
    Analyze the last N commits and return findings from:
    - git diff (patch)
    - commit message
    """
    ensure_valid_repo(repo_path)

    if n <= 0:
        return []

    hashes = get_last_n_commit_hashes(repo_path, n)
    all_findings:  list[dict] = []

    for commit_hash in hashes:
        # 1) Diff scan
        diff_text = get_commit_diff(repo_path, commit_hash)
        diff_findings = scan_diff_for_passwords(diff_text, diff_source=commit_hash)
        all_findings.extend(diff_findings)

        # 2) Commit message scan
        message_text = get_commit_message(repo_path, commit_hash)
        message_findings = scan_text_for_passwords(
            message_text,
            "COMMIT_MESSAGE",
            commit_hash=commit_hash,
        )
        all_findings.extend(message_findings)
    return all_findings

def ensure_valid_repo(repo_path: str) -> None:
    """
    Validate that repo_path looks like a git repository (directory with a .git folder).
    Raise ValueError with a clear message if not.
    """
    if not os.path.isdir(repo_path):
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_path}")

    git_dir = os.path.join(repo_path, ".git")
    if not os.path.isdir(git_dir):
        raise ValueError(f"Path is not a git repository (no .git folder found): {repo_path}")

def get_commit_message(repo_path: str, commit_hash: str) -> str:
    """
    Return the commit message (subject + body) for a specific commit hash.
    """
    result = subprocess.run(
        ["git", "show", "-s", "--format=%B", commit_hash],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

def is_repo_url(repo: str) -> bool:
    return repo.startswith(("http://", "https://", "git@")) or repo.endswith(".git")

def prepare_repo(repo: str) -> tuple[str, tempfile.TemporaryDirectory | None]:
    if os.path.isdir(repo):
        return repo, None
    if is_repo_url(repo):
        tmp = tempfile.TemporaryDirectory()
        local_path = tmp.name
        try:
            subprocess.run(
                ["git", "clone", repo,  local_path],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"failed to clone repo: {repo}\n{e.stderr}") from e
        return local_path, tmp
    raise ValueError(f"'{repo}' is neither an existing directory nor a supported URL")