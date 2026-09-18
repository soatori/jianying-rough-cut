# Transcript correction gate (修字闸门)

Correct misheard text **before** any content decision. This stage runs after the material-completeness audit and before the orientation and cut passes. It changes only spelling and word form; it never changes what was said, when it happened, or which tokens exist.

## Why it comes first

A misheard proper noun is not a redundant word, and deletion cannot fix it. If you judge cuts while the transcript still contains wrong names, every downstream rule has to route around the error — that is why "an ASR mishearing is never itself a deletion reason" has to exist at all. Fix the text first and that patch becomes unnecessary. See [preference-and-dictionary.md](preference-and-dictionary.md) for where the dictionaries live and how corrections accumulate.

## Hard rules

- Change only text. Never change timing, token count, or a token's stable identity. Editing timing would make every later cut land on the wrong place.
- Change only spelling/form, never meaning. A speaker who misspoke and then re-said the line produced a false start / self-correction: that belongs to the deletion passes, not to this gate.
- When no candidate form is confirmed correct, do not guess. Report it and let a human add it to the dictionary later. Planting an invented name in the user's video is worse than leaving a misheard one; a name written wrong is worse than a name merely misheard.
- Keep spoken Chinese as spoken. If the speaker said "叉", "大模型", or "智能体", that is their utterance — preserve it. This gate resolves multiple spellings of the *same* name and clear mishearings; it does not do translation or term normalization.
- The dictionary is applied every transcription, not "occasionally fix a name": re-running ASR on the same audio can produce different errors, and the dictionary itself, blind to context, can over-normalize (for example turning a genuinely spoken plural proper noun into the singular). So **always read the applied-corrections list after running it** — when you see a wrong change, fix the dictionary, not some downstream patch.

## Inputs and procedure

1. Consult the general dictionary, then the per-user dictionary (see [preference-and-dictionary.md](preference-and-dictionary.md)). Each entry maps one canonical form to its known misrecognized variants.
2. Emit a **correction table**: `original → corrected → surrounding context`, merged across dictionaries, for human review.
3. Only when the dictionary cannot settle a term and the speaker's own script exists, do one context alignment: propose changes where context matches, and report as `不敢定` / unresolved anything it cannot confirm. Never word-diff the script against speech or insert words the speaker did not say.
4. Record unresolved proper nouns and suspected mishearings as `unresolved_terms` / `needs_context` in the orientation output. They lower confidence on any affected decision and must not be turned into deletions.

## Contract with the plan

This stage does not mutate the transcript file; it records what should be corrected. The applied-corrections table and the unresolved list are required outputs (see SKILL.md). A cut decision that touches an uncorrected or unresolved term inherits `domain_sensitive` and stays reviewable; it may not be a high-confidence destructive action.

## Boundary with deletion passes

- Wrong-but-spoken once and re-said correctly → the *deletion* passes handle it (keep the correct take).
- A name merely transcribed wrong, said once → this *gate* handles it (fix text, keep the unit).

Do not delete a unit because its text looks wrong; correct the text first, then judge the unit on meaning.
