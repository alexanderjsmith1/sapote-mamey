# PATCH — Genus Inference from antiSMASH Output
**Patch ID:** GENUS_INFERENCE_20260624
**Applies to:** Sapote (Claude / LLM judgment tier) — intake and session-start procedure
**Bundle version:** v9.7.122+
**Status:** ACTIVE

## Problem
When a strain's genus is PENDING in the handoff, Sapote was accepting PENDING as final
and labelling deliverables "PENDING_GENUS" without attempting inference. The antiSMASH
output contains enough genus signal to make a probabilistic inference in most cases.

## Procedure
1. **GBK ORGANISM field** (fastest, zero compute) — if populated and not "." / "Unknown",
   use it. DEFINITIVE confidence.
2. **ClusterBlast genus-frequency scan** (primary for de novo assemblies) — count
   actinomycete genus mentions across clusterblast/*.txt; the dominant genus by frequency
   is inferred. Confidence: ≥70% HIGH / 50–69% MODERATE / 30–49% LOW / <30% or tie INDETERMINATE.
3. **KnownClusterBlast cross-check** (secondary) — softer signal; cross-validates step 2.
   If top KCB genus matches top CB genus, confidence increases; if conflict, hold at MODERATE.
4. **Biosynthetic profile coherence** (sanity check only, never overrides step 2).

## RECONCILIATION with the runbook "genus never from KCB" rule
The runbook (AutoPipeline_antiSMASH_to_Compendium.md) states genus is never inferred from
KCB. This patch is COMPATIBLE: step 2 infers from **ClusterBlast genome-homology**
(genome-to-genome similarity, allowed), NOT from KnownClusterBlast chemistry-similarity.
KCB appears only as a step-3 cross-check, never the primary signal. The two are not in
conflict — "genus never from KCB" forbids KCB-chemistry-driven genus calls, which this
patch also avoids.

## Application
Apply the inferred genus at session start, before Mode B, to all card headers, the
COMPLETE header, layperson guide, ecology synthesis, and the Mamey `--taxonomy` flag.
Language scales with confidence: HIGH → "*Genus* sp. (genus inferred from ClusterBlast
frequency, N% actinomycete CB hits; pending 16S confirmation)"; MODERATE → "probable
*Genus* sp."; LOW/INDETERMINATE → retain PENDING_GENUS with the inference attempt noted.
Never use the inferred genus in ecological comparative claims unless HIGH and coherent.
Never fabricate a genus — if inference fails, hold at PENDING.

## AS-XXX worked example
ORGANISM blank → ClusterBlast scan: *Streptomyces* 2,880/3,392 hits = 84.9% → HIGH.
KCB top hits (kirromycin, bottromycin, skyllamycin, microtermolide) confirm *Streptomyces*
as dominant producer class. Profile coherent. Inferred: *Streptomyces* sp. AS-XXX (HIGH).
Consistent with Master_Strain_List_v3 (AS-XXX = Streptomyces/Vespidae/Wisconsin).

*Genus Inference Patch v1.0 · Sapote–Mamey v9.7.122 · 2026-06-24*
