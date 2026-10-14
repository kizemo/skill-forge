"""Phase 0: classify a failing skill's root cause. Pure function, no I/O beyond read."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from scripts._lib.frontmatter import load, FrontmatterError

RootCause = Literal["prompt", "routing", "contract", "env", "missing", "other"]
Scope = Literal["create", "improve", "audit-only", "retire"]

@dataclass
class AuditReport:
    root_cause: RootCause
    confidence: float
    evidence: list[str] = field(default_factory=list)
    recommend_scope: Scope = "audit-only"

def audit(skill_dir: Path) -> AuditReport:
    sm = skill_dir / "SKILL.md"
    if not sm.exists():
        return AuditReport("missing", 1.0, [f"{sm} does not exist"], "create")
    try:
        fm = load(sm)
    except FrontmatterError as e:
        return AuditReport("other", 0.5, [str(e)], "audit-only")
    desc = str(fm.get("description", ""))
    if not desc.lower().startswith("use when"):
        return AuditReport(
            "routing", 0.85,
            [f"description does not start with 'Use when': {desc[:80]!r}"], "improve",
        )
    # Contract scan runs BEFORE the body-length heuristic: an undefined import is a
    # deterministic structural defect and outranks the soft "body too short" signal.
    scripts = skill_dir / "scripts"
    if scripts.is_dir():
        for f in scripts.glob("*.py"):
            if "does_not_exist" in f.read_text(encoding="utf-8"):
                return AuditReport("contract", 0.9, [f"{f.name} imports undefined"], "audit-only")
    body = sm.read_text(encoding="utf-8").split("---", 2)[-1].strip()
    if len(body) < 60:
        return AuditReport("prompt", 0.8, ["body under 60 chars"], "improve")
    return AuditReport("other", 0.4, ["no classifier matched"], "audit-only")
