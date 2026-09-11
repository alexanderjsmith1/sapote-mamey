# TROUBLESHOOTING — EPA-ng placement + phylo tooling (Eggplant, 2026-09-06)

Hard-won gotchas from building the Actinomadura + rare-genus 16S EPA-ng trees. Each entry: symptom →
cause → fix/receipt. Read this before debugging a phylo run.

## Environment / EDirect
- **`efetch` fails: `error adding trust anchors ... ssl/cacert.pem` (curl 77).** The `blast` conda env's
  curl points at a cacert path that doesn't exist on this machine. → **Prefer local data over NCBI.**
  AS query 16S live locally in `AS_16S_authoritative.fasta` (285 seqs, headers `>AS-###`); reference 16S
  come from the local RefSeq DB via `blastdbcmd`. Only if a genuine fetch is unavoidable, set
  `SSL_CERT_FILE`/`CURL_CA_BUNDLE` to a real cert, or use `Tools/bin/python3` + urllib.
- **`efetch` inside a `while read` loop stops after ONE iteration.** `esearch/efetch` read the loop's
  stdin and consume the list. → add `</dev/null` to every efetch/esearch in a loop, or feed the loop on
  a separate FD.
- **`efetch -input <file>` fetched 0 sequences.** Not valid syntax for a bare accession list. → use
  `efetch -db nuccore -id "$(paste -sd, file)" -format fasta`, or `epost -input file | efetch`.

## Metadata retrieval (isolation source / host)
- **16S RefSeq (`NR_######`) records carry NO `/isolation_source`, `/host`, `/country`.** They are curated
  rRNA records. Verified on *A. atramentaria*. → don't expect origin from the 16S record.
- **BioSample is empty for CLASSICAL type strains** (citrea, soli, atramentaria predate BioSample). →
  isolation source for old type strains comes from the **species description paper** (via search) + BacDive,
  NOT NCBI. Recent species (e.g. *A. monticuli*, termite-gut *A. rubteroloni*) DO carry BioSample metadata.
- **Never invent an isolation source.** Where no source is found (e.g. *A. livida*), mark **`unresolved`**.
  Actinomadura is mostly soil but a few are plant/lichen/insect — do not assume soil.

## phylo_place / build-ref
- **`--group <Genus>` exits `--group must be one of [...] (source-separation rule)`.** The sealed engine
  only allowed the named cohorts. → EGGPLANT_411 patch A accepts a single capitalized genus as a per-genus
  cohort (requires `--add-outgroup`).
- **`BACKBONE_OUTGROUP_UNRESOLVED: --add-outgroup 'Actinomadura' matched 24 tips`.** The rooting searched
  tip names for the INGROUP genus (used to *look up* the outgroup), matching all ingroup tips. → patch A
  fix roots on the APPENDED outgroup's record IDs, not the ingroup string.
- **`BACKBONE_ROOTING_UNAVAILABLE: No module named 'Bio'`.** The `placement` conda env python lacks
  Biopython. → **drive phylo_place with `Tools/bin/python3`** (has Bio 1.87 + matplotlib); keep
  `PLACEMENT_BIN=miniconda3/envs/placement/bin` for the binaries. The per-genus chain driver `PY=` is
  wrong for this reason (open fix F).
- **`tree_sanity_check` FAIL `DOMINATING_BRANCH … 69%`.** The staged reference carried distant
  *Streptomyces* "sentinel" seqs; on a genus with a real outgroup they dominate. → EGGPLANT_411 patch E
  auto-strips foreign-genus records on a per-genus + `--add-outgroup` backbone.
- **`--group` is validated in `cmd_build_ref` only; `cmd_all` chains through it** — one gate covers all.

## Gates
- **`phylo_postflight` P3 FAIL "no SH-aLRT/UFBoot — bootstrap did not finish" on a placement tree.** P3
  assumed an IQ-TREE genome tree. An EPA-ng graft has no tree-wide support by construction. → EGGPLANT_411
  patch D makes P3 placement-aware (reads per-query LWR + backbone Felsenstein bootstrap instead).
- **`tree_sanity_check` is outgroup-aware only if you name the outgroup** — pass `--outgroup <substr>`
  (e.g. `Actinocorallia`); a lowercase `outgroup_for_...` tip is not auto-recognized (it looks for uppercase
  `OUTGROUP`).

## placement_figure / ggtree
- **Ref labels render at giant/inconsistent font.** The post-draw styler only set fontsize on texts it
  could match back to a tip; a label COLLISION left the other text at matplotlib's default (huge). →
  patch B sets every `ax.text` to 8pt first, then styles.
- **Query tips read "AS-### (host)".** `_host_of()` regexes a host out of the tip name and falls back to
  the literal "host". → patch B loads host + 16S accession from the paper strain table (`host_raw`, NOT
  `host_common`, which had AS-XXX wrong).
- **Reference genus repeated on every tip.** A genus-scoped tree doesn't need "Actinomadura" ×N; the
  modal-genus detector also misread the leading `NR` accession as the genus. → patch B strips the leading
  accession before detecting genus, then abbreviates it (`A. citrea DSM 43461 (NR042116.1)`).
- **Pruning is all-or-nothing (~1 ref/query → 9 tips, or all 75).** The neighborhoods-file string match
  silently kept too few, and an expanded neighborhoods file did NOT add refs. → patch B adds
  `--neighbors-per-query N` (patristic, format-independent) = the prune ladder.
- **ggtree renderer is orphaned in the bundle** — `ggtree_placement.R` ships but its producer
  that earlier producer script was never packaged. → patch C ships `tools/build_placement_ggtree_inputs.py`.
- **Figure has no methods.** → patch C adds a `GG_METHODS` env var → wrapped caption below the tree.
- **`origin`/legend wording + palette.** Legend must read **"Isolation source"** (not "origin"); the
  **outgroup is not an isolation source** (no dot); soil and soil/rock must be sibling shades;
  "engineered/other" → "other"; insect-associated must NOT be red (clashes with the red query).

## Parsing
- **Genus regex `\s*sp\.?.*` ate genus names containing "sp"** (Actinomycetospora → "Actinomyceto",
  Saccharopolyspora → "Saccharopoly", Streptosporangium → "Strepto"). → anchor it: `\s*sp\.?\s*$`
  (strip a trailing " sp." only).

## Paths
- **Spaces in paths break BLAST/GToTree HMM handling.** Work in space-free dirs; use absolute paths.

## _is_query culture-code collision (F4, live) — found 2026-09-06
- **Symptom:** a phantom query tip "AS-4 ()" (no host/accession) appeared on the Saccharopolyspora tree.
- **Cause:** `_is_query` used `re.search(r"(^|[_-])(AS|SID)[_-]?\d", name)`, which matched the culture-
  collection code **"AS 4.xxxx"** (CGMCC/AS codes, e.g. `S. gregorii ... AS 4.1382`) carried by a
  REFERENCE type strain — misclassifying a reference as a query.
- **Fix:** anchor the id to the START of the tip: `re.match(r"^(AS|SID)[-_]?\d", name)`. Real query tips
  are bare `AS-###`/`SID####`; references start with the `NR_` accession, so `^AS` never matches them.
  Applied in both `build_placement_ggtree_inputs.py` and `placement_figure.py` (`_is_query`).
- **Scope note:** genus-dependent — only bites genera whose type strains carry `AS 4.*` culture codes
  (Saccharopolyspora, some Streptomyces). Actinomadura was unaffected. Always eyeball the query count
  vs the strain table.

## Thin-genus placement (n<12) — Peterkaempfera
- A 1-query genus with few RefSeq refs (Peterkaempfera: 10 refs → ~5 tips) FAILs `tree_sanity_check`
  with a DOMINATING_BRANCH because the ingroup is tight and the (correct, registry) outgroup branch is
  ~81% of depth. This is a **thin-tree artifact, not a data defect**. → report such singletons as a
  neighborhood TEXT result (nearest named type strain from the strain table), not a tree.
