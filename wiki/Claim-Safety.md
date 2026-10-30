<a id="claim-safety--the-language-contract-every-output-obeys"></a>
# Claim safety for interpreting outputs

Use evidence-bound language when interpreting outputs.  
This page is for anyone writing or reviewing results.

Use class-level capacity language and defer judgment where the evidence requires it. Some output
surfaces and tests implement claim-safety checks, but their coverage is not universal. Review the
selected output and its source evidence before making a claim; use these framings when writing.

## The core rules

1. **Similarity is not identity.** A KnownClusterBlast / MIBiG hit means "this cluster resembles
   the reference at the gene/architecture level" — a *class-level hypothesis about biosynthetic
   capacity*, never "this strain makes compound X."
2. **A diagnostic gene is capacity, not identity.** Finding a halogenase, a KS domain, or a
   resistance marker says the machinery *could* be present; it does not name a product.
3. **Bioactivity is strain/extract-level context.** Even measured activity from the same strain does not establish locus-specific causality; a BGC claim needs separately governed linkage evidence.
   Literature bioactivity of a compound family never transfers to an uncharacterized cluster.
4. **Expression is "unknown" without culture data.** Presence of a BGC says nothing about whether
   it is transcribed, translated, or productive under any condition.
5. **rDNA / 16S / ITS identity is a neighborhood, not a species call.** Marker identity anchors a
   strain to a clade; species delimitation needs genome-scale evidence (ANI / genome trees), and
   calls within ~1% of the 95% ANI boundary are *boundary/indeterminate*, not confident.
6. **Missing evidence is not absence.** Missing, unrun, failed or truncated evidence remains
   unavailable or incomplete. Only a completed, scoped search with a recorded no-hit result supports
   "not detected under these parameters"; it never establishes "the strain lacks X."
7. **Every metric carries its denominator.** Report the numerator, denominator and defined
   search scope. Absence from a reference set does not establish novelty.
8. **An RG-GMCI pair is a candidate link.** It is homology-guided; it does not join contigs.
9. **Every individual BGC claim carries complete identity:** `strain / full node-or-contig / region / BGC alias`, copied from one bound source record. A locked alias or node/region-only citation is insufficient. Tree statements retain the exact tip label and bound input/gate receipt. Missing or conflicting identity is a hold.

## Where it is enforced

- **Triage priors are routing, not scores** — `scoring.py` computes attention-routing floors; the
  judgment tiers (Sapote-slim / Sapote full, Markdown protocols) make the interpretive calls, and
  even those emit class-level language.
- **Gates before figures** — `tree_sanity_check` and the 8-item analysis sign-off must PASS before
  a phylogenetic figure is shown; a gate FAIL is an engineering/quality finding needing diagnosis. Long branches can reflect alignment, reference, model or biological factors; the failure does not prove novelty. Inspect the sign-off report because its advisory CLI exits 0 even when issues remain.
- **Release and disclosure checks** — omitted public authority defaults to PRIVATE, regardless
  of identifier prefix. Exact profile assignments or an admitted explicit PUBLIC request can
  select a run label, subject to private guards. Review the actual release decision and the
  [privacy/evidence contract](../docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) before sharing.
  Identifier tests and release audits have bounded scopes; a PUBLIC label or passing test is not
  proof that every private field was removed or permission to publish.
- **Mandatory phrasing in packages** — compound names from reference hits are labeled as
  class-level hypotheses; bioactivity fields carry the strain-level-context caveat; expression
  fields default to "unknown."

## Templates you can lift

> "<strain> / <full node-or-contig> / <region> / <BGC alias> resembles the <family> reference cluster (<n>/<m> genes, KCB) — a class-level
> hypothesis of <family>-like biosynthetic capacity. No structural or bioactivity claim is made;
> expression is unknown without culture data."

> "On the <marker> tree (gate PASSED, <support>), strain X places in the neighborhood of <clade> —
> an anchor, not a species call; species-level placement awaits genome/ANI evidence."

*The point of the contract: the pipeline's credibility rests on never claiming more than the
evidence supports — the interesting result survives review precisely because it was stated
carefully.*
