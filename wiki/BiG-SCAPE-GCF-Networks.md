# BiG-SCAPE GCF networks — grouping clusters without over-claiming

Learn how to prepare and interpret gene cluster family networks.  
This page is for researchers using BiG-SCAPE with existing evidence.

*Source of truth: `docs/BIGSCAPE_GCF_WORKFLOW.md`, under `docs/LLM_COMPANION_TOOL_PROTOCOL.md`.
BiG-SCAPE clustering has separate outputs, and its families are **run-specific similarity groups, not compound identities**. Optional Mamey ingestion can rewrite Mode B cards in place; it is not an immutable overlay. Preserve the original package/cards and use a separately bound working copy for any selected integration. See [integration limits](../docs/BIGSCAPE_MAMEY_INTEGRATION.md).*

## What it does

BiG-SCAPE groups antiSMASH **region GBKs** by Pfam domain architecture and sequence features into
Gene Cluster Families (GCFs) at chosen distance cutoffs. A GCF says "these regions look like the
same kind of machinery in this run" — a class-level statement that depends on the cutoff, the
input set, and the version.

## Input contract (provenance-first)

- Stage region GBKs from an antiSMASH ZIP or an existing folder of region GBKs,
  following the preparer's input rules. Do not substitute whole-genome FASTA or
  Mamey CSV rows. Bind folder inputs to their source provenance separately.
- `tools/bigscape_prep.py` writes `STAGED_MEMBERS.tsv` with strain, source, source SHA-256 (blank
  for folder inputs), member path, bytes, SHA-256, record id, region and staged file. It has no BGC
  ID, antiSMASH version or cohort-vs-reference flag. Bind those through a separate checked crosswalk,
  and hold any member the crosswalk cannot bind.
- Skip macOS AppleDouble members (`__MACOSX/`, `._*`); quarantine malformed/colliding locators.

## Run-type declaration (decides what language you may use)

| run type | what it licenses |
|---|---|
| **cohort-only** | within-run family sharing only — NO known/novel language |
| **cohort-plus-MIBiG** | reference-panel anchoring (record MIBiG version + hashes; never auto-download) |
| **reference-augmented** | other reference GBKs, each with provenance |

A GCF that contains a MIBiG reference is an *anchor to a characterized family*; a cohort-only GCF
licenses no novelty claim at all — "not in this run's families" is not "novel."

## Canonical run shape (BiG-SCAPE 2.x)

`bigscape cluster` with the Pfam-A path, `--record-type region`, `--classify category`,
`--gcf-cutoffs 0.3,0.5,0.7`, `--include-singletons` — but the locally verified `--help` is
authoritative over any template: capture the exact command in `COMMAND.sh` and the version in
`RUN_MANIFEST.json`. The bundled launcher checks that Pfam-A.hmm and its four pressed companions
(`.h3f`, `.h3i`, `.h3m`, `.h3p`) exist. That presence check does not establish that
they came from the same press; verify their shared provenance before use. Check that
`fasttree`/`FastTree` naming resolves (2.0.3 may call the lowercase name; a run-local symlink is an
acceptable, *recorded* recovery).

**Retain the selected workflow's alignment policy.** This workflow recommends
`auto` for fragmented inputs, but inspect the installed version's help, defaults
and actual command rather than inferring every pair's behavior from that label.
Changing alignment policy is a method choice; review its effect on the comparison
and preserve the original run instead of silently substituting `global`.

## Reading the output honestly

- Families are **cutoff-dependent**: report the cutoff with every family count, and expect
  singletons (they are data, not failures — `--include-singletons` exists for a reason).
- A family shared across strains = shared machinery class in this run; product identity, activity,
  and expression remain unclaimed.
- Fragmented BGCs can land apart from their intact relatives (see the RG-GMCI split-pathway rules)
  — check the fragment surfacing before reading a "family split" as biology.
- Never quote a family count without its denominator (n regions, n strains, cutoff, run type).

*Claim-safety: GCF membership is a similarity statement under one parameterization of one run.
Judgment — including any novelty read — is deferred and requires the declared reference context.*

## Related pages

For individual-locus review, continue to [Mode B](Mode-B.md); for protein comparisons, see [BLASTp](BLASTp-Novelty.md).
