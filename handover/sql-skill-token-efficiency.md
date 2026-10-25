# 移交:`sql-skill` 的 token 效率问题与方案

**日期:** 2026-10-25(第二版,用 skill-forge 新增的 cost 轴 + validator 复核)
**给:** sql-skill 所属项目 · **来源:** skill-forge 的 token 效率审计
**依据:** Perplexity《Designing, Refining, and Maintaining Agent Skills》+ Anthropic 官方 `skill-creator` 的篇幅约定

---

## 1. 结论先说

**`sql-skill` 已经做对了最难的那一步 —— 它有 `chapters/`(10 章)+ `supporting/` 的渐进式披露结构。问题在于 SKILL.md 把 chapters 的摘要又抄了一遍,加上 description 塞了 19 个短语、且缺少全部四个通用元数据字段。**

用 skill-forge 自己的 cost 轴 + validator 实测:

| 层级 | 实测 | 预算 | 判定 |
|---|---|---|---|
| **Index**(每会话都付) | **231 tok** | ~100 | ✗ **超 131** |
| **Load**(触发时) | **5,503 tok** | ~5,000 | ✗ **超 503** |
| **Files**(按需读) | **0 tok** | 无限 | ✗ **没有 references/ 目录,溢出无处可去** |

**每次触发 ≈ 5,734 tok。** 对比 `evidence-skill` 的 2,662 tok,贵一倍多。

**skill-forge validator 对它报了 11 条警告:**

```
1. `description` should start with a routing-trigger prefix ('Use when', 'Load when')
2. `description` is 101 words, recommended ≤ 50
3. `triggers` is missing or empty
4. `mutating` is missing
5. `brain_first` is missing
6. `when_to_use` is missing
7. `version` is missing
8. index tier is 230 tokens, over the ~100-token budget
9. body: no gotcha-style section found
10. body: 408 lines (> 150); consider moving heavy content to references/ or assets/
11. body: load tier is 5503 tokens, over the ~5000-token target
```

**这 11 条就是一份可执行的清单。**

---

## 2. 问题一:frontmatter 只有两个字段,而且都不合规

现在的 frontmatter **只有 name + description**:

```yaml
name: sql-skill
description: "通用 SQL 编写专业度 Skill — PostgreSQL 视角。Use when writing enterprise
PostgreSQL queries, debugging slow queries, deciding between index types (B-Tree / GIN /
BRIN / Hash), reading EXPLAIN ANALYZE plans, using JSONB / array / GIN indexes, querying
via postgres_fdw cross-DB, handling Chinese schema columns (双引号 / 假名 / date SUBSTR),
or evaluating query plan operators (Seq Scan / Index Scan / Hash Join / Sort). Triggers:
'sql skill', 'PG performance', 'index decision', 'EXPLAIN ANALYZE', 'jsonb_path_ops',
'GIN index', 'BRIN time-series', 'taobao.mart_X', 'postgres_fdw', 'pg_stat_statements',
'jsonb @>', 'Chinese column', 'shop_name 假名', 'SUBSTR date', 'array unnest', 'pgbouncer
session', 'OFFSET keyset', 'pg 索引', 'explain 解读'."
```

**101 词 / 231 tok。** Perplexity 的规则是 **≤ 50 词**,且"**2-3 examples usually cover 80/20**"。这里有 19 个。

**更关键的是:description 以"通用 SQL 编写专业度 Skill"开头 —— 它描述的是"这是什么",不是"何时加载"。** 这正是 Perplexity 说的反面:

> "A bad description describes what the Skill does."
> "A good description says when the agent should load the Skill."

**方案:**

```yaml
---
name: sql-skill
description: >-
  Use when writing or debugging enterprise PostgreSQL queries — index selection
  (B-Tree / GIN / BRIN), reading EXPLAIN ANALYZE plans, JSONB and array columns,
  cross-DB via postgres_fdw, and Chinese-schema column quirks.
triggers:
  - "sql skill"
  - "PG performance"
  - "index decision"
  - "EXPLAIN ANALYZE"
  - "GIN index"
  - "BRIN time-series"
  - "jsonb @>"
  - "postgres_fdw"
  - "OFFSET keyset"
  - "explain 解读"
mutating: false
brain_first: exempt
when_to_use: "Enterprise PostgreSQL query writing and performance debugging."
version: 0.1.0
---
```

- description 降到 **~35 词 / ~85 tok**,以 "Use when" 开头
- **`triggers:` 补上** —— 它现在是唯一该放短语的地方
- 补齐 `mutating` / `brain_first` / `when_to_use` / `version` 四个字段(validator 第 4-7 条警告)
- **业务特定词移出 index 层**:`taobao.mart_X`、`shop_name 假名`、`SUBSTR date` 属于"要查什么内容"的线索,不是"何时加载这个 skill"的线索 —— 它们进 `chapters/` 的检索路径和 `supporting/`

**预计 index 231 → ~130 tok。**

---

## 3. 问题二:12 大框架内联在正文,与 chapters 重复

正文 412 行里最重的一块是 `## Core Frameworks & Mental Models(12 大)`,**≈ 85 行 / ~1,700 tok**。

**但这 12 条,chapters 里已经全都写过一遍:**

| 内联框架 | 已有章节 |
|---|---|
| 1 SQL 执行顺序 · 2 NULL 三值逻辑 | [ch01](chapters/ch01-grammar.md)(8 子句执行顺序 / 别名作用域 / NULL 三值逻辑 / 风格铁律) |
| 3 索引选择 · 4 WHERE 索引失效 · 6 排序分组索引 · 7 分页 Top-N | [ch08](chapters/ch08-indexes-perf.md)(索引结构 / WHERE 索引 / JOIN 算法 / 排序分组 / 分页窗口 / EXPLAIN ANALYZE) |
| 5 JOIN 算法 | [ch02](chapters/ch02-joins.md)(JOIN 7 种 + 性能差异) |
| 9 JSONB vs JSON · 10 array 列决策 · 11 postgres_fdw | [ch07](chapters/ch07-pg-specific.md)(JSONB / array / GIN / FDW 2-segment / 中文 schema 雷区) |
| 8 EXPLAIN ANALYZE | ch08 |
| 12 慢 query 排查 SOP | ch08 / ch09 |

**Perplexity 的判据直接适用:** "Every sentence has to earn its place." —— 这 12 段是 chapters 的**摘要副本**,而 `chapters/` 已经在 runtime 层(按需读)。摘要在 load 层重复一遍,就是白付一次钱。

**方案(选 A 或 B):**

**方案 A(推荐):12 大框架整体移出正文,换成一张路由表**

```markdown
## Core Frameworks 速查(按需读)

| 框架 | 读哪一章 |
|---|---|
| SQL 执行顺序 · NULL 三值逻辑 · 风格铁律 | [ch01](chapters/ch01-grammar.md) |
| JOIN 7 种 + 性能差异 | [ch02](chapters/ch02-joins.md) |
| 窗口函数 / CTE / 聚合 | [ch03](chapters/ch03-window-functions.md) · [ch04](chapters/ch04-cte-recursion.md) · [ch05](chapters/ch05-aggregates.md) |
| 集合操作 | [ch06](chapters/ch06-set-ops.md) |
| JSONB / array / GIN / FDW 2-segment / 中文 schema 雷区 | [ch07](chapters/ch07-pg-specific.md) |
| 索引结构 · WHERE 索引失效 · JOIN 算法 · 排序分组 · 分页窗口 · EXPLAIN ANALYZE | [ch08](chapters/ch08-indexes-perf.md) |
| 7 类 25+ 反模式 | [ch09](chapters/ch09-antipatterns.md) |
```

正文保留 12 行表格,删掉 85 行摘要。**省 ~1,550 tok。**

**方案 B(保守):框架留在正文,但每条压到 2 行(只留结论 + 指针)**

```markdown
### 3. 索引选择 — B-Tree 默认 / GIN 多值 / BRIN 时序 / Hash 几乎不用
→ 详见 [ch08](chapters/ch08-indexes-perf.md)
```

12 条 × 2 行 = 24 行,**省 ~1,100 tok**,且"最常被问的 12 件事"仍然直接可见。**如果你担心纯表格会丢掉"agent 该想到去查索引"这个信号,选 B。**

---

## 4. 问题三:正文没有 gotcha 小节(validator 第 9 条警告)

`validate_skill_body` 报:`body: no gotcha-style section found`。

**但你其实有 25+ 条反模式** —— 它们在 [ch09](chapters/ch09-antipatterns.md)(7 类 25+ 反模式)和 ch02/ch07 的各自小节里,**只是正文的小节标题没有一个命中 gotcha 的模式**。

**Perplexity 的命名约定**:`Gotchas` / `Common pitfalls` 是正文小节;`SPECIAL_CASES.md` / `FORMATTING.md` 是按需文件。

**方案(二选一,改动都很小):**

- **把 ch09 提上来**:正文加一节 `## Gotchas`,放 5-8 条最高频的反模式(每条一行,指向 ch09 详述),其余留在 ch09
- **或改标题**:把正文里某个已有小节改名成 `## Gotchas`(例如现在的"其他入口"或某段注意事项)

**关键是这个信号要出现在正文**:agent 触发 skill 时看到 gotchas,才会主动去查;看不到就只会用通用知识硬答。

---

## 5. 问题四:Layer 0 的 Obsidian 检索说明 ~23 行

`### Layer 0: 直接 Read + Grep 检索 Obsidian SQL vault(NEW · v2.1)`(23 行)+ `Layer 0+`(5 行)+ `其他入口`(10 行)= **38 行**,描述的是**怎么用这个 skill**(去哪个 vault 路径、怎么 grep)。

**方案:**
- 正文保留一行:"知识源在 `E:/obsidian/SQL/`,章节映射见 `supporting/`;先用 Grep 定位主题,再 Read 对应 chapter"
- 23 行 → 1 行,**省 ~450 tok**
- 详细检索策略(路径、命令、fallback 顺序)→ `supporting/retrieval.md`,由 Layer 0 小节指向它

**这同时补上了 validator 第 10 条警告**("408 lines > 150")的一半。

---

## 6. 问题五:`Chapter Index` 15 行(可选)

`## Chapter Index(10 章)` 那张表列了每章的"关键内容 + 状态 ✅"。15 行里,状态列(`✅ Phase 2 完成`)**是开发过程信息,不是给 agent 的检索信息**。

**方案:** 删掉"状态"列,只留 `# | 主题 | 关键内容`。压到 8 行。**省 ~200 tok。**

---

## 7. 改完之后

| | 现在 | 方案 A | 方案 B |
|---|---|---|---|
| index | 231 tok | ~130 tok | ~130 tok |
| load | 5,503 tok | ~3,300 tok | ~3,750 tok |
| **每次触发合计** | **5,734** | **~3,430** | **~3,880** |
| 降幅 | — | **-40%** | **-32%** |

方案 A + Layer 0 压缩 + Chapter Index 压缩三项都做,正文约 5,503 → ~3,000 tok,仍在 5,000 预算内且留有余量。

**Anthropic 官方对照:** "**SKILL.md body** - In context whenever skill triggers (**<500 lines** ideal)" —— 改后约 240 行,达标。

---

## 8. 验收标准

| 检查 | 目标 | 怎么验 |
|---|---|---|
| description 词数 | ≤ 50 词 | 现在 101 词 |
| description 以 "Use when" 开头 | ✓ | 现在以"通用 SQL 编写专业度 Skill"开头 |
| `triggers:` 存在且 ≥ 3 条 | ✓ | 现在完全没有 |
| `mutating`/`brain_first`/`when_to_use`/`version` | 全部有 | 现在全缺 |
| index 层 token | ≤ ~130 tok | `## Cost` 段的 index 行 |
| 正文字数 | ≤ ~3,300 tok / ≤ 250 行 | `## Cost` 段的 load 行 |
| 正文有 gotcha 小节 | ✓ | validator 第 9 条警告消失 |
| `chapters/` + `supporting/` | **不变**(这是你已经做对的部分) | `ls` |
| 12 大框架 | 要么只留路由表,要么每条 ≤ 2 行 + 指针 | 肉眼 |
| 触发一次的上下文 | ≤ ~3,500 tok(当前 5,734) | `## Cost` 段合计 |

**复审工具已就绪:** 改完直接跑
```bash
python -m scripts.run --skill <你的 skill 目录> --scope audit-only
```
`## Cost` 段给出三层实测值,validator 的 11 条警告逐条消失即可。

**回归检查:** 改 description 时**一次只改 1-2 个词、每步跑一次 eval**。sql-skill 与 evidence-skill 意图重叠(都在 PostgreSQL 侧),改任一方前**先重跑另一方的 eval** —— Perplexity 明写:"Adding a new Skill can break other pre-existing Skills." 建议补一个邻居混淆 eval:`"evidence 报表加了个新过滤维度"` 应命中 evidence-skill 而非 sql-skill。

---

## 9. 附:完整 token 测量口径

CJK ≈ 1 token/char,latin ≈ 1 token/3.5 chars。**index 层 = 整个 frontmatter**(每个字段都会被注入,不只 description)。测量实现:`skill-forge/scripts/_lib/token_cost.py`。
