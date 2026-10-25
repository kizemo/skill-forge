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


# ---------------------------------------------------------------------------
# P0-1 (2026-10-15): router forwards the benchmark / split / budget to
# gbrain skillopt, and isolates GBRAIN_HOME from the user's real brain.
#
# Evidence for each defect (gbrain skillopt --help, v0.60.287.0):
#   - benchmark is REQUIRED: "Required (one of): --benchmark <path> |
#     --bootstrap-from-skill | --bootstrap-from-routing"
#   - "--split TRAIN:SEL:TEST  Default '4:1:5'; refuses if D_sel < 5"
#     -> 15 rows at 4:1:5 yields D_sel < 5, so the run refuses. gbrain's own
#     documented 15-task recipe is "--split 1:1:1" (5 train / 5 sel / 5 test).
#   - "--max-usd N|off  Hard cap. Default 5.00" -> make the cap explicit.
#   - GBRAIN_HOME is honoured by gbrain (it creates <GBRAIN_HOME>/.gbrain/),
#     and the user's real brain may be locked by a live `gbrain serve`.
# ---------------------------------------------------------------------------


def _capture_route(tmp_path, monkeypatch, **kwargs):
    """Run route() with a fake gbrain on PATH; return (cmd, env, result)."""
    skill = tmp_path / "x"
    skill.mkdir()
    seen: list[dict] = []

    def fake_run(cmd, **kw):
        seen.append({"cmd": list(cmd), "env": kw.get("env")})
        class R:
            returncode = 0
            stdout = b"ok"
            stderr = b""
        return R()

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/gbrain" if name == "gbrain" else None)
    monkeypatch.setattr("subprocess.run", fake_run)
    r = route(skill, "improve", AuditReport("prompt", 0.8, [], "improve"), **kwargs)
    return seen, r


def test_route_passes_benchmark_path_to_gbrain(tmp_path, monkeypatch):
    """P0-1 defect 1: Phase 2 generates a 15-row benchmark but the router
    never told gbrain about it. gbrain's CLI requires one of
    --benchmark/--bootstrap-from-*, so the forward was guaranteed to fail
    with a missing-benchmark error."""
    bench = tmp_path / "skillopt-benchmark.jsonl"
    bench.write_text('{"task_id":"t-001"}\n', encoding="utf-8")
    seen, r = _capture_route(tmp_path, monkeypatch, benchmark=bench)
    assert r.forwarded_to == "gbrain-skillopt"
    cmd = seen[-1]["cmd"]
    assert "--benchmark" in cmd, cmd
    assert str(bench) in cmd, cmd


def test_route_omits_benchmark_flag_when_no_benchmark_given(tmp_path, monkeypatch):
    """No benchmark -> no --benchmark flag (gbrain would refuse, but we
    must not pass a dangling flag with a fabricated path)."""
    seen, r = _capture_route(tmp_path, monkeypatch)
    assert "--benchmark" not in seen[-1]["cmd"]


def test_route_passes_split_to_gbrain(tmp_path, monkeypatch):
    """P0-1 defect 2: the default split 4:1:5 yields D_sel < 5 on a
    15-row benchmark and gbrain refuses. The router must pass an explicit
    split."""
    seen, r = _capture_route(tmp_path, monkeypatch, split="1:1:1")
    cmd = seen[-1]["cmd"]
    assert "--split" in cmd, cmd
    assert "1:1:1" in cmd, cmd


def test_route_default_split_is_the_15_task_safe_recipe(tmp_path, monkeypatch):
    """The DEFAULT split must be one that satisfies gbrain's D_sel >= 5
    gate for the default 15-row benchmark. gbrain's own docs pair
    '--bootstrap-reviewed' with '--split 1:1:1' for a 15-task benchmark."""
    seen, r = _capture_route(tmp_path, monkeypatch)
    cmd = seen[-1]["cmd"]
    assert "--split" in cmd, cmd
    i = cmd.index("--split")
    assert cmd[i + 1] == "1:1:1", cmd


def test_route_passes_max_usd_to_gbrain(tmp_path, monkeypatch):
    """P0-1 defect 2b: the spend cap must be explicit and auditable in the
    argv, not left to an invisible default."""
    seen, r = _capture_route(tmp_path, monkeypatch, max_usd="2.50")
    cmd = seen[-1]["cmd"]
    assert "--max-usd" in cmd, cmd
    assert "2.50" in cmd, cmd


def test_route_isolates_gbrain_home_via_env(tmp_path, monkeypatch):
    """P0-1 defect 3: the gbrain subprocess must not touch the user's real
    ~/.gbrain. GBRAIN_HOME is the documented isolation lever (gbrain
    creates <GBRAIN_HOME>/.gbrain/ and reads its brain from there)."""
    home = tmp_path / "isolated-gbrain-home"
    home.mkdir()
    (home / ".gbrain").mkdir()
    (home / ".gbrain" / "config.json").write_text("{}", encoding="utf-8")
    seen, r = _capture_route(tmp_path, monkeypatch, gbrain_home=home)
    env = seen[-1]["env"]
    assert env is not None, "the gbrain subprocess must receive an explicit env"
    assert env["GBRAIN_HOME"] == str(home)


def test_route_leaves_gbrain_home_untouched_when_not_requested(tmp_path, monkeypatch):
    """No gbrain_home requested -> the child inherits the parent env; we
    must not silently rewrite GBRAIN_HOME."""
    seen, r = _capture_route(tmp_path, monkeypatch)
    env = seen[-1]["env"]
    assert env is None or "GBRAIN_HOME" not in env


def test_route_initialises_brain_in_isolated_home_when_missing(tmp_path, monkeypatch):
    """An isolated GBRAIN_HOME starts empty; gbrain then refuses with
    `Error [no_brain]: No brain configured. Run: gbrain init`. The router
    must bootstrap the isolated brain once (`gbrain init --pglite
    --no-embedding`) instead of handing gbrain a guaranteed-to-fail home."""
    home = tmp_path / "isolated-gbrain-home"
    home.mkdir()
    calls: list[dict] = []

    def fake_run(cmd, **kw):
        calls.append({"cmd": list(cmd), "env": kw.get("env")})
        if "init" in cmd:
            # Simulate gbrain init writing the brain config.
            (home / ".gbrain").mkdir(parents=True, exist_ok=True)
            (home / ".gbrain" / "config.json").write_text(
                '{"engine":"pglite"}', encoding="utf-8"
            )
        class R:
            returncode = 0
            stdout = b"ok"
            stderr = b""
        return R()

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/gbrain" if name == "gbrain" else None)
    monkeypatch.setattr("subprocess.run", fake_run)
    skill = tmp_path / "x"
    skill.mkdir()
    r = route(skill, "improve", AuditReport("prompt", 0.8, [], "improve"), gbrain_home=home)
    init_calls = [c for c in calls if "init" in c["cmd"]]
    assert init_calls, f"expected a gbrain init call, saw {[c['cmd'] for c in calls]!r}"
    init_cmd = init_calls[0]["cmd"]
    assert "--pglite" in init_cmd, init_cmd
    assert "--no-embedding" in init_cmd, init_cmd
    # The init must itself run against the isolated home.
    assert init_calls[0]["env"]["GBRAIN_HOME"] == str(home)
    # And the skillopt call must still have happened, after the init.
    skillopt_calls = [c for c in calls if "skillopt" in c["cmd"]]
    assert skillopt_calls, calls
    assert calls.index(init_calls[0]) < calls.index(skillopt_calls[0])


def test_route_skips_init_when_isolated_home_already_has_brain(tmp_path, monkeypatch):
    """A warm isolated home must not be re-initialised on every run
    (gbrain init costs ~14s)."""
    home = tmp_path / "isolated-gbrain-home"
    (home / ".gbrain").mkdir(parents=True)
    (home / ".gbrain" / "config.json").write_text('{"engine":"pglite"}', encoding="utf-8")
    seen, r = _capture_route(tmp_path, monkeypatch, gbrain_home=home)
    assert not any("init" in c["cmd"] for c in seen), [c["cmd"] for c in seen]


def test_route_passes_skills_dir_to_gbrain(tmp_path, monkeypatch):
    """P0-1 follow-up: gbrain resolves the skill as
    `<skills-dir>/<name>/SKILL.md`. It takes a NAME, not a path — with no
    --skills-dir it looks in the installed gbrain skills tree and refuses
    with NoSkill, which is the blocker that stopped the forward phase
    from ever completing.

    `--skills-dir` is a real, working gbrain flag (verified: the full
    pipeline runs with it) but it is absent from `gbrain skillopt --help`
    and from the NoSkill error message. The router must pass the
    directory that CONTAINS the skill dir."""
    skill = tmp_path / "probe"
    skill.mkdir()
    seen: list[dict] = []

    def fake_run(cmd, **kw):
        seen.append({"cmd": list(cmd), "env": kw.get("env")})
        class R:
            returncode = 0
            stdout = b"ok"
            stderr = b""
        return R()

    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/gbrain" if name == "gbrain" else None
    )
    monkeypatch.setattr("subprocess.run", fake_run)
    r = route(skill, "improve", AuditReport("prompt", 0.8, [], "improve"),
              skills_dir=tmp_path)
    assert r.forwarded_to == "gbrain-skillopt"
    cmd = seen[-1]["cmd"]
    assert "--skills-dir" in cmd, cmd
    assert str(tmp_path) in cmd, cmd
    # The skill is addressed by NAME, and the name must be the directory
    # gbrain will look for under --skills-dir.
    i = cmd.index("--skills-dir")
    assert cmd[i + 1] == str(tmp_path), cmd
    assert "probe" in cmd, cmd
    assert str(skill) not in cmd, "the skill must be passed by name, not by path"


def test_route_omits_skills_dir_when_not_given(tmp_path, monkeypatch):
    """No skills_dir -> no --skills-dir flag (gbrain falls back to its own
    resolution; we must not invent a path)."""
    seen, r = _capture_route(tmp_path, monkeypatch)
    assert "--skills-dir" not in seen[-1]["cmd"], seen[-1]["cmd"]
