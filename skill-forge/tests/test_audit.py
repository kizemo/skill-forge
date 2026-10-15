# Fixture precondition (RULING-6 corollary, 2026-10-15): any audit() fixture
# that targets the contract or prompt branch MUST start `description` with
# `Use when ...`. The routing branch fires first when description does not
# start with `Use when`, so the later branches are unreachable from such
# fixtures. See progress.md § Rulings (v2) → RULING-6 corollary.
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


def test_audit_prompt_branch_uses_correct_body_when_yaml_value_contains_dashes(tmp_path):
    """Regression for T3 M-5 / v2-T1: a SKILL.md whose frontmatter has a
    block-scalar value containing '---' (or any '---'-like line) must NOT
    let the audit() body-length check see the frontmatter content as body.

    Before the fix: the OLD parser `text.split("---", 2)[-1]` splits on the
    FIRST '---' anywhere — the one embedded mid-line inside the block-scalar
    value. The leaked tail ('...more continuation lines\n---\n# Demo') is over
    60 chars, so the body-length heuristic sees a "long enough" body and the
    'prompt' branch does NOT fire (root_cause falls through to 'other').

    After the fix: body_of() uses the load() fence rule, so the real body is
    '# Demo' (6 chars) and the 'prompt' branch fires correctly.

    Fixture note (deviation from the v2-T1 brief): the brief's literal fixture
    used a description that does not start with 'use when', which under the
    binding RULING-6 branch order (`... -> routing -> contract -> prompt -> ...`)
    returns 'routing' before the body-length branch is ever reached — so it
    could not distinguish the fixed parser from the broken one. The description
    here starts with 'Use when' (so the routing branch is skipped) and the
    post-`---` leak is deliberately longer than 60 chars (so the broken parser
    produces 'other', not a false-positive 'prompt')."""
    sm = tmp_path / "fake-skill" / "SKILL.md"
    sm.parent.mkdir()
    sm.write_text(
        # The first '---' ALONE ON ITS OWN LINE after the opener is the closer.
        # The '---' embedded mid-line in the block-scalar value is NOT a fence
        # (RULING-3), so the real body is '# Demo' (6 chars) -> prompt.
        "---\n"
        "name: x\n"
        "description: >-\n"
        "  Use when auditing a skill whose frontmatter block scalar contains a\n"
        "  line with three-dashes --- and several more continuation lines so the\n"
        "  leak stays above the sixty character body length threshold\n"
        "---\n"
        "# Demo\n",
        encoding="utf-8",
    )
    fake = tmp_path / "fake-skill"
    report = audit(fake)
    assert report.root_cause == "prompt"

def test_audit_root_cause_literal_does_not_include_env():
    """RULING-10 (v2-T6, Option A): the dead 'env' RootCause member is
    dropped. The Literal in scripts.audit should no longer contain 'env'."""
    from typing import get_args
    from scripts.audit import RootCause
    args = get_args(RootCause)
    assert "env" not in args, (
        f"RootCause Literal must not contain 'env' (RULING-10, Option A); got {args!r}"
    )
    # And the 5 expected members are present.
    assert set(args) == {"prompt", "routing", "contract", "missing", "other"}
