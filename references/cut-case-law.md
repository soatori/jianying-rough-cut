# Cut case-law

Reusable precedents for speech-cleanup decisions. These examples describe structural patterns rather than quoting a project transcript. The detailed rules live in [speech-cleanup.md](speech-cleanup.md); use this page only when an ambiguous case matches a pattern. Precedence: explicit user preference > approved external case-law > these general patterns.

## R1 · Whole-sentence multiple retakes (high risk)

```text
source:   [complete opening] [incomplete restart] [incomplete restart] [complete final take]
delete:   the incomplete earlier starts
remaining:[one complete take]
why:      keep the complete, accurate take. Sentence-level deletion is high risk; include it
          in the repeated-attempt rollup and verify the surrounding context.
```

## R2 · Intra-sentence repeated start (low risk)

```text
source:   [sentence lead-in] [incomplete duplicate phrase] [complete phrase]
delete:   only the incomplete duplicate fragment
remaining:[lead-in plus complete phrase]
why:      remove the restart without deleting the complete statement or splitting its meaning.
```

## R3 · Stutter fragments (low risk)

```text
source:   [complete clause] [series of dangling fragments] [complete continuation]
delete:   the incomplete fragment run
remaining:[complete clause plus continuation]
why:      treat connected restart fragments as one local cleanup group; preserve the final complete pass.
```

## R4 · Divergent retake (high risk)

```text
source:   [shared opening + version A] [shared opening + version B]
delete:   nothing until the versions are compared in context
remaining:[keep both if each adds independent information; otherwise keep the complete, accurate take]
why:      a shared opening does not make two divergent endings redundant; unresolved cases need review.
```

## R5 · Misheard term on a discarded take (high risk)

```text
source:   [earlier take with uncertain term] [later take with candidate correction]
delete:   only after the transcript-correction gate confirms the kept wording
remaining:[a complete take with resolved terminology]
why:      a wrong term is not by itself a deletion reason. Correct the kept text before deciding;
          never use a deletion to hide an unresolved recognition error.
```

## R6 · Single filler kept (counter-example)

```text
source:   [complete sentence with one natural discourse marker]
delete:   nothing
remaining:[unchanged]
why:      removing every natural marker can make delivery sound artificial. Apply the user's
          established density preference; otherwise preserve it unless it impairs comprehension.
```

## R7 · Countdown or slate lead-in (low risk)

```text
source:   [recording cue] [first real content]
delete:   the cue before content starts
remaining:[first real content onward]
why:      a countdown or slate is not content. Actual explanation or qualification before the
          main statement remains subject to the domain-and-outline gate.
```

## Promotion

A repeated, human-confirmed pattern may be proposed for this generic page only after its project-specific evidence has been abstracted and approved. Store original wording and case details outside the skill package.
