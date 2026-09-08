# Sapote–Mamey Trigger Routing Table
**Version:** v9.7.319  **Engine:** Mamey 1.9.111  
*Single authoritative routing table. Edit here; other docs must not define conflicting trigger behaviour.*

---

## 1. Workflow triggers

| Trigger phrase / condition | Route | Module / output |
|---|---|---|
| `CHATGPT_EXECUTION_SLICE_LOADED` or new ChatGPT/Sapote session | Load `docs/CHATGPT_EXECUTION_SLICE_v97147.md`; do not use the slim kernel as the active controller | Full-depth execution slice |
| `MAMEY_COMPLETE` or `MAMEY_COMPLETE_WITH_ISSUES` detected | `MAMEY_COMPLETE_HANDOFF_REQUIRED`: present code-backed outputs, then offer/produce prompt-backed set | Post-complete handback block |
| `ANALYSIS_COMPLETE` after Sapote judgment | `ANALYSIS_COMPLETE_DELIVERABLE_OFFER`: auto-produce or explicitly offer the full prompt-backed set | Deliverable offer/production |
| `locus_maps/` present or `LOCUS_MAP_PRESENTATION_REQUIRED` | List and present every locus-map SVG/PNG; do not bury maps in the package | Locus-map handback |
| "full Mode B", "Full Mode B §1–§30" (also legacy "§1–§20"), "FULL ANALYSIS MODE" | `FULL_MODEB_REQUEST_DETECTED`: §1–§30 contract (`modeb_corrective_full30_v1`) — §1–§20 mandatory in order + §28, §30 mandatory + §21–§27, §29 conditional | Mode B card |
| "offline Mode B", `OFFLINE_EVIDENCE_ALLOWED` | Full Mode B permitted without BLASTP; §16 documents evidence gap | Mode B card |
| "fragmented PKS", "RG-GMCI", "wise PKS" | `WISE_PKS_QUEUE_DETECTED`: `wise_fragmented_pks.py` + `blastp_batch_emitter.py` | FASTA batches + ledger |
| "cross-strain GCF", "cohort GCF", "BiG-SCAPE", "gene cluster families" | `COHORT_GCF_DETECTED`: read `LLM_COMPANION_TOOL_PROTOCOL.md`, resume/current-run check → manifest → preflight → cluster → exact-run QA → portable export. Cohort-only runs cannot emit KNOWN/NOVEL; ingest is separately authorized. | Additive GCF atlas (SOP-17) |
| "GToTree", "phylogenomics", "IQ-TREE", "MLSA" | `PHYLOGENOMICS_DETECTED`: read `LLM_COMPANION_TOOL_PROTOCOL.md` + `phylogenomics.md`; recover whole assemblies, cap references, de-replicate, show size/usage, obtain user approval, then run one core per tree (≤4 total). | Alignment/tree/ANI companion package |
| "make a PDF", `PDF_DELIVERABLE_REQUESTED` | narrative PDF + source MD + evidence CSV + manifest | PDF deliverable |
| "locus map", `--locus-map` flag | `mamey/figures/locus_map.py` | SVG file |
| "cross-strain comparison", `CROSS_STRAIN_COMPARISON_REQUESTED` | Separate comparative report; never replaces Mode B card | Comparison report |
| "integrated table as companion", `INTEGRATED_TABLE_AS_COMPANION` | Emit table alongside card; table never substitutes for card | Table + card |
| "claim ceiling required", `CLAIM_CEILING_REQUIRED` | §19 + §20 receipts; suppress per-gene claim repetition | Mode B card |

---

## 2. Quality-gate triggers

| Condition | Required behaviour | Status |
|---|---|---|
| Output claims Full Mode B but lacks a mandatory §1–§30 section (§1–§20, §28, §30) | Fail closed; mark NOT_FULL_MODEB | ✅ `mamey/modeb_structure_gate.py` (validates against `modeb_full30_corrective_contract.json`) |
| Gene table lacks strand column | Fail; require +/- or UNKNOWN_EXPLICIT | ✅ per contract doc |
| Strand uses only arrows | Fail table validation | ✅ per contract doc |
| BGC class/product missing | Fail unless marked evidence unavailable + next action | ⚠ test needed |
| Integrated table substituted for card | Fail as Full Mode B | ✅ `modeb_full20.py` test 3 |
| Claim-safety preamble repeated after every gene | Fail style gate | ⚠ test needed |
| KCB genome-only / no MIBiG anchor | Force claim ceiling: family/class similarity only | ⚠ test needed |
| Edge/FC/split BGC | Force boundary caveat and rescue/no-rescue decision | ⚠ test needed |
| RG-GMCI present | Require pair class, core fractions, split flag, interpretation guard, rescue decision | ⚠ test needed |
| POOR/VERY_POOR assembly + novelty claim | Force rescue discussion before strong claims | ⚠ test needed |
| POOR/VERY_POOR assembly + edge/FC sort suppression | `POOR_TIER_EDGE_EQUALITY`: rank by score, not boundary; all BGCs visible | ✅ static doc gate v9.7.147 |
| MAMEY_COMPLETE handback without strain brief/figures/locus-map offer | Fail handback | ✅ static doc gate v9.7.147 |
| BGC ID without node/contig citation at first mention | Fail; `node_notation.py` validator | ⚠ v9.7.145 module ships and is unit-tested, but has zero production call sites (v9.7.374 audit); not mechanically enforced |
| Figure labels overlap above threshold | Fail figure render acceptance | ⚠ PATCH-100 open |
| §19 drafted before §5/§9/§11/§12 meet interpretive floor | `INTERPRETIVE_FLOOR_CHECK`: expand thin sections first | ✅ doc gate v9.7.146+ |

---

## 3. Biology-specific escalation triggers

| Condition | Required escalation |
|---|---|
| transAT-PKS / transAT-PKS-like | Module-boundary caution; AT-logic discussion; fragmentation risk |
| T1PKS + NRPS | Hybrid architecture; module/A-domain/KS logic required |
| T1PKS + saccharide | Glycosylation caveat; do not overclaim antifungal lead |
| lassopeptide + transAT-PKS, RiPP + PKS | Composite-vs-adjacent BGC analysis |
| HR-T2PKS + NRPS + thioamide | Flag as chemically interesting mixed aromatic/NRPS lead |
| LanM / LanKC / T43-LAN / RamS | Lanthipeptide Mode B; precursor/synthetase logic |
| ABC transporter + self-resistance high | Self-resistance/export section required |
| POOR or VERY_POOR assembly | Force rescue discussion before novelty claims and activate `POOR_TIER_EDGE_EQUALITY` |
| Interior + high AB/AF + high novelty | Prioritise isolation/chemistry |
| Interior + high AB/AF + low novelty | Prioritise reconstruction/dereplication |
| Edge + high score | Prioritise assembly rescue before strong claims, but do not bury the BGC |
| RG-GMCI present | Require pair class, core fractions, split flag, interpretation guard, rescue decision |

---

## 4. Named trigger constants

| Constant | Meaning | Guard |
|---|---|---|
| `CHATGPT_EXECUTION_SLICE_LOADED` | New default ChatGPT controller is active | startup docs + static test |
| `MAMEY_COMPLETE_HANDOFF_REQUIRED` | Present code-backed outputs and offer/produce prompt-backed deliverables | `test_trigger_routing_handback_v97147.py` |
| `ANALYSIS_COMPLETE_DELIVERABLE_OFFER` | Sapote must not end after analysis without offer/auto-production | deliverable contract |
| `LOCUS_MAP_PRESENTATION_REQUIRED` | Locus maps present in package must be surfaced to user | handback gate |
| `POOR_TIER_EDGE_EQUALITY` | POOR/VERY_POOR assemblies rank by score, not boundary status; all BGCs visible | edge-equality gate |
| `FULL_MODEB_REQUEST_DETECTED` | §1–§30 contract: `modeb_structure_gate.py` enforces §1–§30 (§1–§20 mandatory + §28, §30 + conditionals); `modeb_full20.py` is the §1–§20 facade (artifact-drift / table-substitution checks) | `modeb_structure_gate.py` + `modeb_full20.py` |
| `INTEGRATED_TABLE_AS_COMPANION` | Emit table; never substitute for card | `modeb_full20.py` test 3 |
| `CLAIM_CEILING_REQUIRED` | §19 + §20 receipts; suppress per-gene claim repetition | style gate |
| `OFFLINE_EVIDENCE_ALLOWED` | BLASTP absence does not block Mode B | §16 gap note |
| `INTERPRETIVE_FLOOR_CHECK` | Pre-§19 internal check: expand §5/§9/§11/§12 if thin before writing verdict | execution slice |
| `WISE_PKS_QUEUE_DETECTED` | Use `wise_fragmented_pks.py` stable ledger/Q-ID batching | ledger |
| `CROSS_STRAIN_COMPARISON_REQUESTED` | Separate comparative report; never replaces Mode B | comparison module |
| `PDF_DELIVERABLE_REQUESTED` | narrative PDF + source MD + evidence CSV + manifest | PDF module |

---

## 5. Routing conflict guards

### OFFLINE_EVIDENCE_ALLOWED vs WISE_PKS_QUEUE_DETECTED (PATCH-CF-006)
These two triggers must not cross-fire:
- `OFFLINE_EVIDENCE_ALLOWED`: BLASTP failed/unavailable → proceed with Mode B; document gap in §16.
- `WISE_PKS_QUEUE_DETECTED`: BLASTP pending/batching → queue workflow; emit FASTA batches.

**Guard:** `OFFLINE_EVIDENCE_ALLOWED` suppresses `WISE_PKS_QUEUE_DETECTED` auto-trigger.  
If both could fire, default to `OFFLINE_EVIDENCE_ALLOWED` and note the queue status in §16.

### Slim-kernel legacy conflict
If `docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` and `docs/CHATGPT_EXECUTION_SLICE_v97147.md` are both present, the execution slice controls default behavior. Abbreviated treatment, Interior-first sorting, or POOR-tier edge suppression from legacy docs is overridden.

---

## 6. Required handback inventory for `MAMEY_COMPLETE_HANDOFF_REQUIRED`

The handback block must check and surface, by path/link when available:

1. `OPEN_ME_FIRST.html`
2. `manifest.json`
3. `[StrainID]_8_strain_brief.pdf`
4. `_8a…_8m_fig_*.png` and each companion `_data.csv`
5. `locus_maps/` SVG/PNG files
6. `[StrainID]_5_workbook.xlsx`
7. `checksums_sha256.txt`
8. `issue_log.md`

Then it must offer or auto-produce the prompt-backed set: Layperson Guide, Technical Full-Analysis Report, Bench Guide, Fermentation Card, Wet-Lab Matrix, Metabolomics Readiness, Ecological Synthesis, Reviewer Attack Simulation, and triggered rescue/QC deliverables.

---

*Authoritative source for all trigger routing decisions. Last updated: v9.7.319 · 2026-06-29*
