# skill-forge — foundry reference

Heavy reference for `skill-forge` v0.1.0. This document is bound to the
as-shipped code at the commit that introduced it (one commit on top of
`66a7cf0`). If a flag's default here differs from `argparse` in
`scripts/run.py`, the code is authoritative and this file is the defect.

Related docs:

- `../README.md` — one-page pointer + quick start.
- `../SKILL.md` — the skill body itself (the artifact other agents load).
- `../tests/_artifacts/e2e-skillopt-self.md` — the captured E2E smoke run.
- `../../.superpowers/sdd/plans/2026-10-14-skill-forge/progress.md` — the
  authoritative ruling ledger (RULING-1 .. RULING-9).

**Ruling index.** Every ruling that constrains behaviour is cited below with
the commit that landed it:

| Ruling | Subject | Commit |
|---|---|---|
| RULING-1 | `judge()` skips the rubric when `llm_call is None` | `4fc95e2` |
| RULING-2 | T7 step-5 expected reason (`rc=0` path) corrected | `66a7cf0` |
| RULING-3 | frontmatter fence = first `---` after line 1; `__init__.py` added | `353686f` |
| RULING-4 | `pythonpath = ["."]` so bare `pytest -q` works | T8 (this commit) |
| RULING-5 | `description:` must be a YAML block scalar (`>-`) | `14c4ac9` |
| RULING-6 | `audit()` precedence: contract scan before body-length | `9155b4e` |
| RULING-7 | `bootstrap()` cycles the template bucket to reach `n_tasks` | `fd86978` |
| RULING-8 | rubric-skipped is invisible in the verdict; `baseline` reserved | `4fc95e2` |
| RULING-9 | `route()` subprocess is unguarded → wrap at the call site | `bec007e`, wrapped `66a7cf0` |

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
| `-h` / `--help` | flag | no | — | argparse help. `prog="skill-forge"`. |

Notes:

- `--scope` is **required**; there is no default and no interactive prompt in
  v1. The skill body asks the human to pick the scope; the CLI does not.
- If `args.scope != report.recommend_scope` and `report.confidence >= 0.85`
  and `root_cause != "missing"`, a **warning to stderr** is printed:

  ```
  warning: requested scope 'audit-only' differs from recommended 'improve'
  ```

  It is advisory only — the run continues with the requested scope. In the T8
  E2E this fired, because the bundled skill audits as `routing` (confidence
  `0.85`, recommends `improve`).
- Exit codes: `2` if `--skill` does not exist (with
  `error: <dir> does not exist` on stderr), otherwise `0` if Phase 4 accepted
  and `2` if it refused. Phase 3's subprocess exit code does **not** become
  the process exit code — see § 4.

## 3. The six phases

`run.py` defines `PHASES = ("audit", "scope", "bootstrap", "forward",
"verify", "materialize")` and emits one `[phase N] name: …` line per phase via
`_emit()`. Phases run unconditionally; there is no short-circuit.

| Phase | Verb | Module | Landed |
|---|---|---|---|
| 0 | audit | `scripts/audit.py` | `9155b4e` |
| 1 | scope | argparse (`--scope`) | `66a7cf0` |
| 2 | bootstrap | `scripts/bootstrap_benchmark.py` | `fd86978` |
| 3 | forward | `scripts/router.py` + shim | `bec007e`, wrap `66a7cf0` |
| 4 | verify | `scripts/judge_triple.py` | `4fc95e2` |
| 5 | materialize | `scripts/run.py::_materialize` | `66a7cf0` |

### Phase 0 — audit (`root_cause` classification)

`audit(skill_dir) -> AuditReport(root_cause, confidence, evidence,
recommend_scope)`. `RootCause` is
`Literal["prompt", "routing", "contract", "env", "missing", "other"]`.

**RULING-6 (`9155b4e`) fixes this precedence order.** Deterministic
structural defects outrank soft quality heuristics; the plan's original
ordering made its own contract test unsatisfiable, because a fixture with a
6-char body short-circuited into `prompt` before the contract scan ran.

1. `missing` — `SKILL.md` absent → confidence `1.0`, scope `create`.
2. `FrontmatterError` → `other`, confidence `0.5`, scope `audit-only`.
3. `routing` — description does not start with `Use when` → `0.85`, scope `improve`.
4. **`contract`** — any `scripts/*.py` containing the substring `does_not_exist` → `0.9`, scope `audit-only`.
5. `prompt` — body under 60 chars → `0.8`, scope `improve`.
6. `other` — nothing matched → `0.4`, scope `audit-only`.

The precedence rule, restated: **contract > prompt**. An unresolvable import
is true-or-false and actionable at a known file; body length is a proxy that
is frequently a *symptom* of an earlier break.

Two known v1 limits (parked for v2, from the T3 review): `"env"` is a **dead**
`RootCause` value — declared in the `Literal`, never returned by any branch
(tolerate it from external callers; Phase 0 never emits it). And the contract
scan is a fixture-shaped substring heuristic, **not** an import resolver — do
not read v1 as shipping general-purpose contract checking.

### Phase 2 — bootstrap (RULING-7, `fd86978`)

`bootstrap(skill_dir, report, n_tasks=15) -> Path` writes
`<skill_dir>/skillopt-benchmark.jsonl`. **The default is 15 data rows per
root cause, not 3.** Every bucket in `TEMPLATES` holds exactly 3 prompts, so
the plan's original `tasks[:n_tasks]` slice saturated at 3 for any
`n_tasks >= 3`, silently voiding the signature default. The binding
implementation cycles the bucket instead:

```python
for i, prompt in enumerate((tasks[k % len(tasks)] for k in range(n_tasks)), start=1):
```

Consequences to know: each bucket's 3 prompts recur 5× at the default, so
**duplicate `task` strings are expected v1 behaviour, not a bug**. The file is
sentinel-marked — its literal tail line is `# BOOTSTRAP_PENDING_REVIEW`,
meaning the benchmark is explicitly provisional pending human review and
later LLM authoring. Any future JSONL reader **must skip `#`-prefixed lines**;
a naive `json.loads` on every line crashes on the sentinel. `run.py` passes
the benchmark **path** through as `args.benchmark` and never parses the JSONL,
so that sentinel-tolerance obligation binds the first real consumer (v2 /
SkillOpt), not v1 code. Unknown root causes fall back to `TEMPLATES["other"]`
via `TEMPLATES.get(root_cause, TEMPLATES["other"])`.

### Sample output — the T8 E2E smoke

Verbatim from `../tests/_artifacts/e2e-skillopt-self.md` (run against a copy
of the bundled `gbrain:skill-optimizer`, exit code `2`):

```
[phase 0] audit: root_cause=routing scope=improve
warning: requested scope 'audit-only' differs from recommended 'improve'
[phase 1] scope: user chose audit-only
[phase 2] bootstrap: benchmark=C:\Temp\e2e-target\skill-optimizer\skillopt-benchmark.jsonl
[phase 3] forward: target=gbrain-skillopt degraded=False exit=1
[phase 4] verify: det=False rubric-skipped spot=None accept=False
[phase 5] materialize: wrote audit-report.md
```

The benchmark that run generated holds 15 data rows plus the sentinel (16
lines), confirming RULING-7's default at the default `n_tasks`.

## 4. gbrain soft-bind

Phase 3 forwards the work to a real optimizer when one is available, and
degrades gracefully when it is not. Detection is
`shutil.which("gbrain")` in `scripts/router.py::route()`.

### Three failure modes (RULING-9)

1. **`gbrain` absent + `scope=improve`** — falls through to a `diagnose-only`
   `RouteResult`, `exit_code=0`, `degraded=True`, with a message naming the
   install URL and where the audit was saved:

   ```
   gbrain not installed; install gbrain (https://github.com/garrytan/gbrain)
   to optimize this skill. Audit saved at <skill_dir>/audit-report.md
   ```

2. **`gbrain` absent + `scope=create`** — routes to the **`skill-creator`
   shim**, `degraded=True`:

   ```python
   cmd = ["python", str(Path(__file__).parent / "_legacy_init_skill.py"), skill_dir.name]
   ```

   `_legacy_init_skill.py` resolves `skill-creator/scripts/init_skill.py`
   relative to the repo (`Path(__file__).resolve().parent.parent.parent`) and
   invokes it as
   `[sys.executable, <init_skill.py>, <name>, "--path", str(Path.cwd())]`. If
   the target script is absent it prints a loud `[ERROR]` diagnostic to stderr
   and returns `2` — it never silently swallows the failure.

3. **`gbrain` present but the subprocess throws** — the case RULING-9
   (`bec007e`) was raised for. `route()` calls
   `subprocess.run(..., capture_output=True, timeout=120)` with **no
   `try/except`**, so `TimeoutExpired`, `OSError`, and `FileNotFoundError`
   propagate straight out of `route()` rather than degrading. The plan's
   degrade paths only ever covered "gbrain **absent**".

**The wrap (option 1), shipped in `run.py` at `66a7cf0`.** RULING-9 permitted
either wrapping the call site or explicitly recording that propagation is
accepted; T7 chose the wrap:

```python
try:
    rresult = route(skill_dir, args.scope, report)
except (OSError, subprocess.SubprocessError) as e:
    rresult = RouteResult("diagnose-only", 2, str(e), degraded=True)
```

This preserves the 6-phase / rc contract: a throwing forwarder still produces
all six markers, still writes `audit-report.md`, and still exits `0` or `2` on
Phase 4. It does **not** change `router.py` — `route()` itself is still
unguarded, so any other caller must supply its own guard.

### The Phase 3 `exit_code` is not the process exit code

The `exit=` value in the `[phase 3]` marker is **`r.returncode`** — the router's
own `subprocess.run` return code. It is *not* `main()`'s return and does
**not** propagate: a `gbrain skillopt` exiting `1` leaves the pipeline running,
and the process still exits `0` or `2` purely on Phase 4's `accept`. The T8
E2E shows both at once — `[phase 3] … exit=1` with process exit code `2` driven
by `accept=False`. Separately, `--scope=retire` never forwards at all:
`route()` returns
`RouteResult("diagnose-only", 0, "retire: no forwarding", degraded=True)`.

## 5. Triple-judge contract

`judge(candidate, baseline, report, *, llm_call=None, spot_input=None) ->
TripleVerdict(deterministic_pass, llm_score, spot_accepted, accept)` in
`scripts/judge_triple.py`. Three independent judges, per spec § 6.4
"三路并行": the **deterministic** trace `_deterministic_trace(candidate)`
(requires the file to parse as frontmatter — `FrontmatterError` → `False` —
`name` a non-empty string, `description` lowercasing to a `Use when` prefix,
and no `TODO`/`TBD` in the body); the **LLM rubric**
`max(0.0, min(1.0, llm_call(f"score {candidate}")))`, passing at `>= 0.6`; and
the **spot-check**, `None` when unwired or `bool(spot_input.get("verdict"))`,
where only an explicit `False` blocks acceptance.

`accept = det and rubric_pass and (spot is not False)`.

### RULING-1 (`4fc95e2`): absence skips the rubric, it is not a failure

When `llm_call is None`, the gate is **skipped**:

```python
if llm_call is None:
    llm_score = 0.0    # RULING-1: rubric absent → score 0, gate SKIPPED
    rubric_pass = True
```

Defaulting the score to a passive `0.5` would put absence *below* the `0.6`
threshold, making "no judge" indistinguishable from "the judge said no" —
contradicting the spec intent that absent ≠ refuse. The cost of getting this
backwards: honest local-only runs would exit `2` even when deterministic and
spot both pass.

### RULING-8 (`4fc95e2`): derive rubric state from the call site, never from the score

**Part 1 — branch on `llm_call is None` at the call site.**
`llm_score == 0.0` is **ambiguous**: it is what a skipped rubric returns, but
`max(0.0, …)` also clamps a real model's negative score to `0.0`. Verified
empirically at T5 review — an absent rubric on a deterministic-fail candidate
yields `(llm_score=0.0, accept=False)`, byte-identical to a real model
returning a non-positive score on a deterministic-pass candidate. Therefore
any Phase 4 marker, log line, or report field describing what the rubric did
**must** branch on whether `llm_call` was `None` **at the call site**, and must
**never** infer rubric state from `v.llm_score`. Do **not** add a
`rubric_skipped` field to `TripleVerdict` from a downstream task — that is a
signature change to a T5-approved public dataclass, and belongs in the v2
backlog. `run.py` does this correctly:

```python
llm_call = None
v = judge(candidate, baseline, report, llm_call=llm_call, spot_input=None if args.spot_check == 0 else {"verdict": True})
rubric = "rubric-skipped" if llm_call is None else f"llm={v.llm_score:.2f}"
```

**Part 2 — `baseline: Path` is reserved, not consumed.**
`judge()` accepts `baseline` positionally and **never reads it**: the
deterministic trace inspects `candidate` only, and the v1 rubric prompt is
exactly `f"score {candidate}"` (verified at T5 review by capturing the prompt
string handed to an injected `llm_call`). Intentional v1 scope, not a defect;
T5 was not re-dispatched to widen it. So any real `llm_call` you wire must
build the candidate-vs-baseline comparison **itself** — by closing over
`baseline` in the callable, or by reading the paths it is handed. Callers must
pass `baseline` through unchanged; v1 wires `baseline = candidate` as a
placeholder.

**Part 3 — `report: AuditReport` is type-only.**
`judge()` does not branch on `report.root_cause`; `report` is consumed only by
`isinstance(report, AuditReport)`. Do not add a redundant `report`-dependent
classifier in v1: RULING-6 fixes the `audit()` precedence on disk, and a
second classifier would re-derive the same order with no test backing.

### Injecting a real LLM call

```python
from pathlib import Path
from scripts.audit import audit
from scripts.judge_triple import judge

report = audit(Path("some-skill"))
candidate = Path("some-skill/SKILL.md")
baseline = Path("baseline/SKILL.md")   # reserved; judge() never reads it

# RULING-8: the prompt is exactly f"score {candidate}". Build any
# candidate-vs-baseline comparison here by closing over `baseline`.
v = judge(candidate, baseline, report, llm_call=lambda prompt: 0.82)
print(v.deterministic_pass, v.llm_score, v.spot_accepted, v.accept)
```

`TripleVerdict` exposes **only** the four fields listed above — there is no
`rubric_pass` field, precisely because of RULING-8 Part 1.

## 6. Bundled-skill safety

**NEVER write a bundled `SKILL.md`.** `proposed.md` is the only
forward-produced artifact name, and in v1 nothing writes it at all. The
router's create-fallback writes via the shim to
`skill-creator/scripts/init_skill.py`'s own target, **not** to a bundled
install.

The T8 E2E was run against a **fresh copy** at
`C:\Temp\e2e-target\skill-optimizer\`, never against the bundled install at
`E:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-optimizer\`.
Post-run verification confirmed the bundled directory's mtimes and contents
were unchanged, and that no `audit-report.md` was created there.

The code does **not yet enforce bundle detection** — nothing reads
`~/.gbrain/install.json` to refuse writing into a plugin install. That guard
is deferred to v2. Until then, bundle safety is an operator discipline, not a
code invariant: copy first, mutate the copy.

## 7. Reading `audit-report.md` (Phase 5 output)

`_materialize()` writes `<skill_dir>/audit-report.md` — a 61-byte file.
**In v1 this is the only file materialized.** There is no `best.md`:
producing a promoted-best artifact is v2 work.

```markdown
# skill-forge audit

root_cause: routing
verdict: refuse
```

`root_cause` comes from `report.root_cause` (one of the six `RootCause`
values); `verdict` comes from `v.accept` (`accept` or `refuse`) and is the
same boolean that decides the process exit code. The pipeline writes **into
the target skill directory**, not into the skill's own repo — another reason
to always run against a copy.

The pipeline writes **into the target skill directory**, not into the skill's
own repo — another reason to always run against a copy.

## 8. Failure mode catalog

| Symptom / error | Meaning | Fix |
|---|---|---|
| `FrontmatterError: YAML parse error: … mapping values are not allowed here` | The `description:` value carries inline YAML-structural punctuation and was authored as a plain scalar. | **RULING-5 (`14c4ac9`).** Re-author as a **block scalar** — `description: >-` (folded, strip chomping) or `|`. Single-quoting is **not** a valid fix: the standard trigger phrase `"skill won't trigger"` contains an apostrophe that terminates a single-quoted scalar. |
| `ModuleNotFoundError: No module named 'scripts.run'` | `skill-forge` is not on the import path. | `pip install -e .` from `skill-forge/`, or run from the `skill-forge/` directory so `python -m scripts` resolves the local package. See § 1 for the namespace-package collision when run from the repo root. |
| `No module named scripts.__main__; 'scripts' is a package and cannot be directly executed` | cwd has no `scripts/` dir, so Python assembled a namespace package from unrelated `scripts/` dirs elsewhere on `sys.path`. | `cd skill-forge` first. Not a skill-forge defect. |
| Phase 3 reports `target=diagnose-only … degraded=True` and the stdout mentions "gbrain not installed" | `shutil.which("gbrain")` returned `None` and scope was not `create`. | Install gbrain, or accept the diagnose-only path — it is the documented soft-bind degrade (RULING-9 mode 1). |
| `[ERROR] skill-creator init_skill.py not found at …`, shim exits `2` | Create-scope degrade, but the shim's target script is absent. | The shim resolves `skill-creator/scripts/init_skill.py` relative to the repo root; run from a checkout that contains `skill-creator/`. |
| Phase 3 marker absent / traceback out of `route()` | A third failure mode: `gbrain` **present** but its subprocess threw (`TimeoutExpired`, `OSError`, `FileNotFoundError`). `route()` is unguarded (RULING-9). | Wrap the call site in `try/except (OSError, subprocess.SubprocessError)` returning `RouteResult("diagnose-only", 2, str(e), degraded=True)` — the pattern in `run.py`. If you call `route()` from anywhere else, supply your own guard. |
| `[phase 4] verify: det=False …` and `verdict: refuse` | The deterministic gate failed: no `Use when` prefix, missing/empty `name`, unparseable frontmatter, or a `TODO`/`TBD` in the body. | Fix the SKILL.md. This is the intended refusal — v1 wires no LLM, so `det=False` is decisive. |
| `[phase 4] verify: det=True rubric-skipped spot=…` but `accept=False` | Deterministic passed, rubric skipped (expected), and the spot-check returned explicit `False`. | Re-run with `--spot-check 0` to drop the spot-check, or pass an accepting spot input. |
| `llm_score < 0.6` with a wired `llm_call` | The rubric ran and scored below threshold. Distinct from *skipped* — check `llm_call is None` at the call site, never `llm_score` (RULING-8). | Rewrite the candidate, or loosen the rubric prompt. |
| `--scope=retire` produces `target=diagnose-only … exit=0 degraded=True` | Expected, not a failure: retire never forwards. | None. |
| `warning: requested scope '…' differs from recommended '…'` | Advisory only; fires when confidence ≥ `0.85` and root cause is not `missing`. | Use the recommended scope, or ignore — the run continues with your choice. |
| Audit says `root_cause=prompt` for a skill whose `scripts/` import something undefined | The body-length branch ran first. Should not happen post-RULING-6. | Check that `audit.py` still has the contract scan above the body-length branch (`9155b4e`). |
| A `revision race`: the SHA recorded at audit time no longer matches the file | Not implemented in v1 — `scripts/_lib/sha.py::content_hash()` exists but no phase consumes it. | Deferred to v2. T1's sha helper is dead code in v1. |

### v2 backlog (parked, not load-bearing)

Promote `baseline` from reserved to consumed (+ a regression test asserting
the prompt contains baseline content); type-guard `description` in
`_deterministic_trace` (a YAML-list `description` currently raises
`AttributeError` instead of refusing — a gate should never raise); have
`frontmatter.load()` return `(fm, body)` or export a `body_of(path)` so
`audit()` and `_deterministic_trace` cannot drift (the same parser-drift class
RULING-3 kills); replace bare `"python"` with `sys.executable` in `router.py`
and pass `--path str(skill_dir.resolve())` so a real `subprocess.run` is
cwd-agnostic; enforce bundled-skill detection via `~/.gbrain/install.json`;
resolve the dead `"env"` bucket; produce `best.md`.
