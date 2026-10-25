# 移交:`evidence-skill` 的 token 效率问题与方案

**日期:** 2026-10-25 · **给:** evidence-skill 所属项目 · **来源:** skill-forge 的 token 效率审计
**依据:** Perplexity《Designing, Refining, and Maintaining Agent Skills》+ Anthropic 官方 `skill-creator` 的篇幅约定

---

## 1. 结论先说

**`evidence-skill` 的渐进式披露结构是对的,问题只有两个,都在 index 层和两个重复的索引表上。** 不需要重写,是小改。

| 层级 | 实测 | 预算 | 判定 |
|---|---|---|---|
| **Index**(每会话都付) | description 97 tok + `triggers:` 6 条 → **146 tok** | ~100 | ✗ 超 46% |
| **Load**(触发时) | 正文 2,431 tok | ~5,000 | ✓ 合格 |
| **Files**(按需读) | `references/` 5 个文件 / 13,683 tok | 无限 | ✓ 合格 |

正文 156 行,远在 Anthropic 的"< 500 lines"之内。

---

## 2. 问题一:index 层的短语重复(唯一的超预算项)

现在的 frontmatter:

```yaml
description: >-
  Use when configuring, debugging, or designing Evidence BI Core 2026 pages on
  bi.jury.xxin — charts, tables, filters, Chinese-schema SQL, nginx, themes, MCP,
  upgrades, and report-page UI contracts.
  Triggers: "evidence", "bi.jury.xin", "sales-bi", "Evidence 报表", "combo_chart",
  "legend", "page_size", "Evidence 部署", "FastMCP evidence".
triggers:
  - "evidence"
  - "bi.jury.xin"
  - "sales-bi"
  ...
```

**同一批短语写了两遍**:description 内嵌 9 条 + 独立的 `triggers:` 列表 6 条。

Perplexity 的规则:index 层 ~100 tokens/skill,**"2-3 examples usually cover 80/20"**,而且 description 要回答的是"何时加载",不是"它是干什么的"。

Anthropic 官方 `skill-creator` 的说法更狠:**metadata 只有两个字段** —— "**Metadata** (name + description) - Always in context (~100 words)"。

**为什么这值得改:** index 层是**每个会话、每个用户**都付的钱,而且不随是否触发而变。你本机 63 个 skill,这一项乘以 63。

**方案:**

```yaml
description: >-
  Use when configuring, debugging, or designing Evidence BI Core 2026 pages on
  bi.jury.xin — charts, tables, filters, Chinese-schema SQL, nginx, themes, MCP,
  upgrades, and report-page UI contracts.
triggers:
  - "evidence"
  - "bi.jury.xin"
  - "sales-bi"
  - "Evidence 报表"
  - "combo_chart"
  - "page_size"
  - "FastMCP evidence"
```

- **删掉 description 里的 `Triggers:` 子句**(9 条短语全部搬进 `triggers:`,那里是唯一的清单)
- description 保留**能力范围**(configuring / debugging / designing + 领域词),因为它要帮 resolver 判"该不该加载"
- `triggers:` 补齐到 7-9 条,覆盖被删掉的 `legend` / `Evidence 部署`
- **预计 index 层降到 ~110-120 tok**

> 顺带:本机 `sql-skill` 和 `skill-forge` 自己都有同款重复(`when_to_use` 逐条抄 `triggers:`),见各自的移交文档。

---

## 3. 问题二:正文里有两个"索引表",加起来 52 行

正文 156 行里,这两块是**导航**,不是决策信息:

| 章节 | 行数 | 性质 |
|---|---|---|
| `## Quick Decision Table` | 26 | 索引/速查 |
| `## Chapter Index` | 26 | 索引/速查 |

`Quick Decision Table` 26 行 + `Chapter Index` 26 行 ≈ **700-900 tok**,每次触发都付。

**对照:** `evidence-skill` 已经有 `## References(按需加载)` 这张表:

```
| 文件 | 何时读 |
|---|---|
| `references/cheatsheet.md` | 14 决策表 + 12 阶段 actionable,决策快查 |
| `references/patterns.md` | 8 大模式 + 反模式表,复用现成方案 |
...
```

**这张表写得非常好** —— 文件 + 读取条件,正是 Perplexity 要求的"Read api-errors.md if API returns non-200" 模式。`cheatsheet.md`(203 行)已经在承担 "Quick Decision Table" 的职责。

**方案:**

1. **`Quick Decision Table`(26 行)→ 删。** 它的内容与 `references/cheatsheet.md`(14 决策表)重复;真需要速查时,`References(按需加载)` 表已经指了路。若确有正文才有的部分,压到 5 行以内,只留"最常见 3 个决策 → 读哪个文件"。
2. **`Chapter Index`(26 行)→ 压到 5-8 行。** 只保留"哪章解决什么问题"的一句话映射,详细的章节摘要移进 `references/topic-index.md`(已存在,140 行,80+ 主题 → 章映射)。
3. **`Output Format`(9 行)/ `When it fails`(8 行)→ 移进 `references/`。** 按 Perplexity 的分工,SKILL.md 只留"必须立刻在上下文里的决策信息";输出格式和失败模式是**特定场景才需要**的。
4. **`Scope & Limits`(7 行)留在正文** —— 它是"什么时候别用我",属于路由决策信息,留在正文是对的。
5. **`Anti-Patterns`(15 行)、`Verification`(8 行)、`沉淀回写 SOP`(13 行)留在正文** —— 这三个是 Perplexity 说的"最高价值的 gotcha",触发时确实需要。

**预计正文降到 ~100 行 / ~1,500 tok**,index ~115 tok。**每次触发总成本从 2,577 tok 降到 ~1,615 tok(降 37%)。**

---

## 4. 一个可选的小优化:长参考文件加目录

Anthropic 官方约定:"For large reference files (**>300 lines**), include a **table of contents**"。

你的 `references/patterns.md` 是 **294 行** —— 刚好在边缘。加一个 8-10 行的目录成本很低,而且它是**按需读**的,不影响 index/load 层。

---

## 5. 验收标准

| 检查 | 目标 |
|---|---|
| `description` 词数 | ≤ 50 词(去掉 `Triggers:` 子句后自然满足) |
| index 层 token(description + triggers + when_to_use) | ≤ ~120 tok |
| 正文字数 | ≤ ~1,600 tok(约 100 行) |
| `references/` 文件 | 不变(5 个) |
| `## References(按需加载)` 表 | 保留,这是全文最值钱的一块 |
| 触发一次的实际上下文 | ~1,615 tok(当前 2,577) |

**回归检查:** 改完 description 后,按 Perplexity 的协议**只改 1-2 个词、一次改一处、每步跑一次 eval**。若 `evidence-skill` 有 hero query 集(正面 + 负面 + 邻居混淆),先建基线再改;加任何新 skill 后,重跑邻居的 eval —— "Adding a new Skill can break other pre-existing Skills"。

---

## 6. 附:完整 token 测量口径

CJK ≈ 1 token/char,latin ≈ 1 token/3.5 chars。测量脚本在 skill-forge 审计里,口径一致。
