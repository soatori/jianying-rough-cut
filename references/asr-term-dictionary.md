# General ASR term dictionary

A **small, deliberately domain-neutral** baseline of canonical spellings and their frequent misrecognitions, consumed by the transcript correction gate ([transcript-correction-gate.md](transcript-correction-gate.md)). This skill edits interviews, lectures, tutorials, and talks across any field, so the general list stays tiny and balanced. Real coverage comes from the **per-user dictionary** in [preference-and-dictionary.md](preference-and-dictionary.md), which grows from each project via the Pass 3 retrospective. Add to *this* file only cross-domain terms a human confirms.

## How to read it

- One row maps a canonical form to the variants ASR tends to produce. Only **table rows** are parsed; prose and bullet lists are ignored.
- Correct only spelling/form. Never translate, never normalize a term the speaker genuinely chose, never change timing.
- If a term appears with no confirmable correct spelling, leave it and report it. A wrong-but-invented name is worse than a misheard one.

## Illustrative entries (add per-domain packs to the user dictionary, not here)

| Canonical | Frequent misrecognitions |
| --- | --- |
| OpenAI | openai / Open AI / 欧盆 AI |
| GitHub | github / Git Hub / 吉特哈布 |
| CLI | cli / C L I / 命令行 |
| API | api / A P I |
| statute of limitations | 诉讼时效限制 / 时效限制 |
| deponent | 被告证人 / 证言人 |
| myocardial infarction | 心肌梗塞 / 心机梗死 |
| ejection fraction | 射血分数 / 喷射分数 |
| amortization | 摊销 / 摊消 |
| liquidity ratio | 流动比率 / 流东比率 |

These rows show the *shape* of an entry across tech / law / medicine / finance; they are not the working dictionary. A project's actual proper nouns belong in the user dictionary.

## Keep spoken language as spoken

When a speaker uses a Chinese term, an acronym, or their own wording, that is their utterance — preserve it. This dictionary resolves multiple spellings of one name and clear mishearings; it does not do translation or force term standardization. The test is: would the speaker have written it this way? Yes → correct. No → leave it. Likewise, a plural or possessive proper noun the speaker truly said must not be silently normalized to the singular.

## Unresolved (add here only after a human confirms)

```text
Report  "<X> / <x-variant> each appear once, both look misheard, not in dictionary, left unchanged"
Never    guess a spelling to fill the gap
```
