# Sapote Reuse Prompts — Index
**Vetted against:** Sapote–Mamey v9.7.7 contract · Updated 2026-06-10 (added class-specific prompts + TIGRFAM guard).

These are the reusable prompts that drive the "special output" runs — the Sapote/Claude judgment layer
operating over sealed Mamey packages. All inherit `_SHARED_GUARD_BLOCK.md` (G1–G5) and are vetted
against `docs/DELIVERABLE_CONTRACT.md`, `docs/WORKBOOK_SCHEMA.md`, and the monolith.

## Shared guard (read first)
- `_SHARED_GUARD_BLOCK.md` — G1 claim-safety · G2 locator mandate · G3 evidence-JSON-first ·
  **G4 TIGRFAM-extraction guard (NEW)** · G5 convention checks. Every prompt below inherits these.

## Run prompts
| Prompt | Use | Output |
|---|---|---|
| `SAPOTE_DELIVERABLES_REUSE_PROMPT.md` | Standard full per-strain interpretation | Three deliverable docs + workbook sheets |
| `SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md` | Fragmented assembly, cross-contig reconstruction | RG-GMCI D1/D2/D3, FLBR census, LMPKS rescue |
| `SAPOTE_TOP_N_CLASS_REUSE_PROMPT.md` | Generic parameterized class enumeration | Diagnostic-core-grounded top-N table |
| `SAPOTE_TOP50_POLYKETIDE_REUSE_PROMPT.md` | Polyketide enumeration (enediyne TIGRFAM-affected) | Top-50 PKS deliverable + topology graphics |
| `SAPOTE_TOP50_HALOGENATION_REUSE_PROMPT.md` | Halogenation enumeration | Top-50 halogenation deliverable |
| `SAPOTE_TOP_NUCLEOSIDE_REUSE_PROMPT.md` | Nucleoside enumeration (TIGRFAM-affected — fallback required) | Strict + adjacent nucleoside sections |

## Critical interaction: the TIGRFAM-extraction defect (G4)
The package extractor is Pfam-centric and drops ~99% of TIGRFAM diagnostic hits
(`DEFECT_TIGRFAM_EXTRACTION_GAP_2026-06-10.md`). Class-enumeration prompts targeting
**nucleoside, enediyne, ansamycin, TOMM/thiopeptide** can produce confidently-labeled FALSE NEGATIVES
from the package alone. Until the Mamey-side extractor fix lands, those prompts MUST apply the G4
fallback (read raw genomic `antismash.detection.tigrfam`) and mark strict counts provisional. The
halogenation and standard-polyketide paths are lower-risk (Pfam/label-diagnosed) but apply G4 on any
TIGRFAM co-call.

## Provenance note (header correction)
Earlier copies carried a header saying they "live OUTSIDE the bundle / not under checksums." That is
now stale: as of v9.7.6 the reuse prompts are IN `prompts/reuse/`, version-controlled and checksummed,
regenerated against the current monolith/contract with the evidence-JSON, locator, and TIGRFAM guards
built in. The standalone outside-bundle copies are superseded by these.

Companions in `prompts/`: `SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md`, `MAMEY_CHATGPT_EXECUTION_PROMPT.md`,
`CLAUDE_SYSTEM_PROMPT.md`.
