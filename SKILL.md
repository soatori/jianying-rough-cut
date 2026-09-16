---
name: jianying-rough-cut
description: Use when rough-cutting speech-led video/audio (口播/访谈/教程/讲座) — decide semantic keep/delete/shorten/reorder before touching a project file, or proofread subtitles against edited audio. Triggers: rough cut, 粗剪, semantic cut, content pass vs refinement, subtitle alignment, 字幕校对/对齐, speech cleanup, 去口水音. Do NOT use to edit CapCut/Jianying project files, package effects (花字/卡点), or cut non-speech montage.
---

# Jianying Rough Cut Decision Making

This skill makes editorial decisions for speech-led material. It is software-independent: it analyzes content and produces an auditable decision plan, but never manipulates an editing application or project file.

The surrounding workflow is `jianying-rough-cut → jianying-editor → subtitle alignment → jianying-packaging`. An orchestration layer may call `jianying-editor` to probe the saved edited timeline and to apply an approved plan, but this skill itself never writes a draft. Use [references/workflow-state.md](references/workflow-state.md) for the shared handoff states.

## Governing priority

Semantic correctness > content completeness > logical continuity > information density > rhythm > absolute duration.

Never shorten a piece by changing the speaker's meaning. Protect numbers, units, conditions, causes, prerequisites, negations, comparisons, names, technical terms, and uncertainty qualifiers.

## Evidence

Use any available combination of video, audio, waveform, ASR transcript, subtitles, time-coded transcript, speaker labels, and an already edited version. Do not require video when audio and time-coded speech are sufficient.

Treat ASR, punctuation, and diarization as evidence rather than truth. When audio is available, use it to resolve boundaries, fillers, pauses, overlap, tone, and suspicious transcript text. Record which evidence supports each decision.

Before making destructive decisions, audit material completeness. Record whether the available video, audio, transcript/ASR, subtitle timing, and other evidence are complete, partial, or unknown; list what was checked, what is missing, the evidence for the assessment, and whether the limitation requires review. A missing source must not be silently treated as an empty section.

## Mandatory workflow

The following order is required. Do not propose definite deletion, shortening, deduplication, or reordering before the orientation and outline stages are complete.

1. Establish the requested outcome, target audience, platform/pace, duration constraint, and preservation requirements when they affect decisions.
2. Read or listen through the complete available material, perform the material-completeness audit, and record evidence sources and limitations.
3. Complete the content-orientation stage in [references/domain-and-outline.md](references/domain-and-outline.md): identify the theme, thesis, purpose, audience, professional domain, terminology, entities, protected facts, and information outline.
4. If the domain or a technical term is uncertain, mark the affected units for context or human review. For high-stakes domains, verify against authoritative references when appropriate; otherwise do not make a definite destructive decision.
5. Reconstruct complete semantic units across transcript segments. ASR rows and subtitle cues are timing containers, not sentence or idea boundaries.
6. Identify stable speakers and per-unit conversational functions such as host, questioner, respondent, expert, narrator, correction, or supplement. For multi-speaker/Q&A work, read [references/dialogue-and-qa.md](references/dialogue-and-qa.md).
7. Build the original content map before proposing deletions. For detailed criteria, read [references/content-analysis.md](references/content-analysis.md).
8. Produce the first-pass content rough cut. Preserve complete meaning and allow natural breaths, modest pauses, and harmless small repetitions.
9. Audit the proposed cut against the complete source for missing context, altered claims, incorrect question/answer pairing, out-of-order logic, technical-detail loss, and domain terminology loss.
10. Mark the content pass as draft, stable, or approved. Only when it is stable or approved, produce a separate refinement pass for fillers, false starts, repeated openings, stutters, redundant restatements, excess pauses, tiny audio remnants, and hard joins. Read [references/speech-cleanup.md](references/speech-cleanup.md) and [references/audio-boundaries.md](references/audio-boundaries.md).
11. Output the independent content decision plan described in [references/decision-plan-schema.md](references/decision-plan-schema.md). Do not output an application-specific execution handoff.
12. After the content pass has been executed and the current edited timeline is saved, run the subtitle proofreading and audio-alignment stage in [references/subtitle-proofreading-and-audio-alignment.md](references/subtitle-proofreading-and-audio-alignment.md). Validate the separate [references/alignment-plan.md](references/alignment-plan.md) contract with `scripts/validate_alignment_plan.py` before handing it to `jianying-editor`.

## Content orientation gate

The orientation report must contain, at minimum:

- a theme and one-sentence thesis with confidence;
- the purpose and audience assumption;
- a primary domain or an explicit uncertain/non-specialized classification;
- domain segments when the material covers more than one field;
- terminology, acronyms, named entities, numbers, units, parameters, ranges, and conditions;
- possible ASR errors and unresolved terms;
- an outline of topics, questions, answers, explanations, examples, evidence, qualifications, conclusions, CTA, digressions, and low-information units;
- protected facts and dependencies that must survive editing.

If the orientation is incomplete, the output may contain hypotheses and review candidates, but it must not contain high-confidence destructive decisions for affected material.

## Two-pass boundary

### Pass 1: content rough cut

Optimize correctness, structure, and completeness. Remove clear digressions, failed takes fully covered by a complete take, large redundant passages, and content outside the agreed scope. Keep uncertain material for review.

This pass may retain natural breaths, short thinking pauses, contextual discourse markers, and small repetitions that do not impair understanding.

### Pass 2: rough-cut refinement

After Pass 1 is approved or stable, tighten delivery at phrase and audio-boundary level. Prefer small local cuts over deleting whole sentences. Preserve one natural connector when repeated openings are reduced. Compress pauses rather than forcing speech to zero gap.

Every refinement candidate must be re-auditioned in context. A clean transcript does not prove a natural audio join.

The plan must record the phase status separately: `workflow.content_pass` is `draft`, `stable`, or `approved`; `workflow.refinement_pass` is `not_started`, `draft`, or `approved`. Refinement decisions are not valid while the content pass is still draft.

## Decision rules

- Edit complete semantic units unless the defect is a local filler, false start, stutter, or pause.
- Do not stitch unfinished fragments from different attempts into a synthetic statement. A later take is not automatically better; keep the complete, natural, accurate, contextually connected version.
- Repetition, discourse markers, and overlap: remove only when no new premise, emphasis, emotion, contrast, clarification, condition, or speaker contribution is lost. Criteria in [references/speech-cleanup.md](references/speech-cleanup.md) and [references/dialogue-and-qa.md](references/dialogue-and-qa.md).
- Reordering moves complete semantic units. Recheck pronouns, connectors, chronology, causal dependencies, and domain conditions afterward.
- Record start/end boundary basis for every decision. Exact timestamps when evidence permits; approximate boundary on a destructive action must remain reviewable and may not be high-confidence.
- Boundary evidence and picture-lock rules: [references/audio-boundaries.md](references/audio-boundaries.md) and [references/content-analysis.md](references/content-analysis.md). Do not infer frame-accurate boundaries from vague instructions alone. Picture-lock only where a shot boundary carries a real semantic constraint.
- Time thresholds may flag pause candidates but may not authorize deletion by themselves.
- When evidence is insufficient, use `needs_listen`, `needs_context`, `low_confidence`, or `human_review`; do not convert uncertainty into a delete instruction.
- When material is partial or unknown, do not mark an affected delete, shorten, reorder, or join as high-confidence. Add a review flag to lower-confidence candidates.
- When a decision touches a domain-sensitive fact, terminology, number, unit, condition, or entity, record that sensitivity and retain the evidence.
- Subtitle recognition text is evidence, not truth. Correct current saved subtitles against edited-timeline audio before packaging; do not use an older subtitle copy as the write source.
- Record `audio`, `picture`, or `manual` mode plus boundary basis, evidence, confidence, and review state for both ends of every aligned subtitle unit (see [references/alignment-plan.md](references/alignment-plan.md)).
- Waveform thresholds locate candidates; they never authorize deletion or splitting by themselves. Word-level timestamps are cross-check evidence and require a health check.

## Required outputs

- source/evidence summary and limitations;
- material-completeness status, checked sources, missing items, supporting evidence, and review impact;
- theme, thesis, purpose, audience, and confidence;
- domain analysis, terminology, entities, protected facts, and confidence;
- original information outline with time ranges, roles, dependencies, and confidence;
- speaker/role map with confidence;
- recommended content structure;
- Pass 1 decision table;
- Pass 2 refinement candidates kept separate from Pass 1;
- sequence, speaker, overlap, and continuity issues;
- protected facts and risk points;
- estimated duration change when timing evidence permits;
- expected join description for every removal or reorder;
- start/end boundary basis, evidence, and precision for every decision;
- an independent content decision plan with no application-specific execution fields.
- a separate application-independent `subtitle_alignment_plan` with corrected text, semantic unit IDs, audio/picture/manual boundary decisions, evidence, and re-alignment triggers.

Run `scripts/validate_plan.py <plan.json>` to validate the content decision plan before presenting it for review.
