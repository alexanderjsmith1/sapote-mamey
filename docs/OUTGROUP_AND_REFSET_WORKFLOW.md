# Outgroup generator + right-sized reference sets (outgroup_registry.py, phylo_refset.py)

Two companion tools to `phylo_place.py`. Together they turn "I have query 16S for cohort X" into an annotation-selected,
de-duplicated candidate reference set with explicit rooting review — no bulk downloads, no duplicate tips, no
ad-hoc outgroup.

## 1. outgroup_registry.py — the outgroup generator

Enter a genus, get the selected registry outgroup. It reads the already-curated
external project registry (the taxon→sister-outgroup table with real accessions) and adds a
**sequence layer** on top; it never edits the TSV. Select that governed registry explicitly with
`OUTGROUP_REGISTRY`; a path selection records provenance and does not itself grant scientific
acceptance. The shipped `mamey/data/outgroup_registry.tsv` is reference-only: lookup and sequence
extraction refuse it as project authority. Record the selected registry's source and SHA-256.
In the shipped snapshot, the rare-genera 16S row roots trees on *Bifidobacterium bifidum* KCTC 3202 (T),
accession NR_044771.1, an outgroup inside the phylum Actinomycetota, and the sequence is fetched by accession.
It replaced a *Pseudomonas* row, which drew one genus to the root.

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
  caches it at `OFFICIAL_DATA/outgroup_cache/16S/<Genus>_<species>.fasta`. Cache reuse requires verifying the current registry/accession binding; filename reuse alone does not prevent drift.
- **genome track** — returns the assembly accession and, with `--fetch`, writes a `datasets` fetch script.
  It does NOT download — downloading is a permissioned action; run the script yourself.
- **rule of two rows**: a GENUS tree roots on a sister genus (same family); a FAMILY tree roots outside the
  family. Pass `--scope family` for a backbone tree. The requested scope and selected row still require review; this does not establish sign-off by construction.

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

## Registry, cache, scope and output holds

`find_row` prefers an unambiguous LOCKED exact-scope row when available, but multiple unlocked candidates use file order with a warning. If no exact-scope row exists, it falls back to the first same-taxon row of **any** scope. A family request can therefore select a genus row; inspect and hold scope mismatch rather than assuming the rule-of-two-rows is enforced (`tools/outgroup_registry.py:102–146`). Registry provenance identifies the selected file, not biological outgroup suitability.

The 16S cache filename derives from outgroup genus/species/strain text, not registry SHA-256, database hash or ruled accession. A nonempty cached FASTA is checked for admissible header shape but not rebound to the current ruled accession. If a ruled accession is missing locally, extraction falls back to a name-based choice and checks genus, not exact accession/strain equivalence. Preserve that fallback as an authority hold until reviewed; do not describe it as the exact ruled sequence. Force/re-extraction writes the cache directly and may remove a rejected newly written cache file; optional `--out` copies over its destination (`253–312`). Keep authoritative sources disjoint from writable derived cache/output paths and externally bind sequence/cache hashes.

`cache-16s` returns 0 even when its missing list is nonempty. `list` displays registry rows without lookup's project-authority gate. Neither result admits all rows/sequences as approved current outgroups (`355–396`).

`phylo_refset` marker retrieval skips individual failed/empty `blastdbcmd` extractions and can write fewer records, even an empty marker-only set, with zero exit. A build can still contain just an appended outgroup. Check query/reference/extraction denominators before tree inference. Dedup reports and FASTAs overwrite directly; the report name uses literal `.replace('.fasta', '_DEDUP_REPORT.tsv')`, so an output without `.fasta` can collide with the FASTA and lose its report. Use distinct explicitly reviewed paths and retain output hashes. There is no integrated source/database/code/output hash receipt or fresh-destination guard (`tools/phylo_refset.py:223–232,236–281,304–337`). The proposed sequence collapse is display/reference reduction, not physical strain identity or taxonomy acceptance.
