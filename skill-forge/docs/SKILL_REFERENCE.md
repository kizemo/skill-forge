# SKILL.md reference

Heavy reference material that complements `SKILL.md`. Per the progressive disclosure principle (PRINCIPLES.md § 3), `SKILL.md` body should stay lean (~150 lines, loadable in a single screen); anything that isn't on the hot path of an invocation lives here.

**When to read this file**: troubleshooting a specific failure, writing a new skill that should follow the same shape, or auditing a target skill that uses a similar pattern. Not on every skill invocation.

---

## Output Format

A successful `skill-forge` run produces a 6-phase transcript on stdout followed by two files on disk:

**On stdout (one line per phase):**

```
[phase 0] audit: root_cause=<routing|contract|prompt|missing|other> scope=<create|improve|audit-only|retire>
[phase 1] scope: user chose <scope>
[phase 2] bootstrap: benchmark=<path-to-jsonl>
[phase 3] forward: target=<gbrain-skillopt|skill-creator|diagnose-only> degraded=<True|False> exit=<0|1|2> reason=<...|—>
[phase 4] verify: det=<True|False> rubric=<rubric-skipped|llm=N.NN> spot=<None|True|False> accept=<True|False>
[phase 5] materialize: wrote <audit-report.md|best.md|proposed.md>
```

**On disk (in `--skill <dir>`):**

| File | When | Content |
|---|---|---|
| `audit-report.md` | always | `root_cause: ...`, `verdict: accept\|refuse` |
| `best.md` | accept + non-bundled | the candidate `SKILL.md` content, verbatim |
| `proposed.md` | accept + bundled | the candidate `SKILL.md` content, written next to the bundled `SKILL.md` (which is untouched) |
| `skillopt-benchmark.jsonl` | always | 15 templated benchmark rows (or `--held-out N`) + sentinel |
| `.skill-forge-baseline.json` | accept | the SHA of `SKILL.md` at the time of the run, plus ISO timestamp |

**Exit codes:** `0` accept · `2` refuse · `3` race (a bundled install's `SKILL.md` SHA drifted between audit and materialize). Distinct codes for distinct failure modes so CI can route them differently.

---

## Anti-Patterns

- **Skip Phase 5 to ship faster.** No materialize, no run. Materialize is what makes the run auditable.
- **Run against a bundled install directly.** The `is_bundled()` guard is defence-in-depth, not a lock. Always `cp -r <bundled> <scratch>` first.
- **Skip the MECE check against other skills.** This is a `skill-creator` concern, but `skill-forge` will fail loudly if a target skill has empty `triggers:` — that's the closest the audit comes to MECE.
- **Use `description: y` or any other 1-word description.** The skill resolver cannot match 1-word descriptions. Use a block scalar with a clear "Use when …" + concrete triggers (see PRINCIPLES.md § 1.1).
- **Skip the verification checklist.** Each item on the checklist is a contract with the user; skipping it loses the audit trail.
- **Add a `--dry-run` default.** skill-forge has no `--dry-run`. The output of every phase is already a report; running it produces an `audit-report.md` you can read instead of looking at the stdout transcript.
- **Read `verdict.llm_score` to decide accept/refuse.** Always branch on `llm_call is None` at the call site, never on the score (RULING-8 part 1).
- **Write the candidate to `SKILL.md` directly.** skill-forge writes to `best.md` (non-bundled) or `proposed.md` (bundled) and pins a SHA baseline. The user diffs and merges by hand. Direct `SKILL.md` overwrites lose the audit trail and silently clobber manual edits.
- **Invent a `RootCause` value the code can't produce.** RULING-10 dropped the dead `"env"` member; adding a new one is a contract violation by construction. The audit's `Literal` is the source of truth.

---

## When it fails

- **`rc == 2` (refuse)** — the deterministic trace caught a structural problem (e.g. `TODO` in body, missing frontmatter keys) OR `--held-out N<5` was passed. `audit-report.md` is written with `verdict: refuse`; the baseline is NOT updated; no candidate is written. Read the `evidence` list in the report — it lists the specific reason.
- **`rc == 3` (race)** — the SHA-baseline check detected a drift between audit and materialize on a bundled install. This is **not a code bug**; it means the user edited the bundled `SKILL.md` between runs. Re-copy the bundled skill to a scratch dir, re-run. The non-bundled path is more forgiving: it `[WARN]`-and-proceeds.
- **Phase 3 reports `degraded=True`** — `gbrain` is not on `PATH` (or it returned a non-zero exit). The pipeline still completes; the audit report is written; the candidate is NOT forwarded. To fix: install `gbrain` (https://github.com/garrytan/gbrain) or use `--scope create` (which forwards to `skill-creator/init_skill.py` instead).
- **`FrontmatterError` from `audit()`** — the `SKILL.md` has no `---` closer, or the YAML is malformed, or the parsed YAML is not a dict. Open the file and check the fence rule (RULING-3: first `---` after line 1 is the closer; later `---` lines are body content).
- **OSError reading `~/.gbrain/install.json`** — `is_bundled()` treats this as "not bundled" (fail-open, per Default Decision #2). The audit completes; the materialize writes `best.md`; the bundled `SKILL.md` is at risk. The fail-open is documented in `docs/DEPLOYMENT.md` § 1.
- **Frontmatter validation warnings in `audit-report.md` evidence** — `validate_skill_frontmatter()` runs as part of Phase 0 (PRINCIPLES.md § 1). Warnings about missing `triggers:`, `mutating:`, `brain_first:`, `when_to_use:`, or `version:` are non-fatal but indicate the target skill violates the 8 frontmatter principles. The materialize still runs; the author reviews the warnings.

---

## Tools Used

| Tool | How skill-forge uses it |
|---|---|
| `bash` | runs the 6-phase pipeline via `python -m scripts.run` |
| `read` | reads the target `SKILL.md` (and `docs/foundry.md` on-demand for the heavy reference) |
| `write` | writes `best.md` / `proposed.md` / `audit-report.md` (Phase 5 only; `SKILL.md` is never written) |
| `edit` | edits `~/.claude/skills/skill-forge/SKILL.md` for the local deployment (deployment-mode only) |
| `grep` | finds `does_not_exist` in `scripts/*.py` for the contract scan (Phase 0) |
| `glob` | enumerates `scripts/*.py` for the contract scan (Phase 0) |

The local deployment adds a `pip install -e .` step (run once) and a PowerShell junction from `~/.claude/skills/skill-forge/` to the package directory — see `docs/DEPLOYMENT.md` for the full recipe.

---

## Cross-references

- `docs/PRINCIPLES.md` — the 8 frontmatter principles + body principles this file references
- `docs/foundry.md` — heavy reference; ~670 lines, loaded only when troubleshooting
- `docs/DEPLOYMENT.md` — local Claude-skills deployment backup
- `docs/DEPLOYMENT.md` § 0 — the two-junction layout that makes `@skill-forge` callable from cc-haha
- `analysis-2026-10-14.md` — the v0 spec that started the project
