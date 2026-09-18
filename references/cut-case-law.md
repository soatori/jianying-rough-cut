# Cut case-law

Worked precedents for the deletion passes. Each entry is exactly four lines: **source (in playback order) → delete → remaining reads as → why.** The rules live in [speech-cleanup.md](speech-cleanup.md); this file resolves hard or ambiguous cases by analogy. Precedence: user preference > user case-law > these general cases. Examples keep the original Chinese utterances because the point is prosody and word order, not translation. 【…】 marks the deleted span.

## R1 · Whole-sentence multiple retakes (scan 1, high risk)

```text
source:   现在很少刷叉了【因为今天有什么值得研究已经被我外包给了】【因为今天有什么值得研究已经被我外】【因】为今天有什么值得研究已经被我外包给了Codex和Grok
delete:   the two incomplete earlier starts
remaining:现在很少刷叉了，因为今天有什么值得研究已经被我外包给了Codex和Grok
why:      the same opening was recorded three times; keep only the last complete take.
          Sentence-level deletion is high risk: also list it in the repeated-attempt rollup.
```

## R2 · Intra-sentence repeat (scan 1, low risk)

```text
source:   给我做一份AI日报【最近我就关心】最近我就很关心剪辑
delete:   最近我就关心
remaining:给我做一份AI日报。最近我就很关心剪辑
why:      the first copy is an incomplete start, the second is complete; delete only the
          leading duplicate fragment, do not take the whole sentence with it.
```

## R3 · Stutter fragments (scan 2, low risk)

```text
source:   给了一篇AI日报给我【我看一眼就能看】【就能】我看一眼就能看到他和
delete:   two consecutive incomplete starts
remaining:给了一篇AI日报给我，我看一眼就能看到他和…
why:      a run of dangling fragments is one group; delete all, keep the final complete pass.
```

## R4 · Divergent retake (scan 2, high risk)

```text
source:   【多数Agent能搜到的网页】多数Agent它能搜出网页但Grok…
delete:   the first version
remaining:多数Agent它能搜出网页，但Grok…
why:      same opening, divergent second half → high risk. If both copies carry the same
          information, keep the later; if each adds something independent, that is not
          repetition but supplement — keep both and do not list it as a candidate.
```

## R5 · Wrong proper noun on the deleted copy (scan 3, high risk)

```text
source:   【比如我就让他跟踪】【比如我就让Gokul跟踪Codex团队他就找到了…】比如我让grok跟踪
delete:   the two earlier versions, including the one with the misheard name
remaining:比如我让grok跟踪…
why:      wrong name + restart → keep the correct version. A misheard name inside a *deleted*
          copy needs no fixing; but a misheard name inside the *kept* copy must already be
          corrected by the gate before deletion — deletion cannot repair a misheard word.
```

## R6 · Single filler kept (scan 5, counter-example)

```text
source:   这个功能呢它其实…
delete:   (nothing)
remaining:unchanged
why:      one natural particle is kept; deleting it makes the delivery feel fake. Only a run of
          two or more meaningless particles becomes a low-risk group. Density and tolerance follow
          the user preference file.
```

## Promotion

A pattern the user repeatedly restores or adds (from the Pass 3 diff) is logged as a pending case in the preference file; on its third occurrence, propose promoting it into this file — and only edit this file after human approval. Correction-type precedents (a cut the human vetoed) are still scarce; record them here in the same four-line format as they arise.
