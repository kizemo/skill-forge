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

def test_route_uses_sys_executable_for_skill_creator_subprocess(tmp_path, monkeypatch):
    """v2-T3 / RULING-9 v2 item: the router must invoke the shim with
    sys.executable, not bare 'python'. Bare 'python' breaks venv-only hosts
    and assumes a system Python on PATH; sys.executable uses the same
    interpreter that is running the router (and therefore the same venv)."""
    import sys
    skill = tmp_path / "x"
    skill.mkdir()
    seen: list[list[str]] = []
    monkeypatch.setattr("shutil.which", lambda name: None)  # no gbrain
    def fake_run(cmd, **kw):
        seen.append(cmd)
        class R: returncode = 0; stdout = b""; stderr = b""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    r = route(skill, "create", AuditReport("missing", 1.0, [], "create"))
    assert r.forwarded_to == "skill-creator"
    assert r.degraded is True
    # The shim subprocess must be invoked with the same interpreter that
    # is running the router, not with a bare 'python' on PATH.
    assert seen[0][0] == sys.executable
    assert seen[0][0] != "python"

def test_route_passes_resolved_skill_dir_via_env_or_argv(tmp_path, monkeypatch):
    """v2-T3 / T8 review M-2: the shim's --path must be the absolute resolved
    skill dir, not Path.cwd(). The router must propagate this either via
    SKILL_DIR env var or as an explicit argv position. Verify the
    propagated value resolves to the same absolute path."""
    skill = tmp_path / "x"
    skill.mkdir()
    seen: list[dict] = []
    monkeypatch.setattr("shutil.which", lambda name: None)  # no gbrain
    def fake_run(cmd, **kw):
        seen.append({"cmd": cmd, "env": kw.get("env"), "cwd": kw.get("cwd")})
        class R: returncode = 0; stdout = b""; stderr = b""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    r = route(skill, "create", AuditReport("missing", 1.0, [], "create"))
    assert r.forwarded_to == "skill-creator"
    captured = seen[0]
    # Two acceptable ways to pass the resolved skill dir:
    #   (a) env["SKILL_DIR"] = str(skill.resolve()), or
    #   (b) cmd contains str(skill.resolve()) as a positional arg.
    propagated = None
    if captured["env"] and "SKILL_DIR" in captured["env"]:
        propagated = captured["env"]["SKILL_DIR"]
    else:
        for arg in captured["cmd"]:
            if str(skill.resolve()) in str(arg):
                propagated = str(arg)
                break
    assert propagated is not None, (
        f"shim subprocess must receive the resolved skill dir via SKILL_DIR "
        f"env or argv; saw cmd={captured['cmd']!r} env={captured['env']!r}"
    )
    # And it must NOT be the caller's cwd (the v1 bug).
    assert propagated != str(Path.cwd()) or propagated == str(skill.resolve())

def test_legacy_shim_refuses_when_skill_dir_missing(monkeypatch, capsys):
    """v2-T3: _legacy_init_skill.py's main([]) with SKILL_DIR unset must
    emit a [FATAL] line to stderr and return 2. The shim never silently
    swallows the missing input."""
    monkeypatch.delenv("SKILL_DIR", raising=False)
    from scripts._legacy_init_skill import main as shim_main
    rc = shim_main([])
    assert rc == 2
    err = capsys.readouterr().err
    assert "[FATAL]" in err
    assert "SKILL_DIR" in err or "skill_dir" in err
