# Volume II — The Mamey Engine (deterministic extraction)

> **Currency scope:** This volume retains its historical edition and review stamps. Only the checks listed in the [currency record](Encyclopedia-Currency.md) have been refreshed for the current candidate. Other constants, numerical claims, literature interpretations, and worked-run results have not been comprehensively revalidated. A newer bundle does not make those older observations current.

*Edition: bundle v9.7.33 / engine Mamey 1.9.41 · re-grounded to bundle v9.7.91 / engine Mamey 1.9.91 on 2026-06-20 (record types, the \_edge_status rule, the twelve scan\_\* functions / ten-scan reporting roster, the corrected-count + tier computation, and the package/validator gates verified against the running engine) · 2026-06-15*
*Chapters II.1–II.8. Grounded in the running engine of this edition. Read Volume I first (→ Master Index).*

------------------------------------------------------------------------

## §II.1 · Ingest and the schema gate

Mamey takes one strain's antiSMASH archive and parses it into a set of in-memory records before any analysis
runs. The parse reads the antiSMASH outputs — region GenBank files, the run JSON, and text annotations — and
produces three primary collections that everything downstream consumes: the **BGC records** (one per detected
region, → §II.2), the **CDS features** (every coding sequence, with its product, locus tag, coordinates, and
qualifiers), and the **contig sequences**. A dedicated status parse (`parse_antismash_evidence_status`) records
*how much* evidence the archive actually carried — whether GBK `sec_met_domain` Pfam hits were present, whether
the JSON was read in `off`/`bounded`/`full` mode (→ §VII on evidence levels) — so the run can later be honest
about the provenance of its calls (→ §II.4). <span class="tag t-engine">\[engine\]</span>

**Parse output — the four record types (`models.py`).** <span class="tag t-engine">\[engine\]</span>
- **`GenomeStats`** — `genome_bp`, `contigs`, `gc_pct`, `largest_contig`. Genome-level context for the tiering.
- **`CDSFeature`** — `contig`, `start`, `end`, `strand`, `locus_tag`, `product`, `translation`, `nucleotide_seq`,
`qualifiers{}`. One per coding sequence; the substrate for every motif/keyword scan.
- **`DomainFeature`** — `contig`, `start`, `end`, `strand`, `feature_type` (`aSDomain` \| `PFAM_domain` \|
`CDS_motif` \| `module`), `locus_tag`, `domain`, `database`, `bitscore`, `evalue`, `qualifiers{}`. antiSMASH's
pre-computed domain hits, surfaced with their HMMER bitscore/E-value stated as antiSMASH-internal.
- **`BGCRecord`** — one per region (field table in §II.2).

The **schema gate** is the discipline that protects the rest of the pipeline from malformed or mismatched
input. Files arrive at different schema versions and from different producers; the gate's job is to map each
source onto one canonical record shape before anything is combined, rather than concatenating divergent
structures and silently mis-aligning columns. This is the same normalize-before-combine rule that governs
cohort merges (→ §VII): a source that lacks a field is given an honest blank, never dropped, and the union of
useful columns is conserved. An auto-normalize-at-ingest path (`b1_normalizer`) is a known open item — the
normalizer exists but is not yet wired into the ingest gate, so for now schema reconciliation is applied
deliberately rather than automatically. <span class="tag t-engine">\[engine\]</span>

**Cohort resolution and the non-actinomycete guard (`cohort_resolver`, v9.7.44/47).** A strain enters the
pipeline under whatever identifier it was deposited or isolated with, and that identifier is not always its cohort.
The two failure modes both surfaced in the v9.7.43 shake-down. First, a public *Streptomyces* from the project's SID
collection is frequently deposited in GenBank under a **WGS accession** (e.g. run as `--strain WWGG00000000`, organism
string `Streptomyces sp. SID-XXX`); a classifier keyed on the bare ID prefix sees `WW…`, not `SID…`, and mis-files it
as a generic reference. The `cohort_resolver` (v9.7.44, B-1) resolves cohort from the **embedded SID in the organism
string**, not the accession, so the five WGS-deposited strains in the worked cohort (`WWGG/WWJO/WWKA/WWKH/JAAGLM`)
correctly resolve to **SID**, matching `SID-XXX`/`SID-XXX`. Second, an archive can simply not be an actinomycete at
all: in the shake-down, `WWJQ00000000` parsed as ***Bacillus thuringiensis***. The resolver flags this and the run
emits a loud end-of-run `*** NON-ACTINOMYCETE` warning, because the whole standing-rule and detection apparatus is
calibrated on actinomycete biology — a *Bacillus* should be **excluded from the cohort**, not scored as one. <span class="tag t-engine">\[engine\]</span>

The lesson for an operator is to treat the cohort label as **resolved, not assumed**: watch for an `OTHER` /
non-actinomycete flag at run end, and remember that the resolver's output — not the accession — is the cohort of
record. The same resolver must be consulted wherever cohort is re-derived; v9.7.74 (B-10) closed a gap where the
cross-strain bank re-inferred cohort from the bare prefix and labelled the WGS-deposited SID strains `REF`, so the run
and the merge now agree (→ §VI.8). <span class="tag t-engine">\[engine: v9.7.74\]</span>

## §II.2 · The BGC inventory and boundary status

The inventory is the list of BGC records, each locked at parse time with a stable `bgc_id` (`BGC001`,
`BGC002`, …) that never changes for the life of the run — so a lead can be referred to unambiguously across
every later artifact. Each record carries its **contig**, region number, start/end coordinates, contig length,
the antiSMASH **product** class labels, any MIBiG hits, and a protocluster breakdown. **Every BGC is named with
its contig/node wherever it appears** — a bare "BGC003" with no location is not permitted in any output, because
a cluster's coordinates are part of what makes a claim about it checkable (→ §I, claim-safety apparatus). <span class="tag t-engine">\[engine\]</span>

**`BGCRecord` fields (`models.py:62+`).** <span class="tag t-engine">\[engine\]</span>

| Field | Meaning |
|----|----|
| `bgc_id` | `BGC001…BGCnnn`, locked at parse time, immutable for the run |
| `contig`, `region_number`, `start`, `end`, `contig_length` | location quad + contig size (drives boundary status) |
| `products[]` | antiSMASH product-class labels for the region |
| `mibig_hits[]` | MIBiG reference hits (KnownClusterBlast) |
| `edge_status` | `Interior` \| `Edge` \| `Full-contig` (default `Full-contig`) |
| `architecture_confidence` | A–E structural-completeness grade (default `D`; parse-time, prompt-refined) |
| `architecture_capacity`, `architecture_class_confidence` | claim-safe class-capacity call + `HIGH`/`MODERATE`/`LOW` (v9.7.21, covers marker-invisible classes) |
| `antismash_region`, `source_gbk`, `node_id`, `user_label` | provenance back to the antiSMASH region/GBK/node |
| `kcb_top`, `clusterblast_top`, `kcb_cumulative`, `kcb_protein_hits` | KnownClusterBlast anchor line, raw rank-1 ClusterBlast line (v9.7.22), cumulative score, protein-hit count |
| `riq_score`, `riq_label` | rarity/isolation quotient (0–1) + its label |
| `closest_mibig_accession`, `closest_candidate_kcb_product`, `closest_product_provenance`, `source_kcb_file`, `source_kcb_locator`, `kcb_hit_rank`, `denominator_type` | the KCB resolution chain, each defaulting to `UNRESOLVED` so an unfilled field is never silently blank |
| `parse_confidence` | `LOW` (default) → `MEDIUM` → `HIGH`, set by KCB-parse evidence quality |

The `UNRESOLVED` defaults are deliberate: an unfilled KCB field reads `UNRESOLVED`, never an empty string that
could be mistaken for "no hit." <span class="tag t-engine">\[engine\]</span>

**Boundary status** is the single most consequential per-BGC fact Mamey computes, because it drives both the
corrected count (→ §II.5) and several fragmentation rescues (→ §II.6). Each region is classified by where it
sits on its contig:

- **Interior** — bounded on both sides within the contig; the cluster is plausibly whole.
- **Edge** — runs off one end of the contig; probably truncated.
- **Full-contig** — spans the contig end to end; the strongest signature that the region is a fragment of
  something larger.

Boundary status is a deterministic geometric fact, not a judgment, and it is computed identically every run.
What the pipeline *does* with it — half-weighting an Edge, quarter-weighting a Full-contig, attempting a
cross-contig rescue — is downstream policy built on this floor of fact. <span class="tag t-engine">\[engine\]</span>

**The exact rule (`parsers.py:193`, `_edge_status`).** With `length = end − start + 1` and a 5,000 bp flank: <span class="tag t-engine">\[engine\]</span>

| Condition | Status |
|----|----|
| `length ≥ 0.95 × contig_length` | **Full-contig** (region spans ≥95% of its contig) |
| `start ≤ 5000` **or** `(contig_length − end) ≤ 5000` | **Edge** (region reaches within 5 kb of a contig end) |
| otherwise | **Interior** (≥5 kb of flank on both sides) |
| `contig_length ≤ 0` | **Unknown** (degenerate input) |

**The architecture grade A–E (`parsers.py`, `architecture_grade`)** is derived at parse time from `edge_status`, whether a core
biosynthetic gene is present (`has_core`), region length, and KCB strength — a *structural-completeness* read,
not a tier (→ §V.5, it is decoupled from scoring): <span class="tag t-engine">\[engine\]</span>

| Grade | Condition |
|----|----|
| **A** | Interior, has core, ≥10 kb — a complete, coherent locus |
| **B** | Interior with either a core gene or strong KCB, but limited/compact annotation |
| **C** | Edge-truncated *with* a coherent product annotation — partial interpretation only |
| **D** | Edge-truncated with limited annotation (the conservative default) |
| **E** | Full-contig / highly fragmentary — architecture rests on little |

## §II.3 · The ten First-Pass Scans

After the inventory is built, Mamey runs a battery of **source-derived scans** over the CDS features, contigs,
and BGC regions. The canonical reporting set is **ten First-Pass Scans**, surfaced in `scan_status.scans`; the
engine computes several further source-derived signals (cassettes, domain architecture, quorum-sensing,
glycosylation arms, primary-metabolism and mis-anchor guards) that feed scoring and the judgment layer but are
not part of the headline ten. Each scan is a fixed-rule pass — keyword/motif matching over annotations, or a
geometric/statistical check — never an interpretation. The ten: <span class="tag t-engine">\[engine\]</span>

1.  **KCB_sweep** — the KnownClusterBlast sweep. Extracts each region's similarity hits to characterized
    reference clusters. A hit is a *similarity* signal, never an identification (→ §I.3); it is the raw material
    the mis-anchor guard and the novelty axis later discipline.
2.  **RG_GMCI** — reference-guided gapped multi-contig integration. When an assembly is fragmented, uses a
    reference cluster as a template to propose that fragments sitting on different contigs belong to one pathway,
    graded `HIGH_RG_GMCI_RESCUE` or `MODERATE_RG_GMCI_CANDIDATE`. It is the cross-contig rescue adjudicator.
3.  **FLBR** — fragmented large/modular-biosynthesis rescue. Censuses megasynthase ketosynthase markers and flags
    when fragmented PKS/NRPS regions suggest a split megasynthase (→ §II.6 for the full census).
4.  **CCTT** — the class-corroborating trigger tags, the T43 framework (eighteen trigger families, → §IV). Tags
    diagnostic motifs that corroborate a class-capacity claim, with vetoes that withhold credit when a trigger
    fires on a class-incompatible locus.
5.  **CGAD** — the chitinase / glycan-active-domain scan. A proteome-wide pass for chitin-degrading machinery
    (GH18, GH19, AA10/LPMO, chitin-binding modules). Chitin is the fungal cell wall, so this channel is
    ecologically and biomedically pointed (→ §I.4, the antifungal lens).
6.  **UMED** — maturation/tailoring-enzyme detection: the enzymes that mature a core biosynthetic scaffold into
    a finished product, whose presence raises confidence that a cluster is a complete pathway.
7.  **EFLS** — cross-contig shared-evidence linkage: links fragments across contigs by evidence they share
    (cassettes, CCTT triggers, FLBR signal), complementing RG_GMCI's reference-guided rescue with an
    evidence-driven one.
8.  **resistance** — self-resistance and transporter tiering. Tiers source-derived resistance/self-protection
    signals (T1 diagnostic self-protection / T2 resistance-like / T3 transporter-only) proximal to each BGC, and
    carries the gene-level **HGT guard** that flags mobile-element-dominated regions (described in §III.6 / §IV.8; scoring home → §V (planned)).
9.  **bldA_TTA** — bldA/TTA-codon dependence. Flags TTA codons, whose translation depends on the developmentally
    regulated bldA tRNA in actinomycetes — a control signal often associated with secondary-metabolism timing.
10. **TFBS** — the upstream transcription-factor-binding-site scan: a regulatory-binding-site signal in the
    region upstream of clusters.

A conditional eleventh line, **PHO_CLUSTER**, is appended when the phosphonate trigger (T43-PHO) fires densely
enough to indicate a dedicated C–P-bond locus, carrying a recommendation for ³¹P-NMR and FomA/FomB follow-up.
<span class="tag t-engine">\[engine\]</span>

**Scan-function reference (`source_scans.py`; `run_source_scans → SourceScanBundle`).** Twelve `scan_*` functions
run; the **ten** above are the reporting roster (`scan_status.scans`), the other two are guard scans consumed by
scoring (→ §V): <span class="tag t-engine">\[engine\]</span>

| Function | Role | Reporting? |
|----|----|----|
| `scan_tfbs(upstream_bp=300)` | TFBS upstream-binding-site scan | ten |
| `scan_blda_tta` | TTA-codon / bldA dependence | ten |
| `scan_umed` | maturation/tailoring-enzyme detection | ten |
| `scan_efls` | cross-contig shared-evidence linkage | ten |
| `scan_flbr` | megasynthase KS census (§II.6) | ten (FLBR) |
| `scan_cassettes` | diagnostic cassette detection (feeds EFLS) | source-derived |
| `scan_orphan_megasynthase_motifs` | KS/C motifs outside any called region | source-derived |
| `scan_domain_architecture` | per-BGC domain-architecture read | source-derived |
| `scan_qs_signals` | quorum-sensing signal genes | source-derived |
| `scan_glycosylation_arm_candidates` | glycosylation-arm (saccharide-context) | source-derived |
| `scan_primary_metabolism` | housekeeping/pigment guard (→ §V.4) | guard |
| `scan_misanchor_guards` | KCB-anchor-without-class-diagnostic guard (→ §V.4) | guard |

(KCB_sweep, RG_GMCI, CGAD, and the resistance/HGT tiering are computed in the evidence/adapters layer, not as a
`scan_*` in `source_scans.py`; together with the five `scan_*` marked "ten" they make the ten-scan roster.) <span class="tag t-engine">\[engine\]</span>

**Output shape (`scan_status.scans`, built in `external_adapters.py`).** Each scan reports a **`(name, state, detail)`** triple — the reporting surface a reader sees in the brief (→ §VI.2) and the manifest. The **state** is
one of a small fixed vocabulary, and the **detail** is a human-readable one-line summary: <span class="tag t-engine">\[engine\]</span>

| State | Meaning |
|----|----|
| **PASS** | the scan ran and found a positive result (hits, pairs, triggers) |
| **NULL** | the scan ran cleanly and found nothing — an *informative* negative, not a failure |
| **NOT_APPLICABLE** | the scan does not apply to this input (e.g. `bldA_TTA` when the taxonomy is not a *Streptomyces* relative — the gate is stated in the detail) |
| **FAILED / DEFERRED** | `RG_GMCI` only, when the ClusterBlast context was missing or is pending the CLI's reference pass |

The detail string is scan-specific and quantitative, so the triple is self-documenting:

| Scan | `detail` reports |
|----|----|
| KCB_sweep | "*N* regions parsed; *M* loose hits" |
| RG_GMCI | "*N* pairs; *H* high; *M* moderate; *R* reference records" |
| FLBR | "*grade* — *flag*" (STRONG/WEAK megasynthase-fragment grade) |
| CCTT | per-trigger "*T43-XXX*: *h* hits / *b* BGC, …" or "no triggers" |
| CGAD | per-bucket chitin counts "GH18:*n*, …" or "no hits" |
| UMED | "*N* lanthipeptide GAP regions" or "no maturation gaps" |
| EFLS | "*N* candidate pairs" |
| resistance | "*N* total hits; *M* T1 BGCs" |
| bldA_TTA | "*N* BGCs assessed; *M* T4" — or, when NOT_APPLICABLE, the taxonomy gate reason |
| TFBS | "*N* motif hits; …" |

The triple is only the *reporting* surface. Underneath, each scan function returns a richer dict consumed by
scoring and the judgment layer — the pattern scans (chitin/regulators/transporters/resistance/CCTT) return
`{counts, hits, bgc_coupling}` where `bgc_coupling` is the per-BGC list of proximal hits within the coupling
flank; `scan_tfbs` returns `{status, upstream_bp, counts, hits, total_hits, claim_safety}` with an explicit
`claim_safety` caveat that the motif scan is preliminary. The state vocabulary is the honest-incompleteness
discipline in miniature: a **NULL** says "looked, found nothing" and a **NOT_APPLICABLE** says "this question does
not apply here" — two very different statements the package keeps distinct rather than collapsing both into a blank
(→ §II.4, the honesty of evidence). <span class="tag t-engine">\[engine\]</span>

## §II.4 · Evidence channels and the honesty of evidence

Where the scans answer *what signals are present*, the **evidence channels** answer *what kind of evidence
backs them* — and the engine is deliberately explicit about it, because provenance is part of claim-safety. The
channels, each with a status: <span class="tag t-engine">\[engine\]</span>

- **antiSMASH source domains** — Pfam / `sec_met_domain` hits that antiSMASH pre-computed and Mamey surfaces
  (`COMPLETED_GBK_PFAM_EXTRACTED` when GBK region files carried them, else `COMPLETED_SOURCE_DERIVED`). The
  bitscores and E-values come from antiSMASH's internal HMMER run, stated as such.
- **motif scans** — the keyword/motif passes over source annotations (`COMPLETED_SOURCE_DERIVED`). These are the
  workhorse of the ten scans; the channel's own note tells the reader to confirm important claims externally.
- **custom marker HMMER** — `NEEDS_HMMER_DOMTBLOUT`: a future channel requiring a protein FASTA plus the Mamey
  marker HMM and an `hmmscan --domtblout`. Framework present; scoped to a later release.
- **DIAMOND bulk homology** — `NEEDS_DIAMOND_TSV`: framework present, reference database not yet connected.
- **manual BLASTP, top leads** — `MANUAL_BLASTP_OPTIONAL`: run only for a few selected top proteins, never for
  bulk annotation (and never remote-NCBI for bulk).

The design point: a call is only as strong as its channel, and the engine never lets a motif-scan keyword hit
masquerade as HMMER-confirmed homology. The pending channels are named, not hidden, so a reader knows exactly
what evidence has and has not been brought to bear — the provenance counterpart to the capacity-not-production
discipline of §I.3.

**One distinction inside this is load-bearing for corroboration: *parsed-domain* evidence vs *label/coupling-derived*
signal.** Some fields trace to parsed domains (`architecture_class_confidence`, the resistance tier's
`class_concordant_groups`); others are derived from a product-class *label* or from *proximity coupling*
(`cassette_families`, `bgc_coupling`'s within-flank hits, the raw CCTT keyword patterns that match a class token).
The coupling/label fields are genuinely useful for *routing and linkage*, but they are **not** trustworthy as class
*corroboration*, because a label can match itself: a region labelled "lanthipeptide" picks up a `lanthipeptide`
cassette family from the label token even with no cyclase present. Corroboration that disciplines a label must
therefore trace to parsed-domain evidence, never to another label-derived field — the principle the PC-12 episode
made concrete (→ §V.4, §VIII.5). <span class="tag t-engine">\[engine\]</span>

**`parse_confidence` ladder (per BGC, `antismash_evidence.py`).** `HIGH` when a region resolves a KnownClusterBlast
anchor with a clean denominator; `MEDIUM` on a weaker/partial resolution; `LOW` (the default) when KCB is dark or
unresolved. It is an honesty field on the *parse*, distinct from `architecture_confidence` (structure) and the
lead tier (promise). <span class="tag t-engine">\[engine\]</span>

**JSON-evidence modes (`--json-evidence`, ijson-streamed).** `off` never opens the run JSON — TXT clusterblast
files carry KCB; fastest. `bounded` streams only the KCB/RiQ leaves (`_stream_kcb_riq`). `full` streams whole
records (`_iter_records`). Streaming output is **byte-identical** to a full `json.loads` (`use_float=True`), and
when ijson is absent both paths degrade gracefully to `json.loads`. The mode is recorded so a run is honest about
how deeply the JSON was read. <span class="tag t-engine">\[engine\]</span>

## §II.5 · Assembly tiers and the corrected count (engine view)

The corrected count and assembly tiers are defined conceptually in §I.5; this chapter is how the engine
computes them. From the boundary-status tally (§II.2), Mamey computes:

> corrected = Interior × 1 + Edge × ½ + Full-contig × ¼

and the **assembly tier** from the interior fraction — **GOOD** (interior ≥ 70%), **MODERATE** (45–70%),
**POOR** (20–45%), **VERY_POOR** (\< 20%). Both are emitted in the count summary alongside the raw count, the
per-class breakdown, and the interior percentage, so a reader always sees the raw and corrected figures
together with the assembly quality that contextualizes them. The tier is not a verdict on the strain's biology;
it is a calibrated caution about how much the fragmentation should temper the counts and boundaries, and it is
carried into the brief headline and the deliverables rather than buried. The length-aware successor to the flat
Full-contig weight is recorded as a future direction in §I.5 and is **not** in this edition's computation. <span class="tag t-engine">\[engine\]</span>

## §II.6 · The FLBR megasynthase census

Large modular polyketide synthases and non-ribosomal peptide synthetases are the biggest, most modular assembly
lines in the genome — and precisely because they are large, they are the most likely to be split across contig
boundaries by an imperfect assembly. A naive count treats each fragment of a split megasynthase as a separate
trivial region; the FLBR census exists to catch that. <span class="tag t-engine">\[engine\]</span>

FLBR counts the megasynthase ketosynthase markers across the proteome — modular KS (`mod_KS`), hybrid KS
(`hyb_KS`), trans-AT KS (`tra_KS`) — plus a mega-NRPS marker, and cross-references them against which BGC
regions are fragmented (Edge or Full-contig) and carry PKS/NRPS/trans-AT product labels. It then grades: <span class="tag t-engine">\[engine\]</span>

- **LMPKS_FRAGMENT_SET (STRONG)** — four or more KS markers *and* at least one fragmented PKS/NRPS region: a
  large modular PKS is very likely split across the assembly.
- **MEGASYNTHASE_FRAGMENT_SUSPECT (WEAK)** — four or more megasynthase markers total, or any fragmented
  PKS/NRPS region: a megasynthase fragment is plausible but not strongly supported.
- **NULL** — no megasynthase fragmentation signature.

An orphan-megasynthase-motif pass catches KS/condensation motifs sitting outside any called region — stray
evidence that a cluster boundary was drawn too tightly. FLBR is the engine's structural honesty about
fragmentation: it is what lets the judgment layer treat a set of fragments as one candidate pathway (with
RG_GMCI and EFLS, → §II.3) instead of dismissing each as a stub, while never asserting the reassembled whole as
fact.

## §II.7 · The output package and its validation

A run's deliverable is one sealed **Complete_Package** for the strain — the inventory, the triage board, the
scan status, the figures, the brief, the manifest, and the evidence dumps — carrying its own provenance and
checksums. Two validation layers gate it. <span class="tag t-engine">\[engine\]</span>

**Package contents (the `Complete_Package` file map, v9.7.91).** Artifacts are numbered by pipeline stage; gold mode adds the deep-dive dumps. <span class="tag t-engine">\[engine\]</span>
Entry points: `OPEN_ME_FIRST.html`, `START_HERE.md`. **1** — `1_intake.json` (run context). **2** — `2_inventory.csv` (the BGC inventory, §II.2) + `2b_bgc_crosswalk.csv` (BGC→contig/node/region crosswalk). **3** — `3_scan_states.json` (the ten-scan roster, §II.3). **4** — `4_triage_board.csv` (the scored board, → §V); `4A_RGGMCI_evidence.csv` / `4A_RGGMCI_full.json` / `4A_RGGMCI_ranked_pairs.csv` (reconstruction evidence, §IV.4); `4B_Diagnostic_Rescue_Leads.csv/json/md` + `4B_Diagnostic_Rescue_Tiling.csv` (diagnostic-rescue leads); `4c_AB_lead_board.csv` / `4c_AF_lead_board.csv` (the dedicated antibacterial / antifungal lead boards, v9.7.45). **5** — `5_workbook.xlsx` (the master workbook) + `5b_manual_blastp_worklist.csv` (the manual-BLASTP spot-check worklist; its scoring was fixed in v9.7.91 so it no longer ships empty, → §VI). **6** — `6_output_checklist.csv/md`. **7** — `7_cell_provenance.csv` + README and `7_missing_data_worklist.csv` (cell-level provenance / missing-data). **Figures:** `figures/` (the strain-brief landscape + composition figures, → §VI) and `locus_maps/` (per-BGC gene-arrow maps, now carrying per-arrow ctgN_M labels — v9.7.91). **Data dumps:** `bgc_data.json`, `cds_table.csv`, `records.json`, `gene_context.jsonl`; gold adds `deep_data.json`, `gene_data.json`, `gene_by_gene_top_leads.csv/xlsx`, `modeb_verdicts.csv`. **Judgment:** `verdicts.json`, `judgment_register.json`. **Evidence/parse:** `AntiSMASH_Evidence_Parse.json` (the §II.1 evidence-status parse) and `source_locator_evidence/`. **Handoff:** `ANALYSIS_FORWARD.md` / `analysis_forward.json`, `BATCH_PLAN.md`, `Project_Memory_Snapshot.json`. **Audit/commit:** `boundary_audit.json` (§II.7), `commit_receipt.json`, `gate_validation.json`, `gold_mode_receipt.json`, `issue_log.md`, `run_phase_receipts.jsonl`. **Provenance/integrity:** `manifest.json` + `manifest_short.json` (release/provenance, → §VII) and `checksums_sha256.txt`; plus a `Troubleshooting/` folder.

A **file-presence check** always runs: the package must contain every artifact the contract requires, or the
build does not pass. On top of that, a **gold-aware validator** applies stricter checks in `gold` mode. Its
success set (`cli.py`, the gold-mode status gate) is **`success_statuses = {"MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES", "PASS", "PASS_WITH_ISSUES"}`**, and the exit code is
`0` when the run status is in that set (or its validator status starts with `PASS`), else `1`. **MAMEY_COMPLETE** is the verdict
that matters most: it is the engine stating, in its own validation vocabulary, that the deterministic extraction
is complete and correct but the judgment layer has not yet run — the same honesty the brief's "extraction
complete · judgment pending" banner carries to the human reader (→ §I.2). A package can be a clean, valid,
checksummed deliverable *and* explicitly an unfinished analysis, and the validator refuses to let those two facts
blur — a `MAMEY_COMPLETE` package passes the gate without ever claiming to be a finished analysis. <span class="tag t-engine">\[engine\]</span>

**The evidence-conservation auditor (`boundary_audit.py` + `tools/evidence_conservation_audit.py`).** Beyond
presence, a fail-closed pair of audits guarantees that *nothing the engine found is silently lost* between the
raw antiSMASH output and the sealed package, and that every recorded exclusion was actually honoured. The
**boundary audit** diffs the extractor's records (the BGCRecord side) against the judgment verdicts (the
TriageRecord side) and raises any of seven coded problems — **exit 1 on any of them**: <span class="tag t-engine">\[engine\]</span>

| Code | Meaning |
|----|----|
| **DROPPED** | a deterministic BGC with no verdict — the silent-omission class (a region the engine found but the board lost) |
| **ORPHAN** | a verdict for a `bgc_id` the extractor never produced |
| **STRAIN** | the two payloads describe different strains — a copy-paste / bus error |
| **TIER** | a verdict whose `lead_tier` / `claim_confidence` is outside the known vocabulary |
| **DOWNGRADE** | a verdict flagged standing-rule / primary-metabolism that *still* kept a corrected lead rank (the exclusion was recorded but not honoured) |
| **EXCLUSION** | a record whose products trip an excluded rule (NAPAA / saccharide / hglE-KS) but whose verdict shows no downgrade (a retired-class claim leaking as a clean lead) |
| **RETIRED** | a record carrying a retired id (e.g. BRYO-HGT-001) at all |

A companion **SOURCE→PACKAGE conservation auditor** (`tools/evidence_conservation_audit.py`) catches biosynthetic
evidence present in the raw antiSMASH output but dropped from the sealed package — a count-only completeness check
cannot see this, because a region can survive as a row while its *evidence* is lost. And when sources are unified,
`b1_normalizer.py` enforces **honest blanks** for columns a source lacks and emits a **blank-by-source ledger**, so
a missing field is recorded as an explicit blank attributable to its source, never silently filled or dropped (→
the merge discipline, §VII). Together these make evidence conservation an enforced invariant, not a hope.

The judgment layer reads these same audits from the other side — how Sapote consumes the boundary diff is covered
in Volume III.

## §II.8 · Determinism, the standalone contract, and testing

Everything in this volume is deterministic by design: run the same antiSMASH archive through the same engine
twice and the extraction, the scans, the counts, and the package are identical. This is not incidental — it is
the property that lets the deterministic layer be the trustworthy floor under the judgment layer (→ §I.2), and
it is enforced, not hoped for. <span class="tag t-engine">\[engine\]</span>

The engine pins its own version in a **standalone contract** — a test that asserts the running
`__version__` matches the declared engine version, so a version-string drift across the bundle's files
(pyproject, the package metadata, the changelog) fails the suite rather than shipping. The marker tables are
held to the registry as single source of truth: the registry-backed detector must reproduce the hardcoded
literals bit-for-bit, and the marker catalog must not be stale — so a new marker cannot be added in one place
and forgotten in another (the registry-reassignment and catalog-regeneration disciplines of Volume VIII's trap
list). Each release is cut into four tiers and gated by a per-tier test run and a leak audit (→ §VII), and the
whole suite — several hundred tests at this edition — is run, never assumed, before any cut. The rule that
governs the entire engine is the one stated plainly in Volume I: *test before you declare done*, and show the
check.

## §II.9 · CNBU — class-normalised BGC units <span class="tag t-engine">\[engine\]</span>

**Class-Normalised BGC Units (CNBU)** express the observed biosynthetic coding length of a
strain as a fraction of the expected length for complete pathways of each class. A BGC whose
assembled length is 60 kb when the class prior is 80 kb contributes 0.75 CNBU rather than
one raw count. CNBU is computed by `mamey/cnbu.py` and emitted as part of the standard
package output.

**What CNBU is for.** Corrected BGC count (→ §I.5) adjusts for fragmentation by down-weighting
edge and full-contig regions. CNBU adjusts for length: a highly fragmented strain may have many
short edge BGCs that each count as ½ in the corrected count, but whose combined length suggests
a smaller total secondary metabolite investment than the count implies. CNBU and corrected count
are complementary; neither replaces the other.

**What CNBU is not.** CNBU is a structural-length metric. It does not imply production, activity,
or compound identity. It does not replace the conservative corrected BGC count for ecological
comparisons. <span class="tag t-engine">\[engine\]</span>

**Unknown priors.** When a class has no reference length prior in the registry, the BGC is
labelled `UNKNOWN_PRIOR` and excluded from the CNBU total with a warning. The `UNKNOWN_PRIOR`
count is always reported alongside the total; it is never silently absorbed. <span class="tag t-engine">\[engine\]</span>

------------------------------------------------------------------------

*End of Volume II. Next: Volume III — The Sapote Layer (the judgment contract, Mode B §1–§8, scoring and triage,
the lead-tier ladder, architecture confidence A–E, the hallucination-trap audit). Grounded in the running
engine of its edition before it ships.*

</div>

<div id="vol3" class="section vol">
