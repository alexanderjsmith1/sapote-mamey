# DELIVERABLE — Contig-Rescue Reconstruction (clusterblast-scaffolded)

> **Filing.** `docs/modules/DELIVERABLE_ContigRescueReconstruction.md`.
> **Extends / references:** `tools/build_reconstruction.py` (the deterministic engine), `tools/build_lead_detail.py` (per-lead gene/domain inventory + corrected RG-GMCI rescue groups), `DELIVERABLE_LMPKSRescue.md` (sibling fragment-rescue module — split-pathway PKS), `KNOWLEDGE_ConstellationReporting.md` (the reporting-fidelity rule this delivers under), `prompts/reuse/SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md`. **Do not re-derive the RG-GMCI rescue grouping here — it is owned by `build_lead_detail.py`.**
> **Precedence.** Parent monolith wins. This module owns the *reconstruction report format and the CB-scaffold method*; the *gene/domain extraction* and *rescue grouping* it consumes are owned by Mamey code and must not be re-derived by hand.
> **Status:** `CODE_BACKED` (CB parse, tiling, flank census, CB re-annotation) **+ `PROMPT_BACKED`** (complementarity argument, subclass identity, claim ceiling).
> **One-line purpose.** Turn the raw `clusterblast/` hit tables into a defensible split-pathway *reconstruction hypothesis* for fragments scattered across contigs — ordering them against a complete-genome reference, re-annotating poorly-called genes, and walking each contig flank honestly.

---

## 1. Why clusterblast, not knownclusterblast

**Division of labor:** KCB (MIBiG) **names** the compound; CB **reconstructs** it.
- **knownclusterblast** searches a few thousand curated MIBiG clusters — great for subclass
  identity (AT2433-A1, loonamycin), but too sparse to *order* fragments and often missing the
  tailoring half.
- **clusterblast** searches the full GenBank/RefSeq set, which contains **complete-genome**
  clusters. A complete CB reference is a **scaffold** the fragments tile onto in order, and —
  because it is a fully annotated genome — it **re-annotates** query genes the draft called
  "hypothetical." CB is therefore the engine for **poorly-annotated** BGCs.

## 2. When it is offered (Deliverable Offer Protocol)

Auto-fire — per `DELIVERABLE_CONTRACT.md`, never make the user ask. Triggers:

| Trigger | Condition | Action |
|---|---|---|
| 1 — Functional-complementarity flag | a lead's compound class requires tailoring (GT / P450 / halogenase / deoxysugar) that is **absent** in its region (completeness check) | reconstruct: find the providing fragment + CB scaffold |
| 2 — Strong RG-GMCI group | a CLEAN_SPLIT or HUB component from `build_lead_detail.py` | reconstruct each group |
| 3 — Shared KCB/CB anchor across regions | two regions point at the same indolocarbazole/polyene/glycopeptide reference family | reconstruct |
| 4 — Edge/FC lead with deflated KCB | truncation suspected; CB may carry the missing arm | reconstruct |

**Null result is mandatory:** if no shared CB reference is found across the fragments, emit
the null ("reconstruction not supported by CB; fall back to functional complementarity only").

## 3. What the engine produces (`build_reconstruction.py`)

1. **Shared CB scaffold** — the complete reference(s) every fragment hits, ranked by genes
   covered + cumulative score.
2. **Tiling table** — each query gene mapped to its reference gene, **ordered by reference
   position**, with an overlap test: 0–1 overlap = *complementary, tiles cleanly*.
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
- **Subclass identity from KCB** — e.g. a non-halogenated CB scaffold (staurosporine-type
  *Salinispora*) that scaffolds core+sugar, with the halogenase flagging `CB-family` because
  it hits the *halogenated* references separately → the product is the halogenated subclass
  (AT2433 / loonamycin), not the scaffold's own compound.
- **Claim ceiling** — reconstruction *hypothesis* on CB homology, **not** nucleotide joining;
  confirm by long-read or boundary PCR.

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

- **AS-XXX indolocarbazole** (working case): NODE_182 core + NODE_105 halogenase/sugar →
  *Salinispora arenicola* scaffold (`NZ_KB913036`), 8 reference genes covered, 0 overlap,
  4 hypothetical genes re-annotated. *Use a type strain for any published demonstration; keep
  unpublished antimicrobial leads in their own paper.*
