import argparse
import json
import sys
import subprocess

from git_utils import analyze_last_n_commits, prepare_repo
from llm_utils import select_llm_candidates, build_llm_payload, merge_llm_results, call_openai_llm


def main() -> None:
    """
    CLI entry point: parse arguments, run analysis and write JSON report.
    """
    parser = argparse.ArgumentParser(description="Scan last N git commits for potential secrets")
    parser.add_argument(
        "--repo",
        required=True,
        help="Path to the git repository",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=3,
        help="How many last commits to scan",
    )
    parser.add_argument(
        "--out",
        default="report.json",
        help="Path to JSON report file",
    )
    parser.add_argument(
        "--min-confidence",
        choices=["low", "medium", "high"],
        default="medium",
        help="Minimum confidence level to skip LLM review (default: medium)",
    )
    parser.add_argument(
        "--llm-model",
        default="gpt-4o-mini",
        help="OpenAI model to use for LLM analysis (default: gpt-4o-mini)",
    )

    args = parser.parse_args()
    if args.n <= 0:
        parser.error("--n must be greater than 0")

    tmp = None

    try:
        # 1. Resolve repo: local path or cloned URL
        repo_path, tmp = prepare_repo(args.repo)
        # 2. Analyze commits using the resolved repo_path
        findings = analyze_last_n_commits(repo_path, args.n)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(
            f"Error: git command failed: {e}. "
            "Make sure the repo is valid and has commits.",
            file=sys.stderr,
        )
        sys.exit(1)
    finally:
        # 3. Clean up temporary clone if we created one
        if tmp is not None:
            tmp.cleanup()
    llm_candidates = select_llm_candidates(findings, min_confidence=args.min_confidence)
    llm_payload = build_llm_payload(llm_candidates)

    if llm_payload:
        llm_results = call_openai_llm(llm_payload, model=args.llm_model)
        final_findings = merge_llm_results(findings, llm_results)
    else:
        final_findings = findings


    report = {
        "repository": args.repo,
        "scanned_commits": args.n,
        "findings": final_findings,
    }
    if not findings:
        report ={
            "repository": args.repo,
            "scanned_commits": args.n,
            "findings": [],
        }
        with open(args.out, "w", encoding="utf-8") as out_f:
            json.dump(report, out_f, indent=2)
        print(f"Wrote report to {args.out} (no findings, LLM not called)")
        return

if __name__ == "__main__":
    main()