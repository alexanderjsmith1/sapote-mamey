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

## 2. When to run it

Run it when one of these conditions holds for a lead:

| Trigger | Condition | Action |
|---|---|---|
| 1 — Functional-complementarity flag | a proposed class suggests a function not detected in the reviewed region | check source coverage and alternatives, then search for source-bound candidate roles without assuming absence or a partner |
| 2 — Strong RG-GMCI group | a CLEAN_SPLIT or HUB component from `build_lead_detail.py` | reconstruct each group |
| 3 — Shared KCB/CB anchor across regions | two regions point at the same indolocarbazole/polyene/glycopeptide reference family | reconstruct |
| 4 — Edge/FC lead with deflated KCB | truncation suspected; CB may carry the missing arm | reconstruct |

Report no shared comparator only after confirming every requested fragment and its source/parse coverage. Missing aliases are silently skipped, absent files produce empty evidence, and the helper does not distinguish those cases from a completed comparison with no shared reference. Keep unavailable/unparsed states held; do not promote them to a null result or use functional complementarity to clear that hold.

## 3. What the engine produces (`build_reconstruction.py`)

1. **Shared CB comparator** — intersect parsed reference accessions across the retained fragments and rank by the summed number of parsed hit rows, then cumulative score. Hit rows are not deduplicated gene coverage, and the helper does not independently verify reference completeness.
2. **Tiling display** — order subject IDs by their trailing integer, a reference-order proxy rather than inspected genomic coordinates. The verdict uses overlap fraction relative to the smallest nonempty subject set, not a universal zero-or-one-gene allowance. Retain the emitted fraction and actual evidence denominator; a software verdict does not prove clean physical tiling.
3. **CB re-annotation** — query genes the draft called "hypothetical" re-read against the
   reference (the poorly-annotated-BGC rescue).
4. **Region-file CDS census ("look downstream")** — every CDS parsed from each fragment's selected
   region GenBank file, flagged `★ scaffold` / `· CB-family` / `unexplained`. A region file covers
   the antiSMASH region and its flanks, not necessarily the whole parent contig, so this is not a
   whole-contig census. Flank genes that do not hit are stated as
   the honest boundary, **never** assumed absent. (This is the C8 companion: the boundary
   walk states what the contig edge cannot resolve.)

## 4. What Sapote adds (judgment layer)

- **Functional-complementarity hypothesis** — compare proposed roles, shared-reference evidence, input coverage and alternative explanations. Predicted functions do not prove mechanistic complementarity, a unique pairing or physical linkage. Select an independent validation method suited to the particular question.
- **Subclass hypothesis from comparator and architecture evidence** — retain both compatible and conflicting matches, distinguish direct pathway evidence from broad accessory context, and state alternatives. A comparator label or an accessory annotation does not identify the focal product or establish the reference's modification chemistry.
- **Claim ceiling** — reconstruction *hypothesis* on CB homology, **not** nucleotide joining;
  physical linkage remains unresolved until independently tested with a suitable method.

## Current input/output and identity boundary

For each retained alias the helper chooses the region GenBank in this order: the exact `source_gbk` basename recorded for the BGC; else `<contig>.regionNNN.gbk` for the BGC's region number; else the only `<contig>.region*.gbk` file. When several region files share the contig and none matches, the census marks that fragment `AMBIGUOUS` and lists no CDS (a hold, not an empty region); a missing file is `NOT_FOUND`. The report names the chosen file and how it was chosen. The ClusterBlast text is still the first match of a `<contig>_*.txt` glob and is not bound to the region. Reconcile every selected path with the full source-bound strain / full node-or-contig / region / alias. Missing requested aliases are skipped. Keep the requested and retained rosters separately; no full-locus admission receipt is emitted.

Use explicit fresh external `--out` paths for both reconstruction and lead-detail helpers when preserving a package. Defaults target `reconstruction.md` and `lead_detail.json` inside the package. Reconstruction replaces its chosen destination; lead-detail refuses an occupied one. Choose separate fresh authorized external paths for both. Atomic replacement of one output is not package validation, checksum refresh or scientific acceptance. Preserve original package evidence and bind source/output hashes separately.

## 5. Wiring

Start from the source-bound package produced by the authorized intake route. Cited KnownClusterBlast members are kept under `source_locator_evidence/` only when they were resolved and copied; inspect their status and receipts. Per-gene ClusterBlast tables do not replace the original raw ClusterBlast folder. Resolve any required source files from the hash-bound original ZIP without overwriting evidence.

```bash
python tools/build_lead_detail.py --package runs/EXAMPLE/package --gbk-dir source/region-gbks --leads BGC_ID_FROM_INVENTORY --out reviews/EXAMPLE-lead-detail.json
python tools/build_reconstruction.py \
  --package runs/EXAMPLE/package --clusterblast-dir source/clusterblast \
  --gbk-dir source/region-gbks --fragments BGC_ID_1,BGC_ID_2 --out reviews/EXAMPLE-reconstruction.md
```

Substitute the actual package, source folders, bound aliases and fresh output paths; quote spaces. Bind each alias to its full strain / full contig / region / BGC alias before interpretation. The example IDs are schematic, not evidence for real fragments.

## 6. Validation cases

No worked public case is bundled. For a published demonstration, use a public type-strain genome and write
each fragment as `<strain> / <contig> / region<NNN> / BGCnnn`, copied from the package.
