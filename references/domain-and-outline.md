# Content orientation: theme, domain, and outline

Content editing starts with understanding what the material is about. This reference defines the required orientation pass before any definite cut decision.

## Theme hypothesis

Read or listen through the complete available material before naming the topic. Record:

- the topic in plain language;
- a one-sentence thesis or central proposition;
- the purpose of the material;
- the expected audience and knowledge level;
- the main questions, claims, answers, and conclusions;
- alternative interpretations when the evidence supports more than one theme;
- confidence and the evidence supporting the interpretation.

Do not turn a first sentence, title, or isolated subtitle into the theme without checking the whole exchange.

## Professional-domain identification

Classify the material as general, professional, technical, high-stakes, or multi-domain. Candidate domains include medicine, law, finance, science, engineering, manufacturing, technology, products, business, marketing, education, research, sports, games, and media. These are examples, not a closed taxonomy.

For each domain or domain segment, record:

- domain and subdomain;
- domain confidence;
- terminology, acronyms, abbreviations, and likely homophones;
- people, organizations, products, places, and other named entities;
- numbers, units, parameters, ranges, dates, thresholds, and conditions;
- claims, evidence, qualifications, causes, effects, comparisons, and negations;
- words that ASR may have misrecognized;
- unresolved meanings and the evidence needed to resolve them.

The material may change domain during the conversation. Split the domain map by time range when necessary instead of forcing one label across the whole source.

## Domain-sensitive editing gate

When a term, fact, or domain is unresolved:

- do not delete or shorten the affected sentence merely because it resembles another sentence;
- do not remove a number, unit, qualifier, condition, negation, or named entity as padding;
- do not merge two technical statements until their premises and constraints match;
- mark the unit `needs_context` or `human_review`;
- preserve the original audio and text evidence in the decision record.

For medical, legal, financial, safety, or similarly high-stakes material, use authoritative references when external verification is appropriate. If verification is unavailable, leave the affected decision unresolved rather than guessing.

## Information outline

Build the outline from the source. It may be chronological, topical, question-and-answer, problem/reason/solution, tutorial steps, conclusion-first, or another structure supported by the material.

Record an ordered set of modules and units. Each unit should include:

- source time range and timebase;
- speaker and per-unit function;
- title or summary;
- role: opening, background, question, answer, claim, explanation, example, evidence, qualification, conclusion, CTA, digression, or low-information speech;
- topic module;
- dependencies on earlier units;
- information added compared with previous units;
- domain risk and protected facts;
- transcription and timing confidence.

Keep the original order in the source outline even if a later recommendation reorders complete units. A recommended structure must be traceable back to these source units.

## Completion gate

The orientation stage is complete only when the report contains a theme hypothesis, domain analysis, protected facts, and an outline with confidence. If any of these remains uncertain, the rough-cut plan may contain review candidates but may not contain a high-confidence destructive decision for the affected range.
