# Three small patches against the GToTree v2 rewrite

Patch file: `gtotree2-input-sanity-and-env-compat.patch` (5 files, ~250 lines, against the
`GToTree-toying-with-whole-rewrite` tree dated 2026-08-26).

Context for where these came from: we run 138-marker Actinobacteria trees for a set of
bee- and ant-associated actinomycete genomes. We spent a day on v1.8.19 and hit three
environment problems and two bad input files, then installed v2 to compare. v2 handled
almost all of it better than 1.8.19 did — these are the three places where it still bit us,
or where we think it could stop someone else being bitten.

Everything below was reproduced on this machine. The suite is green with the patch applied:
**1294 passed, 1 skipped**.

---

## 1. `NCBI_ASSEMBLY_DATA_DIR` exits 0 on a fatal error

`check_ncbi_assembly_info_location_var_is_set()` in
`gtotree/utils/ncbi/get_ncbi_assembly_data.py` prints "does not seem to be set :(" and then
calls `sys.exit(0)`. Its sibling `check_gtdb_location_var_is_set()`, doing the same job for
GTDB_DIR, exits 1. Anything wrapping GToTree in a script or a CI step reads the 0 as a
successful run.

Changed to `sys.exit(1)`. That's the whole fix — it's almost certainly just a typo.

## 2. No fallback for the v1.x names of the renamed data-location variables

v2 renamed `NCBI_assembly_data_dir` → `NCBI_ASSEMBLY_DATA_DIR` and `GTDB_dir` → `GTDB_DIR`.
Nothing in the v2 source mentions the old spellings, so someone upgrading from 1.8.x — with
the correct directories already exported, under the old names, probably from a shell profile
they set up long ago — gets told the variable "does not seem to be set", for a variable that
in substance *is* set. Nothing in the message connects it to the rename. This is what
happened to us, and it took a while to work out.

The patch adds `LEGACY_ENV_VARIABLES` and a `resolve_env_variable()` helper in
`data_locations.py`: prefer the new name, fall back to the old one, and say once that it did
so and which name to switch to. The three places that read `os.environ` directly
(`get_gtdb_data.py`, `get_ncbi_assembly_data.py`, `handle_ncbi_tax_info.py`) go through it
too, so the compatibility isn't only in `gtt data locations check`. When neither name is set,
the error now names the old spelling as well.

Verified: with only `NCBI_assembly_data_dir` and `GTDB_dir` exported, `gtt data locations
check` resolves all five variables instead of exiting on the first.

Entirely reasonable to reject this one if you'd rather people just update their profiles —
in that case #1 and #3 stand alone, and the diff separates cleanly.

## 3. Nothing looks inside the input FASTAs before the run starts

`check_input_genome_files()` validates the input *list* thoroughly — whitespace, line
endings, duplicates, existence — on the principle stated in its own docstring: fail before
any asset is downloaded or any taxon resolved. But nothing opens the FASTAs themselves.

Two files in our reference pool turned out to be single gene records that had been saved
under species names. One of them, at 37,469 bp, has genes called and is searched against all
138 profiles before being dropped at the hit-count filter. On our 4-genome reproduction that
was 67 seconds to learn something the first line of the file establishes; on a real run it
scales with the marker set and the genome count. (v1.8.19 handled the same file much worse —
it killed prodigal and took the whole run down with it. v2 degrades gracefully, it just
degrades late.)

The patch adds `check_input_fasta_sanity()` next to the existing checks. It reads each input
until it has seen 500 kb and then stops, so it costs microseconds on a real genome and only
reads a small file in full.

Two severities, and the second one matters:

- **not FASTA at all** (no `>` on the first line) → exit, since nothing downstream can use it;
- **smaller than a typical bacterial/archaeal genome** → **warn only, and continue.**

The warning-only half is deliberate. Our first version exited on both, and it broke
`test_nucleotide_input_has_genes_called_and_targets_found` and
`test_nucleotide_mode_yields_nucleotide_hits_and_drops_both_files` — the `nt-mock-*.fna`
fixtures are ~20 kb. That was the tests correctly catching a bad idea rather than a fixture
problem: viral genomes are routinely 5–200 kb, GToTree supports them, and a hard floor would
reject a legitimate workflow outright. So it warns, names each file with its length and
sequence count, and says that this is expected for viruses. Both tests pass unchanged.

Output on our case:

```
  *********************************** NOTICE ***********************************
These inputs are smaller than a typical bacterial or archaeal genome. That is expected
for viruses, but for anything else it usually means a gene or amino-acid record was saved
under a genome's name -- and such a file will have its genes called and be searched against
every profile in the SCG set before being dropped at the hit-count filter. Flagging it here
so the run isn't spent finding out. If you meant to supply amino acids, `-A` is the flag for
that.

        - Streptomyces_citricolor.fna (37,469 bp in 1 sequence(s))
  ******************************************************************************
```

500 kb is a judgement call and easy to move — it's one named constant, `SMALL_GENOME_BP`.

---

## Two things that are not patches, just notes from the migration

**`-H` with a file path is exactly the escape hatch we needed, and it isn't obvious.** v2's
46 prepackaged sets are GTDB r232 derived, so there is no `Actinobacteria` set any more and
the nearest equivalent, `Actinomycetota`, is 92 genes. Our existing trees are all on the
1.8.x 138-gene Actinobacteria set, so switching sets would have made every new tree
incomparable with every old one. `find_local_hmm_file()` means `-H /path/to/Actinobacteria.hmm`
just works, and `check_gathering_cutoffs` confirmed all 138 profiles carry GA lines. A line in
the migration notes saying "point `-H` at your old HMM file to keep continuity with v1 trees"
would save the next person the source dive.

**Same input, same HMM, same tree.** 19 genomes, the 138-gene set, IQ-TREE `LG+F+G4 -B 1000
-alrt 1000` on both alignments:

| | v1.8.19 | v2.0.0 |
|---|---|---|
| genomes in / out | 19 / 19 | 19 / 19 |
| alignment columns | 31,422 | 30,649 |
| gap fraction | 14.8% | 12.9% |
| GToTree wall time | — | 2 min 53 s |

Robinson–Foulds distance between the two trees is **2**, against a maximum of 32 for 19 tips.
The single differing bipartition carries SH-aLRT 26 / UFBoot 55 in the v1 tree, so it's an
unsupported node either way rather than a real disagreement. v2's alignment is slightly
shorter and noticeably less gappy. We're moving to v2 on the strength of that.

Thanks for the rewrite — the resume state, the partitions files, and `-w` are all things we
had been doing by hand.
