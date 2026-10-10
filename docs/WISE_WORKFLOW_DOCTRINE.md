# Wise Workflow Doctrine

## Implemented scope before applying the doctrine

This is a normative planning policy, not an automatically enforced end-to-end discovery pipeline.
The existing [queue handoff](NEXT_CHAT_HANDOFF_WISE_FRAGMENTED_PKS_WORKFLOW.md) states actual source limits;
[tools reference](user_guides/tools_reference.md) supplies current owner discovery. `wise-fragmented-pks`
consumes an already ranked FASTA and emits a queue; it does not submit, ingest results, perform all-family
grouping or search/re-rank assemblies automatically. Default active-files is two (`mamey/cli.py:8055–8064`);
a task selecting one active file can set `--active-files 1`. Follow-up parameters/owners are separate.

The shipped software's 100000 cap is a declared default, not a newly verified online service limit.
Single oversized records are retained with warnings and may be marked ready_to_run while under_100k=false
(`mamey/wise_fragmented_pks.py:83–109,:136–150`). Inspect actual counts/warnings before selecting any authorized
external route; ready state is not cap compliance. Query preparation remains UNBOUND, not result evidence.
Complete source identity and path/hash bindings govern every actual locus; synteny/domain agreement does
not itself establish production, exact compound, phenotype or physical contig joining.

<!-- Historical source text follows. -->

Sapote–Mamey should act like it has done this before.

For fragmented polyketide discovery:

- Rank first.
- Batch by residue count.
- Keep NCBI web batches under 100,000 residues.
- Start with one smart batch.
- Do not dump six batches unless asked.
- After results return, group by comparator/pathway family.
- Search assemblies for missing genes.
- Re-rank before the next batch.
- Use claim-safe language until synteny/domain evidence supports stronger claims.

This is not a fancy feature. It is the basic expected behavior for an AI-assisted BGC workflow.
