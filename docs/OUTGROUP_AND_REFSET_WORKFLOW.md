# Outgroup generator + right-sized reference sets (outgroup_registry.py, phylo_refset.py)

Two companion tools to `phylo_place.py`. Together they turn "I have query 16S for cohort X" into a clean,
de-duplicated, correctly-rooted reference set with one command — no bulk downloads, no duplicate tips, no
ad-hoc outgroup.

## 1. outgroup_registry.py — the outgroup generator

Enter a genus, get the *decided* outgroup. It reads the already-curated
`OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv` (the taxon→sister-outgroup table with real accessions) and adds a
**sequence layer** on top; it never edits the TSV.

```bash
Tools/bin/python3 Tools/outgroup_registry.py list                 # every registered taxon -> outgroup
Tools/bin/python3 Tools/outgroup_registry.py lookup Actinomadura  # the row (outgroup genus + species + acc)
Tools/bin/python3 Tools/outgroup_registry.py get-16s Streptomyces # cached 16S FASTA (extracts if missing)
Tools/bin/python3 Tools/outgroup_registry.py genome Nocardia --fetch   # GC[AF]_ acc + a fetch script (no download)
Tools/bin/python3 Tools/outgroup_registry.py cache-16s --all      # pre-populate the whole 16S cache
```

- **16S track** — extracts the outgroup species' 16S from the local `ncbi_16S_RefSeq` BLAST DB (offline) and
  caches it at `OFFICIAL_DATA/outgroup_cache/16S/<Genus>_<species>.fasta`. So the correct, *consistent*
  outgroup is one call away every time that genus shows up (the K. setae vs K. albolonga drift can't recur).
- **genome track** — returns the assembly accession and, with `--fetch`, writes a `datasets` fetch script.
  It does NOT download — downloading is a permissioned action; run the script yourself.
- **rule of two rows**: a GENUS tree roots on a sister genus (same family); a FAMILY tree roots outside the
  family. Pass `--scope family` for a backbone tree. This is what makes sign-off gate #1 pass by construction.

## 2. phylo_refset.py — right-sized + de-duplicated reference sets

Fixes two things the Developer or User flagged: (a) "we don't need 400+ genomes" → don't bulk-download, marker-BLAST a
query-relevant set; (b) "duplicate reference strains, 2 culture-collection IDs for the same strain" → dedup.

```bash
# one-shot: marker-blast (top-5 named RefSeq hits/query, union) -> dedup -> add registry outgroup
Tools/bin/python3 Tools/phylo_refset.py build \
    --query cohort_16S.fasta --group streptomyces --outgroup-genus Streptomyces \
    --out refs_final.fasta
# then hand refs_final.fasta to phylo_place:
Tools/bin/python3 Tools/phylo_place.py build-ref refs_final.fasta --group streptomyces --approved-by <name>
```

Sub-steps are also available standalone: `marker-blast`, `dedup`, `add-outgroup`.

### How dedup decides (two auditable tiers — every collapse is written to `*_DEDUP_REPORT.tsv`)
- **Tier 1 (metadata)** — same species + same strain token, two RefSeq accessions (e.g. *S. mashuensis*
  DSM 40221 = NR_026174 = NR_116638). Keep one.
- **Tier 2 (sequence)** — same species, 16S-indistinguishable (≥ `--identity`, default 99.5%). This is the
  same strain deposited under a different culture-collection ID (e.g. *sampsonii* ATCC 25495 vs NRRL B-12325),
  which a strain-token match alone can't catch, so it is decided by the sequence itself. Keep one representative.
- **Which one is kept**: a recognized type-strain collection is preferred (DSM > ATCC > NBRC > JCM > NRRL > …),
  then a present strain token, then the longer sequence, then the lower accession (deterministic).

Tier 2 needs the `blast` env (makeblastdb/blastn); if absent it is skipped with a warning and Tier 1 still runs.

## Wiring into phylo_place
`phylo_place.py build-ref` / `all` accept `--add-outgroup <GENUS>` to append the registry outgroup 16S directly,
if you didn't already build the refset with `phylo_refset.py`.

## Claim-safety (unchanged)
16S is an anchor, not a species call. A right-sized reference set gives "nearest among the chosen refs";
dedup removes redundant tips but does not change that. Judgment deferred; the Developer or User approves reference-tree CPU
and seals any cut.
