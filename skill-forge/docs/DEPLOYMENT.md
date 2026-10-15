# Local deployment backup

This document is the source-of-truth record of how `skill-forge` is deployed on the local machine so that **cc-haha** (and any other Claude variant that scans `~/.claude/skills/`) can call it. If the junction or the installed package ever drifts, this file is what you re-apply from.

Last updated: **2026-10-15** (v0.2.0-rc1 push to GitHub + cc-haha marketplace-link fix).

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
# → 58/58 passed
```

After step 1, the junction is transparent to Claude's skill discovery. The local repo at `F:\soft\00selfmade\skill-optimizer\skill-forge\` remains the single source of truth; edits there are immediately visible at `C:\Users\Duanyi\.claude\skills\skill-forge\`.

## 3. Re-deployment (idempotent)

If the junction is gone or the `pip install -e .` was wiped, run steps 1–2 above. Both are idempotent: `New-Item` errors on a pre-existing junction (so delete first if re-running), and `pip install -e .` re-resolves any drifted egg-info.

## 4. Why this exists (vs. the v0 marketplace install)

The v0 skill at `C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-optimizer\` is a 208-line prompt-only recipe — it tells the LLM what to do but ships no code. The v2 skill at `~/.claude/skills/skill-forge/` is a real Python package: 6-phase CLI, deterministic + LLM-rubric judge, bundled-skill safety, SHA-baseline race check, exit codes 0/2/3, and 58 tests. Both can coexist; cc-haha picks the one whose frontmatter description matches the user intent.

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
# expect: 58 passed

# End-to-end smoke
cd C:\Users\Duanyi\.claude\skills\skill-forge && python -m scripts.run --skill . --scope audit-only
# expect: 6 phase markers, rc=0
```

## 6. SKILL.md snapshot (as deployed)

The full content of `skill-forge/SKILL.md` is preserved here so that if the local junction breaks, the deployed text is still recoverable from the repo. The authoritative live version is at the junction; this snapshot is a freeze.

```markdown
---
name: skill-forge
description: >-
  Use when a skill is not producing the quality you want, when you want to
  bootstrap a benchmark for a new skill, when an existing skill needs
  measurable improvement against a frozen baseline, or when retiring a
  skill that has outlived its purpose. Triggers: "improve this skill",
  "skill won't trigger", "audit skill quality", "fix skill underperformance",
  "make a skill benchmark", "retire old skill", "skill produces shallow output".
mutating: true
brain_first: exempt
---

# skill-forge

**Violating the letter of these rules is violating the spirit of these rules.**

## What this is

A meta-skill that turns "this skill could be better" into a measured,
verifiable improvement — or an honest decision to retire it. It does not
edit skills directly; it routes work to `skill-creator` (create/edit) and
`gbrain:skill-optimizer` (SkillOpt-paper-driven optimization), and scores
the result with a three-judge gate before letting any change ship.

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

Default behavior: bare `python -m scripts.run` from the `skill-forge/` directory. Bundled skills (one registered in `~/.gbrain/install.json`) get `proposed.md` only; the bundled `SKILL.md` is never touched.

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

- [ ] `wc -w SKILL.md` ≤ 500 (this file is the gate)
- [ ] Each phase prints its verb on stdout
- [ ] Bundled-skill runs emit `proposed.md`, not `SKILL.md`
- [ ] Triple-judge summary lists all three judges with scores

## v2 specifics (post v0.2.0)

- **Exit codes** — `0` accept · `2` refuse · `3` race (a bundled skill's `SKILL.md` SHA drifted between audit and materialize). Distinct codes for distinct failure modes so CI can route them differently.
- **Race check** — `.skill-forge-baseline.json` records the `SKILL.md` SHA from the last successful run. A drift on a bundled install refuses with exit `3`; a non-bundled drift warns and proceeds. `SKILL.md` is untouched either way.
- **Bundled-skill safety** — `is_bundled(skill_dir)` reads `~/.gbrain/install.json` and short-circuits the route phase for marketplace installs. **Fails open** if `install.json` is missing — copy the skill to a scratch dir before iterating.
- **`--held-out N`** — overrides the default 15-row benchmark; refuses with exit `2` when `N < 5` (gbrain hard-refuses <5 internally).
- **Triple-judge details** — `description` must be a YAML block scalar (RULING-5); YAML-list `description` refuses instead of raising; `baseline` is consumed in the rubric prompt so a real LLM call can compare candidate vs. baseline; rubric-skipped is invisible in `verdict.llm_score` — branch on `llm_call is None` at the call site, never on the verdict (RULING-8).
- **Skip optional deps gracefully** — `pip install -e .` pulls `pyyaml`; without it the frontmatter loader raises `ImportError` instead of returning a partial result. The rest of the pipeline degrades to `diagnose-only` (no `gbrain` on PATH) or refuses on missing frontmatter (no `pyyaml`).
```

(Snapshot taken from commit `07d6cd9` on 2026-10-15. If `SKILL.md` in the repo changes, regenerate this snapshot by running `cat skill-forge/SKILL.md` and pasting the body into § 6 above.)

## 7. Git state at deployment time

| Field | Value |
|---|---|
| Local HEAD | `07d6cd9` |
| `origin/main` | `07d6cd9` (matches local) |
| Tag | `v0.2.0-rc1` (annotated, peels to `d765930`, the pre-SKILL.md-revision commit) |
| Total commits since v1 final `5a7c2dd` | 17 (12 v2 + 4 post-v2 hardening + 1 SKILL.md update) |
| Test count | 58 |
| Word count of SKILL.md | 486 (within the ≤ 500 gate) |

## 8. What NOT to do

- **Do not** copy this `skill-forge/` directory anywhere else. The junction is the deployment; the repo is the source. If you need a separate copy, clone the GitHub repo, not the local path.
- **Do not** edit files inside `C:\Users\Duanyi\.claude\plugins\marketplaces\gbrain\plugin\skills\skill-optimizer\`. That is the v0 marketplace install and is read-only by v2 design.
- **Do not** `pip install` the package into a system location with `--break-system-packages` or similar. Use the same Python that `python -m scripts.run` already uses; the egg-info is at `skill-forge/skill_forge.egg-info/`, gitignored.
- **Do not** add secrets to the repo. `.skill-forge-baseline.json` is the only file the skill writes at runtime; it contains only SHA + ISO timestamp, no secrets.
