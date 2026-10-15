# skill-forge

A meta-skill for auditing, creating, improving, and retiring other skills.
See `docs/foundry.md` for the heavy reference — quick start below.

## Phases (binding order, RULING-6: contract > prompt)

| Phase | Verb | Code | What happens |
|---|---|---|---|
| 0 | audit | `scripts/audit.py` | Classify root cause: prompt / routing / contract / env / missing / other |
| 1 | scope | (CLI `--scope`) | User picks: create / improve / audit-only / retire |
| 2 | bootstrap | `scripts/bootstrap_benchmark.py` | Generate 15 templated benchmark rows (RULING-7) + sentinel |
| 3 | forward | `scripts/router.py` | Call `gbrain skillopt` or `skill-creator/init_skill` shim; degrade with `RouteResult` (RULING-9) |
| 4 | verify | `scripts/judge_triple.py` | Deterministic + LLM rubric + spot check; RULING-1 llm_call=None → rubric skipped |
| 5 | materialize | `scripts/run.py::_materialize` | Write `audit-report.md`; accept or refuse |

## Rulings that shape this package

- **RULING-4** (`[tool.pytest.ini_options] pythonpath = ["."]` in `pyproject.toml`)
  — bare `pytest -q` now works from `skill-forge/`.
- **RULING-1** — `llm_call=None` SKIPS the LLM rubric. Absent ≠ failure.
- **RULING-6** — `audit()` precedence is `missing → other(frontmatter) → routing → contract → prompt → other`.
- **RULING-7** — `bootstrap()` emits 15 rows by default, sentinel `# BOOTSTRAP_PENDING_REVIEW`.
- **RULING-8** — rubric-skipped is invisible in the verdict; branch on `llm_call is None` at the call site, never on `v.llm_score`.
- **RULING-9** — `route()`'s subprocess is unguarded; `run.py` wraps it (option 1).

## Quick start

```bash
pip install -e .
python -m scripts --skill /path/to/target-skill --scope audit-only
```

Run from `skill-forge/` (see `docs/foundry.md` § 1 — running from the repo root
picks up a stray `scripts` namespace package and fails).

## Verification

- 24 tests pass via `cd skill-forge && pytest -q` (bare invocation, RULING-4).
- One E2E smoke captured at `tests/_artifacts/e2e-skillopt-self.md` (against a
  copy of `gbrain:skill-optimizer`, exit code 2).

## Safety

Never write a bundled `SKILL.md`. Always copy to a scratch dir (e.g.
`C:\Temp\e2e-target\…`) and mutate the copy — the code does not yet enforce
bundle detection. See `docs/foundry.md` § 6.

## Heavy reference

See `docs/foundry.md`.
