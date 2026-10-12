# 粗剪 · Copy-first（已有文案）

The 粗剪 entry used when the speaker recorded to a written copy (口播稿 / 文案).
The copy is the structural spine: you place the best surviving take of each
scripted line **in copy order**, instead of discovering structure from scratch.
It changes no plan schema.

**Only the front end below (粗剪) is copy-specific** — 素材识别与索引 and
按文案排序剔除. Everything after it is the shared **精剪主循环**; do not re-learn it
here, jump to "汇入精剪主循环" and the SKILL.md flow controller / steps 11–15.

This layer stays application-independent: it only emits evidence and validated
plans. The material index is a plain sidecar file this skill drops beside the
media (the draft folder is a convenient location); writing a plain file there is
**not** a draft write. Probing, importing to a timeline, and any `draft_content`
change remain `jianying-editor`'s job, reached only through the explicit
handoff gate.

## 粗剪前端（本入口独有）

The 粗剪 front end loops until the whole copy is covered. Do not enter 精剪
until the copy-ordered cut is `stable`/`approved`
([workflow-state.md](workflow-state.md)).

### 1. 素材识别与索引 (material index)

- Enumerate every source clip and write an index the reviewer can open beside
  the media. One row per clip: `编号 / 文件名 / 对应文案段落 / 内容摘要 /
  时长 / 完整性 / 备注`.
- Map each clip to the copy segment it realizes. When one scripted line was
  recorded more than once, group its attempts so the choice is explicit.
- **Numbered-take default:** for equivalent re-takes of the same line, prefer
  the higher 编号 — a later take usually fixes the flub. This is a whole-clip
  choice between *complete* takes, not a license to stitch fragments across
  takes. When takes diverge, or a later take is incomplete or less accurate,
  keep the complete accurate one and mark `needs_listen`. Details in
  [content-analysis.md](content-analysis.md) (重复尝试汇总) and
  [cut-case-law.md](cut-case-law.md) R1/R4.

**Next step:** once every supplied clip is indexed and coverage limits are
recorded, order the mapped units by the copy. If missing media affects the
requested scope, report it and hold decisions that depend on it.

### 2. 按文案排序、剔除无效片段 (order by copy, drop non-content)

Reconstruct copy order from the index, then classify each span:

- **同段重录 (re-takes):** keep the selected take, drop the losers; every drop
  is a required repeated-attempt rollup entry, never a silent cut.
- **倒数 / 打板 lead-in:** a spoken "3、2、1 开始" or a clap slate at a take's
  head is a recording cue, not content — trim to the first real word. Case-law
  R7.
- **其他内容 (off-copy material):** do **not** delete just because a passage is
  absent from the copy. First judge whether it explains, supplements, or
  qualifies the adjacent unit — on-site the speaker often improvises a needed
  clarification or amends the copy. Improvised content that adds a premise,
  example, correction, or protected fact is **kept** and slotted where the copy
  lacked it; only genuine digression / out-of-scope chatter is dropped. When
  supplement-vs-digression is unclear, use `needs_context` / `human_review`,
  never a confident delete ([domain-and-outline.md](domain-and-outline.md)
  gate).
- Edit complete semantic units; a cut decision is commit-as-`delete` /
  mark-`review` / drop — never "suggest and wait" (SKILL decision rules).

→ Emit the content decision plan ([decision-plan-schema.md](decision-plan-schema.md)).
The copy only tells you which units *should* be present; it is never itself a
deletion or boundary authorization.

**Next step:** resolve any `needs_context` / `human_review` items before
destructive decisions. Once the copy-ordered plan is `stable` or `approved`,
continue to the shared refinement loop below; if approval is still pending,
present the plan and wait at that gate.

## 汇入精剪主循环（两条粗剪入口共用）

Once the 粗剪 front end is stable, continue on the shared **精剪主循环** — identical
to the discovery entry, not part of this runbook's specifics:

1. **Pass 2 refinement** (重复句 / 停顿 / 气口 / 语气词 / 听感不顺), run as
   single-criterion scans and re-auditioned in context; this may loop.
   SKILL.md step 11 and [speech-cleanup.md](speech-cleanup.md).
2. **Subtitle → SRT** against the *edited* timeline audio, written as a
   review-pending sidecar (draft folder is fine). SKILL.md step 13 and
   [subtitle-proofreading-and-audio-alignment.md](subtitle-proofreading-and-audio-alignment.md).
3. **Import to timeline & align** via the `jianying-editor` handoff only when
   that operation is within the user's current request and authorization. A
   range that will not resolve, a cut landing mid-word, or order/sync drift is
   **reported** for that segment — not silently nudged. Do not repeat a
   confirmation for an unchanged, already authorized operation.
4. **发起审查** at the human gates. If packaging is within the current request,
   continue only after its state gates pass; otherwise identify packaging as the
   next available phase without asking again about an already stated scope.
   Plan approval alone does not authorize a packaging write.
   [workflow-state.md](workflow-state.md).
