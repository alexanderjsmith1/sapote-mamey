# Bounded GToTree panel selection

This optional post-seal companion stages a transparent genome panel before
GToTree. It does **not** run GToTree or IQ-TREE and cannot alter a Mamey core run.

## User-visible size choice

```bash
python tools/build_phylo_panel.py --show-options
```

The supported total-tip presets are **20**, **40 (default)**, and **60**. A user
may supply another integer from 3 through 60. Values above 60 are a hard error.
The number is total tips, including AS/SID queries, references/comparators, and
exactly one outgroup. It is not a per-query number.

The default 40-tip panel is intended for the current combined Streptomyces
survey. A focused figure can use 20. Sixty is the release ceiling, not a target.
The user must choose larger panels deliberately.

```bash
python tools/build_phylo_panel.py candidates.tsv staged_panel/ --panel-size 40
```

## Candidate manifest and selection rules

Start from `examples/phylo_panel_candidates.template.tsv`. Required columns are
`candidate_id`, `role`, and `source_path`. Roles are `QUERY`, `REFERENCE`, or
`OUTGROUP`.

- Query IDs are explicit candidate IDs rather than inferred from a fixed prefix.
  Distinct-content QUERY records are retained before references; no unique query
  is dropped merely to meet the panel size. If queries plus one outgroup exceed the target, the tool stops.
- Each `REFERENCE` must carry a curator-supplied `selection_basis` and explicit
  `related_query_ids`. The tool never infers or invents “nearest,” “type,” or
  reference status.
- At most three selected references may be linked to any query. The default and
  hard maximum for `--max-related-per-query` are both 3.
- A named type strain can be added past that cap as a type anchor. It is a
  `REFERENCE` row with `selection_basis` = `nearest_type_strain_<method>` (the
  curator's method, for example `tygs`, `ani` or `mlsa`) and `assembly_fromtype`
  = `assembly from type material`, copied from NCBI Assembly. Any other
  `assembly_fromtype` value stops the tool.
- Type anchors are chosen after the ordinary references, so they never change
  which ordinary references are selected. `--max-type-anchors-per-query` sets
  their limit (0 to 2, default 2). They still count toward the total-tip target,
  and a query never gets more than 4 related references and anchors together.
- `panel_selected.tsv` marks anchors with `type_anchor` = `yes`, and
  `panel_receipt.json` lists them under `type_anchors`, so a caption can say
  which tips were added to anchor names. `plan_gtotree_iqtree.py` re-checks both
  fields and both limits.
- Exactly one unique outgroup is staged. “Outgroup” in the manifest remains a
  curator assertion requiring human review; the tool does not validate that the
  lineage is phylogenetically appropriate.
- Priority is numeric ascending. It controls deterministic selection only; it
  does not represent biological rank or confidence.

## antiSMASH ZIP ingress

`source_path` may point directly to FASTA/GenBank or to an antiSMASH ZIP. For a
ZIP, set `source_member` to the exact assembly FASTA or whole-assembly GenBank
member. This is important because an antiSMASH ZIP usually contains many region
GenBanks that are not independent assemblies. Auto-detection is accepted only
when exactly one unambiguous assembly-like member remains after region/cluster
members are excluded. Unsafe and absent member paths are rejected.

This is a parser check, not assembly validation. FASTA headers and whitespace are dropped; accepted symbols are `ACGTUNRYKMSWBDHVX.-`, and dots and hyphens are removed. GenBank input is read from ORIGIN blocks only. The selector turns U into T, as the planner does, so both compute the same content hash.

## Exact-content duplicate guard

Assemblies are hashed from uppercase nucleotide sequences after ignoring record
headers and contig order. Exact nucleotide-content duplicates are represented
once. Every excluded duplicate points to the retained candidate. This guard does
not collapse merely high-ANI genomes; similarity/ANI adjudication remains a
separate analysis and provenance decision.

The selector applies this deduplication to QUERY records too: equal-content
queries become one retained record plus `EXCLUDED_DUPLICATE` candidates. Role
priority is QUERY, OUTGROUP, REFERENCE, then anchor/priority/ID tie-breaking.
An outgroup duplicating a query can therefore disappear before outgroup validation.
Inspect `panel_candidates.tsv` before accepting the panel; do not equate retained
unique assemblies with independent isolates.

This differs from direct planner ingress, which uses `HOLD_DUPLICATE_QUERY_REVIEW`.
Prepared-panel ingress reads selected rows, so upstream duplicate-query exclusions
are not independently restored by that planner hold. Keep this as an explicit
identity/admission review: preserve every original query alias and obtain the
source-level reconciliation before computing a panel that collapsed owner queries.

## Receipts before computation

The new output directory contains:

| Artifact | Purpose |
|---|---|
| `panel_candidates.tsv` | Every candidate, selection/exclusion reason, source/member and hashes |
| `panel_selected.tsv` | Exact staged panel and all explicit comparator bases |
| `label_crosswalk.tsv` | Five-column, headered human receipt: ID, tree-safe label, display label, role, taxonomy |
| `labels.tsv` | GToTree `-m` map: exactly two columns, no header |
| `panel_receipt.json` | Size option/default/max, counts, duplicates, claim ceiling, input hash |
| `genomes/*.fna` | Normalized staged assemblies |
| `genomes.txt` | Absolute paths for a later GToTree command |

Human review of the selected panel and label crosswalk is required before any
GToTree invocation. Resource enforcement belongs to the selected planner/runner,
not this selector. Serial v1 settings and the governed v2 worker profile have different
requirements; in particular the v2 HMM phase requests two workers per genome job.
Follow [runtime admission](GTOTREE_RUNTIME_ADMISSION.md) and the current approved budget.
Unless an approved budget says otherwise, run at most four trees at once and stay within four
threads in total.

For the admitted v1.8.19 route, use the generated headerless two-column file for GToTree label replacement:

```bash
GToTree ... -m staged_panel/labels.tsv ...
```

Column 1 is the staged FASTA filename (for example `Streptomyces_sp_AS-XXX.fna`)
and column 2 is its unique machine-safe replacement label. Do **not** pass
`label_crosswalk.tsv` to `GToTree -m`; that five-column headered table exists for
human review and provenance only. The governed v2 planner generates a different map whose
keys are the exact absolute paths in its `genomes_absolute.txt`; do not pass this selector's
basename map unchanged to that route. Use the selected planner's bound map and manifest
([current run contracts](COMPANION_RUN_CONTRACTS.md)).

## Staging receipt and recovery limits

The output directory must be absent, including an empty existing directory. Selection
requires exactly the requested tip count; an undersupplied eligible pool is refused,
not silently returned as a smaller panel. Writes then proceed file by file, so a later
error can leave a partial destination that refuses reuse. Preserve that attempt and
use a new reviewed destination for recovery (`tools/build_phylo_panel.py`).

ZIP admission checks names/suffixes and sequence parsing; it does not independently
prove that an explicitly selected GenBank/FASTA is a whole assembly. Type-anchor
admission checks the supplied type-material string, not an NCBI record. Independently
verify source accession/version, assembly scope and deposited type status. Content
deduplication preserves sequence orientation; reverse-complement equivalence is not
normalized.

The receipt hashes the candidate manifest and rows retain whole-source and normalized
content hashes. It does not separately hash each raw ZIP member, staged FASTA, output
TSV or the builder source. Retain those bindings and a stable input snapshot separately
when required for downstream admission; `PANEL_STAGED_NOT_RUN` is not an executed or
scientifically accepted tree.

## Claim ceiling

Panel membership is comparator selection only. It does not establish taxonomic
identity, nearest-neighbor status, strain independence, novelty, biosynthetic
production, or biological activity. A core-gene tree strengthens topology; ANI
and provenance adjudication remain separate. Exact-content duplicates are an
identity warning, not proof of the physical source of a mix-up or contamination.
