# The good-skill guide — standards, practices, and how skill-forge holds itself to them

**The full detail behind the README's 5-minute version — and the ONE place
the standards are taught.**

## Which doc do I read?

| You want… | Read |
|---|---|
| the 8 standards, in full, with why-it-matters and practices | **this doc**, Part 1 |
| the 5 practices that keep a skill good | **this doc**, Part 2 |
| how skill-forge holds itself to its own standards | **this doc**, Part 3 |
| which of the 14 checks are automated and which are process | **this doc**, *The scoring sheet* |
| the rules the code actually enforces | [`PRINCIPLES.md`](PRINCIPLES.md) — the contract, cited by the validator |
| the source article's own ordering, and where every principle came from | [`SKILL_DESIGN_RUBRIC.md`](SKILL_DESIGN_RUBRIC.md) — the provenance lens |

Three documents used to teach this subject; a reader could not tell which
to open. This one is the entry point; the other two are now
specialised views of it.

---

## 🇺🇸 English

### ✨ Good skill standards

These are the eight principles distilled from the 2026-10-15 Perplexity audit
(`docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md`) and codified in
`docs/PRINCIPLES.md`. They are the rubric a good skill is judged against.
`validate_skill_frontmatter()` and `validate_skill_body()` automate checks
**1, 2, 3, and 8**; checks **4, 5, 6, and 7** are process / architectural
and require human review.

For each standard, the section below answers four questions:

- **What it means** — the rule in one sentence
- **Why it matters** — the failure mode it prevents
- **Practices** — concrete do/don't, with a good and a bad example
- **How to check** — what to look for, or which validator warning

#### 1. Description is a routing trigger, not a self-intro

**What it means:** The `description` field is the only thing every session pays for. It must be a routing phrase — start with `Use when…` or `Load when…`, ≤ 50 words, target user intent not workflow.

**Why it matters:** A vague or workflow-summary description makes the skill invisible to the resolver's short-circuit. The resolver falls through to embedding similarity, which is slower, less accurate, and easily hijacked by a sibling skill's description. The skill gets matched on the wrong intents or not at all.

**Practices:**

```yaml
# Good: routing phrase, user intent, 3 distinct intents, "Use when" prefix
description: >-
  Use when a skill is not producing the quality you want, when you want to
  bootstrap a benchmark for a new skill, or when retiring an old one.
triggers:
  - "improve this skill"
  - "audit skill quality"
  - "skill won't trigger"
```

```yaml
# Bad: workflow summary, no "Use when" prefix, no user intent
description: "A meta-skill for skill management"
```

- **Don't** duplicate the same phrases across `description`, `triggers:`, and `when_to_use:`. Pick one home for each phrase; duplication triples the cost without tripling match rate.
- **Don't** describe what the skill *does*; describe what the user is *trying* to do.
- **Don't** exceed 50 words. The 1024-char cap is the looser fallback; ≤ 50 words is the operational target.

**How to check:** `validate_skill_frontmatter` emits `description: should start with 'Use when' or 'Load when'` and `description: is N words, recommended ≤ 50` warnings.

#### 2. Skill is a folder, not a file

**What it means:** `SKILL.md` is the lean hub. `scripts/` `references/` `assets/` are the spokes, loaded on demand. The body itself stays under ~150 lines.

**Why it matters:** A single 1,000-line `SKILL.md` bloats every trigger's load cost. Per Perplexity, "Skills with a lot of fluff will almost certainly degrade other Skills as well as overall agentic capabilities." Splitting into hub-and-spoke means the agent loads only the heavy detail on demand, leaving context budget for the actual work.

**Practices:**

```
skill-name/
├── SKILL.md           # ~150 lines body, always loaded when triggered
├── scripts/           # code the agent runs (not "learns from")
├── references/        # heavy docs, loaded on demand
├── assets/            # templates, schemas, data tables
└── README.md          # human landing page (not loaded by the agent)
```

- **Move** heavy content to `references/` when the body grows past ~150 lines.
- **Use multi-level nesting** for very large skills: a 1,945-section tax code does not belong in a single `SKILL.md` — split by sub-skill (e.g. 300 topics → 20 domains → 15 subtopics → 1).
- **Don't** auto-load runtime files. The agent should choose when to read.

**How to check:** `validate_skill_body` emits `body: N lines (> 150); consider moving heavy content to references/ or assets/` when the body is over 150 lines and no `references/` or `assets/` directory exists.

#### 3. Gotchas are the highest-value content

**What it means:** The body must contain at least one gotcha-style section — `## Common Rationalizations`, `## Red Flags`, `## Anti-Patterns`, `## Pitfalls`, or `## When it fails`.

**Why it matters:** Without gotchas, a skill is a frozen snapshot. With gotchas, the skill is a living artifact that grows from observed failures. Per Perplexity, "Start with a thin body; grow only on observed failures." Gotchas ARE the observed failures, distilled into reusable rules.

**Practices:**

- **Source gotchas from real agent failures**, not from speculation. The flywheel is: agent fails → add gotcha → tighten description → re-run evals.
- **Write goals + constraints**, not command sequences. The agent knows the commands; it does not know your constraints.
- **Cross-link related gotchas.** "See also: Red Flags #3" lets a reader trace a symptom back to its underlying constraint.
- **Make each gotcha copy-pasteable** into the next skill's similar section. Generalize.

**How to check:** `validate_skill_body` regex against `##` headers: `## .*[Gg]otcha|[Pp]itfall|[Ff]lag|[Pp]attern|[Ff]ail|[Rr]ationaliz`. A body with no match emits `body: no gotcha-style section found`.

#### 4. Pascal test per sentence

**What it means:** For every sentence in the body, ask "would the agent fail without this instruction?" If no, the sentence is deleteable. Iron Laws are exempt.

**Why it matters:** Most "documentation" prose is the model explaining itself. "Without this instruction, would the agent fail?" is a fast filter. Saying "Use the file system" doesn't help — the model already knows. The cost of every retained sentence is paid by every session; the benefit must be a decision signal or a constraint, not a tutorial.

**Practices:**

- **Iron Laws** (the one bolded top-of-body sentence that overrides everything) are exempt. "Violating the letter of these rules is violating the spirit of these rules" is the kind of imperative override Perplexity's example table flags as Iron Law.
- **Verification checklist items** pass Pascal individually: "Each phase prints its verb on stdout" — agent fails without it (silent phases). Apply Pascal *within* each item, not to the checklist as a whole.
- **Reference navigation aids** (e.g. "see `docs/SKILL_REFERENCE.md`") do NOT pass Pascal — they're model convenience, not decision signals.
- **Default-behavior statements** ("run from `skill-forge/`") do NOT pass Pascal — the model knows how to run a script.
- **Self-intro sentences** ("It does X; it does Y; it does Z") often fail — the first sentence is the position statement; the rest is duplication.

**How to check:** Manual review per sentence. The audit report's `docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` § 2.3 shows a per-sentence Pascal audit on this very SKILL.md (846 → ~700 words achievable).

#### 5. Token budget: 100 / 5,000 / unlimited

**What it means:** Three tiers, each with its own cost and its own discipline:

| Tier | Content | Budget | When paid |
|---|---|---|---|
| **Index** | `name` + `description` | ~100 tokens/skill | Every session, every user, always |
| **Load** | full `SKILL.md` body | ~5,000 tokens (target) | When the skill is triggered |
| **Runtime** | files in `scripts/` `references/` `assets/` | unlimited | Only when the agent actually reads a file |

**Why it matters:** Mismatched tiers cause context bloat and recall degradation. An agent with 20 installed skills pays 20 × ~100 = ~2,000 tokens in index fees before doing any work. A skill with a 10,000-token body pays that cost every time it triggers, displacing other content from the active context.

**Practices:**

- **Index tier (≤ 100 tokens):** keep `name` + `description` short. Don't duplicate. Avoid workflow summaries.
- **Load tier (≤ 5,000 tokens):** keep body lean. Heavy detail → `references/`. The skill-forge gate is `wc -w SKILL.md ≤ 1000` (~1,300 tokens including frontmatter).
- **Runtime tier (lazy):** never auto-load. Let the agent choose. "Read all files in `assets/` before responding" defeats the lazy-loading contract.

**How to check:** `wc -w SKILL.md ≤ 1000` (skill-forge's gate). The per-tier author checklist lives in `references/token-budget.md`.

#### 6. Action at a distance

**What it means:** Changing one skill's `description` can break another skill's recall. Every `description` shifts the embedding space and the resolver's short-circuit matching.

**Why it matters:** A skill that worked yesterday may stop matching today because a sibling skill's description grew to claim overlapping intent. This is invisible at write time and only shows up as "the agent keeps loading the wrong skill" complaints.

**Practices:**

- **Keep descriptions short and unique.** Long descriptions have more claim surface; short ones have less.
- **Don't claim triggers another skill already claims.** A 5-word description with no overlap is more durable than a 50-word one with shared intent.
- **Re-run hero queries on neighbors** when you change `description` or `triggers:`. The eval rubric catches recall drift.
- **Track skill inventory** in a registry (even an informal one). MECE is a creation-time concern.

**How to check:** MECE / cross-skill registry. PRINCIPLES.md § 11 has the full mitigation table.

#### 7. Write evals first (hero queries)

**What it means:** Before shipping a skill, write a `references/hero-queries.md` with three kinds of queries: 5-10 positive (should match), 3-5 negative (should NOT match), 3-4 neighbor-confusion (could match, isn't).

**Why it matters:** Without an eval set, the resolver decides for you and you find out by user complaint. With an eval set, you have a canary: every `description` or `triggers:` change is testable in seconds. The eval set is also the input to the gotcha flywheel — a query that matches the wrong skill is a candidate gotcha for *that* skill's Red Flags.

**Practices:**

- **Positive queries** are real things the user might say. Each should target a distinct intent the skill covers.
- **Negative queries** are real things the user might say that should match *another* skill. They pin down what this skill is *not*.
- **Neighbor-confusion queries** are the dangerous middle ground — could match, but the better fit is a sibling skill. They surface at the resolver level, not the trigger level.
- **Re-run the eval set** after any `description` / `triggers:` / `when_to_use:` change. Add new queries whenever a user reports the wrong skill loaded.

**How to check:** `references/hero-queries.md` per skill. The skill-forge hero query set itself lives at `references/hero-queries.md` (10 positive, 5 negative, 4 neighbor-confusion).

#### 8. Skill dir name == frontmatter `name`

**What it means:** The directory IS the skill in the marketplace. `my-skill/SKILL.md` must declare `name: my-skill`.

**Why it matters:** A mismatch breaks marketplace lookup, confuses users ("which one is real?"), and silently breaks MECE checks. The marketplace indexes by directory; the resolver indexes by `name`. When they disagree, the resolver can match but the marketplace can't deliver.

**Practices:**

- **Always lowercase kebab-case:** `my-skill`, not `MySkill` or `my_skill`. Regex: `^[a-z0-9][a-z0-9-]*$`.
- **Set both at creation time** and keep them in sync. Renaming the directory means renaming the frontmatter; renaming the frontmatter means renaming the directory.
- **Don't add versioning to the directory name.** That's what `version:` is for.

**How to check:** `validate_skill_frontmatter(fm, skill_dir=...)` emits `dir is 'X' but frontmatter name is 'Y'` when they differ.

### Practices (the meta-process)

Standards describe what a good skill *looks like*; practices describe the process that *keeps it good*. The five below are the meta-habits that turn a static skill into a living artifact.

#### Practice 1: Run the gotcha flywheel

Without a process, gotchas stay frozen at v0.2.0. With the flywheel, they grow from observed failures:

| Symptom | Action |
|---|---|
| Agent fails at X | Add a gotcha for X in the target skill's Red Flags / Anti-Patterns |
| Agent loaded the wrong skill | Tighten the target skill's `description`, add negative evals |
| Agent should have loaded, didn't | Add keywords to `description`, add positive evals |
| System prompt changed | Check for skill conflicts or duplicates |
| New skill added | Re-run evals on existing skills (action at a distance) |

**How skill-forge implements it:** The `audit-report.md` template emits a **Suggested gotchas** section whenever the audit returns a non-trivial verdict (`prompt` / `routing` / `contract`). 1-2 curated, root-cause-specific suggestions, copy-pasteable into the target skill's Red Flags. Without this, the flywheel has no input.

#### Practice 2: Eval-driven iteration

The 6-phase pipeline IS eval-driven iteration. Each run produces a measurable delta:

- **Phase 0 (audit):** names the root cause (`prompt` / `routing` / `contract` / `missing` / `other`) with a confidence score.
- **Phase 2 (bootstrap):** generates a held-out benchmark of 15 rows by default.
- **Phase 4 (verify):** the deterministic + LLM rubric + spot-check gates produce a 0/1 verdict.
- **Phase 5 (materialize):** writes the candidate as `best.md` (or `proposed.md` for bundled), never overwrites the source.

The pipeline accepts only on a gate pass; refuses on a gate fail. No "I'll fix it later" allowed.

#### Practice 3: Safe-by-default materialization

`SKILL.md` is never overwritten by any code path. The materialize step writes a candidate to `best.md` (non-bundled accept) or `proposed.md` (bundled accept); the user diffs and merges manually. This is the safety story:

- A bad run cannot destroy a working skill.
- A bundled install is doubly protected (proposed.md only).
- The audit-report.md is the audit trail for every run.

The discipline: **write the candidate, let the human merge.** This is the same pattern that makes code review safer than direct push to main.

#### Practice 4: Concurrent-edit safety (SHA race check)

`.skill-forge-baseline.json` records the SHA of `SKILL.md` from the last successful run. The next run compares. If the file drifted (someone edited it manually between audit and materialize):

| Drifted? | Bundled? | Behaviour |
|---|---|---|
| yes | yes | `[FATAL]`, `return 3` (`EEXIT_RACE`), nothing written — refuses to overwrite the marketplace install |
| yes | no | `[WARN]`, run proceeds, `best.md` captures the new state |
| no | either | normal materialize |

Exit `3` is deliberately distinct from the refuse exit `2` so CI can tell a race refusal from a quality refusal. A `3` is a deployment signal, not a code signal.

#### Practice 5: Distinct exit codes

`0` accept · `2` refuse · `3` race. The three failure modes — accept, quality-refuse, race-refuse — get three distinct codes so CI can route them differently:

- `0` — accept. `audit-report.md` + `best.md`/`proposed.md` written; baseline updated.
- `2` — refuse. `audit-report.md` written with `verdict: refuse`; no candidate; no baseline update.
- `3` — race. `[FATAL]` on stderr, no writes, no baseline update. The bundled install is preserved.

The baseline is re-pinned **only** on accept: a refuse must not pin a SHA, or it would lock the skill out of future improvement.

### How skill-forge follows its own standards

A meta-skill is credible only if it passes its own bar. The table below is the dogfooding claim: every standard and every practice, with the specific file/line/component where skill-forge itself does the thing it prescribes.

| # | Standard / Practice | skill-forge's own implementation |
|---|---|---|
| 1 | Description is a routing trigger | `SKILL.md` line 4-8: 32 words, "Use when" prefix, 3 distinct intents; `triggers:` has 7 unique phrases, none duplicated in `description` or `when_to_use:` |
| 2 | Skill is a folder, not a file | `SKILL.md` (797 words, hub) + `scripts/` + `references/` + `docs/` + `tests/`; heavy detail in `docs/foundry-details.md` (loaded on demand, not on every invocation) |
| 3 | Gotchas are highest-value | Body has 4 gotcha-style sections: `## Common Rationalizations` (4 rows), `## Red Flags` (4 bullets), `## Verification` (5 items); plus `audit-report.md` "Suggested gotchas" that grows the flywheel |
| 4 | Pascal test per sentence | SKILL.md went 903 → 797 words by removing 4 Pascal-failing sentences; the audit report at `docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` § 2.3 shows the per-sentence review |
| 5 | Token budget 100/5000/unlimited | SKILL.md ~1,100 tokens (Load tier); `docs/foundry-overview.md` ~1,700 tokens (load on first trigger); `docs/foundry-details.md` ~5,200 tokens (load on troubleshoot); per-tier checklist at `references/token-budget.md` |
| 6 | Action at a distance | PRINCIPLES.md § 11 dedicated section; `references/hero-queries.md` includes a "Neighbor-confusion" table to catch false matches |
| 7 | Write evals first (hero queries) | `references/hero-queries.md`: 10 positive + 5 negative + 4 neighbor-confusion queries, maintained alongside the codebase |
| 8 | Skill dir name == frontmatter name | `skill-forge/` directory, `name: skill-forge` frontmatter; `validate_skill_frontmatter(skill_dir=...)` is the 3-line check that enforces it for other skills |
| P1 | Gotcha flywheel | `_SUGGESTED_GOTCHAS` mapping (curated, not generated); `audit-report.md` emits the section on non-trivial verdicts; 1-2 suggestions per root cause |
| P2 | Eval-driven iteration | The 6-phase pipeline IS the iteration loop: audit → bootstrap (15 rows held-out) → forward → verify (3 judges) → materialize |
| P3 | Safe-by-default materialization | `_materialize` writes `best.md` / `proposed.md`, never `SKILL.md`; bundled skills get `proposed.md` only; the v2 invariant "never overwritten" is documented in `docs/foundry-details.md` § 6 |
| P4 | Concurrent-edit safety | `.skill-forge-baseline.json` SHA race check; `scripts/_lib/baseline_log.py::race()`; exit `3` on bundled drift, `[WARN]` on non-bundled drift |
| P5 | Distinct exit codes | `0` accept · `2` refuse · `3` race; implemented in `run.py::main()`; the 3 codes are CI-routable |

The package is a working demonstration of every rule it enforces. A skill that runs through skill-forge emerges with all 8 standards verified, and the meta-skill itself passes the same bar.

---

### The scoring sheet — 14 rows: what is automatable, what is process

| # | Standard | Automated? | Where it should be enforced |
|---|---|---|---|
| 1 | Index tier ≤ ~100 tokens | **yes** | validator: measure `name`+`description` tokens |
| 2 | Description ≤ 50 words, "Load when"/"Use when", no trigger dump | **yes** | validator |
| 3 | No trigger duplication across description / triggers / when_to_use | **yes** | validator |
| 4 | Body ≤ ~5,000 tokens | **yes** | validator: token estimate, not `wc -w` |
| 5 | Body states read-conditions for attached files | **yes** (heuristic) | validator: require a "Read … if …" table |
| 6 | ≥ 1 gotcha / pitfalls section | **yes** | validator (exists) |
| 7 | Conditional content lives in `references/` | **yes** (heuristic) | validator: long body with no `references/` → warn |
| 8 | Pascal test per sentence | no | manual review |
| 9 | Hero queries with positives + negatives | no | process: `references/hero-queries.md` |
| 10 | Progressive-loading eval | no | process: benchmark must contain "read the file" tasks |
| 11 | Description change protocol (1-2 words + baseline) | no | process |
| 12 | Evals across model families | no | process |
| 13 | "5% edge case → reference, not skill" | no | creation-time gate |
| 14 | Multi-level nesting for huge domains | no | design guidance |

**Rows 1-7 are the automatable half — and they are the half that actually
governs token cost.** A validator that implements rows 1-7 catches the bloat
before it ships.

---

<a id="zh"></a>

## 🇨🇳 中文

### ✨ 好 skill 的 8 条标准

这 8 条标准是 2026-10-15 Perplexity 审计(`docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md`)后整理,并已写进 `docs/PRINCIPLES.md`。它们是判断一个 skill 是否合格的总分细则。`validate_skill_frontmatter()` 和 `validate_skill_body()` 把第 **1、2、3、8** 条自动化成检查;第 **4、5、6、7** 条是流程/架构层面的,需要人 review。

每条标准下都回答四个问题:

- **含义** — 一句话规则
- **为什么重要** — 它防住的失败模式
- **实践** — 具体的 do/don't,带好例和坏例
- **如何检查** — 看哪里,或哪条 validator 警告

#### 1. 描述是路由触发器,不是自我介绍

**含义:** `description` 字段是每个会话都会付费的唯一东西。它必须是路由短语 —— 以 `Use when…` 或 `Load when…` 开头,≤ 50 词,目标用户意图而非工作流。

**为什么重要:** 模糊的或工作流总结式的描述让 resolver 的短路匹配失效,只能回退到嵌入相似度 —— 更慢、更不准确、容易被邻居 skill 的 description 抢走。Skill 会被匹配到错误意图,或者根本不被匹配。

**实践:**

```yaml
# 好:路由短语,用户意图,3 个不同意图,"Use when" 前缀
description: >-
  Use when a skill is not producing the quality you want, when you want to
  bootstrap a benchmark for a new skill, or when retiring an old one.
triggers:
  - "improve this skill"
  - "audit skill quality"
  - "skill won't trigger"
```

```yaml
# 坏:工作流总结,没有 "Use when" 前缀,没有用户意图
description: "A meta-skill for skill management"
```

- **不要**在 `description`、`triggers:`、`when_to_use:` 三处重复同样的短语。每个短语只放一处;重复只会让成本翻三倍而不让匹配率翻三倍。
- **不要**描述 skill *做什么*;描述用户*想做什么*。
- **不要**超过 50 词。1024 字符是宽松的上限;≤ 50 词是操作目标。

**如何检查:** `validate_skill_frontmatter` 会输出 `description: should start with 'Use when' or 'Load when'` 和 `description: is N words, recommended ≤ 50` 警告。

#### 2. Skill 是文件夹,不是单文件

**含义:** `SKILL.md` 是精简的 hub。`scripts/` `references/` `assets/` 是 spoke,按需加载。正文本身保持在 ~150 行以内。

**为什么重要:** 单个 1,000 行的 `SKILL.md` 会让每次触发的加载成本膨胀。Perplexity 说"fluff 多的 skill 几乎肯定会拖累其他 skill 以及整体的 agentic 能力"。Hub-and-spoke 切分让 agent 只在需要时加载重内容,把上下文预算留给实际工作。

**实践:**

```
skill-name/
├── SKILL.md           # ~150 行正文,触发时总是加载
├── scripts/           # agent 跑的代码(不是"学到的")
├── references/        # 重文档,按需加载
├── assets/            # 模板、schema、数据表
└── README.md          # 人类落地页(agent 不加载)
```

- 当 body 长过 ~150 行,**把**重内容移到 `references/`。
- 对超大 skill 用**多层嵌套**:1,945 节的税法不该放在单个 `SKILL.md` 里 —— 按子 skill 切(300 主题 → 20 域 → 15 子主题 → 1)。
- **不要**自动加载 runtime 文件。让 agent 决定何时读。

**如何检查:** `validate_skill_body` 在 body 超 150 行且没有 `references/` 或 `assets/` 目录时,会输出 `body: N lines (> 150); consider moving heavy content to references/ or assets/`。

#### 3. Gotcha 是最高价值内容

**含义:** 正文必须至少包含一个 gotcha 风格小节 —— `## Common Rationalizations`、`## Red Flags`、`## Anti-Patterns`、`## Pitfalls`、`## When it fails` 之一。

**为什么重要:** 没有 gotcha,skill 就是冻在某个版本的快照。有了 gotcha,skill 是从观察到的失败中生长的活物。Perplexity 说"从薄正文开始,只在观察到的失败上长"。Gotcha 就是把观察到的失败蒸馏成可复用规则的结果。

**实践:**

- gotcha 的素材要**来自真实 agent 失败**,不是凭空想象。飞轮是:agent 失败 → 加 gotcha → 收紧 description → 重跑 evals。
- **写目标 + 约束**,不写命令序列。Agent 知道命令;它不知道你的约束。
- **互相交叉链接**相关 gotcha。"另见:Red Flags #3" 让读者能把症状追到底层约束。
- 让每条 gotcha 都**可以直接复制粘贴**到下一个 skill 的同类小节。要通用化。

**如何检查:** `validate_skill_body` 对 `##` 标题做正则:`## .*[Gg]otcha|[Pp]itfall|[Ff]lag|[Pp]attern|[Ff]ail|[Rr]ationaliz`。没匹配上的 body 会输出 `body: no gotcha-style section found`。

#### 4. Pascal 测试每句话

**含义:** 对正文里的每一句,问"没这句 agent 会不会失败?"不会,这一句就删。Iron Law 豁免。

**为什么重要:** 大部分"文档"散文是模型在解释自己。"没这句会不会失败"是个快筛。说"用文件系统"没用 —— 模型已经知道。每保留一句的代价是每个会话都付;收益必须是决策信号或约束,不是教程。

**实践:**

- **Iron Law**(顶部加粗的、覆盖一切的那一句)豁免。"Violating the letter of these rules is violating the spirit of these rules" 正是 Perplexity 范例表标为 Iron Law 的那种 imperative 覆盖。
- **验证 checklist 项**单独过 Pascal:"Each phase prints its verb on stdout" —— 没这句 agent 会失败(静默阶段)。Pascal 应用于**每项内部**,而不是整个 checklist。
- **引用导航提示**(比如"见 `docs/SKILL_REFERENCE.md`")**不**过 Pascal —— 是模型便利,不是决策信号。
- **默认行为陈述**("从 `skill-forge/` 运行")**不**过 Pascal —— 模型知道怎么跑脚本。
- **自我介绍句**("它做 X;做 Y;做 Z")通常过不了 —— 第一句是定位陈述,后面是重复。

**如何检查:** 手动逐句过 Pascal。审计报告 `docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` § 2.3 有对本文 SKILL.md 的逐句 Pascal 审计(846 → ~700 词可达成)。

#### 5. Token 预算:100 / 5,000 / 无限

**含义:** 三层,各层有自己的成本和自己的纪律:

| 层 | 内容 | 预算 | 何时付费 |
|---|---|---|---|
| **Index** | `name` + `description` | ~100 tokens/skill | 每个会话,每个用户,总是 |
| **Load** | 完整 SKILL.md 正文 | ~5,000 tokens(目标) | 触发 skill 时 |
| **Runtime** | `scripts/` `references/` `assets/` 里的文件 | 无限 | 只有当 agent 真的读这个文件时 |

**为什么重要:** 层错配会导致上下文膨胀和召回退化。一个装了 20 个 skill 的 agent 在做任何工作前就要付 20 × ~100 = ~2,000 tokens 的 index 费。一个 10,000 token 正文的 skill 每次触发都要付这笔成本,把其他内容挤出活动上下文。

**实践:**

- **Index 层(≤ 100 tokens):** `name` + `description` 保持简短。不要重复。避免工作流总结。
- **Load 层(≤ 5,000 tokens):** 正文保持精简。重细节 → `references/`。skill-forge 的闸门是 `wc -w SKILL.md ≤ 1000`(含 frontmatter 约 1,300 tokens)。
- **Runtime 层(惰性):** 永不自动加载。让 agent 选择。"先读 `assets/` 全部文件" 打破了惰性加载契约。

**如何检查:** `wc -w SKILL.md ≤ 1000`(skill-forge 自己的闸门)。逐层作者 checklist 见 `references/token-budget.md`。

#### 6. Action at a distance(远端作用)

**含义:** 改一个 skill 的 `description` 可能破坏另一个 skill 的召回。每个 description 都会动嵌入空间和 resolver 的短路匹配。

**为什么重要:** 昨天还工作的 skill 今天可能停止匹配,因为兄弟 skill 的 description 长出来抢占了重叠的意图。写时看不出来,只有"agent 老加载错 skill"的用户投诉才会暴露。

**实践:**

- **description 保持简短且唯一。** 长的有更多声明面;短的有更少。
- **不要抢占另一个 skill 已经声明的 trigger。** 5 词无重叠的 description 比 50 词有共享意图的更耐用。
- 改 `description` 或 `triggers:` 时,**对邻居 skill 重跑 hero queries**。eval 细则能抓住召回漂移。
- 把 skill 清单记在**注册表**里(哪怕非正式)。MECE 是创建期问题。

**如何检查:** MECE / 跨 skill 注册表。PRINCIPLES.md § 11 有完整的缓解表。

#### 7. 先写 evals(hero queries)

**含义:** ship 一个 skill 之前,先写一个 `references/hero-queries.md`,包含三种 query:5-10 正面(应匹配)、3-5 负面(不应匹配)、3-4 邻居混淆(可匹配但不是它)。

**为什么重要:** 没有 eval 集,resolver 替你决定,你只能从用户投诉里发现。有了 eval 集,你有个金丝雀:每次 `description` 或 `triggers:` 变更都秒级可测。eval 集也是 gotcha 飞轮的输入 —— 一个匹配错 skill 的 query 是*那个* skill 的 Red Flags 的候选 gotcha。

**实践:**

- **正面 query** 是用户实际可能说的。每个针对一个不同的意图。
- **负面 query** 是用户实际可能说但应匹配*另一个* skill 的。把"这个 skill 不是什么"钉死。
- **邻居混淆 query** 是危险的中间地带 —— 能匹配,但兄弟 skill 更合适。它们在 resolver 层(不是 trigger 层)浮出来。
- 改 `description` / `triggers:` / `when_to_use:` 之后**重跑 eval 集**。每当用户报"加载错 skill"就加新 query。

**如何检查:** 每个 skill 自己的 `references/hero-queries.md`。skill-forge 自己的 hero query 集在 `references/hero-queries.md`(10 正面、5 负面、4 邻居混淆)。

#### 8. 目录名 == frontmatter `name`

**含义:** 在 marketplace 里,目录就是 skill。`my-skill/SKILL.md` 必须声明 `name: my-skill`。

**为什么重要:** 不匹配会破坏 marketplace 查找,让用户困惑("哪个是真的"),悄悄破坏 MECE 检查。Marketplace 按目录索引;resolver 按 `name` 索引。它们不一致时,resolver 能匹配但 marketplace 送不出货。

**实践:**

- **永远小写 kebab-case:** `my-skill`,不是 `MySkill` 或 `my_skill`。正则:`^[a-z0-9][a-z0-9-]*$`。
- **创建时就两个都设好**并保持同步。重命名目录就要重命名 frontmatter;重命名 frontmatter 就要重命名目录。
- **不要在目录名里加版本号。** 那是 `version:` 字段的事。

**如何检查:** `validate_skill_frontmatter(fm, skill_dir=...)` 在两者不一致时输出 `dir is 'X' but frontmatter name is 'Y'`。

### 5 条实践(元流程)

标准描述好 skill *长什么样*;实践描述让 skill *保持好*的过程。下面五条是把静态 skill 变成活物的元习惯。

#### 实践 1: 跑 gotcha 飞轮

没过程,gotcha 永远冻在 v0.2.0。有了飞轮,gotcha 从观察到的失败里长:

| 症状 | 行动 |
|---|---|
| Agent 在 X 失败 | 在目标 skill 的 Red Flags / Anti-Patterns 加 X 的 gotcha |
| Agent 加载了错的 skill | 收紧目标 skill 的 `description`,加负面 evals |
| Agent 应该加载但没加载 | 在 `description` 加关键词,加正面 evals |
| 系统提示词变了 | 检查 skill 冲突或重复 |
| 新 skill 加了 | 对现有 skill 重跑 evals(action at a distance) |

**skill-forge 怎么实现:** `audit-report.md` 模板在 audit 返回非平凡 verdict(`prompt` / `routing` / `contract`)时输出 **Suggested gotchas** 章节。1-2 条针对该 root cause 的、精心写好的建议,可直接复制粘贴到目标 skill 的 Red Flags。没有这个,飞轮没输入。

#### 实践 2: Eval-driven iteration(评测驱动迭代)

6 阶段流水线本身就是评测驱动的迭代。每次运行产生一个可量化的 delta:

- **Phase 0(audit):** 命名根因(`prompt` / `routing` / `contract` / `missing` / `other`),带置信度。
- **Phase 2(bootstrap):** 生成默认 15 行的 holdout benchmark。
- **Phase 4(verify):** 确定性 + LLM 评分 + spot-check 三路闸门输出 0/1 verdict。
- **Phase 5(materialize):** 把候选写为 `best.md`(非 bundled)或 `proposed.md`(bundled),绝不覆盖源。

流水线只在闸门通过时接受;闸门失败时拒绝。不允许"我等下再修"。

#### 实践 3: 默认安全的物化

任何代码路径都不覆盖 `SKILL.md`。物化步骤把候选写到 `best.md`(非 bundled accept)或 `proposed.md`(bundled accept);用户 diff 完手动合并。这就是安全故事的本体:

- 一次坏的运行不能毁掉一个工作的 skill。
- bundled install 有双重保护(只写 `proposed.md`)。
- `audit-report.md` 是每次运行的审计轨迹。

纪律:**写候选,让人类合并。** 这跟"code review 比直接 push main 更安全"是同一种模式。

#### 实践 4: 并发编辑安全(SHA 竞态检查)

`.skill-forge-baseline.json` 记录上一次成功运行时 `SKILL.md` 的 SHA。下次运行比对。如果文件漂移了(有人在 audit 和 materialize 之间手改了):

| 漂移? | bundled? | 行为 |
|---|---|---|
| 是 | 是 | `[FATAL]`,`return 3`(`EEXIT_RACE`),什么都不写 —— 拒绝覆盖 marketplace install |
| 是 | 否 | `[WARN]`,继续运行,`best.md` 捕获新状态 |
| 否 | 任意 | 正常物化 |

Exit `3` 故意和拒绝 exit `2` 区分开,方便 CI 区分竞态拒绝和质量拒绝。`3` 是部署信号,不是代码信号。

#### 实践 5: 不同的退出码

`0` 接受 · `2` 拒绝 · `3` 竞态。三种失败模式 —— 接受、质量拒绝、竞态拒绝 —— 给三个不同的码,方便 CI 走不同分支:

- `0` — 接受。`audit-report.md` + `best.md`/`proposed.md` 已写;baseline 已更新。
- `2` — 拒绝。`audit-report.md` 写 `verdict: refuse`;不写候选;不更新 baseline。
- `3` — 竞态。stderr 写 `[FATAL]`,不写任何东西,不更新 baseline。bundled install 被保护。

Baseline **只在**接受时重新钉:拒绝不能钉 SHA,否则会把 skill 锁死,无法未来再改进。

### skill-forge 如何遵循自己的标准

元 skill 的可信度只能通过"自己达到自己的标准"来证明。下表就是 dogfooding 主张:每条标准 + 每条实践,都配上 skill-forge 自己落实这件事的具体文件/行/组件。

| # | 标准 / 实践 | skill-forge 自己的实现 |
|---|---|---|
| 1 | 描述是路由触发器 | `SKILL.md` 第 4-8 行:32 词,"Use when" 前缀,3 个不同意图;`triggers:` 7 个唯一短语,与 `description`、`when_to_use:` 无重复 |
| 2 | Skill 是文件夹 | `SKILL.md`(797 词,hub)+ `scripts/` + `references/` + `docs/` + `tests/`;重细节在 `docs/foundry-details.md`(按需加载,不是每次触发都加载) |
| 3 | Gotcha 是最高价值 | 正文有 4 个 gotcha 风格小节:`## Common Rationalizations`(4 行)、`## Red Flags`(4 项)、`## Verification`(5 项);外加 `audit-report.md` 的 "Suggested gotchas" 飞轮生长点 |
| 4 | Pascal 测试每句话 | SKILL.md 从 903 → 797 词,删了 4 句不过 Pascal 的;逐句审计见 `docs/AUDIT_2026-10-15_PERPLEXITY_PRINCIPLES.md` § 2.3 |
| 5 | Token 预算 100/5000/无限 | SKILL.md ~1,100 tokens(Load);`docs/foundry-overview.md` ~1,700 tokens(首次触发时加载);`docs/foundry-details.md` ~5,200 tokens(排错时加载);逐层 checklist 在 `references/token-budget.md` |
| 6 | Action at a distance | PRINCIPLES.md § 11 专章;`references/hero-queries.md` 包含"邻居混淆"表,用来抓错匹配 |
| 7 | 先写 evals(hero queries) | `references/hero-queries.md`:10 正面 + 5 负面 + 4 邻居混淆 query,跟代码一起维护 |
| 8 | 目录名 == frontmatter 名 | `skill-forge/` 目录,`name: skill-forge` frontmatter;`validate_skill_frontmatter(skill_dir=...)` 是 3 行检查,强制其他 skill 也满足 |
| P1 | Gotcha 飞轮 | `_SUGGESTED_GOTCHAS` 映射(curated,非生成);`audit-report.md` 在非平凡 verdict 时输出章节;每个 root cause 1-2 条建议 |
| P2 | 评测驱动迭代 | 6 阶段流水线本身就是迭代环:audit → bootstrap(15 行 holdout)→ forward → verify(3 判)→ materialize |
| P3 | 默认安全的物化 | `_materialize` 写 `best.md` / `proposed.md`,永不写 `SKILL.md`;bundled skill 只拿 `proposed.md`;v2 不变量"永不被覆盖"写在 `docs/foundry-details.md` § 6 |
| P4 | 并发编辑安全 | `.skill-forge-baseline.json` SHA 竞态检查;`scripts/_lib/baseline_log.py::race()`;bundled 漂移 → `exit 3`,非 bundled 漂移 → `[WARN]` |
| P5 | 不同的退出码 | `0` 接受 · `2` 拒绝 · `3` 竞态;在 `run.py::main()` 实现;3 个码都可被 CI 路由 |

这个包是它强制执行的每条规则的工作示例。一个跑过 skill-forge 的 skill 出来时 8 条标准都过检,而这个元 skill 自己也过同一道杠。

---

### 评分表 —— 14 行:哪些可自动化,哪些是流程

| # | 标准 | 可自动化? | 应该在哪被强制 |
|---|---|---|---|
| 1 | index 层 ≤ ~100 token | **是** | validator:量 `name`+`description` 的 token |
| 2 | description ≤ 50 词,`Load when`/`Use when` 开头,无 trigger 清单 | **是** | validator |
| 3 | description / triggers / when_to_use 三处无短语重复 | **是** | validator |
| 4 | 正文 ≤ ~5,000 token | **是** | validator:按 token 估,不是 `wc -w` |
| 5 | 正文给出附属文件的读取条件 | **是**(启发式) | validator:要求有 "Read … if …" 表 |
| 6 | ≥ 1 个 gotcha / pitfalls 小节 | **是** | validator(已实现) |
| 7 | 条件性内容放 `references/` | **是**(启发式) | validator:长正文无 `references/` → 报警 |
| 8 | Pascal 测试,逐句过 | 否 | 人工 review |
| 9 | hero query 含正例与负例 | 否 | 流程:`references/hero-queries.md` |
| 10 | 渐进式加载型 eval | 否 | 流程:benchmark 必须含"必须读那个文件"的任务 |
| 11 | description 改动协议(1-2 词 + 基线) | 否 | 流程 |
| 12 | 跨模型族跑 eval | 否 | 流程 |
| 13 | 「5% 边缘场景 → 做成 reference,不做 skill」 | 否 | 创建期闸门 |
| 14 | 超大领域用多层嵌套 | 否 | 设计指引 |

**第 1-7 行是可自动化的那一半 —— 也正是真正管住 token 成本的那一半。**
把第 1-7 行实现出来的 validator,能在 skill 出厂前就抓住膨胀。

---
