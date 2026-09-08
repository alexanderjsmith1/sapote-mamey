# Prose-Style Field Card

The one-page version of the house prose style for Sapote-authored text (Mode B narrative
sections, synopses, lay guides, ecological synthesis, cross-strain write-ups, progress notes).
Companion to the **Voice** discipline in `SKILL.md`. This is a debugger for the specific way
LLM prose drifts toward a padded corporate-explainer mean — it is **not** a general style guide,
and it never overrides Priority #0 (claim safety). Where the two meet, claim safety wins; the
one section below marks exactly where.

**Highest-leverage use: the audit pass.** Write the draft first, then scan it against the three
passes at the bottom and fix the hits that matter. Applying the rules while drafting works too,
but the audit is where the tells actually get caught.

## Where claim safety overrides this card (read first)

The anti-LLM-prose rules say "don't hedge, take a side, cut the disclaimers." Science-discipline
text does the opposite **on purpose**, and that is correct here:

- **Keep the capacity/similarity hedges.** "Capacity consistent with," "similarity, not identity,"
  "candidate," "predicted," "may encode" are load-bearing claim-safety language, not padding. Never
  cut them to sound more confident.
- **Keep provenance and NODE·region tags.** They read as scaffolding to a prose linter; they are
  required evidence anchors here.
- **Keep earned uncertainty.** "The extract inhibits; which BGC is responsible is unknown" is a
  precise claim, not a hedge to delete.

The rules below apply to *everything else* — the connective prose, the explanations, the framing.

## Vocabulary — the tells to cut

Any one is fine; three in a paragraph reads as machine-generated. Replace with the specific word.

| Drop | Use |
|---|---|
| delve, delve into | look at, go into, or cut |
| robust | reliable, well-tested (or the specific property) |
| leverage (verb) | use |
| facilitate | help, let, make easier |
| navigate (when nothing is being navigated) | handle, deal with |
| enhance | improve (or name the change) |
| foster | build, grow, encourage |
| streamline | simplify (or name the change) |
| underscore, highlight, emphasize (as "show") | show, prove, argue |
| pivotal, a testament to | important, evidence of (or name the impact) |
| showcase (verb) | show, feature, include |
| myriad, plethora | many, or a number |
| intricate, tapestry, landscape (abstract), a journey (metaphor) | name the concrete thing |

Domain caution: `enhance`/`robust` show up legitimately in package/gate descriptions ("a more
robust check"). The rule is about prose, not code comments — don't lint the machinery.

## Significance-puffery — cut it

Phrases that assert importance without showing it: "stands as / serves as / represents a...",
"plays a crucial/pivotal role in...", "a turning point in...", "shapes the future of...", "in
today's fast-paced world." If you can't replace the phrase with the concrete evidence, the
sentence shouldn't be there. This is the same instinct as **receipts, not adjectives** — "the gate
passed" needs the number, not "the pipeline is robust."

## Scaffolding openers — cut on sight

"It's important to note that," "It's worth mentioning," "One could argue," "Many people find,"
"Most experts agree." If it's important, say it. If a claim needs a source, name it.

## Transition padding

"Additionally," "Furthermore," "Moreover," "In conclusion," "Ultimately," "In summary" at the
start of a sentence — cut, or restructure so the link is implicit.

## Sentence structure

- **Use "is."** LLMs swap plain "is/are" for "serves as / represents / constitutes / marks." "The
  siderophore cluster is the strain's clearest iron-economy signal" beats "...serves as."
- **Drop "not X but Y" parallelisms** unless the negation corrects a real misreading. "It's about
  the coverage" lands harder than "it's not just about the score, it's about the coverage."
  (Exception that recurs here: "similarity, **not** identity" — that negation is doing real work.
  Keep it.)
- **Kill rule-of-three padding.** "fast, simple, and powerful." If dropping the third item loses
  nothing, drop it. Two real leads beat three where one is filler.
- **No false ranges.** "From healthcare to finance" has no scale; "from beginner to expert" does.
  If you can't name a coherent middle, it's not a range.
- **Repeat the name.** Don't shuffle "BGC025" → "the cluster" → "this locus" → "the assembly line"
  to avoid repetition. The name and pronouns are fine; the synonym shuffle reads as AI.

## Structure and formatting

- **Break the LLM outline** (definition → three benefits → three challenges → "despite these
  challenges" → "looking ahead"). Open with the specific finding, not a textbook definition. Don't
  always do three of anything. Drop the "future outlook" close unless there's an actual prediction.
- **Don't over-bold.** Bold is for defined terms and scan-anchor items, not emphasis inside a
  sentence. A paragraph with a bolded clause every other line reads as machine scaffolding. (Lay
  guides legitimately bold the teaching points and NAPAA/exclusion flags — that's anchoring, fine.)
- **Em-dashes: at most one per paragraph of prose.** They're right for a parenthetical stronger
  than a comma or an abrupt turn; wrong as default connective glue. Replace the rest with commas,
  periods, or parentheses. **Prose only** — `NODE_6·region001 — nocobactin NA` locus labels and
  table-cell dashes are data formatting, not prose, and don't count. (This is the one rule a naive
  grep over-flags in this project; scope it to prose.)
- **Sentence case headings** in guides, reports, and READMEs ("Why this matters"), not Title Case
  ("Why This Matters"). Title Case only for formal document titles and citations.
- **No motivational kicker.** Don't close with "the future belongs to..." or "with the right tools,
  anything is possible." End on the strongest concrete thing, a real question, or a specific next
  action ("C18 LC-MS on the EtOAc extract, days 4 and 7").
- **No knowledge-cutoff disclaimers in shipped text.** If something's unknown, say so plainly (which
  the science discipline already requires) — don't prefix speculation with an "as of my last update"
  banner.

## Audit checklist — three passes, ~a minute each

1. **Vocabulary.** grep the draft for: delve robust leverage facilitate navigate enhance foster
   streamline underscore pivotal testament showcase myriad plethora intricate tapestry landscape
   journey. Each hit: is this the most specific word? Usually not. (Skip code/gate descriptions.)
2. **Scaffolding.** Search: "It's important to note," "Additionally," "Furthermore," "Moreover," "In
   conclusion," "Ultimately," "Despite these challenges," "Looking ahead," "in today's." Cut or
   rewrite.
3. **Rhythm.** Read it aloud. Same paragraph length every time → vary it. Every list exactly three
   → vary it. More than one prose em-dash per paragraph → thin them. Bolded clause every other line
   → strip to defined terms.

A paragraph that survives all three, and still carries its claim-safety hedges, is done.

## Provenance

Adapted from the "Signs of AI writing" pattern catalogue (Wikipedia) via a project rules file, then
reconciled against Sapote's claim-safety discipline — the override section above is the reconciliation
and takes precedence. This card is prescriptive (rules to break the patterns); the source is
descriptive (the patterns themselves).
