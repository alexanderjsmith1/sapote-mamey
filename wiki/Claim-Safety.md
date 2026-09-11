# Claim-safety — the language contract every output obeys

Sapote-Mamey's outputs are **class-level hypotheses with judgment deferred**. This is not a
disclaimer bolted on at the end — it is a contract enforced in the emitted text, the tests, and the
review gates. If you edit any output surface, keep the language; if you write about results, use
these framings.

## The core rules

1. **Similarity is not identity.** A KnownClusterBlast / MIBiG hit means "this cluster resembles
   the reference at the gene/architecture level" — a *class-level hypothesis about biosynthetic
   capacity*, never "this strain makes compound X."
2. **A diagnostic gene is capacity, not identity.** Finding a halogenase, a KS domain, or a
   resistance marker says the machinery *could* be present; it does not name a product.
3. **Bioactivity is strain-level context only** unless wet-lab evidence exists for that strain.
   Literature bioactivity of a compound family never transfers to an uncharacterized cluster.
4. **Expression is "unknown" without culture data.** Presence of a BGC says nothing about whether
   it is transcribed, translated, or productive under any condition.
5. **rDNA / 16S / ITS identity is a neighborhood, not a species call.** Marker identity anchors a
   strain to a clade; species delimitation needs genome-scale evidence (ANI / genome trees), and
   calls within ~1% of the 95% ANI boundary are *boundary/indeterminate*, not confident.
6. **Missing evidence is not absence.** An empty scan or absent hit is "not detected under these
   parameters," never "the strain lacks X."
7. **Every metric carries its denominator.** "44 novel GCFs" is meaningless without "of 1,753
   governed"; quote counts with their scope.
8. **Every claim traces to a stable node.** BGC statements cite the locked `bgc_id`; tree
   statements cite the tip label and the gate receipt. No node, no claim.

## Where it is enforced

- **Triage priors are routing, not scores** — `scoring.py` computes attention-routing floors; the
  judgment tiers (Sapote-slim / Sapote full, Markdown protocols) make the interpretive calls, and
  even those emit class-level language.
- **Gates before figures** — `tree_sanity_check` and the 8-item analysis sign-off must PASS before
  a phylogenetic figure is shown; a gate FAIL can itself be the finding (a genuinely divergent
  taxon trips long-branch checks — report the numbers, withhold the figure).
- **Release-tier redaction** — unpublished strain identifiers never leak into a public tier
  (`tests/test_no_unpublished_ids_in_public_tier.py`); prefix-based release derivation fails safe
  to PRIVATE for unrecognized prefixes.
- **Mandatory phrasing in packages** — compound names from reference hits are labeled as
  class-level hypotheses; bioactivity fields carry the strain-level-context caveat; expression
  fields default to "unknown."

## Templates you can lift

> "BGC NODE_x region y matches the <family> reference cluster (<n>/<m> genes, KCB) — a class-level
> hypothesis of <family>-like biosynthetic capacity. No structural or bioactivity claim is made;
> expression is unknown without culture data."

> "On the <marker> tree (gate PASSED, <support>), strain X places in the neighborhood of <clade> —
> an anchor, not a species call; species-level placement awaits genome/ANI evidence."

*The point of the contract: the pipeline's credibility rests on never claiming more than the
evidence supports — the interesting result survives review precisely because it was stated
carefully.*
