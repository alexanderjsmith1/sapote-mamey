# Gemini offline analysis — drop-in guide for an off-network Claude

This bundle is self-contained for **two-strain comparative genomics with no network access**.
If you are a Claude instance that just received this bundle, this is your starting point.

## What Gemini does

Given two strains' whole-genome FASTAs + their antiSMASH result ZIPs, Gemini determines the
species/strain relationship (ANI), quantifies shared vs divergent biosynthetic capacity gene
by gene, recovers the ClusterBlast/SubClusterBlast/KnownClusterBlast comparator layers, and
uses the better assembly to scaffold the more fragmented one. Derived from and validated on
the AS-XXX × *Streptomyces* sp. Amel2xC10 analysis.

## Step 1 — install the stack offline (one command)

```bash
bash install_sapote_addons.sh
```

This installs pyrodigal (S1), pyfastani (S2), pyswrd (S4/S5 aligner), biopython, numpy from
the vendored wheels in `sapote_addons/wheels/` — no PyPI needed. It verifies every import at
the end. All wheels are checksum-listed in `sapote_addons/wheels/MANIFEST.txt`.

## Step 2 — provide the inputs

Gemini needs, per the module spec:
- `genome_A.fasta`, `genome_B.fasta` — whole-genome nucleotide assemblies (for S1/S2/S4).
- `antismash_A.zip`, `antismash_B.zip` — antiSMASH result sets (region GBKs +
  clusterblast/ subclusterblast/ knownclusterblast/ txt) — for S5/S6/S7.
- (optional) a 16S sequence for a fast species cross-check (S3).

If you only have the antiSMASH ZIPs (no genome FASTAs), stages S3/S5/S6/S7 still run; the
ANI/proteome stages (S1/S2/S4) need the assemblies.

## Step 3 — run the comparison

```bash
python3 -m mamey compare --strain-a <A.zip or pkg> --strain-b <B.zip or pkg> \
    [--genome-a A.fasta --genome-b B.fasta] --out gemini_out
```

Outputs: species-relationship report (ANI + 16S), per-BGC gene-level similarity table
(grouped by class then boundary Interior→Edge→Full-contig), comparator tables
(ClusterBlast organism / SubClusterBlast operon / KnownClusterBlast compound), and a
fragmentation/scaffold map.

## The standing rules you MUST carry (from the spec guardrails)

- **Similarity ≠ identity ≠ production.** Every %id/%sim value is sequence similarity; never
  claim a strain *produces* a compound from it.
- **Confirm divergence calls.** A sub-70% "absent/strain-specific" call is a CANDIDATE until
  confirmed by exhaustive alignment — the k-mer prefilter has a verified false-negative mode
  (BGC050 lanthipeptide dehydratase). Gemini flags these as `divergent_candidate`, never
  asserts absence.
- **Boundary honesty.** Low conservation on an Edge/Full-contig BGC may be truncation, not
  divergence — Gemini attaches a note; respect it.
- **Aligned fraction with ANI.** Never report ANI without its aligned fraction.
- **Validate the toolchain.** Reproduce at least one value against an external BLASTp result
  (done historically: BGC047 NRPS 96.0% to the decimal).

## Alignment backend

Runs on the **pyswrd** SIMD Smith–Waterman backend (proven). If a `diamond` binary is on
PATH, Gemini auto-upgrades to it (faster). DIAMOND is NOT vendored — see
`sapote_addons/DIAMOND_STATUS.md` for how to enable and verify it. The pyswrd backend is
sufficient and correct for a single strain pair.

## Relationship to Mamey/Sapote

Gemini is the two-strain comparative layer alongside Mamey (extraction) and Sapote
(judgment). It consumes sealed Mamey packages (or runs Mamey per strain first) and feeds the
per-BGC similarity + comparator evidence back into Mode B card sections §8b (cross-strain
conservation) and §8c (multi-source comparator). The comparator retention (organism names,
full MIBiG ranking, subcluster operons) is already inside Mamey as of v9.7.166.
