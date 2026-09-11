# BUNDLE PATCH NOTES — v9.6.22

**Engine 1.9.13 · bundle v9.6.22.** Builds on v9.6.21 (validator realign, CAS-safe redaction,
`--master` guard). This cut adds the contig-rescue reconstruction line and the reporting-fidelity
guard, plus the lead-detail and punch-card tooling from the working session.

## What changed

### New tools (`tools/`)
| File | Status | Purpose |
|---|---|---|
| `build_reconstruction.py` | CODE_BACKED | clusterblast-scaffolded split-pathway reconstruction: shared CB scaffold → tiling (ordered, overlap test) → CB re-annotation of hypothetical genes → contig-flank census |
| `build_lead_detail.py` | CODE_BACKED | per-lead gene/domain/resistance/transport detail; ctg/NODE + `ctgN_M` locus tags; corrected RG-GMCI rescue groups; iterative-thinking scaffold |
| `build_punchcard.py` | CODE_BACKED | deterministic post-Mamey multi-strain literature punch card; anchor dedup; gene-marker scan; NAPAA/primary de-prioritize |

### New modules (`docs/modules/`)
| File | Status | Purpose |
|---|---|---|
| `DELIVERABLE_ContigRescueReconstruction.md` | CODE+PROMPT | reconstruction deliverable: offer protocol, engine output, Sapote complementarity/identity/claim-ceiling |
| `KNOWLEDGE_ConstellationReporting.md` | KNOWLEDGE | no-compression rule for multi-gene constellations; flank census; collective-weight ranking |
| `SAPOTE_LEAD_DETAIL_MODULE.md` | (from session) | corrected rescue rule + iterative thinking + punch-card handoff |

### Corrections folded in
- **RG-GMCI rescue interpretation** — grade on `strong_supporting_references` +
  `complete_or_chromosome_references` + `max_protein_sum`, **not** shared-product-token agreement
  (splits annotate differently by design). Report connected-component groups. The
  **completeness check** (compound class needs tailoring X; X absent) — not the strong-ref
  threshold — triggers the orphan-tailoring search; complementary partners outrank redundant cores.
- **ctg/NODE surfaced** in lead detail (every gene carries its `ctgN_M` locus tag, matching the
  antiSMASH HTML for direct BLASTp).

## Apply-to-all-tiers checklist
This is the MERGED (private scaffold) tier. Propagate to CODE / CODE-analysis-free / SID-public via
`tools/make_public_tier.sh` with a shared `BUILD_STAMP`, then leak-audit (0 AS strain IDs) before ship.

- [ ] copy `tools/build_reconstruction.py`, `tools/build_lead_detail.py`, `tools/build_punchcard.py`
- [ ] copy `docs/modules/DELIVERABLE_ContigRescueReconstruction.md`, `KNOWLEDGE_ConstellationReporting.md`, `SAPOTE_LEAD_DETAIL_MODULE.md`
- [ ] `pyproject.toml` version 1.9.13; CHANGELOG v9.6.22 entry present
- [ ] redaction pass on the SID/CODE tiers (the new modules reference the AS-XXX NODE_105/NODE_182 case — keep contig IDs but verify no SID#### leaks; AS-XXX NODE labels are assembly-derived, not SID identifiers)
- [ ] validator PASS on `examples/test_data/test_master.xlsx` (unchanged from v9.6.21)
- [ ] `python -m py_compile tools/*.py mamey/*.py`

## Open items (next cut)
- **PACKAGE_RETAIN_CLUSTERBLAST (P0 for reconstruction at scale):** the package discards raw
  `clusterblast/`. `build_reconstruction.py` currently needs `--clusterblast-dir` pointing at the raw
  antiSMASH output. Add a Mamey step to copy/extract per-region CB hit tables into the package so
  reconstruction runs offline from the package alone.
- **`mamey run --punchcard`** flag to auto-emit the literature card at end of extraction.
- **Uncalled-contig orphan-tailoring scan** (antiSMASH won't call a lone-tailoring fragment).
- **good_geometry_references / avg_min_identity empty under `--json-evidence off`** — investigate
  whether `bounded` (vendored ijson) is needed to populate them (would sharpen rescue grouping).
- Demonstrate the full line on **type-strain genomes** (publishable) before applying to unpublished
  antimicrobial leads (reserved for their own paper).
