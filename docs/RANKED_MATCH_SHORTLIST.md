# Saved top-3 and top-5 reference matches

The adapter presents saved KnownClusterBlast ranks within one exact `strain / full contig / region / BGC alias`, run and evidence channel. It does not run a reference search, introduce a scoring rule, select a replacement comparator or draw locus maps.

## Existing owners

The external audit script `inventory_audit.py::parse_kcb` (not shipped) extracts the saved KCB rank, reference identifier/name, cumulative BLAST score, distinct AS query count, distinct reference subject count and median identity after keeping each query's highest-bitscore row. Its ranking TSV is a saved-channel summary, not a new exhaustive MIBiG search.

The bundle's `tools/multi_reference_comparison.py::rank_references` owns a separate DIAMOND comparison policy: discovery-threshold filtering, one-to-one pair selection, then distinct matched genes and summed bitscore ordering. Its builder also applies reference/span/annotation filtering and compound grouping. This candidate does not call or transplant that policy onto KCB rows.

The retained selection-policy audit documents original choices, including maximum-query-count/first-tie policy consistency, explicit paired comparators and assembly/package holds. Those are copied as source-labeled snapshots, not converted into a new recommended order. A policy-consistent choice is not automatically biologically optimal.

## Command

```sh
python3 tools/ranked_match_shortlist.py --config /path/to/config.json \
  --json-out /path/to/candidate.json --html-out /path/to/candidate.html
```

Python 3.9+ standard library only. No browser, network, search, renderer or source write. The JSON and optional HTML are derived outputs. They cannot overwrite selected source inputs or be symlinks. Existing changed candidates require `--replace-candidate`; identical replay is allowed. Individual replacements are atomic; a two-file pair can be partial after interruption. Exit 0 means the requested preview was produced, not reference adoption or freedom from review holds.

## Input contract

```json
{
  "schema": "sapote.ranked_match_shortlist.v1",
  "evidence_channel": "SAVED_KNOWNCLUSTERBLAST",
  "rankings": {"path": "/path/to/REFERENCE_RANKINGS.tsv", "sha256": "<actual SHA-256>"},
  "owner": {"path": "/path/to/inventory_audit.py", "sha256": "<actual SHA-256>", "excerpt": "<exact source-scope excerpt>"},
  "run_metadata": {"path": "/path/to/RUN_AUDIT.tsv", "sha256": "<actual SHA-256>"},
  "selection_policy": {"path": "/path/to/SELECTION_POLICY_REVIEW.tsv", "sha256": "<actual SHA-256>"},
  "contexts": [{"identity": "<complete source identity>", "run": "<exact saved run path>"}]
}
```

Every supplied file is hash-pinned and read once for hashing/parsing. Source owner text must contain the pinned scope excerpt. This binds the reviewed producer and chosen data; it is not a general proof that arbitrary code produced an arbitrary TSV. The current CLI adapter admits only the saved-KCB channel. A row declaring a different channel fails. Other channel formats need their own reviewed adapters and must not be relabeled to fit this contract.

`selection_policy` is optional; absent policy remains null. Omit `contexts` to present all source groups. Selected contexts must exist exactly; an unknown context is an input error, not a no-hit. Headers must be unique and contain the source fields. Numeric blanks stay null. Invalid/negative/nonfinite fields, impossible identity percentages, zero/fractional ranks and fractional gene counts fail input validation.

## Presentation

Each context carries top3 and top5 windows in saved-rank order. A window takes the first N ranked source rows and retains every row sharing the boundary's saved rank, so it may contain more than N. Same AS-query counts are annotated independently; they do not expand the native-rank window or create a new rank tie. Source order is retained inside a saved-rank tie.

Original selected references are always shown separately, including selections outside top5. The exact run and channel are displayed. Repeated identifiers in different runs remain independent contexts. Intentional paired comparators are not merged. Distinct MIBiG records with related compound annotations are not collapsed by this adapter.

Duplicate reference rows within a context retain all source rows and hold the shortlist instead of silently deduplicating. Incomplete identity, missing run, invalid reference identity or disagreement between ranking/selection sources also holds the shortlist. Unranked rows remain visible separately. Missing run metadata or an original selection absent from the ranking remains an explicit review hold.

The source table provides matched-query and matched-reference counts, not complete gene denominators. Query/reference gene denominators and coverage rules therefore remain JSON null and HTML unavailable. Raw rescue totals, reference CDS inventories and DIAMOND one-to-one counts are not substituted across channels. Cumulative BLAST score is not a percentage. Reference names are annotations of the reference, not AS compound identities.

## Validation boundary

Source hashes and stored archived-member hashes bind the retained snapshots. They do not alone replay source sequences or thresholds.

Keep the existing figure/identity/scientific/adoption holds. Use the top3/5 table to review alternatives and original rationale before choosing any map rebuild; the adapter never adopts a reference.
