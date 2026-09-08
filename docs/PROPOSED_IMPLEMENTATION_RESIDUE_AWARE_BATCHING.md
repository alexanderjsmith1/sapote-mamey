# Proposed Implementation — Wise Fragmented PKS FASTA Batching

## Core idea

This is not complicated. The assistant should avoid obvious bad defaults.

- NCBI web BLASTP has a 100,000-residue cap.
- Large modular PKS proteins can be 3,000–9,000 aa each.
- Therefore 30 proteins can still be too large.
- The correct batching unit is total residues, not sequence count alone.
- The correct workflow is trial → result → re-rank → next batch.

## Core helper

```python
def split_ranked_fasta_by_residues(records, target_residues=85000, hard_cap=100000):
    batches = []
    current = []
    current_residues = 0

    for record in records:
        residues = len(record.sequence)

        if residues > hard_cap:
            record.warning = (
                "single sequence exceeds NCBI web BLASTP cap; "
                "use standalone BLAST, ElasticBLAST, or HMMER/domain tools"
            )
            batches.append([record])
            continue

        if current and current_residues + residues > target_residues:
            batches.append(current)
            current = []
            current_residues = 0

        current.append(record)
        current_residues += residues

    if current:
        batches.append(current)

    for batch in batches:
        total = sum(len(r.sequence) for r in batch)
        if total > hard_cap:
            raise ValueError(f"NCBI batch exceeds hard cap: {total}")

    return batches
```

## Better user-facing default

```python
def choose_default_fragmented_pks_plan(ranked_records):
    batches_85k = split_ranked_fasta_by_residues(ranked_records, target_residues=85000)
    batches_50k = split_ranked_fasta_by_residues(ranked_records, target_residues=50000)

    return {
        "recommended_first": batches_85k[0],
        "recommended_second": batches_85k[1] if len(batches_85k) > 1 else None,
        "extra_safe": batches_50k,
        "deferred": batches_85k[2:],
        "instruction": (
            "Run Batch A first. Upload results. Do not run all batches until "
            "we see comparator/pathway-family signal."
        ),
    }
```

## Required tests

```python
def test_ncbi_batch_never_exceeds_100k():
    batches = split_ranked_fasta_by_residues(example_large_pks_records, target_residues=85000)
    assert all(sum(len(r.sequence) for r in b) <= 100000 for b in batches)

def test_batch2_keeps_filling_past_top30():
    batches = split_ranked_fasta_by_residues(example_top30_plus_records, target_residues=85000)
    assert batches[0].rank_range == (1, 22)
    assert batches[1].rank_range[0] == 23
    assert batches[1].rank_range[1] > 30

def test_readme_tells_user_to_run_trial_first():
    readme = render_fragmented_pks_readme(plan)
    assert "Run Batch A first" in readme
    assert "Upload results" in readme
```
