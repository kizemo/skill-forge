# skill-forge — foundry overview

Heavy reference for `skill-forge`. This file is the **load-on-first-trigger**
page; the detailed version lives in `foundry-details.md` (load only when
troubleshooting). If a flag's default here differs from `argparse` in
`scripts/run.py`, the code is authoritative and this file is the defect.

Related docs:

- `../README.md` — one-page pointer + quick start.
- `../SKILL.md` — the skill body itself (the artifact other agents load).
- `foundry-details.md` — phase details, gbrain soft-bind, triple-judge
  contract, bundled-skill safety model, v2 changelog.
- `../PRINCIPLES.md` — the rules this code is enforcing.
- `../references/hero-queries.md` — the eval set for this skill.
- `../references/token-budget.md` — the index/load/runtime tier table.

---

## 1. Install

```bash
cd F:/soft/00selfmade/skill-optimizer/skill-forge
pip install -e .
```

`pyproject.toml` declares `requires-python = ">=3.11"` and two runtime
dependencies: `pyyaml>=6.0` and `pytest>=8.0`.

Two ways to invoke, and **the working directory matters**:

```bash
# works: cwd is skill-forge/, so `scripts` is the local package
cd skill-forge && python -m scripts --skill <dir> --scope audit-only

# works after `pip install -e .`, from anywhere
skill-forge --skill <dir> --scope audit-only
```

### Run-location caveat (observed in the T8 E2E, not a ruling)

The brief's canonical command was `python -m scripts …` run from the **repo
root**. That fails with
`No module named scripts.__main__; 'scripts' is a package and cannot be
directly executed` — the repo root has no `scripts/` directory, so CPython
falls through `sys.path` and assembles a **namespace package** from two
unrelated dirs on this host
(`E:\Users\Duanyi\.claude\skills\book-to-skill\scripts` and
`C:\Python314\Lib\site-packages\win32\scripts`), neither of which carries
`__main__.py`. A host-path collision, not a skill-forge defect — but always
run from `skill-forge/`, or use the installed `skill-forge` entry point.

## 2. CLI flags

All flags live in `scripts/run.py::main()`. Defaults below are transcribed
verbatim from the `argparse` calls, not paraphrased.

| Flag | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `--skill` | `Path` | yes | — | Target skill directory (holds `SKILL.md`). |
| `--scope` | choice | yes | — | One of `create`, `improve`, `audit-only`, `retire`. |
| `--benchmark` | `Path` | no | `None` | Existing JSONL to reuse. `None` → Phase 2 generates one. |
| `--spot-check` | `int` | no | `0` | `0` → no spot-check (Phase 4 reports `spot=None`). Any other int wires `{"verdict": True}`. |
| `--held-out` | `int` | no | `None` | Number of held-out tasks, passed to Phase 2 as `n_tasks`. `None` → Phase 2's default of `15`. **Refuses with exit `2` when N < 5.** |
| `-h` / `--help` | flag | no | — | argparse help. `prog="skill-forge"`. |

Notes:

- `--scope` is **required**; there is no default and no interactive prompt.
  The skill body asks the human to pick the scope; the CLI does not.
- If `args.scope != report.recommend_scope` and `report.confidence >= 0.85`
  and `root_cause != "missing"`, a **warning to stderr** is printed:

  ```
  warning: requested scope 'audit-only' differs from recommended 'improve'
  ```

  It is advisory only — the run continues with the requested scope.
- Exit codes: `2` if `--held-out` is below `5` (with the `[FATAL]` line below
  on stderr) or if `--skill` does not exist; otherwise `0` if Phase 4
  accepted, `2` if it refused, and `3` if Phase 5 refused a bundled skill
  because `SKILL.md` drifted since the last run (race check, see
  `foundry-details.md` § 6).

The detailed gbrain-binding model, race-check semantics, and per-phase
internals live in `foundry-details.md`.

## 7. Reading the Phase 5 output

`_materialize()` writes `<skill_dir>/audit-report.md` on **every** run — a
~80-byte file. It also writes `best.md` (non-bundled accept) or `proposed.md`
(bundled accept) on accept; on refuse or race, only `audit-report.md`.

```markdown
# skill-forge audit

root_cause: routing
verdict: refuse
```

`root_cause` comes from `report.root_cause` (one of the five `RootCause`
values: `prompt`, `routing`, `contract`, `missing`, `other`); `verdict`
comes from `v.accept` (`accept` or `refuse`) and is the same boolean that
decides the process exit code. The pipeline writes **into the target skill
directory**, not into the skill's own repo — another reason to always run
against a copy.

`best.md` (or `proposed.md`) receives the candidate `SKILL.md` content
**verbatim** (accept). It is the "desired overwrite" target: the user
diffs `best.md` against `SKILL.md` and merges by hand. **`SKILL.md` is
never modified in place** — a bad run cannot destroy a working skill.

## 8. Failure mode catalog

Quick reference for common errors. The full backstories (sentinels /
RULINGs / corpus traces) are in `foundry-details.md` § 3, § 4, and § 6.

| Symptom | Meaning | Fix |
|---|---|---|
| `FrontmatterError: YAML parse error … mapping values are not allowed here` | `description:` carries inline YAML-structural punctuation and was authored as a plain scalar. | Re-author as a **block scalar** — `description: >-` or `|`. Single-quoting is **not** a valid fix: the standard trigger phrase `"skill won't trigger"` contains an apostrophe that terminates a single-quoted scalar. |
| `ModuleNotFoundError: No module named 'scripts.run'` | `skill-forge` is not on the import path. | `pip install -e .` from `skill-forge/`, or run from the `skill-forge/` directory so `python -m scripts` resolves the local package. |
| `No module named scripts.__main__; 'scripts' is a package and cannot be directly executed` | cwd has no `scripts/` dir; Python assembled a namespace package from unrelated `scripts/` dirs elsewhere on `sys.path`. | `cd skill-forge` first. Not a skill-forge defect. |
| Phase 3 reports `target=diagnose-only … degraded=True` and the message mentions "gbrain not installed" | `shutil.which("gbrain")` returned `None` and scope was not `create`. | Install gbrain, or accept the diagnose-only path — the documented soft-bind degrade. |
| `[ERROR] skill-creator init_skill.py not found at …`, shim exits `2` | Create-scope degrade, but the shim's target script is absent. | The shim resolves `skill-creator/scripts/init_skill.py` relative to the repo root; run from a checkout that contains `skill-creator/`. |
| Phase 3 marker absent / traceback out of `route()` | `gbrain` **present** but its subprocess threw (`TimeoutExpired`, `OSError`, `FileNotFoundError`). `route()` is unguarded by design. | Wrap the call site in `try/except (OSError, subprocess.SubprocessError)` returning `RouteResult("diagnose-only", 2, str(e), degraded=True)` — the pattern in `run.py`. If you call `route()` from anywhere else, supply your own guard. |
| `[phase 4] verify: det=False …` and `verdict: refuse` | The deterministic gate failed: no `Use when` prefix, missing/empty `name`, unparseable frontmatter, or `TODO`/`TBD` in the body. | Fix the SKILL.md. The intended refusal — v1 wires no LLM, so `det=False` is decisive. |
| `[phase 4] verify: det=True rubric-skipped spot=…` but `accept=False` | Deterministic passed, rubric skipped (expected), and the spot-check returned explicit `False`. | Re-run with `--spot-check 0` to drop the spot-check, or pass an accepting spot input. |
| `llm_score < 0.6` with a wired `llm_call` | The rubric ran and scored below threshold. Distinct from *skipped* — check `llm_call is None` at the call site, never `llm_score`. | Rewrite the candidate, or loosen the rubric prompt. |
| `--scope=retire` produces `target=diagnose-only … exit=0 degraded=True` | Expected, not a failure: retire never forwards. | None. |
| `warning: requested scope '…' differs from recommended '…'` | Advisory only; fires when confidence ≥ `0.85` and root cause is not `missing`. | Use the recommended scope, or ignore — the run continues with your choice. |
| `[FATAL] skill_dir SKILL.md has drifted since the last skill-forge run` and the process exits `3` | `.skill-forge-baseline.json` records a SHA that no longer matches the current `SKILL.md` (someone edited the file between runs) **and** the skill is bundled. | Re-run after reviewing your edit, or delete `<skill_dir>/.skill-forge-baseline.json` to re-baseline. Copy the bundled skill to a working dir first if you did not. |
| `[WARN] skill_dir SKILL.md has drifted since the last skill-forge run` and the process exits `0` | Same drift, but the skill is **not** bundled, so the forgiving path runs. | Advisory. Inspect `best.md` vs `SKILL.md` and merge manually. |
| `reason=bundled-skill-safety` in the `[phase 3]` marker | `is_bundled()` matched `skill_dir` against `~/.gbrain/install.json`; no subprocess was launched. | Expected on a marketplace install. Copy the skill to a working dir and re-run. Note: this will not fire on a host with no `install.json`. |

---

## Pointer

For phase internals, gbrain binding, the triple-judge contract, bundled-
skill safety, and the v2 changelog, see `foundry-details.md`. Load it only
when the overview doesn't answer your question.