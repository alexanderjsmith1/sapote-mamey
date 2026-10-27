# DELIVERABLE — Contig-Rescue Reconstruction (clusterblast-scaffolded)

> **Filing.** `docs/modules/DELIVERABLE_ContigRescueReconstruction.md`.
> **Extends / references:** `tools/build_reconstruction.py` (the deterministic engine), `tools/build_lead_detail.py` (per-lead gene/domain inventory + corrected RG-GMCI rescue groups), `DELIVERABLE_LMPKSRescue.md` (sibling fragment-rescue module — split-pathway PKS), `KNOWLEDGE_ConstellationReporting.md` (the reporting-fidelity rule this delivers under), `prompts/reuse/SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md`. **Do not re-derive the RG-GMCI rescue grouping here — it is owned by `build_lead_detail.py`.**
> **Precedence.** The current user task and [assistant governance](../ASSISTANT_GOVERNANCE.md) govern actions. This is reconstruction/reporting guidance over selected source outputs; the actual helper owns its implemented joins and verdicts. The monolith is design/history reference, and historical worked cases do not bind a current locus.
> **Status:** `CODE_BACKED` (CB parse, tiling, flank census, CB re-annotation) **+ `PROMPT_BACKED`** (complementarity argument, subclass identity, claim ceiling).
> **One-line purpose.** Turn the raw `clusterblast/` hit tables into a defensible split-pathway *reconstruction hypothesis* for fragments scattered across contigs — ordering them against a complete-genome reference, re-annotating poorly-called genes, and walking each contig flank honestly.

---

## 1. Why clusterblast, not knownclusterblast

**Evidence roles:** KCB/MIBiG supplies similarity to characterized references; ClusterBlast supplies comparison to its selected genome-cluster reference set. Neither names the focal product or proves a physical reconstruction. Verify the actual database/reference version, completeness and locus membership instead of inferring them from the channel name.
- **knownclusterblast** compares against the run's selected MIBiG reference set. Retain its actual database version, hit scope and query/subject binding; characterized-reference metadata does not identify the focal compound.
- **clusterblast** supplies saved genome-cluster comparisons. A selected reference can orient a reconstruction hypothesis only after its identity, completeness and membership are checked. Transferred annotations remain homology-supported candidates, not independent functional validation or a new authoritative query annotation. The helper does not certify the database as the entire current GenBank/RefSeq collection.

## 2. When it is offered (Deliverable Offer Protocol)

Auto-fire — per `DELIVERABLE_CONTRACT.md`, never make the user ask. Triggers:

| Trigger | Condition | Action |
|---|---|---|
| 1 — Functional-complementarity flag | a lead's compound class requires tailoring (GT / P450 / halogenase / deoxysugar) that is **absent** in its region (completeness check) | reconstruct: find the providing fragment + CB scaffold |
| 2 — Strong RG-GMCI group | a CLEAN_SPLIT or HUB component from `build_lead_detail.py` | reconstruct each group |
| 3 — Shared KCB/CB anchor across regions | two regions point at the same indolocarbazole/polyene/glycopeptide reference family | reconstruct |
| 4 — Edge/FC lead with deflated KCB | truncation suspected; CB may carry the missing arm | reconstruct |

Report no shared comparator only after confirming every requested fragment and its source/parse coverage. Missing aliases are silently skipped, absent files produce empty evidence, and the helper does not distinguish those cases from a completed comparison with no shared reference. Keep unavailable/unparsed states held; do not promote them to a null result or use functional complementarity to clear that hold.

## 3. What the engine produces (`build_reconstruction.py`)

1. **Shared CB comparator** — intersect parsed reference accessions across the retained fragments and rank by the summed number of parsed hit rows, then cumulative score. Hit rows are not deduplicated gene coverage, and the helper does not independently verify reference completeness.
2. **Tiling display** — order subject IDs by their trailing integer, a reference-order proxy rather than inspected genomic coordinates. The verdict uses overlap fraction relative to the smallest nonempty subject set, not a universal zero-or-one-gene allowance. Retain the emitted fraction and actual evidence denominator; a software verdict does not prove clean physical tiling.
3. **CB re-annotation** — query genes the draft called "hypothetical" re-read against the
   reference (the poorly-annotated-BGC rescue).
4. **Contig-flank census ("look downstream")** — every CDS on each contig flagged
   `★ scaffold` / `· CB-family` / `unexplained`. Flank genes that do not hit are stated as
   the honest boundary, **never** assumed absent. (This is the C8 companion: the boundary
   walk states what the contig edge cannot resolve.)

## 4. What Sapote adds (judgment layer)

- **Functional complementarity** — the load-bearing argument: confirm the fragments are
  *mechanistically* complementary (core + GT needing a donor ↔ halogenase + the cassette that
  builds the donor), not merely co-hitting indolocarbazole genes. This is stronger than
  reference overlap and is what RG-GMCI scores miss.
- **Subclass hypothesis from comparator and architecture evidence** — retain both compatible and conflicting matches, distinguish direct pathway evidence from broad accessory context, and state alternatives. A comparator label or an accessory annotation does not identify the focal product or establish the reference's modification chemistry.
- **Claim ceiling** — reconstruction *hypothesis* on CB homology, **not** nucleotide joining;
  confirm by long-read or boundary PCR.

## Current input/output and identity boundary

For each retained alias the helper chooses the first matching ClusterBlast text and region GenBank from contig-prefix globs; it does not join the exact region or refuse multiple matches. Reconcile every selected path with the full source-bound strain / full node-or-contig / region / alias, especially when several regions share a contig. Missing requested aliases are skipped. Keep the requested and retained rosters separately; no full-locus admission receipt is emitted.

Use explicit fresh external `--out` paths for both reconstruction and lead-detail helpers when preserving a package. Defaults write `reconstruction.md` and `lead_detail.json` inside the supplied package, replacing existing files. Atomic replacement of one output is not package validation, checksum refresh or scientific acceptance. Preserve original package evidence and bind source/output hashes separately.

## 5. Wiring

```
mamey run … --master …                         # inventory + RGGMCI (unchanged)
# retain raw clusterblast/ in the package (see patch notes: PACKAGE_RETAIN_CLUSTERBLAST)
python tools/build_lead_detail.py …            # completeness check flags absent tailoring
python tools/build_reconstruction.py \
   --package <pkg> --clusterblast-dir <raw/clusterblast> \
   --gbk-dir <region_gbks> --fragments <core>,<tailoring>   # → reconstruction.md
# Sapote: complementarity + subclass identity + claim ceiling → front-page reconstruction
```

## 6. Validation cases (type strains preferred for publication)

- **AS-XXX indolocarbazole** (working case): core fragment + halogenase/sugar fragment, each written
  `AS-XXX / <contig> / region<NNN> / BGCnnn` →
  *Salinispora arenicola* scaffold (`NZ_KB913036`), 8 reference genes covered, 0 overlap,
  4 hypothetical genes re-annotated. *Use a type strain for any published demonstration; keep
  unpublished antimicrobial leads in their own paper.*
