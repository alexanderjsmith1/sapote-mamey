# Run observations template

Use this template to write down what you found on one analysis thread: a single BGC, a
reconstruction or a cross-strain comparison. Fill it by hand. It does not run anything.

State the finding first, then the evidence. Tag each claim **observed** (in a named field or file),
**computed** (by a stated rule), **inferred** or **assumed**, and give the basis for each assumption.
Definitions are in the [glossary](../GLOSSARY.md); result fields are explained in
[Read your results](../READING_YOUR_RESULTS.md).

---

**Header:** scope (single BGC / reconstruction / cohort) · bundle and engine versions that produced
the data · source package or archive, with its SHA-256 and provenance receipt when available · release label (PUBLIC/PRIVATE) · who may
read this · affiliation.

The release label records the data's source. It does not decide who may read this record; write
that separately.

**Locus identity.** For a single BGC, give **strain / full node-or-contig / region / BGC alias**,
copied from the source record. If any part cannot be confirmed, write **IDENTITY_BINDING_HOLD** and
do not attribute evidence to the locus. For a reconstruction, list each region's full identity. For
a cohort or workflow observation, write **NOT_APPLICABLE — <reason>** and name the strain roster
instead.

## Observation

What you found, in plain words.

## Quantitative evidence

Give each number with its source path and SHA-256, unit, denominator and how it was calculated.
Keep protein identity and alignment coverage in separate columns; a best hit is not proof of
orthology. Label weighted counts and board scores by their real definitions. Mark a measured
negative differently from not tested, not supplied, not read or unbound. If there are no numbers, say why.
Point to existing files by path and SHA-256; do not copy packages or evidence sets into the record.
For a Mode B observation, name the [profile](../MODEB_PROFILE_MATRIX.md) you used.

## Reflection

The class the evidence fits, in claim-safe words ("biosynthetic capacity consistent with"). Why the
engine read it this way. Which earlier calls this refines or replaces.

## Honest flags

Refuted ideas, likely artifacts, claim-safety limits and what is not established.

## Confidence

Confidence for each claim (high / open / unestablished), keeping class-level, product-level and
activity-level claims apart.

---

*Before you call the record reviewed, open the rendered pages, not just the source. Filling this
template is not an experiment, an activity attribution or a novelty finding.*
