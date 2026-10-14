import json
from pathlib import Path
from scripts.audit import AuditReport
from scripts.bootstrap_benchmark import bootstrap

def test_bootstrap_writes_jsonl_with_sentinel(tmp_skill_tree: Path):
    report = AuditReport("routing", 0.85, ["test"], "improve")
    out = bootstrap(tmp_skill_tree, report, n_tasks=3)
    assert out.exists()
    lines = out.read_text(encoding="utf-8").splitlines()
    # Last line is sentinel comment, not JSON
    assert lines[-1].startswith("# BOOTSTRAP_PENDING_REVIEW")
    payload = [json.loads(l) for l in lines[:-1]]
    assert len(payload) == 3
    for row in payload:
        assert {"task_id", "task", "judge"} <= row.keys()
        assert row["judge"]["kind"] == "rule"

def test_bootstrap_respects_n_tasks(tmp_skill_tree: Path):
    report = AuditReport("prompt", 0.8, [], "improve")
    out = bootstrap(tmp_skill_tree, report, n_tasks=5)
    payload = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    assert len(payload) == 5

def test_bootstrap_adapts_tasks_to_root_cause(tmp_skill_tree: Path):
    r = AuditReport("routing", 0.85, [], "improve")
    out = bootstrap(tmp_skill_tree, r, n_tasks=3)
    payload = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    # Routing root cause → at least one task about description / triggers
    assert any("description" in row["task"].lower() or "trigger" in row["task"].lower() for row in payload)
