# `gbrain skillopt` integration feedback — from the skill-forge maintainer

**Date:** 2026-10-24
**gbrain version tested:** 0.60.287.0 (0.60.400.0 / 0.60.421.0 available)
**Reporter:** skill-forge maintainer (`github.com/kizemo/skill-forge`)
**Upstream repo:** `github.com/garrytan/gbrain`

---

## TL;DR

> **中文摘要**
>
> 我在把 skill-forge 的 Phase 3(转发给 `gbrain skillopt`)做对的时候,踩到 7 个问题。其中**第 1 条最要紧**:`--skills-dir <path>` 这个 flag **真实可用、能让整条流水线跑通**,但它**在 `--help` 里一次都没出现**;而且当 skill 找不到时,`NoSkill` 错误信息**只提示 `gbrain skillify scaffold`**,完全不提 `--skills-dir` —— 而同族的"找不到 skills 目录"错误**提了**。一个只想优化自己 workspace 里某个 skill 的调用者,会被引导去全局 skills 树里创建一份。
>
> 另有一条:默认 `--split 4:1:5` 在 15 行的 benchmark 上会因 `D_sel < 5` 直接拒绝,而错误信息**不说最小行数要求**,也不告诉你 15 行该用 `1:1:1`。
>
> 第 3、4 条是文档/UX 层面的,第 5-7 条是行为契约需要澄清的地方。
>
> 下面每一条都带可复现命令和原样输出。**我没有改任何 gbrain 代码**,全部是 CLI 契约层面的反馈。

`gbrain skillopt` is a strong tool and most of it works well. This is a list of **discoverability, ergonomics, and contract-clarity** issues found while wiring it into a second skill-optimization pipeline. Every item has a reproduction and the exact output.

The headline: **`--skills-dir <path>` works, is not in `--help`, and is not mentioned by the error an integrator actually hits.** A caller who wants to optimize a skill in their own workspace is told to create that skill in the global tree instead.

---

## 0. Environment

| Item | Value |
|---|---|
| gbrain | 0.60.287.0 (`gbrain.exe`, Windows) |
| OS | Windows 11, `MSYS2/Git Bash` + `cmd` + `PowerShell` |
| Callers | `skill-forge` Phase 3 (`scripts/router.py`) — a Python CLI that shells out to `gbrain skillopt` |
| Brain mode | `GBRAIN_HOME` redirected to an isolated dir (PGLite, `--no-embedding`) |

---

## 1. `--skills-dir <path>` works but is completely undocumented

**This is the biggest issue.** It is the flag that makes `gbrain skillopt` usable by *any* tool that does not want to mutate the global skills tree — and it does not exist in the help output.

### 1.1 It is absent from `--help`

```bash
$ gbrain skillopt --help | grep -c -- "--skills-dir"
0
```

Zero occurrences. The full help has a `Required (one of):` group, a `Training knobs:` group, `Models:`, `Modes:`, `Safety:`, `Batch + fleet + background:`, `Exit codes:` and `Diagnostics:` — and no mention of where the skill is read from.

### 1.2 But it works, and it makes the whole pipeline run

```bash
$ mkdir -p /tmp/sf-sd/skills/probe
$ cp skill/SKILL.md /tmp/sf-sd/skills/probe/SKILL.md
$ gbrain skillopt probe \
    --skills-dir /tmp/sf-sd/skills \
    --benchmark /tmp/sf-sd/skillopt-benchmark.jsonl \
    --bootstrap-reviewed --split 1:1:1 --max-usd 5.00 --dry-run
```

```
[skillopt] cap: $5.00 (--max-usd; remove it with --max-usd off)
[skillopt] Models for probe:
[skillopt]   optimizer  anthropic:claude-opus-4-7  (built-in default) *
[skillopt]   target     anthropic:claude-sonnet-4-6  (built-in default) *
[skillopt]   judge      anthropic:claude-sonnet-4-6  (inactive: rule/qrels benchmark)
[skillopt]   expansion  anthropic:claude-haiku-4-5-20251001  (built-in default) *
[skillopt]   chat       anthropic:claude-sonnet-4-6  (built-in default) *
[skillopt]   embedding  (unresolved)  (unverified embedding identity (gbrain migrate embeddings --status)) *

[skillopt] Cost estimate for 4 epochs × 1 steps × 8 rollouts:
  Rollouts:   117 calls
  Reflects:   12 calls
  Judges:     0 calls
  Tokens:     ~447K in / ~112K out
  Est. cost:  $3.01 (cap: $5.00)
  Per call:   largest single call reserves $0.10 (optimizer anthropic:claude-opus-4-7, 4096 output tokens)
[skillopt] Dry run: no model calls made.
```

Full pipeline, cost estimate, model banner — all correct. The only problem is that nothing in `--help` says this flag exists.

### 1.3 The error an integrator hits never mentions it

Two different errors, two different levels of help:

**(A) No skills directory at all** — this one is helpful:

```
$ GBRAIN_SKILLS_DIR=/tmp/nonexistent gbrain skillopt probe --dry-run
gbrain skillopt: cannot find skills directory. Pass --skills-dir <path> or run from a workspace with a skills/ directory.
```

**(B) Skills directory found, but that skill is not in it** — this is the one an integrator hits, and it points somewhere else entirely:

```
$ gbrain skillopt probe --dry-run
gbrain skillopt: NoSkill: Cannot find SKILL.md for 'probe' at C:\Users\<user>\gbrain-latest\skills\probe\SKILL.md. (Create the skill first via 'gbrain skillify scaffold probe'.)
  hint: Create the skill first via 'gbrain skillify scaffold probe'.
```

The message says *"create the skill first"* and points at `gbrain-latest/skills/` — a source-checkout path on this host. A caller who already **has** the skill (in their own workspace, in a temp dir, in a CI checkout) is told to create a *second* copy in the global tree. The one flag that solves their actual problem (`--skills-dir`) is not in this message.

### 1.4 Requested

1. Document `--skills-dir <path>` in `--help` — ideally in the `Required (one of):` group, since it defines *where the skill comes from*, and add an `Examples:` line.
2. In the `NoSkill` error, add the same hint the sibling error carries:
   `Pass --skills-dir <path> or run from a workspace with a skills/ directory.`
3. Consider printing the resolved skills root in the `[skillopt]` banner, e.g. `skills dir: <resolved path>`. Right now the only way to learn where gbrain looked is to read the error message.

---

## 2. `GBRAIN_SKILLS_DIR` is honored but also undocumented

Setting it redirects the skills root:

```bash
$ GBRAIN_SKILLS_DIR=/tmp/sf-probe gbrain skillopt probe --dry-run
gbrain skillopt: cannot find skills directory. Pass --skills-dir <path> or run from a workspace with a skills/ directory.
```

(The message changed from `NoSkill` to "cannot find skills directory" — proof the env var redirected the lookup. The dir simply had no `skills/` subdir.)

**Requested:** document it next to `--skills-dir`, or state explicitly that only the flag is supported. An env var that silently changes resolution is worth pinning down, since a stale `GBRAIN_SKILLS_DIR` in a CI environment would redirect a run to the wrong tree with no warning.

---

## 3. Workspace auto-discovery works — but it is only mentioned in an error

Running from a directory that contains `skills/<name>/SKILL.md` is discovered automatically:

```bash
$ cd /tmp/sf-sd          # contains skills/probe/SKILL.md
$ gbrain skillopt probe --benchmark /tmp/sf-sd/skillopt-benchmark.jsonl \
    --bootstrap-reviewed --split 1:1:1 --max-usd 5.00 --dry-run
[skillopt] cap: $5.00 (--max-usd; remove it with --max-usd off)
[skillopt] Models for probe:
...
```

This is a nice ergonomic property. It is documented **only** inside the "cannot find skills directory" error string, never in `--help`.

**Requested:** add a line to the help, e.g. under a new `Skill resolution:` group:

```
Skill resolution:
  --skills-dir <path>   Directory containing <name>/SKILL.md. Default: the
                        nearest workspace with a skills/ directory, else the
                        installed gbrain skills tree. $GBRAIN_SKILLS_DIR
                        overrides the default.
```

---

## 4. The default `--split` refuses on a 15-row benchmark, and the error does not say why

`--split` defaults to `4:1:5` and the help says *"refuses if D_sel < 5"*. On a 15-row benchmark that default leaves the selection set below 5, so the run refuses:

```
$ gbrain skillopt meeting-prep --benchmark bench.jsonl --dry-run
```

With a 15-row benchmark, `4:1:5` yields a selection set of 1–2 rows. The documented recipe for a 15-task benchmark is `--split 1:1:1` (5 train / 5 sel / 5 test), but that appears only in the `Examples:` block, and only next to `--bootstrap-from-skill`.

Two concrete asks:

1. **State the minimum explicitly in the error.** When the split is refused, the message should name the required minimum and the fix, e.g.

   ```
   split 4:1:5 yields 1 selection row, but 5 are required.
   Use --split 1:1:1 (or a split whose selection share is >= 5/N), or a
   benchmark with more rows.
   ```

2. **Print the resolved split in the banner.** The `[skillopt] Models for probe:` banner shows models, tokens and cost but not the split. A caller debugging a refusal has to infer it.

For reference, gbrain's own 15-task recipe (`--bootstrap-from-skill` → `--bootstrap-reviewed --split 1:1:1`) is a good default to surface.

---

## 5. `--bootstrap-reviewed` vs `--benchmark <path>` — the sentinel contract is ambiguous

The help lists these separately:

```
Required (one of):
  --benchmark <path>            JSONL benchmark file
  --bootstrap-from-skill        ...
  --bootstrap-from-routing      ...
  --bootstrap-reviewed          Confirm bootstrap benchmark was hand-reviewed
```

But `--bootstrap-reviewed` is not in the "one of" group, and the `Examples:` show it paired with `--bootstrap-from-*`:

```
# Bootstrap benchmark from existing routing-eval, then review:
gbrain skillopt meeting-prep --bootstrap-from-routing
# After review (sentinel deleted), run the optimizer:
gbrain skillopt meeting-prep --bootstrap-reviewed
```

The `Examples:` text says *"review + strengthen the judges, **delete the sentinel line**"*. So the contract is: **the sentinel must be physically removed** and `--bootstrap-reviewed` is the human assertion that this happened.

What is not stated:

- Does `--bootstrap-reviewed` **validate** that the sentinel is gone, or is it an unchecked assertion?
- May `--bootstrap-reviewed` be combined with `--benchmark <path>`? (A caller with a hand-reviewed file naturally writes both — that combination is what I use, and it is accepted.)
- Is the sentinel *required* to be absent when `--bootstrap-reviewed` is passed, or only required to be absent when it is **not** passed?

**Requested:** document the three-state contract (sentinel present + no flag / sentinel present + flag / sentinel absent), and state whether the combination `--benchmark <path> --bootstrap-reviewed` is supported and what it means. If the flag is only an assertion, saying so is enough; if gbrain validates it, that validation is worth surfacing (it is a cheap guard against shipping an unreviewed benchmark).

---

## 6. `--models-strict` fires on built-in defaults, including during `--dry-run`

With the default configuration, five touchpoints are reported as *"not chosen by touchpoint-specific configuration"*:

```
models strict check: 5 active model touchpoint(s) were not chosen by touchpoint-specific configuration:
  optimizer  anthropic:claude-opus-4-7  (built-in default)
```

Two observations:

1. The `*` marker in the banner already flags these, and the strict check is doing its job — that part is good and clearly signposted.
2. **It fires during `--dry-run`**, where no model is called and no spend occurs. A caller using `--dry-run` to preview a plan will see a hard abort that has no cost implication, which is confusing: the preview tells you the run cannot proceed, without saying that the *reason* (unconfigured model provenance) is orthogonal to the preview.

**Requested:** either exempt `--dry-run` from the strict abort (still print the `*` markers), or state in the error that the strict check is about spend-provenance, not about the dry-run plan. The current text reads as if the dry run itself failed.

---

## 7. `gbrain agent run` is asynchronous, and the async job cannot run while a `gbrain serve` holds the brain

Not strictly a `skillopt` issue, but it blocks a natural integration path (using a second model as a reviewer):

```bash
$ gbrain agent run "Reply with exactly the number 0.42"
submitted: job 1 (subagent)
1
```

The reply is **not** on stdout — stdout carries `submitted: job <id>` and the job id. The actual answer has to be fetched separately with `gbrain agent logs <id>`. A caller wanting a synchronous single-shot LLM call has to implement submit-and-poll itself.

Additionally, with the real brain held by a live `gbrain serve`:

```
$ gbrain agent run "..."
Error [pglite_busy]: GBrain's local database is already open through `gbrain serve`
(MCP, PID 559988). Use the live serve's IPC/MCP tools or stop it before opening this PGLite datastore.
```

Redirecting `GBRAIN_HOME` to an isolated brain does work around the lock, but then the run has no access to the user's brain (memories, resolver rows, prior context) — so the "durable agent" value is largely lost.

**Requested:** consider a synchronous one-shot mode, e.g. `gbrain agent run --wait --print-result`, that blocks and prints the final text. It would make `gbrain agent` usable as a reviewer/judge primitive from other tools, and it would be a natural companion to `gbrain skillopt --dry-run`'s "no model calls, plan only" mode.

---

## 8. Things that work well (for the record)

So the list above is not read as "this tool is broken":

- **`--max-usd` is excellent.** It is echoed in the banner (`[skillopt] cap: $5.00`), it is enforced before spend, and the cost estimate is itemized down to "largest single call reserves $0.10". The preflight estimate (`$3.01 (cap: $5.00)`) is exactly what a caller needs to decide whether to proceed. This is the model for how safety flags should behave.
- **`--dry-run` is genuinely free.** "no model calls made" is stated plainly, and the models banner + cost estimate still come through, so a caller can budget before spending.
- **`--no-mutate` / `proposed.md` semantics are clear** and make the "never overwrite in place" property easy to adopt.
- **The exit-code contract is documented** (`0` / `1` / `2`) and distinguishable, which is what a CI integration needs.
- **The `hint:` line under `NoSkill`** is a good pattern — it is only that the hint points at the wrong remedy for the "skill lives elsewhere" case (see § 1.3).
- **The models banner with `*` markers** makes model provenance visible without forcing configuration. Good default.

---

## 9. Suggested patch sketch (non-normative)

For § 1–§ 3, the help text alone would close most of the gap:

```
Skill resolution:
  --skills-dir <path>   Directory that contains <name>/SKILL.md.
                        Default: nearest workspace with a skills/ directory,
                        else the installed gbrain skills tree.
                        Env: GBRAIN_SKILLS_DIR.

  Resolution order: --skills-dir > $GBRAIN_SKILLS_DIR > nearest workspace
  skills/ dir > installed skills tree.
```

and for the `NoSkill` error:

```
gbrain skillopt: NoSkill: Cannot find SKILL.md for '<name>' at <resolved-root>/skills/<name>/SKILL.md.
  hint: the skill was looked up in <resolved-root>/skills/.
        If your skill lives elsewhere, pass --skills-dir <path> (the directory
        that contains <name>/SKILL.md) or run from a workspace with a skills/
        directory. `gbrain skillify scaffold <name>` is only needed if you
        want to create a new skill in the global tree.
```

For § 4, the refusal message should name the minimum and the fix.

---

## 10. Reproducer

Everything above is reproducible with the following. `$SD` is any directory laid out as
`$SD/skills/<name>/SKILL.md` plus a 15-row JSONL benchmark at `$SD/bench.jsonl`.

```bash
GBRAIN_HOME=/tmp/iso-brain          # isolated brain (PGLite, no embedding)
export GBRAIN_HOME

# § 1.1 — flag absent from help
gbrain skillopt --help | grep -c -- "--skills-dir"     # -> 0

# § 1.2 — flag works
gbrain skillopt <name> --skills-dir "$SD/skills" \
    --benchmark "$SD/bench.jsonl" --bootstrap-reviewed \
    --split 1:1:1 --max-usd 5.00 --dry-run

# § 1.3(A) — helpful error
GBRAIN_SKILLS_DIR=/tmp/nonexistent gbrain skillopt <name> --dry-run
#   -> "cannot find skills directory. Pass --skills-dir <path> or run from a
#       workspace with a skills/ directory."

# § 1.3(B) — unhelpful error (no --skills-dir hint)
gbrain skillopt <name> --dry-run
#   -> "NoSkill: Cannot find SKILL.md for '<name>' at <root>/skills/<name>/SKILL.md.
#       (Create the skill first via 'gbrain skillify scaffold <name>')"

# § 2 — env var is honored
GBRAIN_SKILLS_DIR="$SD" gbrain skillopt <name> --dry-run   # -> resolves under $SD

# § 3 — workspace auto-discovery
cd "$SD" && gbrain skillopt <name> --benchmark "$SD/bench.jsonl" --dry-run

# § 4 — default split refuses
gbrain skillopt <name> --benchmark "$SD/bench.jsonl" --dry-run

# § 6 — strict check fires during dry-run
gbrain skillopt <name> --skills-dir "$SD/skills" --benchmark "$SD/bench.jsonl" \
    --models-strict --dry-run
```

---

## 11. What the submitter changed on their side

For reference, so it is clear which side each fix belongs to. The consuming tool
(`skill-forge`) now passes:

```
gbrain skillopt <name> \
    --skills-dir <dir containing <name>/SKILL.md> \
    --benchmark <skill_dir>/skillopt-benchmark.jsonl \
    --bootstrap-reviewed \
    --split 1:1:1 \
    --max-usd 5.00 \
    --dry-run
```

with `GBRAIN_HOME` pointed at an isolated brain so the run never touches the user's
real PGLite store. The consumer-side workarounds for § 1–§ 4 are contained in that
one command line; the underlying discoverability gaps are what this report is about.
