# Verification levels (报告分级)

Every claim this skill makes carries the weakest tier its evidence can support. Never promote a conclusion above its evidence, and never let one tier impersonate another.

| Tier | Backed by | Does NOT mean |
| --- | --- | --- |
| `plan_consistency` PASS | the decision plan is internally consistent and validates (`validate_plan.py` / `validate_alignment_plan.py`): ranges, timebase, boundaries, IDs, gates | the wording or join actually sounds right |
| `visual_frame` PASS | a saved/probed timeline shows the visible result — subtitle text, position, timing — matching intent, read back from the current draft by `jianying-editor` | the audio was actually listened to |
| `human_listening` PASS | a person actually listened to the affected spans and recorded the verdict | anything inferred from transcript, waveform, DOM, screenshot, or media probe |

## Rules

- Without a real human listening record, the auditory verdict is `human_listening UNVERIFIED`. Do not upgrade it from "the waveform looked like a pause" or "the transcript reads clean".
- A structural/transcript derivation is at most `plan_consistency`. Producing a plan never earns `visual_frame`; only a read-back of the rendered/visible timeline does.
- A screenshot or probe of a draft is not listening. A played audio clip that no one evaluated is not `human_listening`.
- ASR output is raw material, not a product. Never report "transcribed" as "the cut is correct" or "subtitles are done".
- When a stage cannot reach a tier, say so plainly and leave the affected unit `needs_listen` / `human_review`. An honest `UNVERIFIED` is a passing result; a borrowed `PASS` is a defect.

Tag each required output and each report row with its tier so the reviewer sees exactly what has and has not been confirmed before packaging.
