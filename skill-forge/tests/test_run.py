import json
from pathlib import Path
import pytest
from scripts.run import main

def test_run_prints_six_phase_markers(tmp_path, capsys, monkeypatch):
    skill = tmp_path / "demo"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Use when A or B with symptom S.\n---\n# Demo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("shutil.which", lambda name: None)
    rc = main(["--skill", str(skill), "--scope", "audit-only"])
    out = capsys.readouterr().out
    for i in range(6):
        assert f"[phase {i}]" in out.lower() or f"phase {i}" in out.lower()
    assert rc in (0, 2)  # permissive; per RULING-2 + RULING-1 with the stub fixture, rc=0

def test_run_writes_audit_report(tmp_path, monkeypatch):
    skill = tmp_path / "demo"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Use when A.\n---\n# body\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("shutil.which", lambda name: None)
    main(["--skill", str(skill), "--scope", "audit-only"])
    report = (skill / "audit-report.md").read_text(encoding="utf-8")
    assert "root_cause" in report


def test_run_writes_proposed_md_for_bundled_skill_and_leaves_skill_md_untouched(tmp_path, monkeypatch):
    """v2-T4 + v2-T5: when a skill is bundled, the materialize phase must
    write proposed.md (the candidate SKILL.md content) and audit-report.md,
    but MUST NOT modify the bundled SKILL.md. The bundled install is
    read-only from skill-forge's perspective.

    v2-T5 NOTE: this byte-identity assertion is now load-bearing. In v2-T4
    it was vacuous (v1 never wrote SKILL.md at all). v2-T5 introduces
    best.md writing for the non-bundled accept path and a SHA race check
    on both paths, so a future regression that accidentally writes SKILL.md
    — or that writes best.md for a bundled skill — would now be caught here."""
    install = tmp_path / "install.json"
    skill = tmp_path / "plugins" / "bundled-skill"
    skill.mkdir(parents=True)
    skill_md = skill / "SKILL.md"
    skill_md_original = (
        "---\n"
        "name: bundled-skill\n"
        "description: Use when a bundled skill is targeted.\n"
        "---\n"
        "# Original body — must NOT be modified\n"
    )
    skill_md.write_text(skill_md_original, encoding="utf-8")
    install.write_text(
        json.dumps({"bundled-skill": str(skill.resolve())}),
        encoding="utf-8",
    )
    # INSTALL_JSON is captured at import time; override it directly.
    monkeypatch.setattr("scripts._lib.bundle.INSTALL_JSON", install)
    monkeypatch.setattr("shutil.which", lambda name: None)  # no gbrain, no shim
    rc = main(["--skill", str(skill), "--scope", "audit-only"])
    # SKILL.md must be byte-identical to the original.
    assert skill_md.read_text(encoding="utf-8") == skill_md_original
    # audit-report.md was written.
    assert (skill / "audit-report.md").exists()
    # proposed.md was written (because verdict was True for the stub fixture).
    assert (skill / "proposed.md").exists()
    # v2-T5: best.md is the non-bundled-only artifact; a bundled skill must
    # never get one.
    assert not (skill / "best.md").exists()
    assert rc in (0, 2)


def test_run_exits_3_on_baseline_sha_drift_for_bundled_skill(tmp_path, monkeypatch):
    """v2-T5: if the SKILL.md SHA has drifted since the last skill-forge
    run AND the skill is bundled, refuse (exit 3) without overwriting
    either SKILL.md or proposed.md. The bundled install is read-only."""
    install = tmp_path / "install.json"
    skill = tmp_path / "plugins" / "bundled-skill"
    skill.mkdir(parents=True)
    skill_md = skill / "SKILL.md"
    original = (
        "---\n"
        "name: bundled-skill\n"
        "description: Use when a bundled skill is targeted.\n"
        "---\n"
        "# Original body\n"
    )
    skill_md.write_text(original, encoding="utf-8")
    install.write_text(
        json.dumps({"bundled-skill": str(skill.resolve())}),
        encoding="utf-8",
    )
    # Pre-existing baseline pins a SHA that does NOT match the current SKILL.md
    # (i.e. user has manually edited SKILL.md since the last run).
    baseline = skill / ".skill-forge-baseline.json"
    baseline.write_text(
        json.dumps({"sha": "deadbeef", "ts": "2026-10-15T00:00:00Z"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts._lib.bundle.INSTALL_JSON", install)
    monkeypatch.setattr("shutil.which", lambda name: None)
    rc = main(["--skill", str(skill), "--scope", "audit-only"])
    assert rc == 3  # EEXIT_RACE — distinct from refuse (2)
    # SKILL.md is byte-identical to the original (no overwrite).
    assert skill_md.read_text(encoding="utf-8") == original
    # No proposed.md written (race refused before materialize).
    assert not (skill / "proposed.md").exists()


def test_run_writes_best_md_on_accept_for_non_bundled_skill(tmp_path, monkeypatch):
    """v2-T5: a non-bundled skill with verdict=True writes best.md
    containing the new SKILL.md content, AND audit-report.md. SKILL.md
    itself is NOT overwritten (best.md is the candidate; user merges
    manually). The baseline is updated on success."""
    skill = tmp_path / "x"
    skill.mkdir()
    skill_md = skill / "SKILL.md"
    original = (
        "---\n"
        "name: x\n"
        "description: Use when A or B with symptom S.\n"
        "---\n"
        "# Original body\n"
    )
    skill_md.write_text(original, encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda name: None)
    rc = main(["--skill", str(skill), "--scope", "audit-only"])
    # Stub fixture deterministic passes → accept → rc=0.
    assert rc == 0
    # SKILL.md untouched (best.md is the candidate).
    assert skill_md.read_text(encoding="utf-8") == original
    # best.md was written with the candidate content verbatim.
    assert (skill / "best.md").exists()
    best = (skill / "best.md").read_text(encoding="utf-8")
    assert "name: x" in best
    # audit-report.md was written.
    assert (skill / "audit-report.md").exists()
    # baseline was updated.
    assert (skill / ".skill-forge-baseline.json").exists()


def test_run_writes_baseline_on_first_run(tmp_path, monkeypatch):
    """v2-T5: a fresh skill_dir (no .skill-forge-baseline.json) is
    treated as 'no prior run'; the race check passes (because there is
    nothing to drift from), materialize proceeds, and the baseline is
    written on success."""
    skill = tmp_path / "fresh"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: fresh\n"
        "description: Use when a fresh skill is targeted for the first time.\n"
        "---\n"
        "# body\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("shutil.which", lambda name: None)
    rc = main(["--skill", str(skill), "--scope", "audit-only"])
    assert rc == 0
    assert (skill / ".skill-forge-baseline.json").exists()
    bl = json.loads((skill / ".skill-forge-baseline.json").read_text(encoding="utf-8"))
    assert "sha" in bl and len(bl["sha"]) == 8  # 8-char hex per T1 sha.py


def test_run_does_not_update_baseline_on_refuse(tmp_path, monkeypatch):
    """v2-T5: if the verdict is False (refuse, rc=2), the baseline is NOT
    updated. A failed run must not pin a SHA, because the next run starts
    from the original baseline again."""
    # Forcing a refuse: name is missing → deterministic gate fails.
    skill = tmp_path / "bad"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "description: Use when bad skill.\n"  # name missing → judge False
        "---\n"
        "# body\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("shutil.which", lambda name: None)
    rc = main(["--skill", str(skill), "--scope", "audit-only"])
    assert rc == 2  # refuse
    # Baseline must NOT be written on refuse.
    assert not (skill / ".skill-forge-baseline.json").exists()


def test_run_does_not_write_best_md_on_refuse(tmp_path, monkeypatch):
    """v2-T5: best.md is only written on accept. On refuse, no best.md."""
    skill = tmp_path / "bad"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "description: Use when bad.\n"
        "---\n"
        "# body\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("shutil.which", lambda name: None)
    rc = main(["--skill", str(skill), "--scope", "audit-only"])
    assert rc == 2
    assert not (skill / "best.md").exists()
