# How to Use Sapote-Mamey v9.7.414

This bundle is split into a deterministic extraction layer (Mamey) and an interpretive judgment layer (Sapote / Claude / ChatGPT handoff).

## Important Custom Instructions warning

The Sapote judgment kernel and full monolith **will not fit** into ChatGPT's small Custom Instructions box. Use a Project knowledge file, paste the relevant prompt at the start of a run, or use the slim kernel plus the completed Mamey package.

## Standard workflow

1. Run Mamey on an antiSMASH ZIP with `python mamey_run.py run --strain STRAIN_ID --input-zip INPUT.zip --mode gold`.
2. Confirm the package validates with `python mamey_run.py validate runs/STRAIN_ID/package`.
3. Use `manifest.json` as the authoritative handoff object for downstream Sapote/Claude judgment.
4. Preserve the generated `Project_Memory_Snapshot.json` alias in each package for backward-compatible handoff workflows.

## Minimum handoff files

A complete package should include `manifest.json`, `_2_inventory.csv`, `_2b_bgc_crosswalk.csv`, `_3_scan_states.json`, `_4_triage_board.csv`, `_4A_RGGMCI_ranked_pairs.csv`, workbook output, provenance files, checksum files, and validation receipts.

## Literature search and §8 completion

Every Sapote analysis defers §8 (Literature support) when network access is
unavailable. To close the deferral:

1. Check the §8 deferral note in the Layer B report for the flagged BGC classes.
2. Run the class-specific searches in `docs/LITERATURE_SEARCH_PROTOCOL.md`.
3. Verify DOIs resolve at https://doi.org/[DOI].
4. Send PMIDs to Claude; §8 is written and the package is regenerated.

A bank of pre-verified references (12 entries, verified for AS-XXX) is included
in `docs/LITERATURE_SEARCH_PROTOCOL.md` and can be reused across strains without
re-verification.

## Reference documents

| Document | Purpose |
|---|---|
| `docs/GLOSSARY.md` | Plain-English definitions of all BGC classes, scan abbreviations, tiers, codes, and metrics |
| `docs/BERT_MODE_PROTOCOL.md` | Citation-verification discipline for all literature deliverables (Verified/Partial/Unverified buckets) |
| `docs/BUNNY_HOP_AUDIT_GAME.md` | Random-sampling, Inspector-vs-Defender code audit of the CODE tier; produces a patch card. **Trigger: "can we bunny hop?" / "run the bunny hop game" / "bunny hop [file]"** — load this protocol and start a session (roll → pick 2–3 → audit → consensus → patch card). Findings are input to a cut, never a cut themselves. |
| `examples/citation_library_exemplar.md` | Path A — verified citation library format (one 15-field entry per compound family) |
| `examples/bench_guide_exemplar.md` | Layer C — multi-strain matrix + deep single-strain (Path B) bench guide formats |
| `examples/fermentation_card_exemplar.md` | Layer C — one-page Fermentation Card format + the full TFBS regulator→induction lookup table |
| `docs/LITERATURE_SEARCH_PROTOCOL.md` | Per-BGC-class PubMed search strings + verified reference bank |
| `docs/WORKFLOW_GUIDE.md` | End-to-end workflow guide |
| `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` | Tier 2 LLM judgment protocol (load into Claude/ChatGPT) |
| `docs/standalone/` | ChatGPT-specific guides for running Mamey without Python |
| `docs/troubleshooting/CELL_STATUS_CODE_GLOSSARY.md` | Workbook cell status codes |

## Output bundles — requesting the full menu

At the end of any full-analysis run you can request named output bundles. Say the code
or plain name:

- `Run CM-2` — Discovery Brief (stat cards + key findings + compound-class table) ● default
- `Run CM-3` — Bench Packet (compound-class + manuscript statement + isolation priority list)
- `Run CM-6` — Publication Packet (everything needed for writing up) ● default
- `Give me the Full Spread` — every single-strain layout (CM-7)
- `Run CM-5` — Ecology Set (full ecological synthesis package) ● when §17 applies
- `Show output options` — see the full §54 registry with all A1–A18, B, C, D layouts

Bundles are **additive only** — they never change detection, scoring, or claim-safety wording.
See `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md §54` for the full registry.


---

## Building the cross-strain master workbook (supported path)

The cross-strain master workbook is built from banked package outputs, **not** by the in-runner master writer:

```bash
# one strain or many — from scratch if no banked dir exists yet
python tools/mamey_intake.py --packages <pkg-dir-or-parent> --banked-dir <dir> --workbook <out.xlsx>

# or the explicit two-step (same result)
python tools/ingest_package.py --package <pkg> --ww <WWxxxx00000000> --merge --banked-dir <dir>
python tools/build_workbook.py --workbook <out.xlsx> --banked-dir <dir> --full
```

**Why not `mamey/master_workbook.py` (`--master`)?** That in-runner writer is intentionally avoided here because it is mid schema-migration: its `update_master_workbook()` entry point still emits the OLD descriptive schema (`Dashboard`, `Strain_Registry`, `BGC_Master`) alongside — not instead of — the canonical coded views, producing a **doubled, non-conformant workbook**. The frozen **v1.2 coded schema** (`A1_Dashboard`, `A2_Strain_Registry`, `B1_BGC_Master`, the deep `BGC_*`/`Gene_*` sheets, `Lead_Board`) is written only by the bundled `tools/build_master.py` + `tools/add_xstrain_sheets.py` that `build_workbook.py --full` orchestrates. Until the in-runner `--master` writer is migrated to the coded schema, **`ingest → build_workbook` (or `mamey_intake`) is the only path that yields a schema-conformant master.** Do not route around it by calling the in-runner `--master` writer.

`build_workbook.py --full` order (each step idempotent): deep-data bank → marker bank → `build_master` → cross-strain overlays → DAPR boards → D5/Activity_Ref → Lead_Board (with RG-GMCI rescue flags + Mode B verdict fold). The deep/marker banks run **first** so the deep sheets populate even on a fresh cohort.

## Run modes & deep-sheet completeness

Two run-mode settings determine how complete the workbook can be. Both are about the **Mamey run** (the chat that runs antiSMASH → packages), not the intake:

**`--json-evidence` (default `bounded`).** Bounded mode streams the antiSMASH region JSON and captures A-domain substrate predictions, aSDomain active sites, RiPP precursor cores, and protocluster class calls. **It falls back to `off` automatically when the run machine lacks network/`ijson`** — and an `off` run does NOT capture that data. The four finer workbook sheets (`Gene_NRPS_PKS_Substrates`, `Gene_Active_Sites`, `Gene_RiPP_Cores`, `BGC_Class_Predictions`) can therefore only be populated from **bounded** packages. `build_deep_data.py` extracts them when present and prints an `OFFLINE-LIMITED` line listing strains whose finer sheets are empty because they were run offline. To populate them: re-run those strains on a networked machine with `ijson` installed so bounded mode actually engages.

**Important correction (GBK recovery).** Three of the four finer sheets do NOT actually require bounded mode: antiSMASH writes A-domain substrate predictions, KR active-site/stereochemistry calls, and protocluster class+category into the **region GBKs regardless of json mode**. So `Gene_NRPS_PKS_Substrates`, `Gene_Active_Sites`, and `BGC_Class_Predictions` are recoverable offline straight from the GBKs. Only `Gene_RiPP_Cores` (RiPP precursor peptide sequences) genuinely needs the region JSON / bounded run. Recovered finer data is tagged `Source = GBK-offline` vs `bounded-json` in each sheet so provenance is explicit.

**`--mode` (default and only analysis mode: `gold`).** `gold` = every BGC gets a full Mode B depth floor (batched if >15 BGCs). `standard` is a **deprecated alias** for `gold` (retired v9.7.92); `smoke` was removed at v9.7.161. There is no mode choice to make — gold runs by default.

**Recommended default for a strain headed to deep treatment:** run on a networked machine with `--json-evidence bounded` (so it doesn't silently fall back) and `--mode gold`. That captures everything the workbook can hold in one pass. The deep/marker banks and `build_deep_data` then fill all sheets automatically — including the four finer ones — with no extra step.

## Fragmentation-robust normalization (chitinase, extensible)

Raw genome-wide gene counts (e.g. chitinases) and raw BGC counts both **inflate with assembly fragmentation** — partial genes at contig ends are double-counted, and single clusters split across contig boundaries are counted as several edge fragments. So `chitinase / total_BGC` is a confounded ratio: the denominator carries the very artifact you want to remove.

The fix is a denominator that fragmentation does **not** inflate. Tested against log10 contig count across the cohort:

| denominator | corr with fragmentation | verdict |
|---|---|---|
| raw total BGC | r = +0.42 | inflates — avoid |
| NRPS | r = +0.42 | inflates (large clusters split) — avoid |
| corrected BGC | r = −0.48 | over-deflates — avoid |
| **ectoine + NAPAA** | **r = −0.02** | **robust — use** |
| halogenase | r = +0.09 | robust but ecologically variable |

`build_chitinase_screen.py` reports `chit_per_unit = chitinase / (ectoine + NAPAA)` and a z-score, with outliers (|z| > 1.3) flagged. Strains missing the reference entirely (dropped by fragmentation) are flagged `no_norm_ref` rather than scored. The normalized ratio is fragmentation-independent (|r| ≈ 0.2) where the raw count is not (r ≈ 0.4). **This pattern generalizes**: any genome-wide count can be normalized to the ecto+napaa single-copy unit for fragmentation-robust cross-strain comparison — useful as the cohort grows and assembly quality varies.

## Saccharide handling (exclude raw count from the headline, like NAPAA)

antiSMASH's `saccharide` rule fires on glycosyltransferase / NDP-sugar machinery, so the raw count is
dominated by tailoring (glycosylation of other scaffolds) and sugar-metabolism islands — not standalone
saccharide products. On this cohort, 1285 saccharide-tagged regions resolve to only ~19 reportable candidate
products. Reporting the raw count puts saccharide at the top of every BGC list while being neither actionable
nor reportable — the same problem the project already handles for NAPAA.

**Rule:** the raw `saccharide` count is excluded from headline class prevalence/rankings. `build_saccharide_triage.py`
(run in `build_workbook --full`) writes a `Saccharide_Triage` sheet splitting every saccharide region into:
- `CANDIDATE_PRODUCT` — standalone with a KCB anchor naming a known sugar/aminoglycoside antibiotic
  (streptomycin/neomycin/gentamicin/tobramycin/kasugamycin/everninomicin/teicoplanin-like). **This is the
  headline reportable count.** KCB = similarity anchor, not identification.
- `UNCHARACTERIZED_STANDALONE` — large (≥15 kb) standalone, no named anchor; candidate but needs manual
  review (novel sugar NP vs sugar-metabolism island).
- `TAILORING` — co-located with a backbone class; report under that scaffold (glycosylated PKS/NRPS/etc.).
- `MACHINERY` — small fragments / weak anchor; sugar-metabolism / trans-acting GT noise, excluded.

When presenting BGC-class counts, use the `CANDIDATE_PRODUCT` count for saccharide, not the raw total.

## TFBS / regulator layer

Two products from the regulatory scans:
- **TFBS_Profile sheet** (`build_tfbs_profile.py`): genome-wide per-strain regulator-family counts + per-Mbp
  density, sorted by SARP density. TFBS counts mildly *deflate* with fragmentation (total r=−0.27; motif
  scanning needs intact promoters that contig breaks destroy), and `ecto+napaa` is the best normalizer —
  consistent with the BGC-class finding. SARP density is fragmentation-robust raw, so it needs no normalizer.
- **Lead_Board regulator columns** (`Regulators`, `SARP_support`): per-BGC regulator coupling banked from each
  package's `regulators.bgc_coupling` into `cohort/tfbs_coupling.json`. A `SARP` flag marks leads coupled to a
  pathway-specific activator (SARP/BTAD) — the strongest candidate evidence that a lead is an
  actively-regulated antibiotic pathway. DasR coupling ties a lead to chitin/GlcNAc-responsive regulation.
  Both are SOURCE_DERIVED preliminary (keyword/annotation first pass) — candidate evidence, confirm with
  HMMER/BLAST before manuscript use. Coverage = 43/59 strains (those with snapshots banked).


---

## Citation-Compact Provenance and Citation Status

Sapote-Mamey v9.7.140 uses citation-compact outputs to separate runtime evidence structure from literature verification.

- **antiSMASH 8.0** is recorded as method/database provenance for BGC detection and product/region calls: DOI `10.1093/nar/gkaf334`.
- **MIBiG 4.0** is recorded as reference-database provenance for curated BGC entries and KnownClusterBlast dereplication context: DOI `10.1093/nar/gkae1115`.
- **`PASS_STRUCTURE`** means the package structure, citation ledger, work-order files, compact reports, manifest tracking, and checksum tracking passed validation. It does **not** mean every literature claim has been manually verified.
- **`operator_supplied`** means the citation/provenance row came from runtime evidence or comparator fields already present in the package.
- **`citation_needed`** means literature support is missing and should be filled by a separate literature-search pass.
- **`Literature_Search_WorkOrder.md/json`** is a safe handoff for another ChatGPT/web-literature session. It is a search instruction, not a verified fact.

Current compact lead tables use `interpretation_scope` for reader-facing scope. The older reader-facing scope field should not appear in current citation-compact outputs.
