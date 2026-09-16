# Subtitle proofreading and audio alignment

This stage runs after the rough-cut content pass has been executed and before packaging begins. It corrects the current Jianying-recognized subtitles against the edited timeline; it is not a packaging operation.

## Inputs and order

1. Save and probe the current edited timeline through `jianying-editor`.
2. Reconstruct the edited timeline audio from the current segment order, source ranges, speed, and handles where applicable.
3. Read the current recognized text and compare it with the actual speech.
4. Correct names, terms, numbers, units, models, negation, conditions, causality, and ASR segmentation.
5. Use listening and waveform evidence to propose boundaries.
6. Review the complete subtitle list in context, then output an application-independent `subtitle_alignment_plan`.
7. After human approval, let `jianying-editor` resolve the semantic ranges to current draft segments and apply the plan.
8. Independently read back and validate before marking `subtitle_alignment=approved`.

If a later rough-cut change changes source order, source range, speed, or duration, repeat this stage. A packaging-only style change does not require full re-alignment unless it changes subtitle timing or segmentation.

## Hybrid boundary policy

Use audio as the default boundary authority. Use local picture-lock only when the picture provides a real semantic constraint:

- do not split a continuous word or phrase only because a shot cuts;
- snap to a shot boundary when it coincides with a natural pause, sentence boundary, speaker change, or deliberate visual binding;
- use local picture-lock for parameters, devices, values, or steps that must remain attached to the visible object;
- send audio/picture conflicts to human review.

Record `mode`, `basis`, evidence, confidence, and review status for both the start and end of every subtitle unit.

## Evidence cautions

Waveform and silence thresholds locate candidates; they do not authorize deletion or splitting by themselves. The current project may use values such as a 10ms hop, 25ms window, 120ms pause floor, and 350ms cap, but those are configurable detector defaults.

Word-level timestamps are a cross-check. If their health check fails or the text and timing disagree, fall back to audio, semantics, and manual listening rather than treating word times as authoritative.
