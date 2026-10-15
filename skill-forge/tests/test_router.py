import shutil
from pathlib import Path
import pytest
from scripts.audit import AuditReport
from scripts.router import route, RouteResult

def test_route_improve_with_gbrain_runs_skillopt(tmp_path, monkeypatch):
    skill = tmp_path / "x"
    skill.mkdir()
    seen: list[list[str]] = []
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/gbrain" if name == "gbrain" else None)
    def fake_run(cmd, **kw):
        seen.append(cmd)
        class R: returncode = 0; stdout = b"dry-run preview\n"; stderr = b""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    r = route(skill, "improve", AuditReport("prompt", 0.8, [], "improve"))
    assert r.forwarded_to == "gbrain-skillopt"
    assert r.exit_code == 0
    assert "--dry-run" in seen[0]

def test_route_create_forwards_to_skill_creator(tmp_path, monkeypatch):
    skill = tmp_path / "y"
    skill.mkdir()
    seen: list[list[str]] = []
    monkeypatch.setattr("shutil.which", lambda name: None)  # neither
    monkeypatch.setattr("subprocess.run", lambda c, **k: (seen.append(c) or type("R", (), {"returncode": 0, "stdout": b"", "stderr": b""})()))
    r = route(skill, "create", AuditReport("missing", 1.0, [], "create"))
    assert r.forwarded_to == "skill-creator"
    assert r.degraded is True

def test_route_retire_skips_forward(tmp_path):
    skill = tmp_path / "z"
    skill.mkdir()
    r = route(skill, "retire", AuditReport("other", 0.5, [], "retire"))
    assert r.forwarded_to == "diagnose-only"
    assert r.degraded is True
