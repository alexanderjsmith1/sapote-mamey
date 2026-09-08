# PATCH — drop-in concepts & front-matter for the v1.1 guides
## Corrected for the two-layer architecture · engine 1.9.31 / bundle v9.7.23

> Replacement prose in the v1.1 guides' own voice — approachable, onboarding-first, written for
> a person at a keyboard rather than a reviewer. Drop these blocks in where the drift map points.
> Each block is labeled with the guide and section it replaces or augments.

---

## REPLACES — User Guide §1 "Introduction" (first half)

These workflows turn the output of an antiSMASH genome analysis into a ranked, claim-safe list of natural-product leads — identifying which biosynthetic gene clusters are most worth following up in the laboratory, and why. You supply the genome data; the pipeline supplies the analytical framework.

The pipeline has two halves, and understanding the split is the key to everything else. **Mamey** is the deterministic engine: it reads your antiSMASH output and extracts the facts — which clusters are present, what their domains and modules are, what they resemble in the known-compound databases, how complete each one is — and it does this identically every time, with every number traceable back to the antiSMASH field it came from. **Sapote** is the judgment layer: it reads what Mamey extracted and decides what is worth your attention, how strongly each lead may be described, and what experiment comes next. Mamey tells you what is *true of the data*; Sapote tells you what is *worth doing about it*. The two never blur — and a built-in audit checks that every cluster Mamey found is actually carried through to a verdict, so nothing is silently dropped.

**Claim-safety.** The pipeline uses careful, scientifically defensible language throughout. Predicting that a genome contains genes consistent with producing a class of compound is different from saying the organism produces that compound. Confirming production requires chemical evidence — fractionation, mass spectrometry, NMR, or genetics. The pipeline provides the genomic triage that tells you where to look. Three rules hold without exception: every class call is stated as *capacity* ("capacity consistent with a glycopeptide"), never as production; every known-cluster match is treated as *similarity*, never identity; and an absence of recorded bioactivity is never read as a negative.

---

## REPLACES — User Guide §6 "Workflow 3 — Mamey" (the opening description)

**Mamey is the deterministic engine underneath the whole pipeline.** It is not a prompt you paste and improvise with; it is a program that reads an antiSMASH package and produces a sealed, checksummed evidence package — the same output every time, fully traceable. When you run a strain, Mamey is what does the extraction: it inventories every cluster, classifies each by boundary (Interior, Edge, or Full-contig), runs the detection stack and the supporting scans, adjudicates any cross-contig fragments, and writes the results as a set of files with a manifest and a per-cell provenance record.

What Mamey produces is the *evidence package* — the intake record, the cluster inventory, the triage board, the cross-contig adjudication outputs, the workbook, the scan-state log, the provenance and checksum files, and the manifest that hands off to the judgment layer. What it deliberately does *not* do is interpret: it assigns no importance and makes no compound claim. That is Sapote's job, and keeping the two separate is what makes the package trustworthy — you can audit any call back to the data it came from.

> **Honest note on the current package.** The sealed Mamey package today contains everything the
> engine computed, but it ships without a reader-facing summary — no PDF, no figures, just the
> machine-readable files and the workbook. A readable one-page *strain brief*, rendered
> deterministically from what the package already contains, is the near-term addition that closes
> this gap; until it lands, the triage board and workbook are the way in.

---

## REPLACES / EXPANDS — Technical Manual §4 "First-Pass Scan Modules" (the framing)

The detection stack is best understood as **three complementary detectors, plus supporting scans, plus cross-contig adjudication.** The three detectors fail in different ways on purpose, so a cluster invisible to one is usually caught by another.

**KnownClusterBlast anchors** are the most specific signal where they exist — a near match to a characterized cluster, including the MIBiG deposits. Their limitation is coverage: many clusters have no close characterized relative. (A correctness fix in the current arc also resolved a case where the *displayed* anchor was the wrong line — for a cluster excised from a sequenced genome already in the database, the rank-1 hit is the genome's own self-match, which masked the real MIBiG cluster. Surfacing the MIBiG line lifted recovery on a 59-strain cohort from under 1% to 59% of clusters.)

**Keyword markers (the T43 family)** are precise, class-definitive flags for specific diagnostics — phosphonate, nucleoside, enediyne, β-lactam, lanthipeptide, indolocarbazole, and the rest. Their limitation is reach: only about 30% of characterized clusters fire any keyword marker, because annotation is fragile and the same enzyme is named differently or not at all across deposits.

**Architecture-based class capacity** is the layer that covers the marker-invisible majority, and it is the central addition of the current arc. Instead of keying on gene names, it classifies a cluster by its architecture — the antiSMASH backbone type, the deduplicated counts of PKS and NRPS modules read from the domain features, and the constellation of tailoring enzymes — a signal robust to the naming noise that defeats keyword matching. It returns a claim-safe capacity call with a HIGH, MODERATE, or LOW confidence grade, and where the architecture is ambiguous it abstains rather than guessing. Across a panel of characterized deposits, marker-or-architecture detection reached 95% against 83% for the KnownClusterBlast anchor — the gap the architecture layer fills.

Around these sit the **supporting scans** — fragmented-megasynthase rescue (FLBR), edge-flank linkage (EFLS), maturation-gap detection (UMED), chitin/glycan capacity (CGAD), cryptic-class triggers (CCTT), resistance-gene tiers, and the rare-codon and binding-site regulatory scans — each triggered by specific evidence and each contributing context the detectors cannot. And **RG-GMCI** adjudicates fragments split across scaffolds, integrating evidence of shared pathway membership without ever asserting a physical join: even at its highest grade it depicts a gap rather than inventing an adjacency.

---

## ADD — any guide front matter, the conventions block

A short conventions block to seat at the top of each guide, replacing the older one-line claim-safety note:

> **Conventions used throughout.** Class calls are stated at the level of biosynthetic *capacity*,
> never production. KnownClusterBlast hits are *similarity*, never identity. Bioactivity is handled
> at the *extract* level, and an absence of recorded activity is never read as a negative — strains
> are contrasted by biosynthetic mechanism, not phenotype. The assembly-corrected cluster count is
> Interior + ½·Edge + ¼·Full-contig. Every cluster is named with its node or contig. Unpublished
> strains never enter a public release, and any merged set containing them is private. The
> affiliation on every artifact is 

---

## ADD — Quick Guide, the "Which mode?" reframe

Replace the access-tier→Sapote-or-Mamey table's framing with a run-*mode* table that no longer
conflates "Mamey" with "free tier":

> **How do you want to run it?** All modes use the same engine (Mamey) and the same judgment rules
> (Sapote); they differ only in setup.
>
> - **Paste-and-go** — frontier model, no setup. Paste the workflow, upload the antiSMASH ZIP, run.
>   Best for deep single-strain analysis.
> - **Projects (persistent)** — paid Claude. One-time setup of the kernel and companions; each
>   strain runs in its own chat; supports batch plans and cross-strain comparison.
> - **Lightweight triage** — any 32K-context model. A reduced run that produces the triage board
>   and a claim-safe summary, with an upgrade trigger to a full analysis when a strain warrants it.
>
> Mamey (the deterministic engine) underlies all three; Sapote (the judgment layer) interprets
> what it produces.
