# Audio, waveform, pauses, and cut boundaries

## Evidence hierarchy

Use waveform and silence detection to locate candidates. Use actual listening plus semantics to decide. A low-amplitude region can be a breath, room tone, trailing consonant, overlap, or edit damage; duration alone does not identify its function.

## Pause classes

Classify a pause as sentence-internal hesitation, sentence boundary, speaker handoff, topic shift, emphasis, emotional beat, breath, failed-take gap, or abnormal edit gap.

Default to compression rather than removal. Preserve enough room for articulation and speaker change. Topic shifts, contrast, emotion, and emphasis may need more time than ordinary sentence boundaries.

Any numerical threshold is a configurable detector, not a deletion rule. Calibrate it to speaking rate, language, recording noise, platform rhythm, and the requested style.

## Boundary checks

For each proposed local cut:

- listen before, across, and after the join;
- avoid clipping plosives, fricatives, vowels, word-final consonants, laughter, and breaths that carry phrasing;
- inspect room-tone and noise-floor discontinuities;
- check whether two speakers overlap;
- preserve sync when picture is tied to production audio;
- flag clicks, abrupt ambience changes, or unnaturally accelerated delivery.

## Already-edited material

Distinguish source defects from edit defects. Look for tiny residual syllables, duplicate frames of speech, reversed source order, missing setup, abrupt room-tone changes, and over-tightened speaker handoffs. Compare against the source or an earlier cut when available.

