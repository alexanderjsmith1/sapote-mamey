# BiG-SCAPE integration adapters: current limits and historical scope

Read the [companion protocol](LLM_COMPANION_TOOL_PROTOCOL.md) and [GCF workflow](BIGSCAPE_GCF_WORKFLOW.md). Default reconciliation is a reviewed additive overlay. The shipped ingest tool directly rewrites cards, so using it on canonical/sealed cards requires the separately authorized, source-preserving reconciliation described there. Use this guide to check input identity, selected database scope and card-write behavior before choosing a workflow.

> **LEGACY IMPLEMENTATION NOTE:** The adapter behavior described here includes retained legacy status and write semantics. Use the linked current workflow for a new task; historical labels do not establish scientific acceptance.

## Exact run and portable identity

`tools/bigscape_ingest_to_mamey.py` requires `--run-id` with `--db`, selects region-level memberships in that run and normalized cutoff, and rejects conflicting family assignments. Family namespace combines run, cutoff and family ID; family ID alone is not a portable cross-run join key. Membership selection does not verify completed-run status or reference provenance.

The triage bridge maps strain+BGC alias to a normalized locator. Duplicate bridge entries overwrite earlier ones; a strain-less fallback is permitted. Package discovery chooses the first matching triage CSV and card directory, rather than enforcing unique candidates. Explicitly bind the reviewed bridge and input directory, and retain strain, full contig/node, region and alias with hashes. Coverage-stripped locator normalization is not proof that differently named biological records are identical.

## Membership, distance and legacy status limits

DB family membership is selected by exact run/cutoff, but the nearest-MIBiG calculation scans the entire distance table without a run/parameter filter (`109–184`). It can therefore attach a nearest-reference result from a different comparison history. Hold that field until an independently scoped distance receipt establishes the selected run and parameters.

`KNOWN` means a parsed MIBiG accession shares the selected family; `NOVEL` is the emitted legacy fallback, not demonstrated novelty. On cohort-only data, suppress known/novel interpretation and report only measured within-panel membership. TSV ingest converts every non-KNOWN status to NOVEL; absent/unknown status must remain a hold rather than an adopted novelty call. Missing/malformed MIBiG name indexes silently yield `?` labels. The block's “no characterized analog” wording overstates absence when reference loading has not been verified.

Portable TSV mode lacks cohort co-member detail even when family namespace fields are available. Empty co-member lists in DB mode describe selected-family membership only; they do not demonstrate organism rarity or absence of related loci elsewhere.

## Card writes, placement and recovery

The ingest CLI has `--dry-run`; its updated count then means proposed changes. Actual writes replace the existing fenced GCF block, otherwise insert near a literal section8 heading, otherwise append at the end. Current full-profile section numbering may have a different meaning, so automatic placement needs a content/layout review. Repeated replacement is text-idempotent, not proof of source/version binding.

Writes use atomic replacement per card, with no whole-batch transaction, original-hash gate, input/output hash receipt or current-profile verifier. A partial batch can survive failure. Cards lacking a locator/context match are skipped; zero exit can mean every card skipped. Inspect updated/skipped/context counts and every proposed locus binding. Despite historical help text, the current CLI does not add GCF columns to the triage CSV (`280–401`). Preserve sources; stage a separately reviewed additive overlay rather than testing mutation on them.

## Pipeline integration hold

`tools/bigscape_pipeline.py` proves an explicit run exists or that exactly one new run row appeared. Skip-cluster and pre-existing/shared databases require explicit IDs; MIBiG chunking remains held. The normal prep call lacks the strictness option required by `bigscape_prep.py`, so the unmodified one-shot prep path fails. No-MIBiG execution still routes through legacy known/novel export, and optional `--ingest-package` writes cards without an approval gate inside the script. The runbook is the approval/provenance authority, not the presence of those flags. See the [GCF workflow](BIGSCAPE_GCF_WORKFLOW.md) for the detailed recovery hold.

## antiSMASH join and BiG-SLiCE limitations

`tools/antismash_bigscape_join.py` validates family namespaces but joins GBK names using the first underscore-delimited strain token and a filename locator. Its optional KCB parser keys hits by strain+region only, uses the first accession/percent regex matches and can overwrite duplicate region keys across contigs. Its agreement label tests KCB hit presence versus family KNOWN status; it does **not** test equality of anchor accessions or methods. Missing KCB context is unmeasured, not disagreement. Output TSV is overwritten directly and can be header-only with zero exit; it has no source/output hash receipt (`54–179`).

`tools/bigslice_query.py` is an external-tool adapter, not universal bacterial novelty evidence. Reference-panel size, model date/sampling and installed-version compatibility require their own receipts. Cluster mode reuses existing symlinks and output paths; read mode may choose the first recursive DB, assigns duplicate locators by last row, and reports only the number of overlapping assignments rather than a quantified agreement score. Query mode requires `--out` in its parser but sends results to the model route and does not use that option (`43–131`). Hold stale outputs and unbound database/model selection. Do not transfer historical 2,088-reference/~1.2M-model or 36-/51-strain test counts to a current run.

Earlier v9.7.319 accounts and named cohort examples are historical implementation reports. Use their original test/run receipts for historical claims and separate scientific acceptance from implementation status. Source owners: `tools/bigscape_ingest_to_mamey.py`, `tools/bigscape_pipeline.py`, `tools/antismash_bigscape_join.py`, `tools/bigslice_query.py`.
