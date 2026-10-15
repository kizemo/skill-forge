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
    """v2-T4: when a skill is bundled, the materialize phase must write
    proposed.md (the candidate SKILL.md content) and audit-report.md, but
    MUST NOT modify the bundled SKILL.md. The bundled install is read-only
    from skill-forge's perspective."""
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
    assert rc in (0, 2)
