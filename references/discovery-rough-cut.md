# 粗剪 · Discovery（无文案 / 采访访谈）

The 粗剪 entry used when there is no accurate written copy — interviews, 对谈 /
访谈, panels, podcasts, unscripted talks. There is no script to order against, so
you discover structure from the transcript itself, then agree editorial
direction with the human before committing cuts. It changes no plan schema.

The application-independent boundary is the same as copy-first: this layer emits
only evidence and validated plans. The generated transcript, subtitles, and SRT
are review artifacts (they may be saved beside the media / in the draft folder);
probing, importing to a timeline, and any `draft_content` write remain
`jianying-editor`'s job, reached only through the explicit handoff gate.

## 粗剪前端（本入口独有）

The 粗剪 front end loops until the whole conversation is understood. Do not enter
精剪 until the 粗剪 cut is `stable`/`approved`
([workflow-state.md](workflow-state.md)).

### 1. 识别素材 + 生成字幕（多人标注）

- Run the material-completeness audit first (SKILL.md "Evidence"; `preflight`
  / the `workflow` material stage).
- Transcribe to a timed transcript and generate *working* subtitles from it —
  this transcript is the substrate you outline and cut from, not yet the final
  aligned subtitle. Keep `review_status=pending`.
- If it is multi-speaker (采访 / 对谈), **annotate speakers**: label each unit
  with the stable speaker and conversational function (host / questioner /
  respondent / expert / narrator). See
  [dialogue-and-qa.md](dialogue-and-qa.md); the generation route is
  `subtitle-generate` in
  [subtitle-proofreading-and-audio-alignment.md](subtitle-proofreading-and-audio-alignment.md).
- Pass the transcript through the correction gate
  ([transcript-correction-gate.md](transcript-correction-gate.md)) so a misheard
  name is fixed **before** you decide structure.

### 2. 大纲：从字幕分析整理整体内容

From the corrected, speaker-labelled transcript build the content orientation and
outline ([domain-and-outline.md](domain-and-outline.md)): theme and thesis,
purpose and audience, topic modules, question→answer pairings, and protected
facts. Preserve the source order in the outline even when a later structure may
differ; the outline must stay traceable to transcript units.

### 3. 评估建议 + 发起询问（剪哪些、是否按顺序）

Because no copy fixes the target shape, present an editorial recommendation and
get direction *before* planning detailed cuts:

- what to keep vs. drop at the **block** level — which topics, answers, and
  examples carry the piece;
- whether to **preserve** chronological / Q&A order or **restructure**
  (hook-first, theme-grouped, problem/solution, …);
- target length, pace, and platform.

This is one up-front direction brief, **not** a per-cut confirmation — do not ask
line by line (SKILL.md decision rules). Record the answers as constraints for the
cut plan.

### 4. 剪辑计划 + 审核（可能循环）

Turn the agreed direction into the Pass-1 content rough cut
([content-analysis.md](content-analysis.md) source map +
[decision-plan-schema.md](decision-plan-schema.md)), self-verify by re-reading
the post-cut text in playback order, and send it for review. Expect a loop:
feedback adjusts the plan, you re-audit against the full source, until
`content_pass` is stable / approved.

- Suggested execution shape on the timeline: run a **coarse content pass first**
  (drop failed / off-topic blocks, keep the whole surviving answers in the agreed
  order) to reach the approximate shape, **then** apply the shared refinement
  tail below to that — do not refine before the block-level rough cut is agreed.

→ Emit the content decision plan, then continue on the 精剪主循环.

## 汇入精剪主循环（两条粗剪入口共用）

Identical to the copy-first entry, so not repeated as specifics here:

1. **Pass 2 refinement** (重复句 / 停顿 / 气口 / 语气词 / 听感不顺), iterative.
   SKILL.md step 11 and [speech-cleanup.md](speech-cleanup.md).
2. **Subtitle → SRT** against the *edited* timeline audio, review-pending
   sidecar. SKILL.md step 13 and
   [subtitle-proofreading-and-audio-alignment.md](subtitle-proofreading-and-audio-alignment.md).
3. **Import to timeline & align** via the `jianying-editor` handoff (explicit
   confirmation first); an unresolved range, a mid-word cut, or order/sync drift
   is **reported** for that segment, never silently nudged.
4. **发起审查** at the human gates, then **ask whether to proceed to
   `jianying-packaging`**. [workflow-state.md](workflow-state.md).
