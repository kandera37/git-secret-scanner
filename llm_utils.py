from typing import Literal

from pydantic import BaseModel, Field
from openai import OpenAI
import json

import os

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

class LLMDecision(BaseModel):
    id: str
    is_secret: bool
    llm_type: str = Field(description='e.g. "hardcoded_password", "hardcoded_token", "hardcoded_secret", "not_a_secret"')
    llm_confidence: Literal["low", "medium", "high"]
    llm_comment: str

class LLMDecisions(BaseModel):
    results: list[LLMDecision]

def select_llm_candidates(
        findings: list[dict],
        min_confidence: str = "medium"
) -> list[dict]:
    """
    Choose which findings should be sent to the LLM based on confidence.

    We map confidence levels to numbers:
        low -> 0
        medium -> 1
        high -> 2

    All findings with confidence level <= min_confidence will be sent to the LLM.
    """
    llm_candidates: list[dict] = []

    order = {"low": 0, "medium": 1, "high": 2}

    min_level = order.get(min_confidence, order["medium"])

    for finding in findings:
        raw_conf = finding.get("confidence", "medium")
        conf = str(raw_conf).lower()
        if conf not in order:
            continue
        level = order[conf]
        if level <= min_level:
            llm_candidates.append(finding)
    return llm_candidates

def build_llm_payload(candidates: list[dict]) -> list[dict]:
    """
    Build a compact payload for LLM from selected findings.
    """
    llm_payload: list[dict] = []

    for index, finding in enumerate(candidates, start=1):
        ids = f"f{index}"
        finding["id"] = ids
        commit_hash = finding.get('commit_hash')
        file_path = finding.get('file_path')
        line = finding.get('line')
        snippet = finding.get('snippet')
        confidence = finding.get('confidence')

        llm_finding ={
            "id": ids,
            "commit_hash": commit_hash,
            "file_path": file_path,
            "line": line,
            "snippet": snippet,
            "confidence": confidence,
        }
        llm_payload.append(llm_finding)
    return llm_payload

def merge_llm_results(
        findings: list[dict],
        llm_results: list[dict],
) -> list[dict]:
    """
    Merge LLM results back into the original findings using the 'id' field.

    For each finding that has an 'id', if there is a matching LLM result
    with the same 'id', we attach LLM fields to the finding.
    """
    results_by_id: dict[str, dict] = {}
    for result in llm_results:
        rid = result.get('id')
        if rid is not None:
            results_by_id[rid] = result

    for finding in findings:
        fid = finding.get('id')
        if fid is None:
            continue

        llm_result = results_by_id.get(fid)
        if llm_result is None:
            continue

        finding["llm_is_secret"] = llm_result.get('is_secret')
        finding["llm_type"] = llm_result.get('llm_type')
        finding["llm_confidence"] = llm_result.get('llm_confidence')
        finding["llm_comment"] = llm_result.get('llm_comment')

    return findings

def build_llm_prompt() -> str:
    """
    System instructions for the LLM.
    Output must match the LLMDecisions schema: {"results": [...]}
    """
    return (
        "You are a security assistant.\n"
        "You will receive JSON findings from a Git secret scanner.\n"
        "For each finding, decide if it is a real secret or a false positive.\n"
        "Return ONLY a valid JSON object with this shape:\n"
        "{\n"
        '   "results": [\n'
        "        {\n"
        '           "id": string, \n'
        '           "is_secret": boolean,\n'
        '           "llm_type": one of ["hardcoded_password", "hardcoded_token", "hardcoded_secret", "not_a_secret"]\n'
        '           "llm_confidence": one of ["low","medium","high"],\n'
        '           "llm_comment": string,\n'
        "       }\n"
        "   ]\n"
        "}\n"
        "No extra keys. No extra text."
    )

def call_openai_llm(payload: list[dict], model: str = "gpt-4o-mini") -> list[dict]:
    """
    Send payload to OpenAI and return validated LLM results as list[dict].

    Uses the LLMDecisions Pydantic schema for structured outputs to ensure that
    the response has the expected shape.
    """
    client = OpenAI()
    system = build_llm_prompt()
    payload_json = json.dumps(payload, ensure_ascii=False)

    model_name = model or DEFAULT_MODEL

    response = client.responses.parse(
        model=model_name,
        input=[
            {"role": "system", "content": system},
            {
                "role":  "user",
                "content": (
                    "Classify these findings. \n"
                    f"Findings JSON:\n{payload_json}"
                ),
            },
        ],
        text_format=LLMDecisions,
    )

    parsed: LLMDecisions = response.output_parsed
    return [r.model_dump() for r in parsed.results]

