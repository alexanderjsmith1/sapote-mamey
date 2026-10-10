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

## TIGRFAM availability is package-specific

The June 2026 extraction-gap report is historical. Current source includes TIGRFAM JSON
extraction and a merge into the per-locus domain channel (`mamey/antismash_evidence.py`,
`extract_tigrfam_hits`, `merge_tigrfam_into_pfam_hits`). The old blanket assertion that the
current extractor drops about 99% of diagnostics must not be copied into a new review.

Read the current [shared G4 guard](_SHARED_GUARD_BLOCK.md#g4--tigrfam-evidence-availability).
Bind the engine, evidence mode, recorded extraction state and actual locus hit list; code presence
alone does not prove a channel ran or was complete. Keep missing evidence unknown and retain a
source-bound recovery receipt when raw evidence is inspected. No prompt authorizes a silent
sealed-package rewrite or a biological negative from a missing diagnostic.

## Provenance note (header correction)
Earlier copies carried a header saying they "live OUTSIDE the bundle / not under checksums." That is
now stale: as of v9.7.6 the reuse prompts are IN `prompts/reuse/`, version-controlled and checksummed,
regenerated against the current monolith/contract with the evidence-JSON, locator, and TIGRFAM guards
built in. The standalone outside-bundle copies are superseded by these.

Companions in `prompts/`: `SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md`, `MAMEY_CHATGPT_EXECUTION_PROMPT.md`,
`CLAUDE_SYSTEM_PROMPT.md`.
