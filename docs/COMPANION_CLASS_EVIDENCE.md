# Optional class evidence and genome-side exports

The following commands read a package and write a fresh external directory, defaulting to `<package.parent>/post_seal/<command>/`. Supply a new `--out` for another run. They refuse outputs that resolve inside the package, including symlinks. Package manifests and integrity files remain unchanged. Stable source files and no concurrent writers are required.

## GECCO

`python mamey_run.py gecco-crosscheck --package <package> --zip <original-antismash.zip> --jobs 1`

GECCO is optional and off by default. Install it separately if desired; the bundle and doctor do not install it. This adapter targets the 0.11 CLI/table format and probes the actual executable version. It runs `gecco run` with `--cds-feature CDS --locus-tag locus_tag --force-tsv` using the whole-genome GBK inside the exact package-bound source ZIP. If more than one whole-genome GBK exists, choose `--genome-member`. The default threshold is 0.8; an explicit threshold is recorded. [Upstream CLI](https://github.com/zellerlab/GECCO/blob/v0.11.0/gecco/cli/commands/run.py) and [table model](https://github.com/zellerlab/GECCO/blob/master/gecco/model.py) describe the external interface.

The outputs include per-region overlap, GECCO-only cluster and gene-probability CSVs, raw tables, and a source/version/threshold receipt. A `NODE_n_length_L` match ignores rewritten coverage suffixes but refuses normalized-contig ambiguity. The adapter checks returned CDS IDs and coordinates against the source before publication. A low probability is not evidence against a cluster; an overlap is a second opinion, not proof.

Repeat `--gap-genes <CSV-or-TSV>` to create external copies of gene tables with `gecco_mean_p` and typed join state. These inputs require `locus_tag`, `query_gene` or `protein_id` from the same genome; unknown tags stay unjoined. Existing tables are never modified.

## Genome-side metabolomics bridge

`python mamey_run.py export-metabolomics --package <package> --source-zip <original-antismash.zip> [--gecco-dir <crosscheck-output>]`

New extraction runs populate `manifest.json`'s `metabolomics_targets` from observed domain counts. The exporter recomputes the same fields for older packages without altering them. PKS, NRPS, RiPP and supported terpene markers map to broad NPClassifier pathway vocabulary in `mamey/data/bgc_class_to_npclassifier.json`; this is a versioned hypothesis table, not a structure classification or CANOPUS result. Other or product-only evidence stays `unmapped`. Hybrid regions retain independent hypotheses. Every entry carries the full strain / contig / region / BGC identity and the ceiling: **capacity; an expected class to look for, not a predicted compound**.

Measured median identity uses distinct per-gene MIBiG evidence for the bound best accession. Unknown measurements and the corresponding 74% close-match flag stay null; cumulative KCB score is never reinterpreted as identity. A supplied GECCO sidecar must match the original package snapshot and its recorded support hash.

Outputs comprise target TSV/JSON, exact source region GBKs with hashed pointers under `nplinker/antismash/`, an operator sample-mapping template, a genome-side PoDP preparation template and README. The templates are explicitly marked incomplete and do not claim validation against external submission schemas. NPLinker, PRISM, GNPS/MASST, SIRIUS/CANOPUS, DeepBGC and BiG-SLiCE are registered optional companions. Web services are labelled manual/offline-unprobed; local detection cannot establish service availability. No MS data are invented, uploaded or associated by this command.

## Explicit non-KS second-proof policy

`python mamey_run.py two-proof-rescue --package <package> --policy nonks_position_v1 --scorecard <bound-scorecard.tsv>`

The normal package run and `--policy ks_clade_v2` preserve the established default KS rule. The named alternative recomputes advisory `_4D` outputs externally and records its policy in every row and receipt. It grants an alternative second proof only for a positively observed non-KS core class, a complementary **HIGH** RG-GMCI linkage, and a scorecard **CONSISTENT** reading with a named relative. A relative of any assembly level can supply this reading. **APART_CLOSE** or **CONFLICT** vetoes an eligible non-KS pair; APART_WEAK, absent/read-unresolved position and unresolved class evidence leave the independent proof unresolved. Observed KS keeps the KS protocol. Per-gene KnownClusterBlast remains supporting evidence, never a second proof.

The scorecard TSV must carry `strain`, exact `identity_a` and `identity_b`, `layers_verdict`, and `relative`. Identities must match this manifest's four-part loci. Duplicate or conflicting pair bindings are refused. No distance threshold is changed or reimplemented: the existing scorecard owns its position reading. Verdicts are class-level candidates for human adjudication, never a merge, production or activity claim. This implementation does not establish benchmark validity for an unmeasured non-KS population.
