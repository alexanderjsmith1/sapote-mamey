# Worked example — run the pipeline end to end on a public genome

**Engine:** Sapote-Mamey v9.7.363, engine 1.9.120
**Example genome:** *Streptomyces olivochromogenes*, NCBI RefSeq **GCF_001514115.1**

This is the bundle's reference walkthrough. It uses a **public** genome with **public** antiSMASH
results, so every number below is reproducible by anyone: download one file, run three commands, compare
your output to this page. Nothing here depends on unpublished data, and nothing is bundled.

> Every figure in this document came from an actual run of this bundle on this genome. If your numbers
> differ, something in your setup differs — that is the point of having a fixed reference.

---

## Why this example and not a project strain

The engine ships **no genomes and no reference datasets** (v9.7.362 removed them — see
`docs/EXTERNAL_DATA.md`). A worked example built on an unpublished in-house strain would be
unreproducible for a reader and would disclose unpublished results. A public RefSeq genome with
precomputed antiSMASH output has neither problem.

*S. olivochromogenes* is a good choice specifically: 43 BGC regions across 29 records, a healthy class
spread (PKS, NRPS, RiPP, terpene, siderophore), several high-similarity MIBiG anchors, and an assembly
that grades **GOOD** — enough structure to exercise the pipeline without being pathological.

---

## Step 0 — get the input (one download, no account)

Open the antiSMASH-DB entry:

```
https://antismash-db.secondarymetabolites.org/output/GCF_001514115.1/index.html
```

Click **Download → Download all results**, or fetch it directly:

```bash
curl -O https://antismash-db.secondarymetabolites.org/output/GCF_001514115.1/GCF_001514115.1.zip
```

That is the whole input. It is public, requires no login, and is ~21 MB zipped (~107 MB extracted:
43 region GenBanks, a whole-genome `.gbk`, a `.json`, the run log, and the HTML report).

**Do not commit it to the repo.** It is third-party data with its own provenance; `.gitignore` already
excludes downloaded datasets.

Other public genomes work identically — browse <https://antismash-db.secondarymetabolites.org/> and
substitute any accession. If a genome has no precomputed entry, run antiSMASH yourself and zip the
output directory; the engine reads either.

---

## Step 1 — the gold run

```bash
mamey run --mode gold \
  --strain GCF-001514115 \
  --display-name "Streptomyces olivochromogenes" \
  --input-zip GCF_001514115.1.zip \
  --outdir runs/ \
  --taxonomy "Streptomyces olivochromogenes" \
  --source "NCBI RefSeq GCF_001514115.1 (public)" \
  --source-provenance accession \
  --release PUBLIC \
  --brief none
```

`--source-provenance accession` matters: it records that the organism was read from a **deposited
record**, not inferred from a folder name. The engine tracks evidence strength for the source string so
a figure caption cannot inherit authority the datum lacks. The four values are
`accession | table | filename | asserted`, and `asserted` is the fail-safe default.

### Expected output

```
GBK Pfam extraction: 43 regions, 27 tier-1 diagnostic hits
parsed 43 BGCs from antiSMASH 8.dev-cf2fc5ee(changed)
RG-GMCI: 31 pairs | good-geometry 28 | complementary-split 3 / overlapping-paralog 7
Package: MAMEY_COMPLETE
  → runs/GCF-001514115/GCF-001514115_SapoteMamey_v9.7.363_engine1.9.120_Complete_Package.zip
```

**Reference figures:** 43 BGCs · 90 package files · assembly tier **GOOD** · ~5.2 MB sealed package.

The sealed `Complete_Package.zip` is the **unit of exchange** — hand that to a collaborator, not a
hand-picked subset of files.

---

## Step 2 — verify the package

```bash
mamey validate runs/GCF-001514115/package
mamey fingerprint runs/GCF-001514115/package
```

`validate` runs the gate battery and reconciles the workbook (expect `real_rows: 43`).
`fingerprint` emits the determinism hash over the score-bearing outputs — `_4A_RGGMCI_ranked_pairs.csv`,
`_4B_pks_ks_fragment_scan.csv`, `_4c_AB_lead_board.csv`, `_4c_AF_lead_board.csv`. **Two runs of the same
genome on the same engine must produce the same fingerprint**; if they do not, something is
non-deterministic and that is a bug worth reporting.

---

## Step 3 — read the results

```bash
mamey list-bgcs runs/GCF-001514115/package --top 5 --axis ab
```

### Reference triage split

| Tier | Count |
|---|---|
| High | 2 |
| Medium | 6 |
| Low | 25 |
| Inventory | 10 |
| **Total** | **43** |

### Reference top leads (AB axis)

| BGC | Contig | Products | Boundary | AB | AF | Tier |
|---|---|---|---|---|---|---|
| BGC014 | NZ_KQ948457.1 | HR-T2PKS; NRPS; NRPS-like | Interior | 74 | 36 | High |
| BGC034 | NZ_KQ948477.1 | RiPP; lanthipeptide-class-i | Interior | 70 | 20 | High |

**Read these correctly.** AB and AF are **routing priors** — they rank what is worth looking at first.
They are **not** activity predictions, and no per-BGC bioactivity claim follows from them. `Boundary:
Interior` means the region is not truncated by a contig edge, so its counts are not a lower bound.

---

## Step 4 — optional layers

Each needs a user-provisioned dataset (`docs/EXTERNAL_DATA.md`). Absent one, the corresponding section
renders **NOT MEASURED** — never an empty result that reads like a measured zero.

```bash
mamey report-card --package runs/GCF-001514115/package --bgc BGC014
python tools/evidence_bundle.py runs/GCF-001514115/package --strain GCF-001514115 --out evidence/
```

| Layer | Needs | Absent → |
|---|---|---|
| MIBiG anchors / comparators | `MAMEY_MIBIG_DIR` | NOT MEASURED |
| Literature enrichment (§5) | `MAMEY_LITERATURE_CORPUS` | NOT MEASURED |
| HMM domain scan | `MAMEY_HMM_DIR` | scan unavailable, reported |
| Dereplication | `MAMEY_NPATLAS_DIR` | optional layer skipped |

Check what you have:

```bash
mamey doctor
```

---

## What this example does *not* demonstrate

Stated plainly, so nobody infers coverage that is not here.

- **Cross-strain / cohort analysis.** One genome is not a cohort. GCF families, prevalence and the
  clinker within-family alignment all need several genomes clustered with BiG-SCAPE.
- **Phylogenomics.** A tree needs a panel — see `docs/GTOTREE_WORKFLOW.md`. Note the practical floor:
  a 3-tip tree **cannot pass `tree_sanity_check`**, because one outgroup against two close queries makes
  the outgroup branch ~89% of tree depth. Use **≥5 tips** with an outgroup chosen from
  `mamey/data/outgroup_registry.tsv`.
- **Bioactivity.** Nothing in the pipeline predicts activity. Bioactivity is extract-level laboratory
  data, entering as an evidence layer, never inferred from sequence.

---

## Claim ceiling for anything produced here

Class-level capacity hypotheses only. Comparators — KCB, BLASTp, BiG-SCAPE, MIBiG, KS-clade — are
**similarity anchors, never identity**. Capacity ≠ production: a cluster with the machinery for a
compound class is not thereby a producer of any compound. AB/AF are routing priors, not activity.
Missing evidence ≠ biological absence. `_4D` / RG-GMCI / KS-clade rows are candidates for adjudication,
never merges or nucleotide joins. Judgment deferred.

---

## Citing

Cite the datasets you actually provisioned, at the release you used — the bundle does not cite on your
behalf and cannot know which release you downloaded. For this example: NCBI RefSeq `GCF_001514115.1`,
and the antiSMASH-DB precomputed results (antiSMASH 8, version string recorded in your package
manifest).
