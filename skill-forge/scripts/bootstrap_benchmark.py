"""Phase 2: synthesize a starter benchmark from audit results. NO LLM call in v1 — template rows."""
from dataclasses import asdict
from pathlib import Path
import json
from scripts.audit import AuditReport

TEMPLATES = {
    "routing": ["When is this skill meant to trigger?", "What does the description promise that the body does not deliver?", "Name two user prompts that should NOT trigger this skill."],
    "prompt":  ["Explain the skill's process in one paragraph.", "What is the strongest rule a reader of this skill must follow?", "If the skill's rules conflict, which wins?"],
    "contract": ["Which scripts does this skill depend on that don't exist yet?", "List the tool surface the skill assumes.", "Where does the skill document its error contract?"],
    "missing": ["What should this skill do, in one sentence?", "Describe 3 user prompts that should trigger it.", "What command runs first?"],
    "other":   ["Summarize what this skill does.", "Why would someone invoke it?", "What's the next thing the skill does after that?"],
}

def bootstrap(skill_dir: Path, report: AuditReport, n_tasks: int = 15) -> Path:
    tasks = TEMPLATES.get(report.root_cause, TEMPLATES["other"])
    rows: list[dict] = []
    # Cycle the bucket's prompts to reach n_tasks: every bucket holds 3 prompts, so a
    # plain slice would cap every benchmark (incl. the n_tasks=15 default) at 3 rows.
    for i, prompt in enumerate((tasks[k % len(tasks)] for k in range(n_tasks)), start=1):
        rows.append({
            "task_id": f"{report.root_cause[:4]}-{i:03d}",
            "task": prompt,
            "judge": {"kind": "rule",
                       "checks": [{"op": "max_chars", "arg": 1500},
                                  {"op": "min_citations", "arg": 1}]},
        })
    out = skill_dir / "skillopt-benchmark.jsonl"
    text = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n# BOOTSTRAP_PENDING_REVIEW\n"
    out.write_text(text, encoding="utf-8")
    return out
