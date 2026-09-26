# Outgroup generator + right-sized reference sets (outgroup_registry.py, phylo_refset.py)

Two companion tools to `phylo_place.py`. Together they turn "I have query 16S for cohort X" into a clean,
de-duplicated, correctly-rooted reference set with one command — no bulk downloads, no duplicate tips, no
ad-hoc outgroup.

## 1. outgroup_registry.py — the outgroup generator

Enter a genus, get the *decided* outgroup. It reads the already-curated
external project registry (the taxon→sister-outgroup table with real accessions) and adds a
**sequence layer** on top; it never edits the TSV. Select that governed registry explicitly with
`OUTGROUP_REGISTRY`; a path selection records provenance and does not itself grant scientific
acceptance. The shipped `mamey/data/outgroup_registry.tsv` is reference-only: lookup and sequence
extraction refuse it as project authority. Record the selected registry's source and SHA-256.

Before the examples, activate the bundle Python environment, work from the bundle root and bind
these separately supplied resources to actual existing locations:

```bash
export OUTGROUP_REGISTRY="/absolute/path/to/governed/OUTGROUP_REGISTRY.tsv"
export NCBI_16S_DB="/absolute/path/to/ncbi_16S_RefSeq/16S_ribosomal_RNA"
export BLAST_BIN="/absolute/path/to/blast/bin"
export OUTGROUP_CACHE="/absolute/path/to/writable/outgroup_cache"
```

Replace the path placeholders before use. Check the selected registry before marker searches or
reference de-duplication so a later outgroup-authority refusal does not waste those steps.

```bash
python tools/outgroup_registry.py list                 # every registered taxon -> outgroup
python tools/outgroup_registry.py lookup Actinomadura  # the row (outgroup genus + species + acc)
python tools/outgroup_registry.py get-16s Streptomyces # cached 16S FASTA (extracts if missing)
python tools/outgroup_registry.py genome Nocardia --fetch   # GC[AF]_ acc + a fetch script (no download)
python tools/outgroup_registry.py cache-16s --all      # pre-populate the whole 16S cache
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
python tools/phylo_refset.py build \
    --query cohort_16S.fasta --group streptomyces --outgroup-genus Streptomyces \
    --out refs_final.fasta
# then hand refs_final.fasta to phylo_place:
python tools/phylo_place.py build-ref refs_final.fasta --group streptomyces --approved-by "<recorded-approval>"
```

Sub-steps are also available standalone: `marker-blast`, `dedup`, `add-outgroup`.

### How dedup decides (two auditable tiers — every collapse is written to `*_DEDUP_REPORT.tsv`)
- **Tier 1 (metadata)** — same species + same strain token, two RefSeq accessions (e.g. *S. mashuensis*
  DSM 40221 = NR_026174 = NR_116638). Keep one.
- **Tier 2 (sequence)** — group same-species reference records whose pairwise 16S matches meet
  `--identity` (default 99.5%) and at least 90% coverage of the shorter sequence. Keep one sequence
  representative per connected group. This removes redundant reference tips; it does not establish
  that different collection IDs denote the same physical strain. Record verified collection aliases
  separately. Transitive group members need not have a measured qualifying alignment to the retained tip.
- **Which one is kept**: a recognized culture-collection token is preferred
  (DSM > ATCC > NBRC > JCM > NRRL > …), then a present strain token, then the longer sequence,
  then the lower accession (deterministic). This ranking does not verify type material; use NCBI
  Assembly `from_type` evidence for a reader-facing `[Type]` label.

Tier 2 needs the `blast` env (makeblastdb/blastn); if absent it is skipped with a warning and Tier 1 still runs.

## Wiring into phylo_place
`phylo_place.py build-ref` / `all` accept `--add-outgroup <GENUS>` to append the registry outgroup 16S directly,
if you didn't already build the refset with `phylo_refset.py`.

## Claim-safety (unchanged)
16S is an anchor, not a species call. A right-sized reference set gives "nearest among the chosen refs";
dedup removes redundant tips but does not change that. Judgment deferred; the Developer or User approves reference-tree CPU
and seals any cut.
