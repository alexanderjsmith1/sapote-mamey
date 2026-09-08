# BiG-SCAPE ↔ Sapote-Mamey ↔ antiSMASH — true integration (v9.7.319)

> **LEGACY IMPLEMENTATION NOTE.** This document explains older adapters; it is not permission to
> run a one-shot pipeline or mutate cards/triage boards. LLMs must follow
> `docs/LLM_COMPANION_TOOL_PROTOCOL.md` and `docs/BIGSCAPE_GCF_WORKFLOW.md`. Default output is an
> additive locator-keyed overlay. `bigscape_ingest_to_mamey.py` requires separate user authorization
> and source-preserving reconciliation. “KNOWN/NOVEL” is prohibited on cohort-only databases.


Prior state (v9.7.319): the bundle could *prep* antiSMASH/Mamey inputs for BiG-SCAPE, *run*
clustering + MIBiG anchoring, and emit a locator-keyed cross-strain TSV. But "ingest GCFs back
into the Mamey locator space" was a manual join — nothing wrote the cross-strain / known-vs-novel
result **into** the per-BGC deliverables. This patch closes that loop.

## The shared key
antiSMASH emits `*.regionNN.gbk`; `bigscape_prep.py` strain-prefixes them to
`<STRAIN>_NODE_..._.regionNN.gbk`. The parsed `strain : node.region` is the single join key across
all three layers. Mode B cards are named `<STRAIN>_BGC###_ModeB.md` (a BGC *number*, not a
locator), so the **triage board is the bridge** — it carries both the BGC number and the
node.region. No triage board → the ingest refuses rather than guess (matches the "reconcile BGC
numbering before authoring" discipline).

## What's new

### `tools/bigscape_ingest_to_mamey.py`  — the missing half
Reads an anchored BiG-SCAPE 2 DB and, for every strain BGC, computes a GCF context: family id +
KNOWN/NOVEL at the chosen cutoff, the MIBiG accession(s) sharing the family (with compound names
from the bundle's `mibig_reference_index.bacterial.json`), the nearest characterized cluster and
its GCF distance, and the other cohort strains in the family. It then **writes a fenced
`GCF cross-strain context` block into each Mode B card** (under §8 Comparator/KCB) and can add GCF
columns to the triage board. Idempotent (re-runs replace the block), capacity-worded, and
provenance-tagged `[store-backed GCF | BiG-SCAPE]`. Tested end-to-end (`tests/…_v9_7_291.py`) on a
synthetic anchored DB *and* verified against the real 36-strain anchored DB.

### `tools/bigscape_pipeline.py`  — one command, whole loop
`prep → cluster+anchor → known_novel + cross_strain → ingest`. Pure orchestration of the shipped
adapter tools + the external BiG-SCAPE binary; adds no new science. Resumable (`--skip-cluster`),
and `--chunk-mibig N` routes references through `bigscape_mibig_batches.py` for small-memory hosts.

### `tools/bigslice_query.py`  — BiG-SLiCE as a second opinion
BiG-SCAPE clusters by pairwise domain alignment against **2,088 MIBiG** references. BiG-SLiCE
embeds each BGC as a BiG-FAM feature vector (super-linear) and can **query against the ~1.2M-GCF
BiG-FAM model built from all of NCBI** — turning "novel vs MIBiG" into "novel vs essentially all
sequenced bacterial biosynthesis". Modes: `cluster` (de novo on the cohort, diff against the
BiG-SCAPE families — agreement = robust family, disagreement = inspect), and `query` (vs a
downloaded BiG-FAM model). Verified: BiG-SLiCE 2.x installs (`pip install bigslice`) and the CLI
matches this tool's invocations. **Not run end-to-end here** — a real run needs the BiG-SLiCE
sub-Pfam HMM DB and (for `query`) the multi-GB BiG-FAM `full_run_result`, both external downloads
like antiSMASH/Pfam. Treat BiG-SLiCE as an optional prerequisite, not a vendored dependency.

## Recommended flow
```
# 1-4 in one shot (antiSMASH zips or sealed Mamey packages as --inputs):
python tools/bigscape_pipeline.py \
    --inputs <pkg-or-antismash>... --pfam Pfam-A.hmm --mibig-dir mibig_gbks/ \
    --workdir bigscape_run/ --chunk-mibig 300 \
    --ingest-package <MameyPackage/> \
    --mibig-index mamey/data/mibig/mibig_reference_index.bacterial.json

# optional global-novelty second opinion:
python tools/bigslice_query.py cluster --input bigscape_run/input --out bigslice_out/
python tools/bigslice_query.py read --out bigslice_out/ --bigscape-tsv bigscape_run/cross_strain_GCFs.tsv
```

## Reading the injected block (discipline)
KNOWN = the family shares a bin with a MIBiG reference → **architecture-consistent, capacity-level**,
never a compound-identity claim. GCF distance is domain-architecture distance (0 identical … 1
maximal). The block explicitly defers to the card's own KCB/Mode B evidence for per-BGC calls.
Bioactivity stays extract-level; nothing here is a per-BGC phenotype claim.

## What is and isn't tested in this cut
- **Tested:** `bigscape_ingest_to_mamey.py` (synthetic DB unit test + real 36-strain anchored DB;
  KNOWN/NOVEL split, MIBiG accession+compound resolution, nearest-distance, idempotency, §8
  placement, capacity wording).
- **Orchestration only (not a new algorithm):** `bigscape_pipeline.py` chains existing verified tools.
- **CLI-verified but not executed here (external model DB required):** `bigslice_query.py`.

## Addendum — antiSMASH ↔ BiG-SCAPE reconciliation (`tools/antismash_bigscape_join.py`)
antiSMASH and BiG-SCAPE each compare a BGC to MIBiG by different methods: antiSMASH
KnownClusterBlast (gene-level BLAST → % similarity) vs BiG-SCAPE GCF (domain-architecture family
→ KNOWN if it contains a MIBiG ref). This tool joins them per BGC on the node.region locator and
flags agreement/disagreement (a disagreement is the BGC worth a look). It is DB-free and portable:
reads antiSMASH region GBKs (aSDomain architecture) + the small BiG-SCAPE cross_strain/known_novel
TSV; optionally reads antiSMASH `knownclusterblast/` for the actual KCB accessions. Verified on the
51-strain cohort (1,608 BGCs joined; correctly links a cohort strain's T1PKS to its novel family with
full KS-AT-KR-ACP-TE domain architecture; specific strain→family pairings withheld from the public code tier). Upload the antiSMASH `knownclusterblast/` dirs to enable the KCB column.
