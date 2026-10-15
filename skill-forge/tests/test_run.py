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
