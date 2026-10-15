# skill-forge — foundry reference

Heavy reference for `skill-forge`. The v1 sections describe the code as it
shipped at `66a7cf0` (one commit on top of v1-T7); sections and rows marked
**v2** describe the v2 hardening landed through `5b2ab23`. If a flag's
default here differs from `argparse` in `scripts/run.py`, the code is
authoritative and this file is the defect.

Related docs:

- `../README.md` — one-page pointer + quick start.
- `../SKILL.md` — the skill body itself (the artifact other agents load).
- `../tests/_artifacts/e2e-skillopt-self.md` — the captured E2E smoke run.
- `../../.superpowers/sdd/plans/2026-10-14-skill-forge/progress.md` — the v1
  ruling ledger (RULING-1 .. RULING-9, immutable).
- `../../.superpowers/sdd/plans/2026-10-15-skill-forge-v2/progress.md` — the
  v2 ruling ledger (RULING-6 corollary, RULING-9 v2 corollary, RULING-10).

**Ruling index.** Every ruling that constrains behaviour is cited below with
the commit that landed it:

| Ruling | Subject | Commit |
|---|---|---|
| RULING-1 | `judge()` skips the rubric when `llm_call is None` | `4fc95e2` |
| RULING-2 | T7 step-5 expected reason (`rc=0` path) corrected | `66a7cf0` |
| RULING-3 | frontmatter fence = first `---` after line 1; `__init__.py` added | `353686f` |
| RULING-4 | `pythonpath = ["."]` so bare `pytest -q` works | `5a7c2dd` |
| RULING-5 | `description:` must be a YAML block scalar (`>-`) | `14c4ac9` |
| RULING-6 | `audit()` precedence: contract scan before body-length | `9155b4e` |
| RULING-7 | `bootstrap()` cycles the template bucket to reach `n_tasks` | `fd86978` |
| RULING-8 | rubric-skipped is invisible in the verdict; `baseline` reserved (v1) / consumed by the rubric prompt (v2-T2, `3020cb2`) | `4fc95e2` |
| RULING-9 | `route()` subprocess is unguarded → wrap at the call site | `bec007e`, wrapped `66a7cf0` |
| RULING-6 corollary | `audit()` fixtures targeting `contract`/`prompt` must start `description` with `Use when` | `4e3c1b4` |
| RULING-9 v2 | Router invokes the shim with `sys.executable`; shim takes the skill dir via `SKILL_DIR` env or `argv[0]` | `072db5e` |
| RULING-9 v2 corollary | `{**os.environ, "SKILL_DIR": ...}` — the router's value outranks any ambient `SKILL_DIR` | `5b2ab23` |
| RULING-10 | The dead `env` `RootCause` member and `TEMPLATES` bucket are dropped (Option A) | `b31ec91` |

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
- Exit codes: `2` if `--held-out` is below `5` (with the `[FATAL]` line below on
  stderr) or if `--skill` does not exist (with
  `error: <dir> does not exist` on stderr); otherwise `0` if Phase 4 accepted,
  `2` if it refused, and — **v2 only** — `3` if Phase 5 refused a bundled
  skill because `SKILL.md` drifted since the last run (`EEXIT_RACE`, see § 6).
  Phase 3's subprocess exit code does **not** become the process exit code —
  see § 4.

**One new CLI flag landed in v2:** `--held-out N` (v2-T8). The other four rows
are unchanged from v1; the rest of the v2 work hardened what happens *under*
the existing flags (invocation, bundle detection, race detection, artifact
naming) rather than adding surface.

`--held-out` is a thin wrapper over Phase 2's existing `n_tasks` parameter
(`bootstrap_benchmark.bootstrap(..., n_tasks=15)`); the default of `15` is
preserved in both the function and the CLI, and only the call site changes.
gbrain hard-refuses a held-out count below `5` internally, so the CLI surfaces
the constraint up front instead of generating a benchmark the downstream call
would reject:

```
[FATAL] --held-out must be >= 5 (gbrain hard-refuses held-out <5 internally); got 3
```

The guard short-circuits **before** the `--skill` existence check and before
any phase runs, so no `audit-report.md`, no benchmark, and no baseline are
written on a refused `--held-out`. Its exit code is `2` — the existing refuse
code. Race stays `3` (Default Decision #3).

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
`Literal["prompt", "routing", "contract", "missing", "other"]` (**v2**, five
members — v1 declared a sixth, `"env"`, that no branch ever returned; see
§ 9 RULING-10).

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

Two known v1 limits:

- **RESOLVED in v2.** v1's `"env"` was a **dead** `RootCause` value — declared
  in the `Literal`, never returned by any branch. v2-T6 dropped the member and
  the matching `bootstrap_benchmark.TEMPLATES` bucket (RULING-10, Option A).
  Nothing that worked under v1 changes; only direct references to `"env"`
  break. External callers that round-trip an `"env"` root cause must add the
  classifier branch, the `Literal` member, the bucket, and the docs together —
  see § 9.
- **STILL TRUE.** The contract scan is a fixture-shaped substring heuristic
  (`does_not_exist` inside `scripts/*.py`), **not** an import resolver — do not
  read it as shipping general-purpose contract checking.

**Fixture precondition (RULING-6 corollary).** Because `routing` (step 3)
fires before `contract` (step 4) and `prompt` (step 5), **any fixture that
intends to exercise the `contract` or `prompt` branch must start `description`
with `Use when …`.** Without it, `routing` short-circuits first and the later
branches are unreachable — a test can look like it covers the body-length
heuristic while actually only re-testing `routing`.

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
   cmd = [sys.executable, str(Path(__file__).parent / "_legacy_init_skill.py"), skill_dir.name]
   env = {**os.environ, "SKILL_DIR": str(skill_dir.resolve())}
   ```

   **v2 (RULING-9 v2).** v1 invoked the shim with a bare `"python"`, which
   assumed a system Python on `PATH` and broke venv-only hosts; v2 uses
   `sys.executable` — the same interpreter running the router, therefore the
   same venv.

   `_legacy_init_skill.py` resolves `skill-creator/scripts/init_skill.py`
   relative to the repo (`Path(__file__).resolve().parent.parent.parent`) and
   invokes it as
   `[sys.executable, <init_skill.py>, <name>, "--path", str(skill_dir.resolve())]`.
   The skill dir comes from **`SKILL_DIR` in the environment** (preferred,
   cwd-agnostic) with `argv[0]` as the back-compat fallback; if neither is
   present the shim prints `[FATAL]` to stderr and returns `2`, never
   silently swallowing the input. If the target script is absent it prints a
   loud `[ERROR]` diagnostic to stderr and returns `2`.

   **Why `--path` is the resolved dir, not `Path.cwd()`.** v1 passed the
   shim's own cwd, so the shim targeted whatever directory the router
   happened to be launched from — the wrong-directory-with-no-signal bug
   class. v2 pins it to `str(skill_dir.resolve())` in both directions, and
   when both `SKILL_DIR` and `argv[0]` are set the **env value wins**
   (`os.environ.get("SKILL_DIR") or argv[0]`).

   **Why the env-merge order is `{**os.environ, "SKILL_DIR": ...}`**
   (RULING-9 v2 corollary). Python's `**` spread inside a dict literal is
   **last-wins**, so the opposite order
   (`{"SKILL_DIR": …, **os.environ}`) would let a stale ambient `SKILL_DIR`
   outrank the value the router just computed — the v1 wrong-directory bug
   class, back in disguise, with no signal (`route()` returns
   `degraded=True` either way). The `**os.environ` spread is nonetheless
   **load-bearing and must not be dropped**: `subprocess.run(..., env=...)`
   *replaces* the child's environment wholesale, so passing only
   `{"SKILL_DIR": …}` would strip `SystemRoot` / `COMSPEC` / `PATHEXT` /
   `TEMP` on Windows and break subprocess creation entirely. Only the order
   changed.

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

**Part 2 — `baseline: Path` was reserved in v1; v2 consumes it.**
In v1, `judge()` accepted `baseline` positionally and **never read it**: the
deterministic trace inspected `candidate` only, and the rubric prompt was
exactly `f"score {candidate}"` (verified at T5 review by capturing the prompt
string handed to an injected `llm_call`). Intentional v1 scope, not a defect.

**v2-T2 closed this.** The rubric prompt now carries both paths
(`f"score {candidate} (baseline={baseline})"`), so the comparison is built by
`judge()` rather than left to the caller's closure. Two limits remain and are
load-bearing:

- Closure is still at the **identifier** level — the prompt carries *paths*,
  not bodies. `Callable[[str], float]` declares no filesystem capability, so
  a real `llm_call` that needs the baseline's *content* must open the path
  itself.
- `run.py` hard-wires `llm_call = None`, so the rubric branch is currently
  **unreachable in production**. RULING-1 therefore still applies to every
  real run: the rubric is skipped, not failed.

Callers must still pass `baseline` through unchanged; the shipped pipeline
wires `baseline = candidate` as a placeholder (Phase 5 may separately re-pin
the SHA via the race check — see § 6).

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

## 6. Bundled-skill safety and the v2 file-state model

**NEVER write a bundled `SKILL.md`.** In v1 this was an operator discipline,
not a code invariant. In v2 it is (partly) enforced.

### What v1 did

Nothing read `~/.gbrain/install.json`. `_materialize()` wrote exactly one
artifact, `audit-report.md`, for every run. The T8 E2E was run against a
**fresh copy** at `C:\Temp\e2e-target\skill-optimizer\`, never against the
bundled install at
`E:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-optimizer\`.
Post-run verification confirmed the bundled directory's mtimes and contents
were unchanged, and that no `audit-report.md` was created there.

### What v2 added

**`scripts/_lib/bundle.py::is_bundled(skill_dir)` (v2-T4).** Reads
`~/.gbrain/install.json` and returns `True` iff the resolved `skill_dir`
appears among the recorded skill paths. It accepts two on-disk shapes — a
name→path dict, and `{"skills": [{"name":…, "path":…}]}` — and drops anything
it cannot parse.

Two properties callers rely on:

- **Fail-open.** A missing, unreadable, or malformed `install.json` yields
  `False` (not bundled) rather than raising or blocking. Fail-closed would
  block every v2 run on a host without a gbrain install. (v2 progress.md
  Default Decision #2.)
- **Never raises.** Guarded against `(OSError, ValueError, RuntimeError)`
  including the `Path.resolve()` symlink-loop class on Windows. Callers need
  no `try/except`.

`is_bundled()` is consulted in two places:

| Site | Effect when bundled |
|---|---|
| `router.py::route()` | Short-circuits **before any subprocess**: returns `diagnose-only`, `exit_code=0`, `degraded=True`, `reason="bundled-skill-safety"`. Neither `gbrain skillopt` nor the create-shim is invoked. |
| `run.py::main()` / `_materialize()` | Selects the `proposed.md` artifact instead of `best.md`, and arms the race check (below). |

**Read the `reason` field, not the message.** `RouteResult.stdout` is
diagnostic *prose* written for a human reading logs; `RouteResult.reason` is
the machine-readable discriminator. Note the prose names the target it
declined to forward to (`gbrain` or `skill-creator`) even for scopes that
would never have forwarded anyway — that is cosmetic, not a contract
violation. Branch on `reason == "bundled-skill-safety"`.

**`scripts/_lib/baseline_log.py` + the SHA race check (v2-T5).**
`<skill_dir>/.skill-forge-baseline.json` records `{"sha": <8-hex>, "ts": …}`
for the `SKILL.md` as it stood at the end of the last **successful** run. It
is written atomically (temp file in the same dir + `os.replace`); the
`.skill-forge-baseline.<rand>.tmp` intermediate is gitignored. `read_baseline`
/ `write_baseline` / `race` never raise — an unreadable baseline is treated as
"no prior run".

On accept, Phase 5 compares the recorded SHA against the current one
(`race(skill_dir, current_sha)`):

| Drifted? | Bundled? | Behaviour |
|---|---|---|
| yes | yes | `[FATAL]` on stderr, `return 3` (`EEXIT_RACE`), **nothing written** — no `proposed.md`, no `audit-report.md`. |
| yes | no | `[WARN]` on stderr, run **proceeds**: `best.md` captures the new state. |
| no | either | normal materialize. |
| no baseline on record | either | treated as first run — no drift. |

Exit `3` is deliberately distinct from the refuse exit `2` so CI can tell a
race refusal from a quality refusal. The baseline is re-pinned **only** on
accept: a refuse must not pin a SHA, or it would lock the skill out of future
improvement.

### The file-state model (v2 Default Decision #6)

| Artifact | Written when | Bundled? |
|---|---|---|
| `audit-report.md` | every run | yes — same content either way |
| `best.md` | accept, **non-bundled** only | no |
| `proposed.md` | accept, **bundled** only | yes |
| `.skill-forge-baseline.json` | accept only | yes |

The **target skill's own** `SKILL.md` is **never overwritten** by any path. That
is the safety-critical invariant; `best.md` / `proposed.md` are reviewable
artifacts that the user merges by hand.

**One caveat — a path that *creates* rather than overwrites.** `--scope create`
with no `gbrain` installed forwards to `skill-creator/scripts/init_skill.py`
via `_legacy_init_skill.py`. That script writes a template `SKILL.md` at
`<skill_dir>/<basename-of-skill_dir>/SKILL.md`, i.e. a *new* sibling directory
— and it refuses (returns `None`, non-zero exit) when that directory already
exists, so it can never clobber an existing skill. `route()` also
short-circuits bundled skills **before** the shim is invoked, so the bundled
install is unreachable from this path. The invariant is therefore "never
overwritten", not "never written anywhere".

### What "the caller's working copy" means

`proposed.md` and `audit-report.md` are written **into `skill_dir`**, and for
a bundled skill `skill_dir` **is** the bundled install. They are *not*
redirected to a scratch directory. The intended workflow is that the caller
copies the bundled skill to a working dir and points `--skill` at the copy:

```bash
cp -r ~/.claude/plugins/marketplaces/gbrain/plugin/skills/<name> C:/Temp/work/<name>
skill-forge --skill C:/Temp/work/<name> --scope improve
```

`is_bundled()` is a **safety net for the case where the caller forgot to
copy** — it catches the mistake, but it cannot undo artifacts already written
before the check. Copy first; treat the guard as the second line of defence.

### Known limitation — the guard is inert on this host

`~/.gbrain/install.json` **does not exist** on the machine this package was
developed on, and no producer for it was found under `~/.claude/plugins/` or
`~/.gbrain/`. A live check confirmed `is_bundled(<real bundled skill-optimizer
dir>)` returns `False`. So `reason == "bundled-skill-safety"` will **not**
fire here, even when `--skill` points straight at a marketplace install.

This is the state Default Decision #2 anticipated: fail-open was chosen so
that v2 could ship and be tested at all. Treat the bundled path as
**defence-in-depth, not an enforced invariant** on this host. A complementary
signal — e.g. "is `skill_dir` under `~/.claude/plugins/`?" — would close the
gap and is **open future work**; it is deliberately not in v2, because adding a
second bundled-detection heuristic is a behavioural change that needs its own
brief.

## 7. Reading the Phase 5 output

`_materialize()` writes `<skill_dir>/audit-report.md` on **every** run — a
61-byte file. In v1 this was the *only* file materialized; v2 adds `best.md`
(non-bundled accept) and `proposed.md` (bundled accept). See § 6 for the full
file-state model and the race-check interaction.

```markdown
# skill-forge audit

root_cause: routing
verdict: refuse
```

`root_cause` comes from `report.root_cause` (one of the five `RootCause`
values); `verdict` comes from `v.accept` (`accept` or `refuse`) and is the
same boolean that decides the process exit code. The pipeline writes **into
the target skill directory**, not into the skill's own repo — another reason
to always run against a copy.

`best.md` receives the candidate `SKILL.md` content **verbatim** (accept,
non-bundled). It is the "desired overwrite" target: the user diffs `best.md`
against `SKILL.md` and merges by hand. `SKILL.md` is never modified in place,
so a bad run cannot destroy a working skill.

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
| `[FATAL] skill_dir SKILL.md has drifted since the last skill-forge run` and the process exits `3` | **v2.** `.skill-forge-baseline.json` records a SHA that no longer matches the current `SKILL.md` — someone edited the file between runs — **and** the skill is bundled. | `EEXIT_RACE` is a deliberate refusal, not a bug (§ 6). Re-run after reviewing your edit, or delete `<skill_dir>/.skill-forge-baseline.json` to re-baseline. Copy the bundled skill to a working dir first if you did not. |
| `[WARN] skill_dir SKILL.md has drifted since the last skill-forge run` and the process exits `0` | **v2.** Same drift, but the skill is **not** bundled, so the forgiving path runs: `best.md` is written to capture the new state and `SKILL.md` is untouched. | Advisory. Inspect `best.md` vs `SKILL.md` and merge manually. |
| `reason=bundled-skill-safety` in the `[phase 3]` marker | **v2.** `is_bundled()` matched `skill_dir` against `~/.gbrain/install.json`; no subprocess was launched. | Expected on a marketplace install. Copy the skill to a working dir and re-run. Note this will not fire on a host with no `install.json` — see the known limitation in § 6. |

### Body-parsing invariant (v2)

**The body always comes from `body_of()`, which reuses the `load()` fence
rule.** Two consumers — `audit()`'s body-length branch and
`judge_triple._deterministic_trace()`'s `TODO`/`TBD` scan — read the same
`body_of(path)` helper instead of each slicing the raw text.

Why this matters: the old ad-hoc parser was `text.split("---", 2)[-1]`, which
splits on the **first `---` anywhere in the file**, including one embedded
mid-line inside a frontmatter block scalar. RULING-3 defines the closer as the
first `---` **alone on its own line** after line 1. The two disagreed, and the
disagreement was invisible until a skill happened to contain a `---`-like
line inside its `description`. Centralising on one helper means `audit()` and
`_deterministic_trace()` cannot drift apart again — it removes the
possibility rather than adding a test that would catch the next divergence.

### v2 backlog — what v1 parked, and what v2 closed

Every item v1 parked here is now landed. For the record:

| v1 backlog item | Closed by |
|---|---|
| Promote `baseline` from reserved to consumed (+ regression test on the prompt) | v2-T2 |
| Type-guard `description` in `_deterministic_trace` (a YAML-list `description` raised `AttributeError` instead of refusing — a gate should never raise) | v2-T2 |
| Have `frontmatter.load()` return `(fm, body)` or export a `body_of(path)` so `audit()` and `_deterministic_trace` cannot drift | v2-T1 — see the invariant above |
| Replace bare `"python"` with `sys.executable` in `router.py` and pass `--path str(skill_dir.resolve())` | v2-T3 |
| Enforce bundled-skill detection via `~/.gbrain/install.json` | v2-T4 — see § 6, **with the inertness caveat** |
| Resolve the dead `"env"` bucket | v2-T6 (RULING-10, Option A) |
| Produce `best.md` | v2-T5 |

### Still open (not v2)

- Wire a real `llm_call`. Until `run.py` stops hard-wiring `None`, the rubric
  branch is unreachable and every run is `rubric-skipped` (RULING-1).
- A held-out split (`--held-out N`, refusing `N < 5`) to measure improvement
  against data the judges have not seen. **Landed in v2-T8** — see § 2. What
  remains open is *using* the split (scoring held-out rows separately in the
  verify phase); the flag itself only sizes the Phase 2 benchmark.
- A complementary bundled-detection signal, so the guard is not dependent on
  `~/.gbrain/install.json` existing (§ 6).
- The contract scan is still a substring heuristic, not an import resolver.

## 9. v2 changelog

v2 was eight tasks (T1 parser → T2 judge → T3 router → T4 bundle → T5 race →
T6 env → T7 docs → T8 held-out) landing on the v1 HEAD, all on `main`. **All
eight have landed** (T1–T7 landed in v2-T7; T8 in v2-T8, which also closed the
v2-T7 reviewer's M-1 by recording T8 here). What changed, and the rulings that
pin it:

| Task | Change | Ruling |
|---|---|---|
| v2-T1 | `body_of()` helper; `audit()` and `_deterministic_trace()` share one fence rule | RULING-3 extended |
| v2-T2 | `baseline` promoted reserved → consumed (prompt carries both paths); `description` type-guard in the deterministic trace so a YAML-list value refuses instead of raising | RULING-8 part 2 |
| v2-T3 | Router uses `sys.executable`; shim takes the skill dir via `SKILL_DIR` env or `argv[0]`; `--path` is the resolved dir | RULING-9 v2 |
| v2-T4 | `is_bundled()` + the `bundled-skill-safety` refuse in `route()` | Default Decision #2 (fail-open) |
| v2-T5 | `.skill-forge-baseline.json` SHA race check; `best.md` (non-bundled) / `proposed.md` (bundled); exit `3` on a bundled race | Default Decisions #3, #6 |
| v2-T6 | The dead `env` `RootCause` member and its `TEMPLATES` bucket dropped | RULING-10 |
| v2-T7 | This file, `README.md`, `SKILL.md`, and the v1 plan-doc typo; env-merge order flip + 5 regression tests | RULING-9 v2 corollary, RULING-6 corollary |
| v2-T8 | `--held-out N` flag threaded into Phase 2's `n_tasks`; refuses with exit `2` before any phase runs when `N < 5`. Default `15` unchanged | Default Decision #3 (race stays `3`) |

**Rulings added in v2** (full text in the v2 ledger, linked at the top of this
file):

- **RULING-6 corollary** — an `audit()` fixture targeting the `contract` or
  `prompt` branch must start `description` with `Use when …`, because
  `routing` fires first. (See § 3.)
- **RULING-9 v2 corollary** — the env-merge order in `router.py` is
  `{**os.environ, "SKILL_DIR": …}`: the router's value outranks an ambient
  one, and `**os.environ` must stay load-bearing. (See § 4.)
- **RULING-10** — `env` is dropped from the `RootCause` contract. (See § 3.)

Two candidate rulings (the "briefs are reviewed for consistency" rule and the
`body_of` API rule) were deliberately **not** numbered: the first is a
process rule with no behavioural invariant, the second is enforced by the
code's shape and documented above as an invariant instead. Numbering them
would have created a second home for decisions that already have one — the
double-maintenance drift the ledger exists to prevent.
