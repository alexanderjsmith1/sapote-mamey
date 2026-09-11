# Sapote–Mamey — What It Actually Does, and Where It's Going

*· 2026-07-02 · a development-stage roadmap, written honestly after the mycotrienin miss.*

## The correction that prompted this

Sapote–Mamey missed mycotrienin — a compound named in plain text on the antiSMASH front page (Region 63.1, "mycotrienin I"). It also only "confirmed" selvamicin after the front page was pointed out. The elaborate scanner machinery was consulted first; the cheapest, highest-signal information (the named KnownClusterBlast hits) was read last, if at all. That is the wrong order, and it's the thing this roadmap fixes first.

**Principle going forward:** read the front page first. Named KCB hits are leads to check, not verdicts to trust — but they are the starting point, not an afterthought.

## What the pipeline is (honest, current state)

Sapote–Mamey turns antiSMASH output into interpreted, capacity-level BGC assessments for a strain collection. It is in active development (engine 1.9.104, bundle v9.7.172). The real components:

**Layer 0 — Read what's already there (the fix, new).**
`kcb_frontpage` reads the "Most similar known cluster" column for every region, preserving antiSMASH's own ranking, and adds a corroboration tier from BOTH similarity% and matching-gene count. This is what stops front-page misses. It distinguishes:
- STRONG: high similarity AND many genes (mycotrienin 50%/26; selvamicin 100%/29) — real cluster relationships.
- COINCIDENTAL: high similarity but 1–2 genes (geosmin 100%/1) — single-protein flukes, correctly demoted.
- LARGE_GENERIC: many genes at tiny similarity — a big region sharing generic genes with many MIBiG entries.

**Layer 1 — Deterministic extraction (Mamey).** The engine: parse regions, compute the corrected BGC count (Interior + ½·Edge + ¼·Full-contig), assembly tiers, boundary/edge handling, the master workbook. This is the stable core.

**Layer 2 — Scanners (capability detection).** Domain co-occurrence gates that answer "what biosynthetic capability is here?" — for EVERY region, including the ones with no KCB hit (the actual unknowns, where this earns its keep). Scanners also corroborate KCB: they read the domain-level evidence that tells a real cluster match from a coincidental one. v0.4 registry, 29 scanners. Cardinal rule: gate on the DISCRIMINATING domain.

**Layer 3 — Analysis modes (new this cycle).**
- `bgc_walk` — ordered HMM readout along a cluster (validated on ionostatin's 7 modules).
- `rare_motif_scan` — flag interesting BGCs by rare / high-value motifs (surfaced AS-XXX's phosphonate, azole-RiPP, lasso).
- Cross-strain: BGC similarity networks, capability matrices, ANI.

**Layer 4 — Judgment & reporting (Sapote).** The §1–§30 Mode B cards, KCB sweeps, synopsis/chapter compilation, in Claude's document voice.

**The Wheelhouse.** Lab-specific DATA store (strains, scanners, validations, HMMs, engine) that travels with the bundle. Round-trippable.

## What each part is honestly FOR

| Layer | Answers | Trust level |
|---|---|---|
| KCB front page | "Is this a known compound?" | Lead — check with scanners |
| Scanners | "What capability class?" (all regions) | Capacity, not proof |
| bgc_walk | "What's in this cluster, in order?" | Descriptive |
| rare_motif | "Which clusters are worth looking at first?" | Prioritization |
| Mode B cards | "Full written assessment" | Interpreted, human-checked |

## The order operations SHOULD run (the roadmap)

1. **KCB front page** — every strain, ranked, corroboration-tiered. The 30-second answer a postdoc gets. FIRST.
2. **Scanners on every region** — capability profile, and corroboration for the KCB hits (real cluster vs coincidence).
3. **Rare-motif scan** — surface the interesting unknowns (no KCB hit + unusual domains).
4. **bgc_walk** on the priority regions — read the architecture.
5. **Cross-strain** — networks, capability matrix, ANI: shared vs strain-unique chemistry.
6. **Mode B compilation** — full cards for the priority BGCs.

Steps 1–2 are cheap and should be automatic for every strain. 3–6 are where human direction picks targets.

## Honest development status

**Solid:** deterministic extraction, BGC counting, workbook, the two-bundle offline install, ANI (pyskani/pyfastani validated to 0.15%), the pyHMMER engine, the KCB front-page reader (new, fixes the miss).

**Working but partial:** scanner registry (validated on AS-XXX 4/4, selvamicin, now the ansamycin gate; but LP01 lipopeptide is SPECIFIED_PARTIAL; scanners are actinomycete-trained and don't transfer to Gram-negatives). Domain-name proxy vs real HMM — engine proven, not yet the default path.

**Known gaps / not built:** front-page reader needs wiring as step 1 of the standard run (built as a module, not yet the default entry point). Scanner corroboration of KCB hits (using domain overlap to grade a KCB match) is designed but not automated. Fragmented assemblies hide large clusters — handled upstream by RG-GMCI, not inside the pipeline.

**The honest bottom line:** the pipeline's deep machinery is real and useful, but it was over-weighted toward sophisticated capability inference while under-weighting the cheap, obvious, high-value read of what antiSMASH already tells you. The correction is not more machinery — it's putting the front-page read first and letting the scanners do what they're uniquely good at: assessing the unknowns and grading the leads. This is a development-stage tool that assists the analysis; it does not replace the person reading the results, and the mycotrienin miss is the reminder of why.

## Standing rules (unchanged)
Capacity language ("machinery consistent with," never "produces"); KCB = similarity not identity, and a hit is a lead not a verdict; corrected BGC count; typed optional bioactivity metadata with no per-BGC attribution; scanners gate on the discriminating domain; no fabrication; affiliation.

## Mode B authoring order — now enforced in the template (v9.7.180)

The KCB front-page read and the independent BLASTp channel are no longer optional steps a
session might forget — they are wired into the emitted §1–§30 template itself:

- **§8 requires the KCB corroboration tier.** The template will not let a KCB anchor be stated
  without its gene coverage; `mamey kcb-frontpage` supplies the tier (STRONG / COINCIDENTAL /
  LARGE_GENERIC). This structurally prevents the BGC006/colibrimycin failure (a high score with
  few shared genes read as identity).
- **§4 requires the independent homology channel.** The template instructs the author to run
  `mamey blastp-online --package <gbk> --bgc <ID>` before writing §4, and to author from the
  reconciled call (CONFIRM / REFINE / OVERTURN) rather than the raw antiSMASH Pfam. If the
  channel is unavailable it must be banded as unverified — never fabricated.
- **§4 routes every OVERTURN to the HMM tie-breaker.** When BLASTp disagrees with antiSMASH,
  `mamey hmm-adjudicate <region.gbk> --locus <lt>` settles it on the domain signature
  (SUPPORTS_BLASTP / SUPPORTS_ANTISMASH / AMBIGUOUS / INSUFFICIENT) — the offline, deterministic
  channel that breaks a BLASTp/antiSMASH tie (worked example: `docs/ONLINE_BLASTP_PROTOCOL.md`,
  a different strain — do not cite its loci elsewhere). This makes
  the three channels — antiSMASH Pfam, BLASTp, HMM — mutually reconciled, not just listed.

Channel division of labour: **HMM = what the machine IS** (intrinsic domain grammar, module
count, short/orphan-gene rescue — offline, deterministic); **BLASTp = whose machine it is most
like + whether the product is known** (extrinsic identity, organism coherence, product novelty —
online, contextual). A lead card reconciles all three.

Canonical run order for a lead BGC: **kcb-frontpage (name the lead) → scanners on every region
(capability + corroboration) → blastp-online on the lead's genes (independent homology) → author
§1–§30 from the reconciled evidence.** The template emitter seeds §4/§8 so this order is the
path of least resistance, not a rule to remember.

## v9.7.338 — new deliverables + fixes (2026-07-28)

This cut is **doc- and deliverable-forward, no engine/version bump**: a family of **post-seal,
non-scoring / advisory** surfaces that read already-sealed package outputs and never move AB/AF/novelty
priors or the lead tier. Each is a class-level capacity read — judgment deferred, similarity not identity,
no structure/product/activity claim.

- **Good Guesses** (`good-guesses`) — the single best claim-safe interpretive read per notable BGC
  (capacity hypothesis + confidence + evidence basis + resolving experiment + earned "flavours") →
  `GOOD_GUESSES.md/.csv/.docx/.pdf`. A reference-dark guess is a *novelty prior, not proof of a new compound*.
- **Mode-B export** (`modeb-export`) — an authored §1–§30 card (or a `mode_b/` dir) → Word `.docx` + `.pdf`,
  real tables, per-page claim-safety footer; the card's own claim language is preserved verbatim.
- **KCB comparative locus map** (`figures kcb-locusmap`) — offline clinker-style map (query over top-N
  MIBiG refs, homology ribbons shaded by %identity) → png/svg/csv, from the in-package KnownClusterBlast txt.
- **Antifungal Lead Dossier** (`af-dossier`) — each sealed package's AF lead board joined to *measured*
  Candida activity; capacity (class-level) and measured activity (strain-level) stay in separate columns.
- **Cohort priority-leads ledger** (`cohort-leads`) + **cross-cohort assembler** (`cohort-assemble`) —
  union sealed triage boards into one ranked `COHORT_PRIORITY_LEADS.csv`, and assemble sealed packages into
  the figure-ready `COHORT_MASTER.csv`; both carry a MIXED-ENGINE comparability caution when strains span
  engine versions.
- **Comparator-coverage evidence** (`comparator-coverage`) — two-denominator MIBiG comparator coverage
  (locus vs defining-core) flagging low-specificity accessory-only collisions — the dominant AF
  false-positive killer, surfaced as evidence, not (yet) wired to scoring.
- **domain-reference / realistic-count / novelty-shortlist** — the Mode-B domain functional-context
  dictionary; the corrected-denominator ("honest") BGC count (marginal-drop + HIGH RG-GMCI merge); and a
  composite multi-signal novelty shortlist (KCB-dark + low recognizability + RG-GMCI + cohort-unique domain).
- **Sign-off QC gate** (`signoff`) — the objective "would a master's student sign off?" checks on
  phylogenetic trees (outgroup / contaminant / label-cruft / support / thin-tree); advisory, exit 0.
- **`verify-modeb --interp`** — adds the Mode-B *interpretation* gate (judgment substance; advisory WARN,
  non-blocking) alongside the existing structure/depth verify, so a card can be structurally green yet still
  flag missing judgment.
