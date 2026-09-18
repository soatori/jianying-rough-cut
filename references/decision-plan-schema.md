# Independent content decision plan schema

This schema describes editorial analysis only. It contains no application-specific execution command, timeline mutation field, or project-file handoff.

Subtitle correction and timing alignment is a separate contract. After the content plan has been executed on the current saved timeline, create and validate [alignment-plan.md](alignment-plan.md) with `scripts/validate_alignment_plan.py`; do not add Jianying locators to this content schema.

## Required top-level fields

- `version`: currently `1`
- `input`: media identity, timebase, optional duration, and a required completeness audit
- `evidence`: evidence sources and limitations
- `goal`: requested outcome and preservation constraints
- `theme_analysis`: topic, thesis, purpose, audience, and confidence
- `domain_analysis`: domain status, primary domain, terminology, entities, and confidence
- `outline`: source information outline and confidence
- `speakers`: stable identities, roles, and confidence
- `original_structure`: ordered source units
- `recommended_structure`: ordered proposed units
- `decisions`: Pass 1 and Pass 2 decisions
- `protected_facts`: details that must survive review
- `workflow`: mode plus content/refinement phase status and gate

The surrounding workflow also tracks `subtitle_alignment` as `not_started`, `draft`, `stable`, or `approved`, but the alignment units live in the separate `subtitle_alignment_plan` rather than in this content decision plan.

`theme_analysis`, `domain_analysis`, and `outline` must each include `confidence` with `high`, `medium`, or `low`.

## Material completeness and phase gate

`input.completeness` is required and contains:

- `status`: `complete`, `partial`, or `unknown`;
- `checked`: a non-empty list of checked sources such as `video`, `audio`, `transcript`, or `subtitle_timing`;
- `missing`: a list of missing sources or evidence;
- `evidence`: a non-empty list explaining how completeness was assessed;
- `impact`: `none` when the material is complete, otherwise `review_required`.

`workflow` is required. `subtitle_alignment` is optional for a content-only plan and defaults to `not_started`; use the separate alignment plan before packaging:

```json
{
  "content_pass": "stable",
  "refinement_pass": "draft",
  "subtitle_alignment": "not_started"
}
```

`workflow.mode` defaults to `content_edit` and may be `content_edit` or `final_draft_audit`. An audit plan must also set `workflow.text_authority` to `final_visible_subtitle`. Audit mode is read-only: its decisions may be `keep` or `review`, but never `delete`, `shorten`, `reorder`, or `join`. For a full final-draft report, use [analysis-report-schema.md](analysis-report-schema.md) rather than turning the audit into an edit plan.

`content_pass` is `draft`, `stable`, or `approved`. `refinement_pass` is `not_started`, `draft`, or `approved`. A refinement decision is valid only when `content_pass` is `stable` or `approved` and `refinement_pass` is not `not_started`.

## Content orientation

```json
{
  "theme_analysis": {
    "topic": "human-readable topic",
    "thesis": "one-sentence central proposition",
    "purpose": "interview|explanation|tutorial|discussion|other",
    "audience": "expected audience and knowledge level",
    "confidence": "medium",
    "alternatives": []
  },
  "domain_analysis": {
    "status": "identified|uncertain|not_applicable",
    "primary_domain": "domain or general",
    "confidence": "medium",
    "segments": [],
    "terms": [],
    "entities": [],
    "protected_facts": [],
    "unresolved_terms": []
  },
  "outline": {
    "confidence": "medium",
    "modules": [],
    "units": []
  }
}
```

Each outline unit should record its time range, title or summary, role, speaker or speakers, dependencies, information added, domain risk, and transcription confidence. The validator requires at least an ID, title/summary, role, time range, timebase, and confidence for each unit.

Highlight groups may be recorded as a separate report handoff. Use the shared roles `hook`, `background`, `question`, `reaction`, `answer`, `evidence`, `technical_detail`, `contrast`, `benefit`, `summary`, and `cta`. Keep their semantic-unit references and protected-fact flags; do not add packaging coordinates or effects to this schema.

## Decision

Each decision includes:

- `id`;
- `pass`: `content` or `refinement`;
- `speaker_id` when known;
- `start`, `end`, and `timebase`;
- `boundary`: start/end boundary basis, supporting evidence, and precision;
- `summary` and `reason`;
- `action`: `keep`, `delete`, `shorten`, `reorder`, `join`, or `review`;
- `confidence`: `high`, `medium`, or `low`;
- `flags`: zero or more of `needs_listen`, `needs_context`, `low_confidence`, `human_review`;
- `domain_sensitive`: whether the decision touches a professional fact, term, entity, number, unit, condition, or qualifier;
- `expected_join` when continuity changes;
- `protected`: facts or relationships touched by the decision.

All decision time ranges use the `input.timebase`. If `input.duration` exists, ranges must remain inside it. A decision involving unresolved domain-sensitive material may not be a high-confidence destructive action.

The `boundary` object is required for every decision:

```json
{
  "start_basis": "phrase_boundary",
  "end_basis": "pause",
  "evidence": ["audio", "transcript"],
  "precision": "exact",
  "note": "The cut ends after the speaker completes the qualification."
}
```

Valid boundary bases are `semantic_unit`, `word_boundary`, `phrase_boundary`, `sentence_boundary`, `pause`, `waveform`, `shot_boundary`, `take_boundary`, `manual_marker`, `derived`, and `unknown`. A destructive decision with `precision: approximate` cannot be high-confidence and should carry a review flag.

When `input.completeness.status` is `partial` or `unknown`, destructive decisions cannot be high-confidence. Lower-confidence affected decisions should carry `needs_context`, `low_confidence`, or `human_review`.

## Independence rule

Plans must not contain `execution_handoff` or application-specific `keep_blocks`. A content plan may be reviewed, revised, or manually translated into another system later, but this schema does not define that translation.
