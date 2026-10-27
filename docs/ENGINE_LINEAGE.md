# Mamey Engine Lineage

What changed in the Mamey engine at each version bump, and whether outputs stay comparable. Newest first. Each bump also has a CHANGELOG entry.

## Engine 1.9.177 — first bundle: v9.7.455

The split-cluster second proof is routed by class (`class_routed_v1`, the default policy). A member’s observed KS count or a PKS/polyketide/transAT product token keeps the pair on the KS route. The core-completion branch requires positively observed non-KS core evidence on at least one member, no KS-route state on either, and different contigs. On that eligible non-KS branch, CONFLICT or APART_CLOSE vetoes; a nonempty `core_completion` value, a HIGH RG-GMCI call and the existing logic gate can yield TWO_PROOF_RESCUE. A CONSISTENT position alone does not promote under this policy. These are helper admission rules, not independent scientific proof of a complete class core or physical linkage. `_4D` adds `core_completion`; the CLI accepts `--input-zip`, and the in-run route can read the run’s input ZIP.

Also in 1.9.177:
- TWO_PROOF_RESCUE needs a HIGH RG-GMCI pair on both routes. A MODERATE pair with both proofs stays RGGMCI_ONLY and keeps its KS clade ID.
- `assembly_sanity_check` flags an assembly above 12 Mb as INFLATED_ASSEMBLY_SUSPECT, with its own warning text.
- Cross-strain figures read a blank, NA or unbound count as missing, not zero, and do not draw it.
- `doctor` and the external-data status add consumer-readiness fields for NP Atlas, read from the files the resolver loads. `provisioned` keeps its meaning.

`_4D` is advisory: RG-GMCI scores, ranks, thresholds and package determinism fields are unchanged. Packages from 1.9.176 and 1.9.177 are not directly poolable for `_4D` two-proof verdicts. Existing outputs are not rewritten.

## Engine 1.9.176 — first bundle: v9.7.451 (unsealed)

`mamey/ref_completion.py` reads compound names as lists whether a names file gives a string or a list. `same_family()` matches family stems only when they are equal or differ by one known prefix (neo, iso, nor, epi, homo, dehydro, deoxy, dihydro, demethyl, desmethyl, seco, pre, pro). The gap-rescue tools now pass compound names into their partner checks. A partner gene whose best reciprocal match is a sibling MIBiG entry of the reference compound can now count toward the family score instead of being set aside as a paralog. A name contained inside another name no longer counts. Gap-rescue tables from 1.9.175 can differ from 1.9.176 for those genes, so they are not directly poolable for partner verdicts. Thresholds are unchanged. Existing outputs are not rewritten.

Also in 1.9.176:
- The two-proof join holds a pair as LOGIC_EVIDENCE_HOLD when its overlap count is blank or malformed (logic version 3). A legacy `_4A` without the column keeps its verdict and says so in `claim_note`.
- The hybrid gate counts each antiSMASH category once (NRPS + NRP-metallophore is one class), so `architecture_rationale` and the reproducibility fingerprint change for affected regions.
- RG-GMCI reports AMBIGUOUS_TERMINUS for contig ends containing N.
- KS-domain parsing stops at the next feature.
- Package runs add RECORD_LIMIT_COVERAGE_UNVERIFIED when the record-limit probe cannot establish coverage.
- The biopython-free GenBank shim refuses records with no sequence and no numeric LOCUS length.

- BLASTp manual and trove ingest collect every explicit query strain claim; a contradictory or foreign claim is refused or held as QUERY_STRAIN_CONFLICT, and receipts are checked before tables change. The master workbook is saved atomically.
- Native `blastp-online` CSVs add `channel` and `source_channel`.
- Reference-guided completion runs the housekeeping-neighbour check on every non-paralog partner find; SUPPORTED needs an adjacent non-housekeeping find; HOUSEKEEPING_PFAM adds YgbB, IspD, CarD, Clp, Lsr2, pantothenate, NadA, QRPTase and Histidinol_dh families.
- Assembly-line outputs and post-seal package snapshots are admitted fail-closed.

Packages from 1.9.175 and 1.9.176 are not directly poolable for two-proof verdicts, hybrid grades or terminus states. Existing outputs are not rewritten.

## Engine 1.9.175 — first bundle: v9.7.450 (unsealed)

The antiSMASH archive parser now prefers full output records over archived input copies of the same contig only when the two sequences match exactly. Mismatches and unusable identities are kept apart and reported, not silently merged. This can change which CDS and coordinates a contig carries when an archive holds both an input copy and an output record, so packages from 1.9.174 built from such archives are not directly poolable with 1.9.175 for gene-level tables. Run-level release decisions are carried on the run context (`release_decision`). Scoring formulas and thresholds are unchanged. Existing delivered packages are not rewritten.

## Engine 1.9.174 — first bundle: v9.7.449 (unsealed)

The CLI adds the optional post-run gap-rescue wrapper. Companion region binding preserves full assembler contig identifiers through the existing parser rule. Scoring formulas and thresholds are unchanged; engine identity changes because engine source changed. Existing delivered packages are not rewritten.

## Engine 1.9.173 — first bundle: v9.7.448

Adds `mamey/figures/locus_comparison.py`, a source-bound locus-comparison renderer that the strain-slide comparison tools share. It writes each figure with a receipt of the drawn coordinates, track orientations and assembly markers. Elsewhere in the engine only docstrings and comments changed, so extraction, scoring, calls and emitted tables are the same as 1.9.172.

## Engine 1.9.172 — first bundle: v9.7.445

Adds emitted contig-depth fields and optional residue-tiling evidence. Product-family comparisons accept separator variants. A separate dominated-diagnostic report preserves tier-1 calls and scores and labels its thresholds uncalibrated. These changes require explicit version binding when comparing outputs. Core region-coordinate extraction is unchanged by these cards; family/routing outputs and advisory fields can differ. No product identity or physical contig linkage is inferred.

## Engine 1.9.171 — first bundle: v9.7.444

RG-GMCI pairs only regions antiSMASH flags as on a contig edge, never two regions on one contig; those
pairs move to a related-loci table (`_4A_RGGMCI_related_loci.csv`) and triage ignores them. The ranked-pairs
table gains its gate columns, proxy-adjacency ties no longer depend on the hash seed, HIGH pairs sharing a
region form candidate groups with group GenBank files, and glycosylated split pathways can be called.
Product-class counting no longer treats antiSMASH category words as product classes. These change emitted
RG-GMCI calls and class counts, so boards from 1.9.170 are not directly poolable for them. The fallback GenBank reader now retains LOCUS names and DEFINITION text, which can change
replicon order and BGC aliases when Biopython is absent. Region-only archives now offset extracted CDS and
domain coordinates by Orig. start; BGC bound conventions and KnownClusterBlast parsing are unchanged.
These changes can alter downstream architecture and gene-to-region assignments. Mechanical validation
does not establish biological interpretation or scientific acceptance.

## Engine 1.9.170 — first bundle: v9.7.443

The adjacent-cluster rescue read (`mamey/clusterblast_genes.py`) adds a MODULAR_CONTINUATION
class with assembly-line and release-gene counts, written as new columns beside
functional_rescue_class and never replacing it. This is an emitted-output change: scoring,
extraction, rules and product-class parsing are byte-identical to engine 1.9.169, so triage
boards remain directly comparable. Packages from 1.9.169 simply lack the new columns.
Mechanical validation does not establish biological interpretation or scientific acceptance.

## Engine 1.9.169 — first bundle: v9.7.439

Output admission now validates primary artifacts and JSON sidecars before writing and refuses
activity-tree collisions. Figure and monitoring paths preserve missing tranche summaries,
undefined denominators, distinct small-range ticks, coincident paired values, quiet BLASTp lanes,
unique dense-series colors, grouped hourly bars, and runtime-derived timezone labels. Automatic
BLASTp submission and resume paths bind explicit public-sequence-upload consent, count/digest
disclosure, strain, and channel. Patch custody reports direction and separates malformed diffs from
strict-patch-compatible `git apply` rejection. Scoring formulas, biological interpretation, and
the bare-ant/environmental classification policy are unchanged; output and monitoring behavior can
differ for fixed inputs, so affected artifacts should be regenerated before version-naive
comparison. Mechanical validation does not establish biological or release acceptance.

## Engine 1.9.168 — first bundle: v9.7.438

The antiSMASH region parser now accepts GenBank partial-position markers on `Orig. start` and
`Orig. end`. For linear inputs carrying those markers, a fixed archive can produce a different
boundary classification and `interior_pct`; affected pre-1.9.168 packages should be regenerated
before version-naive comparison. The interactive figure-set renderer also omits absent FS042 and
FS045 measurements instead of encoding them as observed zero, and online BLASTp now plans locally
unless the operator supplies both submission and public-sequence-upload acknowledgements. Scoring
formulas and thresholds are unchanged. Report, handoff, deterministic-jitter, path-containment,
metadata-label, and assurance-gate changes are described in the v9.7.438 changelog. Mechanical
validation does not establish biological interpretation or scientific acceptance.

## Engine 1.9.167 — candidate first bundle: v9.7.433 (unsealed)

This candidate corrects cofactor-class markers (TIGR03962 mycofactocin MftC; TIGR02109
PQQ PqqE) and retains antiSMASH domain descriptions. It adds optional post-seal BLASTp
snapshot/current-locus binding, protein FASTA signatures, BiG-SCAPE guarded MIBiG
dispatch, and Mode B evidence warnings. The cofactor correction changes class reads
for affected loci; earlier triage boards should not be treated as directly pooled
without reconciliation. A matched protein signature identifies a query source, not
a BLASTp result or a metabolite. This entry records an unsealed engineering
candidate; release and scientific acceptance remain open.

## Engine 1.9.166 — first bundle: v9.7.432

Four score-neutral behavior changes, none in a scoring, extraction or sealed-package-schema file,
so v9.7.431 and v9.7.432 boards remain poolable. (1) HMM resolution: `SM_HMM_DB` (file),
`MAMEY_HMM_DIR` (directory) and `$MAMEY_DATA_ROOT/hmm` resolve through one shared precedence in
`mamey/external_data.py` / `mamey/wheelhouse.py`, and `doctor` reports the path the scanner will
actually read instead of a different one. (2) `published_registry` in `mamey/dedup_and_guard.py`
distinguishes "not configured" (`None`, the default; unchanged behavior) from "configured and
empty" (every AS strain PRIVATE); no caller passes the parameter yet, so nothing changes at
runtime until the roster is populated. (3) Strain attribution from staged BiG-SCAPE filenames in
`mamey/bigscape_namespace.py`: a variant suffix between the strain prefix and the `_NODE_` contig
token (`<strain>_second_NODE_…`) now yields its own visible id (`<strain>_second`) instead of being
merged into the canonical strain. Clean names and the 1.9.165 `"?"` sentinel are unchanged. The
third is a changed emitted identity value, which is why the engine bumps. (4) `ingest-blastp-trove`
in `mamey/blastp_ingest.py` / `mamey/cli.py` gains an explicit, opt-in `--rekey-by-locus` mode that
resolves stale trove BGC aliases through the package's `*cds_table.csv`. The default strict path,
the overlay schema of existing rows and every scoring surface are untouched (two columns are
appended to new overlay rows, and the receipt schema name changes only in that mode).

## Engine 1.9.165 — first bundle: v9.7.431

Strain attribution from staged BiG-SCAPE filenames now returns the `"?"` sentinel when a name
carries a `_NODE_` contig token but no parseable strain prefix, instead of falling through to a
contig-bearing stem. The sentinel itself is not new — `stem.strip() or "?"` already covered the
empty case — but it now also covers the contig-bearing case. So an input that previously emitted a
contig-derived stem as a strain identity emits `"?"`, which is countable and visible as an anomaly
rather than silently becoming a phantom strain. This is a changed emitted identity value, which is
why the engine bumps: two trees both stamped 1.9.164 must not disagree on attribution for identical
input. No scoring or extraction file is touched — scoring formulas, triage thresholds, source scans
and sealed-package schemas are unchanged, and v9.7.430 / v9.7.431 boards remain poolable.

## Engine 1.9.164 — first bundle: v9.7.429

Input admission now refuses obvious taxonomy placeholders and preserves absent taxonomy as explicit unknown. The full-JSON guard is 80 decimal MB; bounded-mode limits are unchanged. Entry-page status/identity reporting, summary PDF layout and Darwin memory units are corrected. Post-seal tree admission, metadata, series completeness and portable artifact handling incorporate reconciled incoming candidates. Scoring formulas and triage thresholds are unchanged; evidence availability can differ when the larger full-JSON guard admits additional inputs. Prior benchmark observations remain bound to their original engine/configuration.

## Engine 1.9.163 — first bundle: v9.7.428

Post-seal phylogeny tooling now exports a complete standalone collaborator package for every
accepted tree display. It applies explicit reviewed query-identity exclusions at panel admission
and distinguishes accession-shaped laboratory strain codes from conflicting deposited accessions.
It supports reproducible closest-type-strain neighborhood catalogs and avoids MAFFT's restricted
`/dev/stderr` wrapper path. Figure metadata and palettes are refined, and the bioassay plate-map
utility adds a validated plate-geometry layer. Core antiSMASH extraction, source scans, scoring,
triage thresholds, and sealed-package schemas are unchanged.

## Engine 1.9.162 — first bundle: v9.7.427

Post-seal phylogeny display changes add a declared Tree Catalog, exact placed-query role binding,
reference-definition screening, specimen-level internal labels, concise publication metadata, and
explicit horizontal layout controls. Distinct isolates remain distinct even when their submitted
16S sequences are identical. Core antiSMASH extraction, source scans, scoring, triage thresholds,
and sealed-package schemas are unchanged.

## Engine 1.9.161 — first bundle: v9.7.426

Post-seal Figure Factory behavior changes for fixed bioassay inputs: a canonical observation schema
retains material lineage, dose, time point, replication, controls, exclusions, and material amount.
The planning kind inventories raw, precomputed, MIC, and in-vivo datasets. An explicit endpoint
or named fraction-set maximum can become a typed tree annotation. The 16S autopilot now screens
queries, selects MAFFT fragment alignment for partial reads, and holds near-tied cross-genus routing.
Reference admission and metadata display are shared across phylogenetic producers. Core antiSMASH
extraction, source scans, scoring, triage thresholds, and sealed-package schemas are unchanged.

## Engine 1.9.160 — first bundle: v9.7.425

Post-seal widgets, Mode B scaffolds, Lab Quest inventories, reports, guides and lead figures now preserve complete locus identity and typed missingness for fixed package inputs. Ambiguous, malformed and unsafe roster/evidence inputs return explicit refusals, and external guide output no longer rewrites the source package. Core extraction and scoring thresholds are unchanged. Generated scaffolds, references and test success do not establish scientific interpretation, production, activity or owner acceptance.

## Engine 1.9.159 — first bundle: v9.7.424

Reference-panel filtering, advisory terminal assessment and portable placement display integration change workflow outcomes. Exact accession and metadata refusals are preserved. Display conventions change labels only; full accession identities remain in source records.

## Engine 1.9.158 — first bundle: v9.7.423

BLASTp discovery excludes account-level automatic roots and the CLI reports typed discovery refusals. Identity-claim hedges are scoped to their clause in plain and structured lint results. Placement annotation can bind binary bioassay summaries with explicit missingness and duplicate/value refusals. These changes affect workflow and validation outcomes for fixed inputs; mechanical verification does not establish scientific acceptance.

## Engine 1.9.157 — first bundle: v9.7.421

Failure-state propagation changes verification, report, inspection, and evidence-admission outcomes for fixed inputs. Caught BLASTp file-set failures restore prior output or expose a recovery hold. Reference discovery, metadata projection, and exact outgroup-token handling change post-seal tooling. Scientific interpretation, product identity, and production claims remain deferred; mechanical validation does not confer acceptance.

## Engine 1.9.156 — first bundle: v9.7.420

Failure handling changes verification, report and evidence-admission outcomes for fixed inputs. Missing linkage no longer becomes a zero rescue measurement. Reference-label refusal diagnostics and narrowly scoped collection-prefix handling change post-seal display behavior. Core extraction algorithms and scoring thresholds are unchanged. Mechanical tests do not establish scientific acceptance.

## Engine 1.9.155 — first bundle: v9.7.419

Reference-label disambiguation and mixed-store admission change post-seal display and refusal behavior for fixed inputs. Refpkg filtering and supplemental citation checks are tightened. Core extraction, scans, scoring and sealed-package schemas remain unchanged. Test success does not establish scientific identity, rooting or acceptance.

## Engine 1.9.154 — first bundle: v9.7.418

Display labels change for fixed inputs and reference metadata gains explicit source states and provenance. Outgroup lookup refuses reference-only bundled authority and contradictory locked rows. These post-seal presentation and refusal changes warrant an engine identifier; core extraction, scans, scoring and sealed-package schemas are unchanged. Render or test success does not establish scientific rooting, identity or acceptance.

## Engine 1.9.153 — first bundle: v9.7.416

Post-seal deliverable commands now return a nonzero status on canonical-write refusal or execution failure, preserving actionable diagnostics and successful zero exits. The cut integrates portable phylogenetic workflow tools and stricter provenance/refusal behavior described in the changelog. Core extraction, scan and scoring algorithms are unchanged. A mechanically validated tree workflow does not establish scientific rooting, taxonomic identity or biological conclusions. Release test results are recorded separately in the release manifest.

## Engine 1.9.152 — first bundle: v9.7.414

Also shipped in v9.7.415: folder organization, post-seal inspector identity, test portability, companion-command failure handling, optional hooks, and documentation. No extraction/scoring or sealed-package schema change.

The post-render summary retains its relative package anchor and now copies subject identity and available engine/workflow fields from the package manifest. This changes a shipped artifact for a fixed input and warrants an engine bump. The cut also adds display-only title/host parsers to the existing label owner, Git-checkout audit exclusions scoped inside the audited root, portable link checking, test-skip repair, and signed-waiver ceiling enforcement. Scoring and biological scan outputs are unchanged. Display parsing is not taxonomy or host-association verification. Full-suite results are recorded in the release manifest.

## Engine 1.9.151 — first bundle: v9.7.413

The JSON parser receipt now preserves the original requested mode through timeout fallback and records structured-path request flags and budget outcomes. Validation exposes advisory JSON visibility fields. This changes emitted evidence receipts for a fixed input and warrants an engine bump. Missing historical fields stay unknown; the new visibility field does not change overall package acceptance. No new biological scans or scientific interpretations are introduced by this visibility change. The cut also includes source-bound post-seal evidence adapters and rendering/gate repairs described in the changelog. Existing source and cohort holds remain explicit.

## Engine 1.9.150 — first bundle: v9.7.412

**Reason for bump:** the emitted `manifest.json` changes for a fixed input. `mamey/packaging.py` (BC412_08) adds `gold_figures/figure_receipts.jsonl` to `MUTABLE_RECEIPT_NAMES`, so it is no longer hash-pinned in the manifest/checksums. This corrects a false `mamey validate` FAIL: `figure_save.py` appends that file into the package after the seal, so a pinned hash always went stale on a MAMEY_COMPLETE package.

**Scoring / parser semantics:** UNCHANGED. No scoring, source-scan, or parser module changed. Only the packaging pin-set and validate's reciprocal scan differ.

**Comparability:** a 1.9.149 package re-run under 1.9.150 produces identical score-bearing output. The manifest differs by exactly one entry: `figure_receipts.jsonl` is present-and-pinned under 1.9.149 (and makes validate FAIL) and present-but-unpinned under 1.9.150 (validate PASS). Consumers that enumerated pinned manifest entries see 100 vs 101.

**Tests at bump:** ACCEPT-union .412 slice 308 passed / 21 skipped; graft-integrity 25; parity gold-run on `examples/test_data/smoke_antismash_small.zip` (validate rc=0 vs .411 rc=1). Full suite is the seal gate (owner-run).

## Engine 1.9.149 — first bundle: v9.7.409

**Also shipped on 1.9.149 (engine unchanged, bundle-only bump):** v9.7.410 — reconciled two-stream fold (Codex chain + rebased Claude lanes + hostile-audit rounds + ported round-7 lanes). Scoring-neutral, no scoring module changed, cross-strain comparability with .409 preserved.

**Why the engine bumps here:** one parser-level guard changes what can reach the evidence tables.
`parsers.QUALIFIER_MAX_CHARS = 4000` caps a single GenBank qualifier value at parse time. A region
GBK carrying a 300 KB `/note` on one CDS (reproduced from a hostile fixture) previously flowed
uncapped into `_2_inventory.csv` and the figure label path; the CSV reader then failed its field-size
limit and the renderer was killed. Annotation text beyond the cap is truncated with an explicit marker.
No scoring prior, scan pattern, class route or RG-GMCI band changes in this cut; the remainder of
v9.7.409 is gate, refusal, export-safety and documentation work.

**Comparability:** a 1.9.148 package re-run under 1.9.149 is identical unless a qualifier exceeded
4,000 characters, in which case only that annotation text differs. Use `tools/determinism_fingerprint.py`
to show a score-bearing re-run reproduces.

Older entries, 1.9.148 back to 1.9.99, are in [history](history/ENGINE_LINEAGE_1.9.99_to_1.9.148.md).

---

## Release gate

`sync_version.py --check` reads the engine from `pyproject.toml` and searches an existing
`docs/ENGINE_LINEAGE.md` for `Engine <version>` followed by a nondigit boundary.
This is a token-presence check, not a comparison with a previous release baseline,
a required-heading parser, or validation of the entry’s completeness or assertions.
A missing token prints `ENGINE LINEAGE MISSING` and exits nonzero; an absent file
prints a warning in that branch. Other version-sync checks can refuse independently.

Future engine bumps must include:
- Old engine version
- New engine version  
- First bundle carrying new engine
- Reason for bump
- Whether scoring/parser semantics changed
- Tests run at bump
