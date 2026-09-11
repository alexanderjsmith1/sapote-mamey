# MODE B WRITE — Sapote Judgment Persistence Protocol
**v1.1 · 2026-06-21 · Sapote–Mamey v9.7.319**

## Purpose

After completing Mode B for a BGC, Sapote writes the output to disk so it persists
across sessions and accumulates across batches. This closes the gap identified in
worst-list item 29 (Mode B is session-ephemeral) and enables PDF-003/004/011 in
the compiled deliverables.

**Do this after EVERY completed Mode B, every batch.**

---

## The §1–§10 card (v9.7.112 — full Mode B contract)

A FULL Mode B card has **all ten sections, written out** — concise, not padded, but complete. §9 and
§10 were historically omitted; they are now required and gate-checked. "None found in the gene table"
is a valid, recorded §10 finding — the requirement is to *look and report*, not to invent.

- **§1 Identity** · **§2 Assembly/locus context** · **§3 Biosynthetic core** · **§4 Gene
  neighborhood, regulation, cofactor supply** · **§5 Pharmacology / target context** · **§6 Priority
  & lead class** · **§7 Isolation/fermentation rationale** · **§8 Verdict & claim-safe summary**
- **§9 — Activation, fermentation & detection strategy.** bldA/TTA-tier-aware activation path
  (medium, co-culture, ribosome engineering); detection method (LC-HRMS m/z class targets, UV-vis,
  GC-MS for terpenes, CAS for siderophores); mechanism-confirmation assay; isolation priority with
  rationale. BGC-specific, not generic.
- **§10 — Forensic sweep** (four mandatory sub-targets; address each, "none on this contig" is valid):
  - **(A) Resistance / self-immunity / efflux** — enumerate; classify efflux vs enzymatic-inactivation
    vs target-modification. State when none is present and what it implies.
  - **(B) Transcriptional regulators / TFBS** — each regulator's DNA-binding family + operator
    implication. Do not assert binding sites not in the data; flag TFBS as follow-up if absent.
  - **(C) Rare / diagnostic markers** — NB-ARC, halogenase, HypF, corrinoid, radical-SAM/SPASM,
    enediyne KS, desaturases; report CCTT triggers, `ks_domain_count`, `ene_ks_count`.
  - **(D) RG-GMCI split-cluster linkage** — follow the `RGGMCI_HOWTO` block in the package's
    START_HERE.md: filter the ranked-pairs CSV to HIGH/MODERATE, report
    `functional_rescue_class` strongest-first (BOTH_CORE > COMPLEMENTARY > ACCESSORY_ONLY >
    AMBIGUOUS), heed the promiscuity caution, and quote the `interpretation_guard` verbatim.

Fragments (single-ORF / full-contig, sub-2k chars) are exempt from the §9/§10 length requirement —
§10(D) is their key section (how the fragment links to its parent); §1–§8 are thin by nature and
forcing length would mean inventing detail (evidence-conservation).

### §11–§20 — mandatory enrichment block (v9.7.112)

Each of §11–§20 is individually optional, but every non-fragment card must carry **≥ 1,000 characters
of combined §11–§20 content**. Do not hand-author this — `mamey.enrichment_sections` drafts it
deterministically from the gene table so the floor is reachable from data, never padded prose:

```python
from mamey.enrichment_sections import parse_genes, genome_domain_frequency, compose_enrichment
genes_by_bgc = {bid: parse_genes(rows_for_bgc) for bid, rows_for_bgc in cds_by_bgc.items()}
freq = genome_domain_frequency(genes_by_bgc)              # genome-wide → "rarest" is data-grounded
enrichment, used = compose_enrichment(genes_by_bgc[bgc_id], freq, products, floor=1000)
```

The rarity catch-alls (`rarest_genes`, `rarest_domains`) and `domain_inventory` fire on any card with
≥1 domain-bearing gene, so every BGC class reaches the floor; class-specific sections (NRPS/PKS typing,
peptide-precursor, halogenase subtyping) add depth where the substrate exists and return nothing
(honestly) where it doesn't. Genuine fragments (STUB, sub-2k chars) are exempt — the gate
short-circuits to STUB before the enrichment check, so a 1-gene fragment is never penalized for
enrichment it can't honestly produce.



After producing the **full §1–§10** card for a BGC (v9.7.112 — §9 and §10 are now required, not optional), invoke the write path:

```python
# In the Claude session — use the bash or create_file tool:
python3 - << 'PY'
import sys
sys.path.insert(0, ".")
from mamey.judgment_store import record_mode_b

record_mode_b(
    package_dir = "/path/to/AS-XXX/package",
    bgc_id      = "BGC001",
    mode_b_md   = """
# §1 Overview — BGC001
...full §1–§10 markdown here...
""",
    layperson_paragraph = """
BGC001 encodes biosynthetic capacity consistent with an azole-containing RiPP.
The KCB similarity profile (bombyxamycin class) suggests a cyclic peptide backbone.
At extract level, the strain shows antibacterial activity; fractionation is required
to link activity to this specific cluster.
""",
    fermentation_note = """
Culture in ISP2 at 28°C for 7 days. The bldA/TTA tier is 1 (constitutive) — no special
induction required. Extract with EtOAc at pH 7; reverse-phase C18 fractionation.
Detection handle: UV absorption at 280 nm (azole chromophore).
""",
    session_id = "batch_1",
)
print("BGC001 written")
PY
```

---

## Required fields

| Field | Required | Contents |
|---|---|---|
| `package_dir` | ✅ | Absolute path to the sealed Mamey package directory |
| `bgc_id` | ✅ | BGC ID exactly as in the triage board (e.g. `BGC001`) |
| `mode_b_md` | ✅ | Full **§1–§10** Mode B markdown (not abbreviated). §9 and §10 are required — the write-time gate stamps SHALLOW and lists missing sections if either is absent. |
| `rank` | recommended | Triage-board rank (sets the priority char floor: HIGH≥9k / MID≥8k / LOW≥6k). Omit → LOW floor. |
| `layperson_paragraph` | recommended | 3–5 sentences: what it makes, why it matters, how to detect it. No jargon, no compound identity claims. Used for PDF-003. |
| `fermentation_note` | recommended | §7 isolation strategy condensed: culture conditions, extraction, detection handle. Used for PDF-004. |
| `session_id` | recommended | Batch label (e.g. `batch_1`, `batch_2`) for provenance tracking |

---

## Output files produced

After calling `record_mode_b`, the following files are written/updated:

```
<package_dir>/judgment/<strain>_BGC001_mode_b.md         # §15.3 per-BGC Mode B
<package_dir>/judgment/<strain>_laypersons_section.md    # accumulated layperson text
<package_dir>/judgment/<strain>_fermentation_section.md  # accumulated fermentation text
<package_dir>/<strain>_judgment_register.json            # completion tracker
```

The judgment register is read by `render_brief.py` (via `render-all-figures ... brief`) to populate PDF-003/004 pages
when `render_brief()` is called. No further action is needed.

---

## Batch completion tracking

At the end of each batch, Sapote can also mark multiple BGCs complete at once:

```python
from mamey.judgment_store import record_batch_complete
record_batch_complete(
    package_dir   = "/path/to/package",
    session_id    = "batch_1",
    bgc_ids_complete = ["BGC001", "BGC002", "BGC003", ...],
)
```

---

## Checking progress

```python
from mamey.judgment_store import read_register, pending_bgcs

reg = read_register("/path/to/package")
print(f"Completion: {reg['completion_pct']}% ({reg['complete_bgcs']}/{reg['total_bgcs']})")
print(f"Pending: {pending_bgcs('/path/to/package')}")
```

---

## When to trigger compiled PDF

The compiled master PDF (`_Complete_Analysis_Compilation.pdf`) should only be
rendered when `read_register()` returns `judgment_status == "COMPLETE"`.
Until then, `render_brief.py` (via `render-all-figures ... brief`) emits the PDF-003/004 pages with whatever
Sapote content is already written (partial is fine — it shows progress).

---

## Claim-safety

The `layperson_paragraph` and `fermentation_note` fields must follow the same
claim-safety rules as all Sapote output:
- Capacity-based language ("biosynthetic capacity consistent with...")
- No compound identity claims
- No bioactivity claims pinned to a specific BGC
- KCB hits are similarity, not identity

---

## Writing back to the master workbook

After completing one or more batches, update the master workbook so all strain
data is collected in one cross-strain file:

```python
python3 - << 'PY'
from mamey.master_workbook import update_e1_from_judgment

result = update_e1_from_judgment(
    package_dir          = "/path/to/AS-XXX/package",
    master_workbook_path = "/path/to/Master_Workbook.xlsx",
)
print(result)
# {"strain": "AS-XXX", "bgcs_written": 48, "bgcs_complete": 20,
#  "bgcs_pending": 28, "e1_audit_status": "IN_PROGRESS_20of48", ...}
PY
```

This updates two sheets in the master workbook:
- **E1_Mode_B_Index** — one row per BGC with `mode_b_status`, `layperson_summary`,
  and `fermentation_note` columns populated from the judgment store.
- **A4_Completeness_Audit** — `E1_mode_b` cell updated to `COMPLETE`,
  `IN_PROGRESS_Nof48`, or `JUDGMENT_PENDING`.

Call this after each batch. It is idempotent — Batch 2 replaces Batch 1 rows.

---

## Integration with ANALYSIS_FORWARD.md

After each batch, the ANALYSIS_FORWARD.md progress tracker is automatically
updated by the judgment register. Sapote does not need to manually update the
checkboxes — the register tracks completion and render_brief reads it.


---

## Group 2 workbook write-back functions

After Sapote completes specific analysis steps, call these functions to populate
the remaining judgment-facing master workbook sheets.

### C3/C4 — Sapote composite rank and strategic recommendation

After completing the cross-strain priority synthesis (ranking all strains):

```python
from mamey.master_workbook import update_c3c4_from_sapote

result = update_c3c4_from_sapote(
    master_workbook_path = "/path/to/Master_Workbook.xlsx",
    strain_id            = "AS-XXX",
    sapote_rank          = 1,          # integer rank among all project strains
    sapote_score         = 91.5,       # Sapote composite score
    sapote_composite     = "Priority A — 2 High leads, high novelty, MRSA-active at extract level",
    recommended_role     = "Lead compound strain — WAC cohort flagship; BGC001 azole-RiPP priority",
)
```

Updates: C3_Lead_Tier_Summary (sapote_composite, recommended_role) and
C4_Strain_Decision_Table (sapote_rank, sapote_score, recommended_role).
Preserves all deterministic extraction fields in those rows.

### D3 — RG-GMCI pair confirmation after Mode B

After completing Mode B for the anchor BGCs of each promoted RG-GMCI pair:

```python
from mamey.master_workbook import update_d3_from_sapote

result = update_d3_from_sapote(
    master_workbook_path = "/path/to/Master_Workbook.xlsx",
    strain_id            = "AS-XXX",
    promoted_pairs = [
        {
            "group_id": "AS-XXX_RG01",
            "fragments": "BGC001+BGC013",
            "evidence_basis": "Mode B §4 analysis is consistent with kirromycin-class transAT-PKS capacity on BGC001; BGC013 carries halogenase + RRE consistent with azole-containing RiPP arm. 8 shared references, 6 good-geometry.",
            "claim_ceiling": "Class-level biosynthetic capacity consistent with kirromycin-class + azole-RiPP co-cluster; physical linkage unproven — confirm by long-read assembly or PCR",
            "chemistry_consequence": "transAT-PKS / azole-containing-RiPP",
            "status": "MODE_B_SUPPORTED",
        },
    ],
)
```

### G1 — Literature citations from Literature Deep Dive

After running a Literature Deep Dive on one or more BGCs:

```python
from mamey.master_workbook import update_g1_from_sapote

result = update_g1_from_sapote(
    master_workbook_path = "/path/to/Master_Workbook.xlsx",
    strain_id            = "AS-XXX",
    citations = [
        {
            "BGC_ID": "BGC001",
            "track": "bombyxamycin / azole-containing RiPP",
            "citation": "Martinet L et al. (2019). Nat. Chem. Biol. 15, 988-996.",
            "doi": "10.1038/s41589-019-0349-9",
            "evidence_purpose": "biosynthesis",
            "verification_status": "Verified",
        },
    ],
)
```

G1 accumulates across calls — second call adds new citations without removing prior ones.
De-duplicates on (strain, BGC_ID, doi).

### G2 — Validation roles and manuscript assignment

After completing the strategic role assessment:

```python
from mamey.master_workbook import update_g2_from_sapote

result = update_g2_from_sapote(
    master_workbook_path = "/path/to/Master_Workbook.xlsx",
    strain_id            = "AS-XXX",
    primary_role         = "lead compound strain",
    manuscript_use       = "WAC cohort §3 lead — BGC001 azole-RiPP feature strain; MRSA-active extract-level",
)
```

