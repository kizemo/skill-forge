# 决策:继续用 skill-forge,还是换成 Anthropic 的 skill-creator?

**日期:** 2026-10-25 · **给:** skill-forge 的维护者 · **来源:** token 效率审计引发的战略自查

---

## 结论

**不放弃。但必须承认:两边有一块功能重叠,而 skill-forge 在那块上做得更差 —— 评测/benchmark 机制。**

正确动作不是二选一,是**把 Anthropic 的评测骨架搬进 skill-forge,保留 skill-forge 独有的三样东西**。

理由一句话:**两者做的是流水线的一半。** Anthropic skill-creator 负责「**写**」,skill-forge 负责「**审 + 判 + 安全落地**」。你需要的正好是后者,但你借来的评测工具应该用前者的。

---

## 1. 两者实际是什么

| | **Anthropic `skill-creator`** | **skill-forge** |
|---|---|---|
| 形态 | 提示词 + 脚本 + subagent 目录 | 独立 CLI,6 阶段流水线 |
| 入口 | agent 读 SKILL.md 后照着做 | `python -m scripts.run --skill <dir> --scope <s>` |
| 结构 | SKILL.md + `agents/grader.md` + `references/schemas.md` + `scripts/` | SKILL.md + `scripts/` + `references/` + `docs/` |
| 元数据 | **name + description,两个字段,~100 words** | name + description + `triggers:` + `when_to_use:`(+ tools/mutating/brain_first/version) |
| 正文上限 | **< 500 lines** | `wc -w ≤ 1000` |
| 接近上限时 | **加一层 hierarchy + 明确指针** | 无此规定 |
| 参考文件 | **> 300 lines 要加目录** | 无此约定 |
| 判定机制 | grader subagent 按 **assertions** 逐条评 | 确定性 + LLM rubric + spot-check 三路 |
| A/B 基线 | **同 turn 并发跑 with-skill 与 baseline**,baseline = 改动前的快照 | **`baseline = candidate`(占位符!)** |
| 成本度量 | 记录 **`total_tokens`** → `timing.json`;`benchmark.json` 输出 **pass_rate / time / tokens**,mean ± stddev + delta | **无 token 轴** |
| 根因诊断 | 无(只知失败,不知为何) | **prompt / routing / contract / missing / other + confidence + 类型化 recommend_scope** |
| 安全 | 编辑前手动 `cp -r` 快照 | **bundled 只读(proposed.md)/ SHA 竞态(exit 3)/ 绝不覆盖 SKILL.md / 退出码 0-2-3** |
| 规范载体 | agentskills.io/specification(短) | **PRINCIPLES.md 12 节 + 可自动化的 validator** |
| 成熟度语义 | — | **RULING-1:absent ≠ failure**(基础设施缺失不等于质量判负) |

---

## 2. skill-forge 真正的短板(3 条,按严重度)

### ① `baseline = candidate` —— 这是个 bug,不是 gap

`scripts/run.py` 里:

```python
candidate = skill_dir / "SKILL.md"
baseline = candidate   # ← 占位符
```

**基线和候选是同一个文件。** 也就是说 Phase 4 的 rubric 判分器在拿候选跟它自己比 —— 分数必然是"没有变化",而 Phase 5 的 `best.md` 也没有对照物。

Anthropic 的做法:改动前 `cp -r <skill-path> <workspace>/skill-snapshot/`,把 baseline subagent 指向那个快照,**同 turn 并发**跑两组。

**这是 skill-forge 目前最要命的缺陷** —— 一个"优化器"没有真正的 before/after。修它之前,任何 "pass_rate 提升了" 的说法都没有证据支撑。

### ② 没有 token 成本轴

Anthropic 的 `benchmark.json` 同时给 `pass_rate` 和 `tokens`。skill-forge 的 benchmark 只有质量维度 —— 所以一个 5,500 token 的正文能一路 accept(这正是本次 `sql-skill` 的遭遇)。

**这一条是用户报告的直接成因,也是最便宜的修复。**

### ③ benchmark 任务是模板轮转,不是真实用例

RULING-7:`bootstrap()` 循环 3 个模板 prompt 凑够 15 行。Anthropic 用的是**真实用例 + assertions**(每条断言可程序化验证)。

模板轮转能测"格式合规",测不了"这个 skill 是否真的帮上了忙"。

---

## 3. skill-forge 真正的优势(3 条,别在借鉴时丢掉)

### ① 根因分类 + 类型化 scope

Anthropic 没有分类器 —— 它只告诉你"这次没通过"。skill-forge 告诉你**为什么**(routing? prompt? contract?)和**该怎么办**(create / improve / audit-only / retire,带 confidence)。

对一个要**批量治理**几十个 skill 的场景,这个差别是决定性的:没有分类器,你只能人肉读每一个。

### ② 安全不变量

| skill-forge | Anthropic skill-creator |
|---|---|
| bundled skill **只写 proposed.md**,`SKILL.md` 永不被覆盖 | 直接就地编辑(靠人先手动 `cp -r` 快照) |
| SHA 竞态检测:audit 与 materialize 之间被手改 → 拒绝(exit 3) | 无 |
| 退出码 0 / 2 / 3 三态可 CI 路由 | 无 |
| 失败重定向:`--scope retire` 不做任何转发 | 无 |

对一个装了几十个 skill、其中一部分是 marketplace 插件的环境,「**绝不覆盖任何 SKILL.md**」这条不变量值多少?—— 很多。

### ③ 规范 + 可自动化的子集

skill-forge 有 14 条原则的成文规范(PRINCIPLES.md)+ 12 条标尺(SKILL_DESIGN_RUBRIC.md)+ 一个能自动检查其中 7 条的 validator。Anthropic 的规范更短(agentskills.io),但**没有把规范编译成检查器**。

---

## 4. 该从 Anthropic 搬过来的 4 件事

按 ROI 排序:

### 搬 1:token 成本轴(最高优先,直接解决用户报告)

`benchmark.json` / `audit-report.md` 增加 `tokens` 维度,与 `pass_rate` 并列:
- index 层 token(每会话都付的那份)
- load 层 token(触发时付的那份)
- files 层 token(按需读的那份)

**判定建议(已由用户裁决):正文 5,000 tok 上限只报不拦;index 层只警告。** 与 skill-forge 既有的 "audit, don't block"(RULING-1)一致。

### 搬 2:真基线 + 同 turn 并发 A/B

- 改动前 `cp -r` 快照成 baseline(**不是 candidate**)
- with-skill 与 baseline 两组**同 turn 并发**跑
- 报告给出 delta

这一条修的是 §2 的 ①,是最要命的那个。

### 搬 3:assertion 式评测

Anthropic 的 grader subagent 按 `assertions[]` 逐条判,每条断言形如 `{text, passed, evidence}`;**能用脚本验的就写脚本跑**,不要用 LLM 眼估。

skill-forge 的对应改动:Phase 2 生成的 15 行 task 里,加一批**"不读某个 references/ 文件就答不对"**的任务 —— 于是「渐进式披露做得好不好」变成可测的分数,而不是一个只能靠人看的原则。

### 搬 4:篇幅与目录约定

- body **< 500 lines**(取代 `wc -w ≤ 1000`)
- 参考文件 **> 300 lines 加目录**
- 接近上限 → **加一层 hierarchy + 明确指针**(读条件表)

---

## 5. 不该搬的 2 件事

| 不搬 | 理由 |
|---|---|
| 放弃根因分类器 | Anthropic 没有。这是 skill-forge 独有的 |
| 放弃安全模型 | Anthropic 没有。这是 skill-forge 独有的 |

---

## 6. 什么情况下应该直接换用 Anthropic skill-creator

诚实地说,存在这种场景:

| 场景 | 选谁 |
|---|---|
| 只用 Claude Code,只写**全新** skill,不管 marketplace 安装 | Anthropic(更简单、评测更成熟、有人维护) |
| 要**迭代已有** skill,要审计轨迹,要能 CI 化 | skill-forge |
| 环境里有 marketplace 插件 skill,怕被覆盖 | skill-forge(Anthropic 会就地编辑) |
| 批量治理几十个 skill,想知道每个为什么坏 | skill-forge(根因分类器) |
| 需要 headless / CI 跑 | skill-forge(是 CLI,Anthropic 的是提示词+脚本) |
| 想要 subagent 并行评测 + assertions + token 计费 | **Anthropic 的骨架 + skill-forge 的判定层** |

---

## 7. 一句话定位

> **Anthropic skill-creator 是「写 skill 的工具」;skill-forge 是「审 skill、改 skill、且保证不把任何东西改坏的门禁」。**
>
> 你需要的是门禁,但门禁的体检指标应该抄 Anthropic 的。

**建议的下一步顺序:** 先搬 token 成本轴(1 天,直接回应用户报告)→ 再搬真基线 A/B(修 `baseline = candidate` 这个 bug)→ 再搬 assertion 评测 → 最后才考虑要不要在两边之间做调用层的整合。

---

## 8. 引用

- Anthropic `skill-creator`:`anthropics/skills` → `skills/skill-creator/SKILL.md`(篇幅约定、benchmark harness、grader 约定)
- 规范正文:`https://agentskills.io/specification`
- Perplexity《Designing, Refining, and Maintaining Agent Skills at Perplexity》→ 本仓库 `skill-forge/docs/SKILL_DESIGN_RUBRIC.md`(14 条标尺)
- 本次审计:`skill-forge/docs/AUDIT_2026-10-25_SKILL_FORGE_TOKEN_EFFICIENCY.md`
