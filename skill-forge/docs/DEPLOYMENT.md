# Local deployment backup

This document is the source-of-truth record of how `skill-forge` is deployed on the local machine so that **cc-haha** (and any other Claude variant that scans `~/.claude/skills/`) can call it. If the junction or the installed package ever drifts, this file is what you re-apply from.

Last updated: **2026-10-16** (MiniMax Code deployment verified + test count refreshed).

---

## 0. Two-junction layout (v0.2.0)

`skill-forge` v2 lives in **two** parallel locations on disk, both pointing at the same v2 source:

| Path | What it is | Why |
|---|---|---|
| `C:\Users\Duanyi\.claude\skills\skill-forge\` (junction → `F:\soft\00selfmade\skill-optimizer\skill-forge\`) | User-scope skill — shown in cc-haha settings panel as a "技能" card | Discovered by filesystem enumeration of `~/.claude/skills/` |
| `C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-forge\` (junction → same target) | Marketplace-link skill — registered as `gbrain:skill-forge` | **Required for `@skill-forge` invocation in cc-haha** |

**Why both**: cc-haha's settings panel reads `~/.claude/skills/` (filesystem) but its `@-invoke` resolver reads the plugin registry (`enabledPlugins` + the marketplace plugin's `plugin/skills/`). The user-scope junction alone is enough to be *listed* in the settings but not enough to be *invoked* via `@skill-forge`. The marketplace-link junction closes the gap by making the skill appear under the already-enabled `gbrain` plugin.

Both junctions point to the same `F:\soft\00selfmade\skill-optimizer\skill-forge\` source, so editing the source updates both views simultaneously. The v0 `skill-optimizer` at the marketplace path is untouched (mtime `Oct 14 07:58`, unchanged from before this fix).

---

## 0b. MiniMax Code deployment (verified 2026-10-16)

MiniMax Code (the `minimax` runtime, `activeDataDir = E:\Users\Duanyi\.minimax\.minimax`) also
discovers `skill-forge`, through **no extra junction**: it scans the Claude compat surface
`~/.claude/skills/` in addition to its native `skills/` directory. The existing junction from §0
therefore already satisfies MiniMax Code.

**Verified state (2026-10-16, this machine):**

| Check | Result |
|---|---|
| `skill` tool load by name `skill-forge` | succeeds; reports `Location: files:///F:/soft/00selfmade/skill-optimizer/skill-forge/SKILL.md` (junction resolved to the F: source) |
| Catalog listing | `skill-forge` present in the skill catalog, auto-trigger + explicit `/skill-forge` both available |
| Junction target | `E:\Users\Duanyi\.claude\skills\skill-forge` → `F:\soft\00selfmade\skill-optimizer\skill-forge` (Junction / ReparsePoint) |
| Interpreter | `C:\Python314\python.exe` 3.14.6, `pyyaml` 6.0.2 |
| `gbrain` | `E:\Users\Duanyi\.claude\Cache\.bun\bin\gbrain.exe` 0.60.287.0 |
| `python -m pytest -q` | **147 passed** in 1.4s |
| `python -m scripts.run --skill . --scope audit-only` | rc=0, all 6 phase markers printed, `audit-report.md` + `best.md` written |

**Deliberately NOT done: a second copy under `.minimax/.minimax\skills\skill-forge`.**
The native skills directory already holds 40 skills and shares no names with `.claude/skills/`,
so a duplicate `skill-forge` entry there would introduce a name collision and ambiguous
resolution for zero functional gain — the Claude compat junction already resolves to the same
F: source. If you ever want the Claude compat surface removed, add the junction then:

```powershell
New-Item -ItemType Junction `
    -Path 'E:\Users\Duanyi\.minimax\.minimax\skills\skill-forge' `
    -Target 'F:\soft\00selfmade\skill-optimizer\skill-forge'
```

…and delete the `.claude` junction in the same step, never both.

### Known runtime condition (not a deployment defect) — MITIGATED as of 2026-10-24

Before the P0-1 pass, Phase 3 forwarded to `gbrain skillopt <dir> --dry-run
--bootstrap-reviewed` with no `--benchmark`, no `--split`, no `--max-usd`, and no
`GBRAIN_HOME` isolation. Two consequences, both now fixed:

1. gbrain had **no benchmark** to optimize against (its CLI makes one REQUIRED) and its
   default `--split 4:1:5` **refuses** at `D_sel < 5` on skill-forge's 15-row benchmark.
2. The child inherited the user's real `~/.gbrain`, so while a `gbrain serve` held the
   PGLite datastore, gbrain exited 1 with:

```
Error [pglite_busy]: GBrain's local database is already open through `gbrain serve`
(MCP, PID <n>). Use the live serve's IPC/MCP tools or stop it before opening this PGLite datastore.
```

The P0-1 fix isolates the child into its own `GBRAIN_HOME` (default
`<temp>/skill-forge-gbrain-home`, auto-initialised once with `gbrain init --pglite
--no-embedding`), so the forward no longer touches the locked PGLite at all. The live
`gbrain serve` keeps its lock and is never disturbed — which matters, because the error
text is explicit that the live holder's lock must never be removed.

Phase 3 now issues:

```
gbrain skillopt <name> --dry-run --bootstrap-reviewed \
    --benchmark <skill_dir>/skillopt-benchmark.jsonl \
    --split 1:1:1 --max-usd 5.00
```

with `GBRAIN_HOME` set to the isolated home. Override with `--split`, `--max-usd`,
`--gbrain-home`.

**Resolved 2026-10-24.** The blocker above was a *discoverability* problem, not a
capability gap: gbrain resolves `<skill-name>` as `<skills-dir>/<name>/SKILL.md`, and
`--skills-dir <path>` selects that root. The flag works (the whole pipeline runs with
it) but it appears **0 times** in `gbrain skillopt --help`, and the `NoSkill` error
points only at `gbrain skillify scaffold` — never at `--skills-dir`, while the sibling
"cannot find skills directory" error does mention it. Reported upstream in
`docs/GBRAIN_UPSTREAM_FEEDBACK_2026-10-24.md`.

Phase 3 now issues (skill-forge side):

```
gbrain skillopt <name> \
    --skills-dir <dir that contains <name>/SKILL.md> \
    --benchmark <skill_dir>/skillopt-benchmark.jsonl \
    --bootstrap-reviewed --split 1:1:1 --max-usd 5.00 --dry-run
```

`--skills-dir` defaults to the skill's parent directory; override with `--skills-dir`.
Verified end-to-end against the real gbrain: `[phase 3] forward: target=gbrain-skillopt
degraded=False exit=0` (was `exit=2` / NoSkill).

---

## 1. Deployment target

| Field | Value |
|---|---|
| **Discoverable path** | `C:\Users\Duanyi\.claude\skills\skill-forge\` |
| **Junction target** | `F:\soft\00selfmade\skill-optimizer\skill-forge\` |
| **Junction type** | Windows directory junction (`ReparsePoint`, no admin needed) |
| **Editable install** | `pip install -e .` already run; package `skill-forge-0.1.0` registered |
| **Entry point** | `skill-forge = "scripts.run:main"` (declared in `pyproject.toml`) |
| **Python** | `C:\Python314\python.exe` (3.14); `pyyaml` + `pytest` pulled by `pip install -e .` |
| **Bundled install (DO NOT TOUCH)** | `C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-optimizer\` — this is v0, kept for back-compat with any workflow that still points at the marketplace path |

## 2. How the deployment was made

```powershell
# 1. User-scope junction (settings panel):
New-Item -ItemType Junction `
    -Path 'C:\Users\Duanyi\.claude\skills\skill-forge' `
    -Target 'F:\soft\00selfmade\skill-optimizer\skill-forge'

# 2. Marketplace-link junction (cc-haha @-invoke):
New-Item -ItemType Junction `
    -Path 'C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-forge' `
    -Target 'C:\Users\Duanyi\.claude\skills\skill-forge'

# 3. Install the package + dependencies:
cd F:\soft\00selfmade\skill-optimizer\skill-forge
C:\Python314\python.exe -m pip install -e .
# → installs skill-forge-0.1.0, pyyaml>=6.0, pytest>=8.0

# 3. Smoke test:
C:\Python314\python.exe -m scripts.run --skill . --scope audit-only
# → all 6 phases print, rc=0
C:\Python314\python.exe -m pytest -q
# → 147 passed (2026-10-24, after the P0-1/P0-2 pass)
```

After step 1, the junction is transparent to Claude's skill discovery. The local repo at `F:\soft\00selfmade\skill-optimizer\skill-forge\` remains the single source of truth; edits there are immediately visible at `C:\Users\Duanyi\.claude\skills\skill-forge\`.

## 3. Re-deployment (idempotent)

If the junction is gone or the `pip install -e .` was wiped, run steps 1–2 above. Both are idempotent: `New-Item` errors on a pre-existing junction (so delete first if re-running), and `pip install -e .` re-resolves any drifted egg-info.

## 4. Why this exists (vs. the v0 marketplace install)

The v0 skill at `C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-optimizer\` is a 208-line prompt-only recipe — it tells the LLM what to do but ships no code. The v2 skill at `~/.claude/skills/skill-forge/` is a real Python package: 6-phase CLI, deterministic + LLM-rubric judge, bundled-skill safety, SHA-baseline race check, exit codes 0/2/3, and 147 tests. Both can coexist; cc-haha picks the one whose frontmatter description matches the user intent.

The marketplace v0 is intentionally not replaced. It serves workflows that want a pure-prompt recipe (no Python needed). The user-scope v2 serves workflows that want an executable, gated, auditable pipeline.

## 5. Verification (run after any re-deploy)

```bash
# Junction exists and points to the right target
powershell -NoProfile -Command "(Get-Item 'C:\Users\Duanyi\.claude\skills\skill-forge').Attributes"
# expect: Directory, ReparsePoint

# SKILL.md is accessible through the junction
ls C:\Users\Duanyi\.claude\skills\skill-forge\SKILL.md
# expect: a non-empty file

# Package is importable
python -c "import scripts._lib.frontmatter; print('ok')"
# expect: ok

# Full test suite
cd C:\Users\Duanyi\.claude\skills\skill-forge && python -m pytest -q
# expect: 147 passed

# End-to-end smoke
cd C:\Users\Duanyi\.claude\skills\skill-forge && python -m scripts.run --skill . --scope audit-only
# expect: 6 phase markers, rc=0
```

## 6. SKILL.md snapshot (as deployed)

The full content of `skill-forge/SKILL.md` is preserved here so that if the local junction breaks, the deployed text is still recoverable from the repo. The authoritative live version is at the junction; this snapshot is a freeze.

```markdown
---
name: skill-forge
version: 0.2.0
description: >-
  Use when a skill is not producing the quality you want, when you want to
  bootstrap a benchmark for a new skill, when an existing skill needs
  measurable improvement against a frozen baseline, or when retiring a
  skill that has outlived its purpose.
triggers:
  - "improve this skill"
  - "skill won't trigger"
  - "audit skill quality"
  - "fix skill underperformance"
  - "make a skill benchmark"
  - "retire old skill"
  - "skill produces shallow output"
tools:
  - bash
  - read
  - write
  - edit
  - grep
  - glob
mutating: true
brain_first: exempt
when_to_use: >-
  Use when the user asks: "improve this skill", "skill won't trigger",
  "audit skill quality", "fix skill underperformance", "make a skill benchmark",
  "retire old skill", or "skill produces shallow output".
---

# skill-forge

**Violating the letter of these rules is violating the spirit of these rules.**

## What this is

A meta-skill that turns "this skill could be better" into a measured,
verifiable improvement — or an honest decision to retire it. Routes work
to `skill-creator` / `gbrain:skill-optimizer`; uses a three-judge gate
before any change ships.

## When NOT to use

- You have not identified a specific failing skill and an observable symptom.
- "Improve" means you want to change taste or style, not quality.
- The skill already passes a deterministic trace + LLM rubric + spot check.

## Core Process

| Phase | Verb | What happens |
|---|---|---|
| 0 | audit | Static scan the target SKILL.md → root cause: prompt / routing / contract / missing / other |
| 1 | scope | You pick: create / improve / audit-only / retire |
| 2 | bootstrap | Generate 15 benchmark rows by default (RULING-7) — override with `--held-out N`; refuses if `N < 5` — plus sentinel |
| 3 | forward | `gbrain skillopt X --bootstrap-reviewed` (or `skill-creator/init_skill.py` shim for create) |
| 4 | verify | Deterministic trace + LLM rubric + spot check; absent rubric ≠ failure (RULING-1); any regression refuses |
| 5 | materialize | `audit-report.md` (always) + `best.md` (non-bundled accept) or `proposed.md` (bundled accept); bundled `SKILL.md` is never overwritten |

Bundled skills (one registered in `~/.gbrain/install.json`) get `proposed.md` only; the bundled `SKILL.md` is never touched.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Audit passed, must be ready to optimize" | Audit names root cause; optimizer still needs benchmark + judges. |
| "Rule judges are cheap, skip the LLM rubric" | Model can game rule judges by emitting the literal keywords. |
| "Triple judge is overkill, two is enough" | Three judges cover three failure modes: shape (deterministic), intent (rubric), acceptance (spot). Drop one, lose one. |
| "Skip Phase 5 to ship faster" | Materialize is what makes the run auditable. No materialize, no run. |

## Red Flags

- Phase 0 says "no benchmark" but Phase 1 chose improve.
- Deterministic trace 100% pass, LLM rubric 0% pass.
- best.md older than SKILL.md at end of Phase 5.
- gbrain missing → still tried to call `gbrain skillopt`.

## Verification

- [ ] `wc -w SKILL.md` ≤ 1000 (this file is the gate — heavy reference lives in `docs/SKILL_REFERENCE.md`, not here)
- [ ] Each phase prints its verb on stdout
- [ ] Bundled-skill runs emit `proposed.md`, not `SKILL.md`
- [ ] Triple-judge summary lists all three judges with scores
- [ ] `validate_skill_frontmatter()` returns `[]` (no principle violations in this SKILL.md) — see PRINCIPLES.md § 1

The v0 gate was 500 words; the v2 frontmatter layout lifts the natural size to 800-1000. Below 800 the SKILL.md is probably missing reference material; above 1000 it duplicates `docs/SKILL_REFERENCE.md`.

## v2 specifics (post v0.2.0)

- **Exit codes** — `0` accept · `2` refuse · `3` race (a bundled skill's `SKILL.md` SHA drifted between audit and materialize). Distinct codes for distinct failure modes so CI can route them differently.
- **Race check** — `.skill-forge-baseline.json` records the `SKILL.md` SHA from the last successful run. A drift on a bundled install refuses with exit `3`; a non-bundled drift warns and proceeds. `SKILL.md` is untouched either way.
- **Bundled-skill safety** — `is_bundled(skill_dir)` reads `~/.gbrain/install.json` and short-circuits the route phase for marketplace installs. **Fails open** if `install.json` is missing — copy the skill to a scratch dir before iterating.
- **`--held-out N`** — overrides the default 15-row benchmark; refuses with exit `2` when `N < 5` (gbrain hard-refuses <5 internally).
- **Triple-judge details** — `description` must be a YAML block scalar (RULING-5); YAML-list `description` refuses instead of raising; `baseline` is consumed in the rubric prompt so a real LLM call can compare candidate vs. baseline; rubric-skipped is invisible in `verdict.llm_score` — branch on `llm_call is None` at the call site, never on the verdict (RULING-8).
- **Skip optional deps gracefully** — without `pyyaml` the frontmatter loader raises; without `gbrain` the pipeline degrades to `diagnose-only.
```

(Snapshot regenerated from commit `24a92c0` on 2026-10-24, after the Perplexity audit pass (Pascal trim) and the P0-1/P0-2 router + rubric work. If `SKILL.md` in the repo changes, regenerate this snapshot by running `cat skill-forge/SKILL.md` and pasting the body into § 6 above.)

## 7. Git state at deployment time

| Field | Value |
|---|---|
| Local HEAD | `24a92c0` |
| `origin/main` | `24a92c0` (matches local) |
| Tag | `v0.2.0-rc1` (annotated, peels to `d765930`, the pre-SKILL.md-revision commit) |
| Total commits since v1 final `5a7c2dd` | 17 (12 v2 + 4 post-v2 hardening + 1 SKILL.md update) |
| Test count | 147 (was 58 at the v0.2.0 snapshot, 98 before the P0-1/P0-2 pass) |
| Word count of SKILL.md | 797 (within the ≤ 1000 gate; was 903 before the Pascal trim) |

## 8. What NOT to do

- **Do not** copy this `skill-forge/` directory anywhere else. The junction is the deployment; the repo is the source. If you need a separate copy, clone the GitHub repo, not the local path.
- **Do not** edit files inside `C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-optimizer\`. That is the v0 marketplace install and is read-only by v2 design.
- **Do not** `pip install` the package into a system location with `--break-system-packages` or similar. Use the same Python that `python -m scripts.run` already uses; the egg-info is at `skill-forge/skill_forge.egg-info/`, gitignored.
- **Do not** add secrets to the repo. `.skill-forge-baseline.json` is the only file the skill writes at runtime; it contains only SHA + ISO timestamp, no secrets.
