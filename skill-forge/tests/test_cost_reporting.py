"""P0: the cost axis must be VISIBLE.

Two things have to happen for the cost axis to matter:
  1. the validator warns when a skill's tiers are over budget
  2. the audit report shows the measured numbers

Both are warnings/reports, never refusals (user ruling 2026-10-25: the
5,000-token body ceiling is REPORTED; the index tier is a WARNING). That
matches skill-forge's existing contract — "a skill that fails a principle
is suboptimal, not broken".
"""
import pytest
from scripts._lib.frontmatter import validate_skill_frontmatter, validate_skill_body
from scripts._lib.token_cost import measure_skill


def test_validate_warns_on_an_over_budget_index_tier(tmp_path):
    """A fat description must produce an index-tier warning. The whole
    frontmatter counts — the sibling fields are injected too."""
    from pathlib import Path
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\n"
        "name: skill-x\n"
        "description: Use when " + "触发场景" * 40 + ".\n"
        "triggers:\n"
        + "".join(f'  - "场景{i}"\n' for i in range(12))
        + "---\n"
        "# body\n",
        encoding="utf-8",
    )
    from scripts._lib.frontmatter import load
    fm = load(p)
    warnings = validate_skill_frontmatter(fm, skill_dir=tmp_path)
    assert any("index" in w.lower() and "token" in w.lower() for w in warnings), warnings


def test_validate_does_not_warn_on_a_lean_index_tier(tmp_path):
    from pathlib import Path
    from scripts._lib.frontmatter import load
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: skill-x\ndescription: Use when A.\n---\n# body\n",
        encoding="utf-8",
    )
    fm = load(p)
    warnings = validate_skill_frontmatter(fm, skill_dir=tmp_path)
    assert not any("index tier" in w.lower() for w in warnings), warnings


def test_validate_body_warns_on_an_over_budget_body(tmp_path):
    """A body over 5,000 tokens warns. It is REPORTED, not refused."""
    from pathlib import Path
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: skill-x\ndescription: Use when A.\n---\n"
        + ("内容行\n" * 20000),
        encoding="utf-8",
    )
    warnings = validate_skill_body(p, {"name": "skill-x"})
    assert any("5,000" in w or "5000" in w for w in warnings), warnings


def test_validate_body_does_not_warn_on_a_shorter_body(tmp_path):
    from pathlib import Path
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\nname: skill-x\ndescription: Use when A.\n---\n# small\n"
        "## Red Flags\n- x\n",
        encoding="utf-8",
    )
    warnings = validate_skill_body(p, {"name": "skill-x"})
    assert not any("5,000" in w or "5000" in w for w in warnings), warnings


def test_measure_skill_of_the_real_skill_forge_is_reported(tmp_path):
    """Sanity: the module works on a real skill-shaped directory."""
    d = tmp_path / "x"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: x\ndescription: Use when A.\n---\n# body\n", encoding="utf-8"
    )
    c = measure_skill(d)
    assert c.index_tokens > 0
    assert c.load_tokens > 0
    assert not c.index_over_budget


def test_audit_report_contains_the_cost_section(tmp_path):
    """The report must SHOW the measured tiers — a number in the report is
    what makes the cost visible."""
    from scripts.run import _materialize
    d = tmp_path / "x"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: x\ndescription: Use when A.\n---\n# body\n", encoding="utf-8"
    )
    _materialize(d, verdict=False, root_cause="other")
    report = (d / "audit-report.md").read_text(encoding="utf-8")
    assert "## Cost" in report
    assert "| index |" in report
    assert "| load |" in report
    assert "| files |" in report


def test_phase0_marker_prints_the_index_cost(tmp_path, monkeypatch, capsys):
    """The index tier is paid by every session, so its number belongs in
    the FIRST marker — the operator sees it before anything else runs."""
    from scripts.run import main
    d = tmp_path / "x"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: x\ndescription: Use when A or B with symptom S.\n---\n# body\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("shutil.which", lambda name: None)
    main(["--skill", str(d), "--scope", "audit-only"])
    out = capsys.readouterr().out
    assert "index=" in out, out
    assert "tok" in out, out
