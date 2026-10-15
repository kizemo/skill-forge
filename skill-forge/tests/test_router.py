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

def test_route_returns_bundled_skill_safety_when_skill_is_installed(tmp_path, monkeypatch):
    """v2-T4: a bundled skill must NOT be forwarded to gbrain or the shim.
    route() returns a diagnose-only degraded RouteResult with reason set,
    without invoking subprocess.run at all."""
    import json
    install = tmp_path / "install.json"
    skill = tmp_path / "plugins" / "bundled-skill"
    skill.mkdir(parents=True)
    install.write_text(
        json.dumps({"bundled-skill": str(skill.resolve())}),
        encoding="utf-8",
    )
    # INSTALL_JSON is captured at import time; override it directly.
    monkeypatch.setattr("scripts._lib.bundle.INSTALL_JSON", install)
    # If route() actually called subprocess.run, this would record an entry.
    # It must NOT — bundled skills short-circuit.
    called: list[bool] = []
    def fake_run(cmd, **kw):
        called.append(True)
        class R: returncode = 0; stdout = b""; stderr = b""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/gbrain" if name == "gbrain" else None)
    r = route(skill, "improve", AuditReport("prompt", 0.8, [], "improve"))
    assert r.forwarded_to == "diagnose-only"
    assert r.degraded is True
    assert r.reason == "bundled-skill-safety"
    assert r.exit_code == 0  # bundled-safety is not an error, it's a deliberate degrade
    assert called == [], f"subprocess.run was called for a bundled skill: {called!r}"


def test_route_skill_dir_env_overrides_ambient_value(tmp_path, monkeypatch):
    """v2-T7 + RULING-9 v2 corollary: even if a stale SKILL_DIR is set in
    the parent's environment, the router's computed value wins because
    **os.environ is spread BEFORE the router's SKILL_DIR key (last-wins
    per Python dict-literal semantics)."""
    skill = tmp_path / "x"
    skill.mkdir()
    wrong_dir = tmp_path / "wrong"
    wrong_dir.mkdir()
    monkeypatch.setattr("shutil.which", lambda name: None)  # no gbrain
    # Inject a stale parent SKILL_DIR.
    monkeypatch.setenv("SKILL_DIR", str(wrong_dir.resolve()))
    seen: list[dict] = []
    def fake_run(cmd, **kw):
        seen.append({"env": kw.get("env")})
        class R: returncode = 0; stdout = b""; stderr = b""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    r = route(skill, "create", AuditReport("missing", 1.0, [], "create"))
    assert r.forwarded_to == "skill-creator"
    # The router's SKILL_DIR (correct dir) outranks the parent one (wrong dir).
    assert seen[0]["env"]["SKILL_DIR"] == str(skill.resolve())


def test_legacy_shim_passes_resolved_skill_dir_via_env_to_init_skill_path(tmp_path, monkeypatch):
    """v2-T7 + v2-T3 I-1: when SKILL_DIR is set in the shim's environment
    and argv is empty, the shim's constructed cmd must pass the resolved
    skill dir to --path (not Path.cwd(), which is v1's bug class)."""
    skill = tmp_path / "x"
    skill.mkdir()
    monkeypatch.setenv("SKILL_DIR", str(skill.resolve()))
    seen: list[list[str]] = []
    def fake_run(cmd, **kw):
        seen.append(cmd)
        class R: returncode = 0; stdout = b""; stderr = b""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    from scripts._legacy_init_skill import main as shim_main
    rc = shim_main([])
    assert rc == 0
    # The shim's command shape: [sys.executable, <init_skill.py>, name, "--path", dir]
    assert seen[0][-2] == "--path"
    assert seen[0][-1] == str(skill.resolve())
    assert seen[0][-3] == skill.name


def test_legacy_shim_falls_back_to_argv_when_env_unset(tmp_path, monkeypatch):
    """v2-T7 + v2-T3 I-1: when SKILL_DIR is unset and argv has a path,
    the shim uses argv[0] as the skill dir and passes it (resolved) to --path."""
    skill = tmp_path / "y"
    skill.mkdir()
    monkeypatch.delenv("SKILL_DIR", raising=False)
    seen: list[list[str]] = []
    def fake_run(cmd, **kw):
        seen.append(cmd)
        class R: returncode = 0; stdout = b""; stderr = b""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    from scripts._legacy_init_skill import main as shim_main
    rc = shim_main([str(skill.resolve())])
    assert rc == 0
    assert seen[0][-2] == "--path"
    assert seen[0][-1] == str(skill.resolve())
    assert seen[0][-3] == skill.name


def test_legacy_shim_env_wins_over_argv_when_both_set(tmp_path, monkeypatch):
    """v2-T7 + RULING-9 v2 corollary: when both SKILL_DIR and argv are set
    to different values, the env value wins (per v2-T7's RULING-9 v2
    corollary flip)."""
    env_dir = tmp_path / "env_dir"
    env_dir.mkdir()
    argv_dir = tmp_path / "argv_dir"
    argv_dir.mkdir()
    monkeypatch.setenv("SKILL_DIR", str(env_dir.resolve()))
    seen: list[list[str]] = []
    def fake_run(cmd, **kw):
        seen.append(cmd)
        class R: returncode = 0; stdout = b""; stderr = b""
        return R()
    monkeypatch.setattr("subprocess.run", fake_run)
    from scripts._legacy_init_skill import main as shim_main
    rc = shim_main([str(argv_dir.resolve())])
    assert rc == 0
    # env wins.
    assert seen[0][-1] == str(env_dir.resolve())
    assert seen[0][-1] != str(argv_dir.resolve())


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
