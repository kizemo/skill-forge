from pathlib import Path
import pytest
from scripts.audit import audit, AuditReport

def test_audit_missing_skill_md(tmp_skill_tree: Path):
    target = tmp_skill_tree / "ghost-skill"
    target.mkdir()
    report = audit(target)
    assert report.root_cause == "missing"
    assert report.confidence >= 0.95
    assert report.recommend_scope == "create"

def test_audit_detects_routing_when_description_missing_triggers(tmp_skill_tree: Path):
    p = tmp_skill_tree / "SKILL.md"
    p.write_text("---\nname: x\ndescription: A tool that does things.\n---\n# body\n", encoding="utf-8")
    report = audit(tmp_skill_tree)
    assert report.root_cause == "routing"
    assert any("description" in ev.lower() for ev in report.evidence)

def test_audit_classifies_prompt_when_body_empty(tmp_skill_tree: Path):
    p = tmp_skill_tree / "SKILL.md"
    p.write_text(
        "---\nname: x\ndescription: Use when A, B, or C happens with symptoms.\n---\n",
        encoding="utf-8",
    )
    report = audit(tmp_skill_tree)
    assert report.root_cause == "prompt"

def test_audit_classifies_contract_when_scripts_import_undefined(tmp_skill_tree: Path):
    (tmp_skill_tree / "scripts").mkdir()
    (tmp_skill_tree / "scripts" / "broken.py").write_text(
        "from scripts._lib.does_not_exist import x\n", encoding="utf-8"
    )
    report = audit(tmp_skill_tree)
    assert report.root_cause == "contract"
    assert report.recommend_scope in ("improve", "audit-only")
