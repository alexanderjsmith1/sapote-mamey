# BiG-SCAPE GCF networks — grouping clusters without over-claiming

*Source of truth: `docs/BIGSCAPE_GCF_WORKFLOW.md` (v9.7.401), under `docs/LLM_COMPANION_TOOL_PROTOCOL.md`.
BiG-SCAPE is a downstream companion: it never alters a sealed Mamey run, and its families are
**run-specific similarity groups, not compound identities**.*

## What it does

BiG-SCAPE groups antiSMASH **region GBKs** by Pfam domain architecture and sequence features into
Gene Cluster Families (GCFs) at chosen distance cutoffs. A GCF says "these regions look like the
same kind of machinery in this run" — a class-level statement that depends on the cutoff, the
input set, and the version.

## Input contract (provenance-first)

- Region GBKs only — not whole-genome FASTA, not Mamey CSV rows; read them directly from the
  antiSMASH ZIP.
- Every staged member records: source ZIP path + SHA-256, member path + bytes + SHA-256, strain,
  BGC ID, `contig·region` locator, antiSMASH version when recoverable, cohort-vs-reference flag.
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
`RUN_MANIFEST.json`. Preflight checks Pfam-A and its pressed companions match, and that
`fasttree`/`FastTree` naming resolves (2.0.3 may call the lowercase name; a run-local symlink is an
acceptable, *recorded* recovery).

**Alignment mode stays `auto`** for fragmented assemblies (global for complete pairs, glocal when
one is fragmented, local for divergent domain-subset pairs). Never force `global` on a cohort with
contig breaks — fragmented assemblies + global alignment inflate distances and split families.

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
