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
4. **Expression needs direct evidence for the recorded condition.** A BGC annotation
   alone does not establish transcription, translation or product formation. Keep
   those measurements and their conditions separate.
5. **rDNA / 16S / ITS identity is a neighborhood, not a species call.** Marker similarity supports a
   placement hypothesis under a reference scope, not automatic species assignment.
   For bacterial ANI comparisons, retain the selected method, aligned fraction,
   reference identity and decision rule. A value near a chosen threshold needs
   review; neither a universal 95% rule nor a fixed ±1% band establishes a species call.
6. **Missing evidence is not absence.** Missing, unrun, failed or truncated evidence remains
   unavailable or incomplete. Only a completed, scoped search with a recorded no-hit result supports
   "not detected under these parameters"; it never establishes "the strain lacks X."
7. **Every metric carries its denominator.** Report the numerator, denominator and defined
   search scope. Absence from a reference set does not establish novelty.
8. **An RG-GMCI pair is a candidate link.** It is homology-guided; it does not join contigs.
9. **Every individual BGC claim carries complete identity:** `strain / full node-or-contig / region / BGC alias`, copied from one bound source record. A locked alias or node/region-only citation is insufficient. Tree statements retain the exact tip label and bound input/gate receipt. Missing or conflicting identity is a hold.

## Where it is enforced

- **Triage scores are routing scores (priors)** — `scoring.py` stores numeric AB, AF and novelty
  scores and uses them to route attention. They are not measured activity, calibrated probabilities
  or biological proof. The interpretive calls are made later, in written Mode B cards and reports
  ([Mode B](Mode-B.md)), and those use class-level language.
- **Gates before figures** — `tree_sanity_check` must PASS before a phylogenetic figure is shown,
  and `tools/signoff_check.py` attempts six advisory check categories; an empty
  or unparseable tree can return before those checks complete. Its usage errors
  return 2, while inspection remains advisory; a gate FAIL is an engineering/quality finding needing diagnosis. Long branches can reflect alignment, reference, model or biological factors; the failure does not prove novelty. Inspect the sign-off report because its advisory CLI exits 0 even when issues remain.
- **Release and disclosure checks** — omitted public authority defaults to PRIVATE, regardless
  of identifier prefix. Exact profile assignments or an admitted explicit PUBLIC request can
  select a run label, subject to private guards. Review the actual release decision and the
  [privacy/evidence contract](../docs/PORTABLE_STRAIN_PRIVACY_AND_EVIDENCE.md) before sharing.
  Identifier tests and release audits have bounded scopes; a PUBLIC label or passing test is not
  proof that every private field was removed or permission to publish.
- **Selected output wording** — some writers add reference-similarity and
  strain-level-context caveats or unknown expression defaults. Inspect the actual
  artifact and its producer; these are not universal coverage guarantees.

## Templates you can lift

> "`<strain> / <full node-or-contig> / <region> / <BGC alias>` resembles the
> `<family>` reference (`<n>/<m>` genes under the stated KCB scope), supporting
> a family-like capacity hypothesis. Product identity and activity remain unestablished;
> expression requires direct evidence under the recorded conditions."

> "On the `<marker>` tree (named gate passed, `<support>`), `<exact tip label>`
> places near `<clade>` under the stated alignment, reference and model scope.
> This is not automatic species assignment; further evidence depends on the lineage and question."

*The point of the contract: the pipeline's credibility rests on never claiming more than the
evidence supports — the interesting result survives review precisely because it was stated
carefully.*
