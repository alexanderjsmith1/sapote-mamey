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

- AS and SID query IDs are supported; no query is silently dropped to meet the
  panel size. If queries plus one outgroup exceed the target, the tool stops.
- Each `REFERENCE` must carry a curator-supplied `selection_basis` and explicit
  `related_query_ids`. The tool never infers or invents “nearest,” “type,” or
  reference status.
- At most three selected references may be linked to any query. The default and
  hard maximum for `--max-related-per-query` are both 3.
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

## Exact-content duplicate guard

Assemblies are hashed from uppercase nucleotide sequences after ignoring record
headers and contig order. Exact nucleotide-content duplicates are represented
once. Every excluded duplicate points to the retained candidate. This guard does
not collapse merely high-ANI genomes; similarity/ANI adjudication remains a
separate analysis and provenance decision.

## Receipts before computation

The new output directory contains:

| Artifact | Purpose |
|---|---|
| `panel_candidates.tsv` | Every candidate, selection/exclusion reason, source/member and hashes |
| `panel_selected.tsv` | Exact staged panel and all explicit comparator bases |
| `label_crosswalk.tsv` | Five-column, headered human receipt: ID, tree-safe label, display label, role, taxonomy |
| `labels.tsv` | GToTree 1.8.16 `-m` map: exactly two columns, no header |
| `panel_receipt.json` | Size option/default/max, counts, duplicates, claim ceiling, input hash |
| `genomes/*.fna` | Normalized staged assemblies |
| `genomes.txt` | Absolute paths for a later GToTree command |

Human review of the selected panel and label crosswalk is required before any
GToTree invocation. One CPU per concurrently running tree and no more than four
simultaneous trees is a run-orchestration choice outside this selector.

Use only the generated, headerless two-column file for GToTree label replacement:

```bash
GToTree ... -m staged_panel/labels.tsv ...
```

Column 1 is the staged FASTA filename (for example `Streptomyces_sp_AS-XXX.fna`)
and column 2 is its unique machine-safe replacement label. Do **not** pass
`label_crosswalk.tsv` to `GToTree -m`; that five-column headered table exists for
human review and provenance only.

## Claim ceiling

Panel membership is comparator selection only. It does not establish taxonomic
identity, nearest-neighbour status, strain independence, novelty, biosynthetic
production, or biological activity. A core-gene tree strengthens topology; ANI
and provenance adjudication remain separate. Exact-content duplicates are an
identity warning, not proof of the physical source of a mix-up or contamination.
