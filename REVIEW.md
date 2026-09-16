# jianying-rough-cut 完整审查报告

只读诊断。审查方法：skill-creator 结构/触发 → writing-skills SDO/词数 → ponytail-audit 过 scripts/agents/tests。未改任何 skill 文件。

审查时间：本会话。工作区：`C:/Users/cbsjz/Desktop/skills/jianying-rough-cut`。

---

## 0. 总评

| 维度 | 结论 | 等级 |
|---|---|---|
| 结构完整性 | 目录、命名、交叉引用、渐进披露全部合规 | A |
| 校验器 | `validate_skill.py` PASS，0 error / 1 warning | A- |
| 触发 / SDO | description 只写 WHAT，缺 WHEN，缺中文触发词 | **C** |
| 词数 | SKILL.md 1412 词，远低于 5000 硬限；对高频 skill 偏长但可接受 | B+ |
| tests/ | **真测，不是摆设**（20 例全绿，覆盖核心策略门） | **A** |
| 脚本质量 | 两套 validator 自洽、可测；有少量脆断言与重复 helper | B+ |
| agents/ | 仅 `openai.yaml` 4 行，平台专用，用途存疑 | C+ |

**一句话**：内容与工程骨架成熟（两遍粗剪门、材料完整性门、领域敏感门都写进了 validator 和测试）；最大短板在发现层——description 写得像功能清单，agent 很难在正确时机加载它。

---

## 1. skill-creator 结构 / 触发诊断

### 1.1 结构

```
jianying-rough-cut/
├── SKILL.md                 # 1412 词 / 113 行
├── agents/openai.yaml       # 4 行
├── references/              # 9 个分册，最大 651 词
├── scripts/                 # 2 个 validator
└── tests/                   # 2 个测试文件，20 用例
```

- 文件夹 kebab-case，与 frontmatter `name: jianying-rough-cut` 一致
- 无 `README.md` 混入
- `SKILL.md` 精确命名
- `.gitignore` 正确排除 `__pycache__/`；`git ls-files` 干净，工作区无未跟踪垃圾

### 1.2 校验器结果

```
WARNING: description has no obvious WHEN clause (e.g. 'Use when ...')
PASS: 0 error(s), 1 warning(s)
```

唯一 warning 直指 SDO 问题（见 §2）。

### 1.3 交叉引用

SKILL.md 与 references 内部互链共 12 处，**全部存在**，无死链：

- `references/workflow-state.md`
- `references/domain-and-outline.md`
- `references/dialogue-and-qa.md`
- `references/content-analysis.md`
- `references/speech-cleanup.md`
- `references/audio-boundaries.md`
- `references/decision-plan-schema.md`
- `references/subtitle-proofreading-and-audio-alignment.md`
- `references/alignment-plan.md`
- `scripts/validate_plan.py`
- `scripts/validate_alignment_plan.py`
- 内部：`content-analysis.md → domain-and-outline.md`、`decision-plan-schema.md → alignment-plan.md`

### 1.4 触发诊断

当前 description（184 字符）：

> Analyze speech-led video or audio for theme, domain, outline, speakers, semantic rough-cut decisions, and post-cut subtitle proofreading/audio alignment without changing project files.

问题：

1. **只有 WHAT，没有 WHEN** — skill-creator 与 writing-skills 都硬性要求 WHEN；validator 已警告。
2. **接近 workflow 摘要** — writing-skills 的 SDO 陷阱：agent 可能照 description 抄流程、跳过正文。
3. **无用户字面触发短语** — 无 "rough cut"、"粗剪"、"口播"、"访谈"、"字幕校对"、"剪映" 等。
4. **无负向触发** — 未排除「直接改工程文件」「包装/卡点」「非口播 B-roll」等。
5. **语言单一** — 该 skill 明显服务中文口播/剪辑场景，description 全英文，中文检索命中率低。

建议方向（仅建议，未改文件）：

```yaml
description: Use when rough-cutting speech-led video/audio (口播/访谈/教程/讲座) — decide semantic keep/delete/shorten/reorder before touching a project file, or proofread subtitles against edited audio. Triggers: rough cut, 粗剪, semantic cut, content pass vs refinement, subtitle alignment, 字幕校对/对齐, speech cleanup. Do NOT use to edit CapCut/Jianying project files, package effects, or cut non-speech montage.
```

---

## 2. writing-skills：SDO / 词数约束

### 2.1 词数实测

| 文件 | 词数 | 判定 |
|---|---:|---|
| **SKILL.md** | **1412** | 硬限 5000 ✓；软目标「其他 skill <500」超标 |
| references/decision-plan-schema.md | 651 | 合理（重 schema 下沉） |
| references/domain-and-outline.md | 523 | 合理 |
| references/content-analysis.md | 383 | 合理 |
| references/subtitle-proofreading-… | 352 | 合理 |
| references/audio-boundaries.md | 228 | 合理 |
| references/speech-cleanup.md | 279 | 合理 |
| references/dialogue-and-qa.md | 278 | 合理 |
| references/workflow-state.md | 169 | 合理 |
| references/alignment-plan.md | 119 | 合理 |
| scripts/validate_plan.py | ~1500 | 代码，不计 |
| scripts/validate_alignment_plan.py | ~1035 | 代码，不计 |

**判定**：渐进披露做得对——细则几乎都在 references。SKILL.md 1412 词对复杂 workflow skill 可接受，但若追求 token 效率，Decision rules 一节（约 200 词）与 references 有可感知重叠，可再压 150–250 词。

### 2.2 SDO 要点对照

| 检查项 | 现状 |
|---|---|
| "Use when..." 开头 | ✗ |
| 第三人称 | ✓（祈使/描述式，可接受） |
| 字面触发短语 | ✗ |
| 负向触发 | ✗ |
| 不把 workflow 写进 description | ✗（接近越界） |
| 关键词覆盖（错误/症状/工具） | 弱；无中文 |
| 命名 active/清晰 | ✓ `jianying-rough-cut` 可接受 |

### 2.3 其他 writing-skills 观察

- **TDD 证据**：本 skill 有真实 RED-GREEN 痕迹——validator 规则与 tests 一一对应，不是「先写文档再补测」。
- **形态匹配**：失败类型是「agent 在材料不完整/领域未定时仍高置信删改」——skill 用 **结构性门禁 + validator 硬错误** 处理，比纯 prohibition 更稳。这点设计正确。
- **无 rationalization 表 / red flags 清单**：对 discipline 型规则（禁止在 orientation 前定删）可补，但当前靠 validator 拦截，优先级中等。

---

## 3. ponytail-audit（scripts / agents / tests）

> 范围仅 over-engineering。正确性/安全/性能不在本节。

按体积从大到小：

1. **`shrink`** `scripts/validate_plan.py` 与 `scripts/validate_alignment_plan.py` 重复 helper（`is_int`/`_is_number`、`nonempty`/`_nonempty_string`、`string_list`/`_validate_string_array`）。可抽 20 行共享模块；若坚持「单文件可拷走」则保留亦可。路径：两脚本头部。
2. **`shrink`** `validate_alignment_plan.py:235-237` 用 `"manual" in str(unit["boundaries"])` 做警告判断——字符串扫，evidence 文本含 "manual" 会误报。应改为结构化检查 `boundary.mode == "manual"`。路径：`scripts/validate_alignment_plan.py:235`
3. **`yagni`** `agents/openai.yaml` 仅 4 行 OpenAI 界面元数据。若本 skill 只在 MiMo Desktop 加载，此文件可能是跨平台残留；成本极低，删除或保留均可。路径：`agents/openai.yaml`
4. **`delete`** 无死代码、无未用 flag、无单实现抽象层。scripts 的复杂度对应真实校验策略，**不是 bloat**。

```
net: -30 行, -0 deps possible（helper 抽取）；脆断言修复约 -5/+8 行。
```

无 `tools/` 目录（任务中提到的 tools/ 不存在，跳过）。

---

## 4. tests/ 专项：真测还是摆设？

### 结论：**真测。不是摆设。**

证据：

| 指标 | 实测 |
|---|---|
| 用例数 | 20（content 14 + alignment 6） |
| 执行结果 | **全部 OK**，0.001s |
| 断言形态 | 正负成对：合法 base plan → ok；改坏一个字段 → not ok |
| 是否 tautological | 否——用 `self.base()` / `valid_plan()` 构造合法样例后做局部变异 |
| 是否只测 happy path | 否——覆盖领域未完成门、材料不完整门、refinement 相位门、应用字段拒绝 |

### 已覆盖的核心策略门

**validate_plan.py（14）**

- 合法独立计划通过
- domain_analysis 缺失失败
- review action 允许
- 领域未决 + 高置信破坏性删除 → **拒绝**
- 领域未决 + medium + needs_context → 允许
- 多领域 outline 支持
- timebase / duration 越界拒绝
- `execution_handoff` 应用字段拒绝
- completeness=partial + 高置信 delete → **拒绝**
- approximate 破坏性边界 + human_review → 通过
- refinement 依赖 content_pass stable/approved
- boundary 必填
- subtitle_alignment 相位门

**validate_alignment_plan.py（6）**

- 合法 hybrid plan 通过
- picture 模式要求 picture 证据
- manual 边界要求 review=approved
- 应用字段（segment_id）拒绝
- plan approved 要求全部 unit approved
- **validate 不变异输入**（纯函数性）

### 覆盖缺口（有，但不构成「摆设」）

| 缺口 | 脚本 | 风险 |
|---|---|---|
| 决策 id 重复 | validate_plan | 中（会静默放过） |
| action/confidence 枚举外 | validate_plan | 低 |
| version ≠ 1 | validate_plan | 低 |
| speakers 空列表 | validate_plan | 低 |
| expected_join 警告路径 | validate_plan | 低（仅 warning） |
| words_health role 约束 | validate_alignment | 中 |
| tolerance / detector 数值边界 | validate_alignment | 中 |
| pause_cap < pause_min | validate_alignment | 低 |
| end_us > duration_us | validate_alignment | 中 |
| recheck_if 必填 | validate_alignment | 低 |
| CLI `main()` 端到端 | 两者 | 低 |

建议优先补：决策 id 重复、words_health、duration 越界、CLI smoke（各 1 例即可）。

### 测试风格评价

- 两文件加载方式不一致：`test_validate_plan.py` 用 `sys.path.insert`，`test_validate_alignment_plan.py` 用 `importlib`。功能都对，但不统一。
- 无 pytest fixture / parametrize；用 unittest 与 skill 无依赖原则匹配，**正确**。
- 未依赖网络、剪映本体、外部样本——可离线复现，**正确**。

---

## 5. 内容架构亮点（非缺陷，供保留）

这些是本 skill 相对同类的真正优势，审查中应视为资产：

1. **两遍边界硬编码**：content_pass / refinement_pass / subtitle_alignment 相位机写进 validator，refinement 决策在 content draft 时直接 error。
2. **软件无关契约**：`REJECTED_FIELDS` 与 `APPLICATION_KEYS` 禁止 `execution_handoff`、`keep_blocks`、`draft_path`、`segment_id` 等，强制「决策计划」与「执行 handoff」分离。
3. **材料完整性门**：`input.completeness` partial/unknown 时禁止高置信破坏性决策——防止「源不全却下狠手」。
4. **领域敏感门**：domain unresolved + domain_sensitive + destructive → 高置信拒绝。
5. **边界证据制度**：每个决策强制 boundary basis/evidence/precision；approximate + high 置信直接 error。

---

## 6. 问题清单（按优先级）

| # | 优先级 | 问题 | 位置 | 建议动作 |
|---|---|---|---|---|
| 1 | **P0** | description 无 WHEN、无触发短语、无负向 | SKILL.md:3 | 重写 description（见 §1.4） |
| 2 | **P1** | 无中文触发词（粗剪/口播/字幕校对） | SKILL.md:3 | 并入 #1 |
| 3 | **P1** | `"manual" in str(...)` 脆警告 | validate_alignment_plan.py:235-237 | 改为 `mode == "manual"` 结构化判断 |
| 4 | **P2** | tests 缺 id 重复 / words_health / duration / CLI | tests/* | 各补 1–2 用例 |
| 5 | **P2** | 两脚本 helper 重复 | 两 validator 头部 | 可选抽取；或文档化「刻意自包含」 |
| 6 | **P3** | agents/openai.yaml 用途不明 | agents/openai.yaml | 确认宿主是否读取；否则删 |
| 7 | **P3** | SKILL.md Decision rules 与 references 有重叠 | SKILL.md:74-92 | 可压 150–250 词 |
| 8 | **P3** | 两测试文件 import 风格不一致 | tests/* | 统一为 importlib 或 sys.path |

---

## 7. 验证命令备忘

```powershell
# 结构校验
& $env:MIMO_PYTHON "…\skill-creator\scripts\validate_skill.py" <skill-root>

# 单元测试
Set-Location <skill-root>
& $env:MIMO_PYTHON -m unittest discover -s tests -v

# 词数
Get-Content SKILL.md | Measure-Object -Word
```

本次结果：validator PASS(1 warning)；unittest 20/20 OK。

---

## 8. 结论

`jianying-rough-cut` 在**工程与编辑策略层是成熟 skill**：渐进披露正确、契约可机检、tests 是真测且锁住了最关键的三道安全门（领域未决、材料不全、相位门）。

发现层是短板：description 功能清单化 + 缺中文触发，会导致该 skill **该载时不载**。修复 #1/#2 成本极低、收益最高。

ponytail 视角无重大 bloat；scripts 的复杂度对应真实策略，不建议为减行数而削逻辑。
