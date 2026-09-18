# Speech cleanup: five single-criterion scans

Refinement (Pass 2) is run as five separate reads of the same material in **playback order**, carrying one criterion each. Reading once with six criteria in mind is measurably worse than five focused passes; each pass produces a small, checkable set of candidates. A candidate found in an earlier pass is not re-touched by later passes; conflicts are resolved in the summary step.

Precedence of judgment sources: **user preference > user case-law > general case-law > the defaults below.** Rules live here; worked examples live in [cut-case-law.md](cut-case-law.md).

## The five scans

1. **Repetition.** Inter-sentence repeats (same idea twice → delete the earlier) and intra-sentence repeats (delete only the leading duplicate fragment, keep the complete tail). Most objective: two near-identical adjacent attempts. Whole-sentence and divergent-retake repeats are high risk → keep in the repeated-attempt rollup (see below).
2. **False starts and self-corrections.** A fragment clearly abandoned mid-way, or a re-said line that restarts the same thought. Delete the abandoned lead-in, keep the complete version. Preserve one natural connector when several restarts repeat the same lead-in.
3. **Misspoken retakes (wrong number / wrong name).** A wrong fact or proper noun that the speaker later restates correctly. Delete the wrong attempt, keep the correct one. Default is keep-the-later-correct-version. Note: a name *misheard by ASR but said once correctly* is **not** this case — it is a correction-gate item ([transcript-correction-gate.md](transcript-correction-gate.md)), never a deletion.
4. **English stutters.** Repeated word-initials, letters, or syllables in English tokens (do not match only Chinese). Cut at word level only when consonant/vowel boundaries and prosody permit a clean splice.
5. **Fillers and discourse markers.** The most subjective; tune density and tolerance to the preference file. A single natural particle (e.g. "呢", "那个", "well") is conservatively kept — deleting it makes delivery feel fake. Only a run of two-plus meaningless particles is a group low-risk candidate.

## Fillers and discourse markers

No token is an unconditional blacklist. "Then", "so", "actually", "right", "this" can carry structure, stance, response, reference, or emotion. Delete only when the semantic contribution is empty **and** the resulting audio stays natural. If removal produces a hard splice, keep it or shorten only the adjacent pause.

## Repeated-attempt rule

1. Confirm the attempts express the same intended idea.
2. Identify the complete version — the one with the necessary subject, setup, transition, qualifier, and conclusion.
3. Remove only abandoned, wrong, dangling, or fully covered material.
4. Prefer complete + accurate + natural + well connected. Do not mechanically keep the last take, and do not keep the shortest.

When several attempts each add independent information, that is not repetition — it is complement; keep both and do not list them as candidates.

## Pass separation and the two-state rule

Do not mix uncertain micro-cleanup into Pass 1. Keep content structure auditable without dozens of word-level cuts. Pass 2 may be aggressive, but every kept candidate is already self-verified; unresolved joins stay `review` rather than becoming a "suggested delete". A cut is committed or dropped or marked `review` — never a deferred third state.

## Summary and self-read

After the five scans, merge into:

- the **refinement decision table** (one row per candidate: range, scan type, "delete →", "remaining reads as", risk, basis); and
- the **repeated-attempt rollup** (which line, how many times, which kept, which removed, risk) — because a per-word table cannot show take counts, which is exactly what a human most wants to check. See [content-analysis.md](content-analysis.md).

Then read the post-cut text once more in playback order and revoke any line that no longer reads through. Risk only changes how hard you verify; it never changes the output into a "needs approval" placeholder.
