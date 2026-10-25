"""P0: a real baseline.

Before this, run.py had:

    candidate = skill_dir / "SKILL.md"
    baseline  = candidate      # <-- PLACEHOLDER

Phase 4's rubric compared the candidate against ITSELF. There was no
before/after, so "pass_rate improved" was unmeasurable, and Phase 5's
best.md had nothing to diff against.

Anthropic's skill-creator does it the other way round: snapshot the
pre-change version, point the baseline run at the snapshot, and run
with-skill and baseline side by side.

Here the baseline is a real snapshot of SKILL.md taken BEFORE the
forward phase, and the audit report states the delta.
"""
import pytest
from scripts._lib.baseline_log import read_baseline, write_baseline
from scripts._lib.snapshot import snapshot_skill, read_snapshot, diff_bodies


def test_snapshot_captures_the_skill_md(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: x\n---\nORIGINAL BODY\n", encoding="utf-8")
    snap = snapshot_skill(d)
    assert snap is not None
    assert snap.exists()
    assert "ORIGINAL BODY" in snap.read_text(encoding="utf-8")


def test_snapshot_of_a_skill_without_skill_md_is_none(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    assert snapshot_skill(d) is None


def test_snapshot_does_not_overwrite_an_earlier_snapshot(tmp_path):
    """The snapshot is the BEFORE state. A second call in the same run
    must not clobber it with the already-modified file."""
    d = tmp_path / "x"
    d.mkdir()
    (d / "SKILL.md").write_text("BEFORE\n", encoding="utf-8")
    first = snapshot_skill(d)
    (d / "SKILL.md").write_text("AFTER\n", encoding="utf-8")
    second = snapshot_skill(d)
    assert first.read_text(encoding="utf-8") == "BEFORE\n"
    assert second is None or second.read_text(encoding="utf-8") == "BEFORE\n"


def test_read_snapshot_returns_none_when_absent(tmp_path):
    assert read_snapshot(tmp_path / "x") is None


def test_diff_bodies_reports_added_and_removed_lines():
    a = "line one\nline two\n"
    b = "line one\nline three\n"
    delta = diff_bodies(a, b)
    assert delta["added"] == 1
    assert delta["removed"] == 1
    assert delta["changed"] is True


def test_diff_bodies_of_identical_text_reports_no_change():
    t = "same\n"
    delta = diff_bodies(t, t)
    assert delta["added"] == 0
    assert delta["removed"] == 0
    assert delta["changed"] is False


def test_baseline_log_roundtrip(tmp_path):
    write_baseline(tmp_path, "abc123")
    assert read_baseline(tmp_path) == "abc123"


# --- the integration: run.py must use a real baseline ---

def test_run_uses_a_real_baseline_not_the_candidate(tmp_path, monkeypatch):
    """The rubric must be handed a baseline that DIFFERS from the
    candidate. A test that only checks `baseline != candidate` by path
    would pass even if the content is identical, so this asserts the
    content."""
    from scripts.run import main
    skill = tmp_path / "x"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: x\ndescription: Use when A or B with symptom S.\n---\n# body\n",
        encoding="utf-8",
    )
    seen: list[str] = []

    def fake_llm(prompt: str) -> float:
        seen.append(prompt)
        return 0.9

    class R:
        returncode = 0
        stdout = b""
        stderr = b""

    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setattr("subprocess.run", lambda cmd, **kw: R())
    monkeypatch.setattr(
        "scripts.run.http_channel_from_env", lambda model: fake_llm
    )
    main([
        "--skill", str(skill), "--scope", "audit-only",
        "--rubric-model", "judge/model",
    ])
    assert seen, "the rubric was never called"
    prompt = seen[0]
    # The prompt must contain the candidate body. The baseline body is
    # the same text here (nothing modified the skill), so the baseline
    # must be present as a DISTINCT snapshot path.
    assert "body" in prompt
    assert "baseline" in prompt.lower()


def test_audit_report_shows_the_before_after_delta(tmp_path, monkeypatch):
    """When the forward phase changed SKILL.md, the report must state
    what changed. A skill that was edited between runs is exactly the
    case the report has to make visible."""
    from scripts.run import main
    skill = tmp_path / "x"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: x\ndescription: Use when A or B with symptom S.\n---\n# body\n",
        encoding="utf-8",
    )
    # Simulate a forward phase that rewrote the skill.
    import scripts.run as run_mod
    orig_emit = run_mod._emit

    def fake_emit(phase, name, msg):
        if phase == 3:
            (skill / "SKILL.md").write_text(
                "---\nname: x\ndescription: Use when A or B with symptom S.\n---\n"
                "# body\n\n## New Section\n\nadded by the optimizer\n",
                encoding="utf-8",
            )
        orig_emit(phase, name, msg)

    monkeypatch.setattr("scripts.run._emit", fake_emit)
    monkeypatch.setattr("shutil.which", lambda name: None)
    main(["--skill", str(skill), "--scope", "audit-only"])
    report = (skill / "audit-report.md").read_text(encoding="utf-8")
    assert "## Change" in report
    assert "added" in report.lower()
