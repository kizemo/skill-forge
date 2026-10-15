# skill-forge

A meta-skill for auditing, creating, improving, and retiring other skills.
See `docs/foundry.md` for the heavy reference — quick start below.

## Phases (binding order, RULING-6: contract > prompt)

| Phase | Verb | Code | What happens |
|---|---|---|---|
| 0 | audit | `scripts/audit.py` | Classify root cause: prompt / routing / contract / missing / other |
| 1 | scope | (CLI `--scope`) | User picks: create / improve / audit-only / retire |
| 2 | bootstrap | `scripts/bootstrap_benchmark.py` | Generate 15 templated benchmark rows (RULING-7) + sentinel |
| 3 | forward | `scripts/router.py` | Call `gbrain skillopt` or `skill-creator/init_skill` shim; degrade with `RouteResult` (RULING-9) |
| 4 | verify | `scripts/judge_triple.py` | Deterministic + LLM rubric + spot check; RULING-1 llm_call=None → rubric skipped |
| 5 | materialize | `scripts/run.py::_materialize` | Write `audit-report.md`; accept or refuse |

## v2 safety additions

v2 hardened what happens under each phase without adding any CLI flag.

- **`SKILL.md` is never overwritten.** On accept, the candidate content is
  written to `best.md` (your skill) or `proposed.md` (bundled skill); you
  diff and merge by hand.
- **Bundled-skill safety.** `is_bundled()` checks `~/.gbrain/install.json`
  and refuses to forward a marketplace install (exit `0`, `degraded=True`,
  `reason="bundled-skill-safety"`). It **fails open** — no `install.json`
  means "not bundled" — so copy the skill to a scratch dir and point
  `--skill` at the copy. The guard is defence-in-depth, not a lock.
- **SHA race check.** `.skill-forge-baseline.json` records the `SKILL.md`
  hash from the last successful run. If the file drifted since then, a
  bundled skill is refused with exit `3`; a non-bundled skill warns and
  proceeds. `SKILL.md` is untouched either way.

Details and caveats: `docs/foundry.md` § 6 and § 9.

## Rulings that shape this package

- **RULING-4** (`[tool.pytest.ini_options] pythonpath = ["."]` in `pyproject.toml`)
  — bare `pytest -q` now works from `skill-forge/`.
- **RULING-1** — `llm_call=None` SKIPS the LLM rubric. Absent ≠ failure.
- **RULING-6** — `audit()` precedence is `missing → other(frontmatter) → routing → contract → prompt → other`.
- **RULING-7** — `bootstrap()` emits 15 rows by default, sentinel `# BOOTSTRAP_PENDING_REVIEW`.
- **RULING-8** — rubric-skipped is invisible in the verdict; branch on `llm_call is None` at the call site, never on `v.llm_score`.
- **RULING-9** — `route()`'s subprocess is unguarded; `run.py` wraps it (option 1).
- **RULING-9 v2** — the router invokes the shim with `sys.executable` and passes the skill dir via `SKILL_DIR`, which outranks any ambient value.
- **RULING-10** — the dead `env` root cause was dropped from the `Literal` (v2-T6).

## Quick start

```bash
pip install -e .
python -m scripts --skill /path/to/target-skill --scope audit-only
```

Run from `skill-forge/` (see `docs/foundry.md` § 1 — running from the repo root
picks up a stray `scripts` namespace package and fails).

## Verification

- 53 tests pass via `cd skill-forge && pytest -q` (bare invocation, RULING-4).
- One E2E smoke captured at `tests/_artifacts/e2e-skillopt-self.md` (against a
  copy of `gbrain:skill-optimizer`, exit code 2).

## Safety

Never write a bundled `SKILL.md` — and since v2, skill-forge never writes
`SKILL.md` at all (see "v2 safety additions" above). Still copy to a scratch
dir (e.g. `C:\Temp\e2e-target\…`) and mutate the copy: the `is_bundled()`
guard depends on `~/.gbrain/install.json` existing, which it does not on every
host. See `docs/foundry.md` § 6.

## Heavy reference

See `docs/foundry.md`.
