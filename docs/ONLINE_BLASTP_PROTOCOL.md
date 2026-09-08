# ONLINE BLASTp PROTOCOL — Sapote–Mamey internal (Patch Chat)

**Status:** fallback channel for Mode B lead analysis (offline ingest is the default) · drafted from a verified live run
**Engine target:** Mamey ≥ v1.9.111 · bundle ≥ v9.7.319
**Owner layer:** Sapote (judgment) invokes; Mamey (engine) should host the runner
**Author:** Claude analysis session, 2026-07-02 · verified against AS-XXX / BGC006

---

## 1. Why this exists (the failure it fixes)

Mode B §4/§8 have been authored from two evidence channels only: antiSMASH's
pre-computed Pfam/sec_met domain calls, and Mamey's `KCB_top` field (a
KnownClusterBlast score). Both are inherited. Neither is an independent homology
check on the actual protein sequences, and relying on them produces two concrete
error classes we have now caught in the wild on **BGC006 (NODE_12 · region001), AS-XXX**:

1. **KCB score taken as identity.** The card anchored BGC006 to *colibrimycin*
   (KCB score 3734) as a class precedent. The KnownClusterBlast image shows
   colibrimycin sharing only a handful of genes with the query — a partial
   sub-module hit, not cluster identity. A high aggregate KCB score with low
   gene-level coverage is not a compound anchor. **Rule: never state a KCB anchor
   without stating its gene coverage.**

2. **antiSMASH Pfam calls trusted as function.** Live BLASTp overturned two of
   ten domain calls on the first pass:
   - `ctg12_71` — antiSMASH `Beta-lactamase` → BLASTp top hit **EstA serine
     hydrolase / esterase** (78% id). The "self-resistance β-lactamase" read was
     wrong.
   - `ctg12_21` — antiSMASH `Phenol_Hydrox` → BLASTp top hit **ferritin-family
     protein** (97% id).
   - `ctg12_74` — antiSMASH `Antibiotic_NAT` → BLASTp **AAC(3) aminoglycoside
     N-acetyltransferase** (77% id): not overturned, but *sharpened* into a named
     resistance enzyme with a real mechanism-of-action handle.

Online per-gene BLASTp is the independent third channel that catches both. It
also resolves **strain taxonomy**: on BGC006, all ten top hits were
*Amycolatopsis*, which independently placed AS-XXX in that genus (the card had
wrongly said taxonomy was "not supplied").

**This channel becomes the default for every Mode B lead BGC.** It is not
optional enrichment; §4, §8, §27, and §28 are authored *after* it returns.

---

## 2. Scope — when to run it

- **Always** for any BGC receiving a full Mode B card (Exceptional/High leads,
  and any BGC promoted to a card under Full Analysis Mode).
- **Every CDS in the locus** is eligible, run in batches (§4). Priority order when
  the locus is large and time-bounded: (1) catalytic core (KS/CLF/KR/ACP, C/A/T
  NRPS modules, RiPP precursor + cyclodehydratase), (2) tailoring enzymes,
  (3) transport + resistance, (4) regulators, (5) accessory/hypothetical.
- **Skip** only for Inventory-tier BGCs not being written up, and for pure-
  saccharide regions excluded by figure/claim policy.

---

## 3. The verified recipe (NCBI URL API)

NCBI's public BLAST URL API. No key required. Be a good citizen: `tool=` set,
one submission at a time, poll on a delay. This recipe is **tested end-to-end**.

### 3.0 Batch size — the hard rule
**≤ 10 proteins per submission.** Verified timing on AS-XXX/BGC006:

| Batch | Residues | Result |
|---|---|---|
| 61 proteins | 21,756 aa | still `WAITING` at 2.5 min+ (too big; abandoned) |
| 10 proteins | 2,943 aa | `READY` at ~2.5 min, clean parse |

Never submit more than 10. A large locus (BGC006 = 61 translatable CDS) is
**≈7 sequential batches**, prioritised per §2.

### 3.1 Large-protein handling
Any CDS **> 2500 aa** (e.g. the BGC006 NRPS `ctg12_48`, 3297 aa) dominates batch
runtime and risks SIGXFSZ on naive FASTA writes. Run giant proteins **solo or in
a 2–3 batch of their own**, never inside a 10-batch of small genes.

### 3.2 Extract proteins from the region GBK
```python
from Bio import SeqIO
recs = list(SeqIO.parse(region_gbk, "genbank"))
prot = {f.qualifiers["locus_tag"][0]: f.qualifiers["translation"][0]
        for rec in recs for f in rec.features
        if f.type == "CDS" and f.qualifiers.get("translation")}
```
Translation-less CDS (pseudogenes) are silently skipped — note the count
(BGC006: 61 of 63 CDS had translations).

### 3.3 Submit (CMD=Put) → RID
```python
import urllib.request, urllib.parse, re
params = {"CMD":"Put", "PROGRAM":"blastp", "DATABASE":"nr",
          "QUERY":fasta_text,          # ≤10 sequences, multi-FASTA
          "HITLIST_SIZE":"3", "EXPECT":"1e-5", "tool":"SapoteMamey"}
resp = urllib.request.urlopen(urllib.request.Request(
        "https://blast.ncbi.nlm.nih.gov/Blast.cgi",
        data=urllib.parse.urlencode(params).encode()), timeout=120).read().decode()
rid  = re.search(r"RID = (\S+)", resp).group(1)
```
- `DATABASE`: `nr` for maximal coverage (used here). `refseq_protein` is a faster,
  cleaner-annotation alternative when nr is slow. `swissprot` only for a quick
  curated sanity check — too sparse for actinomycete biosynthetic genes.
- `HITLIST_SIZE=3` is enough — we keep the top hit and one or two for context.
- `EXPECT=1e-5` filters junk; loosen to `1e-3` only for short (<80 aa) precursor
  peptides.

### 3.4 Poll (CMD=Get, SearchInfo) until READY
```python
p = urllib.parse.urlencode({"CMD":"Get","RID":rid,"FORMAT_OBJECT":"SearchInfo"})
status = re.search(r"Status=(\w+)", fetch(p))   # WAITING | READY | FAILED | UNKNOWN
```
- Poll interval **≥ 30 s** (60 s is politer). Do not hammer.
- Expect `READY` at **~2.5 min** for a 10-protein moderate batch; longer for
  large proteins or NCBI load.
- `FAILED` / `UNKNOWN` → resubmit once, then fall back (§6).
- RID lifetime is ~24 h; results can be re-fetched within that window.

### 3.5 Retrieve (CMD=Get, XML) and parse
```python
p = urllib.parse.urlencode({"CMD":"Get","RID":rid,"FORMAT_TYPE":"XML",
                            "ALIGNMENTS":"3","DESCRIPTIONS":"3"})
from Bio.Blast import NCBIXML
for rec in NCBIXML.parse(io.StringIO(xml)):     # one record PER query, in order
    a = rec.alignments[0]; h = a.hsps[0]
    pid = 100*h.identities/h.align_length
    cov = 100*(h.query_end-h.query_start+1)/rec.query_length
    org = re.search(r"\[([^\]]+)\]", a.hit_def)   # organism in the def line
```
Records come back **in submission order** — map them back to locus tags by index,
do not trust the query name round-trip.

---

## 4. Output schema (per gene)

One row per CDS, banked to `<pkg>/bgc_blastp_panel/<BGC>_online_blastp.csv`:

| field | source |
|---|---|
| `locus_tag` | GBK |
| `aa_length` | GBK |
| `antismash_domains` | sec_met_domains (the call being checked) |
| `blastp_top_def` | hit_def (trimmed at first `>`) |
| `blastp_accession` | hit accession |
| `blastp_organism` | `[...]` in hit_def |
| `pct_identity` | identities / align_length |
| `query_coverage` | (query_end − query_start + 1) / query_length |
| `evalue`, `bitscore` | HSP |
| `agreement` | `CONFIRM` / `REFINE` / `OVERTURN` vs antiSMASH call (author-set) |

The `agreement` column is the point of the whole exercise — it is what flags a
`ctg12_71`-style overturn.

---

## 5. How it enters the Mode B card

- **§4 gene-by-gene:** add a `BLASTp top hit (org, %id, cov)` column beside the
  domain column. Author prose from the *reconciled* call, not the raw Pfam.
- **§8 comparator/KCB:** state KCB anchor **with gene coverage**, then give the
  per-gene BLASTp verdict. If per-gene hits are all uncharacterised genus
  homologs (BGC006 case), say so — "conserved in genus, no characterised product
  match" is the honest and more valuable read than a weak MIBiG name.
- **§27 self-resistance:** resistance genes must be BLASTp-named (AAC(3), etc.),
  never left as the generic Pfam.
- **§28 provenance ledger:** each BLASTp-derived claim gets evidence type
  **`observed (BLASTp nr, RID <id>, <date>)`** — the RID is the reproducibility
  handle.
- **Strain taxonomy:** if the consensus top-hit organism is uniform across genes,
  record it as a genus inference (evidence type `inferred`, not `observed`) —
  cluster distribution ≠ host taxonomy with certainty, but a uniform per-gene
  consensus is strong.

### Claim-safety (unchanged, restated)
A BLASTp hit is **homology, not function or product identity**. "Capacity
consistent with," never "produces." A hit to a characterised protein is a
hypothesis to test, not an assignment. Coverage and %id are reported so the
reader can weight it; a 40%-id / 60%-cov hit is a lead, not a call.

---

## 6. Failure handling / fallback

- **NCBI slow or FAILED:** resubmit the batch once. If still failing, author the
  card from antiSMASH + KCB **with an explicit banner**: "online BLASTp channel
  unavailable this session — domain calls are antiSMASH Pfam, unverified."
- **No hit above threshold:** record `no hit @ 1e-5`; for a core gene this is
  itself signal (genuinely novel / fast-evolving) — flag, don't hide.
- **Network-restricted environment:** if `blast.ncbi.nlm.nih.gov` is not
  reachable, the channel is simply off; never fabricate hits.

---

## 7. Proposed engine surface (for the patch applicant)

Wrap this recipe as a first-class command so Sapote sessions stop hand-rolling it:

```
mamey blastp-online --package <pkg> --bgc <BGC_ID> \
      [--scope core|tailoring|resistance|all] [--batch-size 10] \
      [--database nr|refseq_protein] [--evalue 1e-5]
```
Behaviour:
1. Pull the CDS set for `<BGC_ID>` from the region GBK (respect priority order).
2. Chunk into ≤`batch-size` submissions; run giant (>2500 aa) proteins solo.
3. Submit → poll (≥30 s) → retrieve XML → parse.
4. Emit `<pkg>/bgc_blastp_panel/<BGC>_online_blastp.csv` (§4 schema) and set the
   `agreement` column heuristically (CONFIRM when Pfam keyword ∈ hit_def).
5. Persist the RID + date so `§28` provenance is reproducible.
6. Fail-closed and offline-safe per §6.

This slots beside the existing `bgc_blastp_panel/` scaffolding (the pipeline
already ships `*_NCBI_safe_round00N_for_BLASTP.faa` batch files — this protocol is
the missing *runner + interpreter* for them). It supersedes taking `KCB_top` at
face value.

---

## 8. Verified worked example — AS-XXX / BGC006 core-10 (RID 4E4J591J016)

| gene | antiSMASH call | BLASTp top hit | organism | %id | cov | verdict |
|---|---|---|---|---:|---:|---|
| ctg12_38 | PKS_KS | β-ketoacyl-ACP synthase | *Amycolatopsis* | 95 | 100 | CONFIRM |
| ctg12_39 | ketoacyl-synt | β-ketoacyl synthase N-term (CLF) | *Amycolatopsis* sp. NPDC114503 | 88 | 100 | CONFIRM |
| ctg12_40 | PKS_KR | 3-oxoacyl-ACP reductase | *Amycolatopsis* | 92 | 100 | CONFIRM |
| ctg12_46 | MbtH | MbtH family protein | *Amycolatopsis* | 82 | 99 | CONFIRM |
| ctg12_21 | Phenol_Hydrox | **ferritin-family protein** | *Amycolatopsis* sp. NPDC004378 | 97 | 100 | **OVERTURN** |
| ctg12_22 | Rieske | Rieske 2Fe-2S protein | *Amycolatopsis* sp. SID8362 | 97 | 100 | CONFIRM |
| ctg12_75 | p450 | cytochrome P450 | *A. dendrobii* | 72 | 100 | CONFIRM |
| ctg12_81 | Dyp_perox | deferrochelatase/peroxidase | *Amycolatopsis* sp. La24 | 92 | 100 | REFINE (iron/heme) |
| ctg12_74 | Antibiotic_NAT | **AAC(3) aminoglycoside N-acetyltransferase** | *A. rhizosphaerihabitans* | 77 | 96 | **REFINE (named)** |
| ctg12_71 | Beta-lactamase | **EstA serine hydrolase (esterase)** | *A. jejuensis* | 78 | 100 | **OVERTURN** |

Outcome: core PKS confirmed; two overturns; one resistance gene named; genus
resolved to *Amycolatopsis* from a uniform per-gene consensus. This is the
evidence quality the default Mode B card must be built on.

---

*Sapote–Mamey · Mamey engine v1.9.104 · bundle v9.7.319,


---

## 9. Cluster-coherence analysis — REQUIRED output (added 2026-07-02)

Per-gene BLASTp is not just for annotation; the **source-organism distribution across
the whole cluster** is a primary evidence axis for BGC evolution, pathway stability,
and believability. Capturing only the top-1 hit's %id (as the first BGC006 pass did)
throws this away. The runner MUST retain, per gene, the **top ~6 hits with full stats**
(`accession, %identity, coverage, e-value, bitscore, organism`) and emit three cluster-level
reads:

1. **Genome-span / syntenic-block signal.** For each source genome, count how many of the
   cluster's genes list it among their top hits. A single genome carrying a large majority
   → a close relative / recent transfer with a near-complete syntenic copy. A spread with no
   genome above ~15% → an old, genus-conserved but diverged cluster (vertically inherited).
   *BGC006: max 9/61 from any one genome → diverged genus-wide family, not recent HGT.*

2. **Identity distribution: core vs periphery.** Compute mean/range %id for the catalytic
   core (KS/NRPS/precursor genes) vs regulators/accessories. A high-identity core with a
   lower-identity periphery = a stable pathway with an evolvable regulatory shell (a
   believability point in favour). *BGC006: core 85–98%, body mean 86%.*

3. **Genus-break / mosaic detection.** Scan for contiguous runs of genes whose top-hit genus
   departs from the cluster consensus at lower identity — candidate HGT sub-islands. Flag the
   locus range and treat those genes as provisional, not core. *BGC006: `ctg12_61–66`,
   6 genes, uniformly Streptomyces/Crossiella at ~78% — candidate acquired island.*

These three reads belong in Mode B **§8 (comparator)**, **§10 (co-capture)**, and
**§25 (genome neighbourhood)** — not just in the gene table. A card that reports per-gene
hits but not the cluster-level coherence read is incomplete.

### §4 stat requirement
Every §4 BLASTp entry carries `accession / %id / coverage / e-value / bitscore / organism`,
tagged `observed` with the RID as source. Not %id alone.

### RiPP/RRE addendum
For any RiPP/RRE/lanthipeptide/lasso cluster, per-gene BLASTp is necessary but not
sufficient: the **precursor peptide sequence** must be extracted from the GBK and carried
into §4, with §21 (precursor mass ladder) and §22 (RODEO/BAGEL) populated. BLASTp rarely
resolves short precursors — sequence extraction + RiPP-specific tools do.

---

## 10. Deriving FUNCTION and NOVELTY from BLASTp (engine spec for wiring)

BLASTp output per gene = top-N hits, each with `hit_def` (description + `[organism]`),
`accession`, `%id`, `coverage`, `e-value`, `bitscore`. Function and novelty are derived
as follows. All of this is deterministic and belongs in Mamey; Sapote only interprets the
emitted fields.

### 10.1 FUNCTION

1. **Consensus annotation, not top-1.** Tokenize each of the top-N `hit_def`s (strip the
   `[organism]`, strip strain/accession noise), take the majority functional term. This
   guards against a single mis-annotated top hit — the reason `ctg12_71` was correctly
   called an esterase, not a β-lactamase, was that the *consensus* said serine hydrolase.
2. **Uncharacterized filter.** A description matching
   `/hypothetical|uncharacteri[sz]ed|DUF\d+|unknown function|putative protein/i` transfers
   NO function. If the consensus is uncharacterized → `function = UNKNOWN` (and this feeds
   novelty, §10.2).
3. **Role bucket** via keyword map → {core_PKS, core_NRPS, core_RiPP, tailoring_oxidative,
   tailoring_methyl/glycosyl, transport, resistance, regulator, precursor, accessory}.
   (KS/ketoacyl→core_PKS; AMP-binding/condensation/adenylation→core_NRPS;
   YcaO/RRE/lanthionine/lasso→core_RiPP; P450/Rieske/monooxygenase/hydroxylase→tailoring_ox;
   methyltransferase→tailoring_methyl; glycosyltransferase→tailoring_glyc;
   MFS/ABC/RND/MMPL/permease/efflux→transport; AAC/APH/NAT/beta-lactamase/van/erm→resistance;
   HTH/TetR/MarR/LuxR/SARP/IclR→regulator.) This drives priority order + which §§ populate.
4. **Confidence tier** from top-hit `%id × coverage`:
   - HIGH  : %id ≥ 40 AND cov ≥ 70 → transfer the specific function.
   - MEDIUM: %id 25–40 AND cov ≥ 50 → family/fold level only ("belongs to X family").
   - NONE  : %id < 25 OR cov < 50 → no transfer.
5. **Verdict vs antiSMASH** (the reconciliation column): CONFIRM / REFINE (BLASTp names a
   generic Pfam, e.g. Antibiotic_NAT→AAC(3)) / OVERTURN (disagreement, e.g.
   Beta-lactamase→EstA esterase) / NEW (function where antiSMASH had no domain, e.g. the 3rd
   KS `ctg12_58`) / NOVEL (no informative hit).

### 10.2 NOVELTY — two axes, kept separate

**(a) Gene-level novelty** — from BLASTp directly:
- `top_id` bins: ≥90 conserved / 70–90 typical / 40–70 divergent / <40 highly divergent /
  no-hit = orphan (strongest signal).
- `uncharacterized_flag` (consensus hypothetical/DUF).
- `gene_novelty = f(top_id, uncharacterized, no_hit)` — high when identity is low OR the best
  match is uncharacterised OR there is no hit.

**(b) Product-level novelty** — the axis that answers "is this a NEW compound," and which
**BLASTp-to-nr alone cannot decide.** A cluster can be 90% conserved across genomes (low
gene-novelty) yet make an unknown compound (high product-novelty) — this is exactly BGC006
(conserved across *Amycolatopsis*, no characterised match). Product novelty needs a
**characterised-reference cross-check**:
1. Cross-reference top-hit accessions against the **MIBiG 4.0 protein set** the bundle ships
   → `characterized_compound_link` (bool + which BGC).
2. Or use the engine's KnownClusterBlast **gated by gene coverage** — the BGC006 lesson:
   colibrimycin scored 3734 but only a handful of genes matched, so it is NOT a product
   match. Require ≥ ~50% of *core* genes hitting one MIBiG BGC before calling KNOWN_COMPOUND.
- `product_novelty`: KNOWN_COMPOUND (core genes match one MIBiG BGC, high id+coverage) /
  KNOWN_CLASS (partial, class-level MIBiG hits) / NOVEL (only uncharacterised-genome hits).

**(c) Believability / coherence** (from §9): `genus_consensus`, `mean_id`, `mosaic_flag`,
`genome_span_max`. Tells you whether a NOVEL cluster is a believable native pathway (BGC006:
single-genus, high-id core) or a mosaic/possible artifact (BGC023: three-genus, moderate id).

### 10.3 Deterministic outputs the runner emits
Per gene: `function_call, function_role, function_confidence, verdict, top_id, top_cov,
uncharacterized_flag, gene_novelty, organism, accession`.
Per cluster: `mean_id, id_range, pct_uncharacterized, genus_consensus, mosaic_flag(+ranges),
genome_span_max, characterized_compound_link, product_novelty_tier, believability_tier`.
Sapote reads these into §4 (function+verdict), §8/§25 (coherence + product novelty), and §14
(what cannot be claimed — anchored to the confidence tiers, never above them).

### 10.4 Guardrails (earned this session)
- Never transfer function below the confidence threshold — tag family-level only.
- A named hit is a hypothesis, not proof — "capacity consistent with," never "is/produces."
- **Sanity-check structural claims before computing derived quantities.** A RiPP "core" that
  is a homopolymer run (e.g. `SSSSSSSCSSCC`) or has all modifiable residues in one terminal
  block is a low-complexity/assembly-artifact suspect — flag it, do NOT compute a mass ladder.
  Homology gives function; it does not validate a precursor core.

---

## Agent-session submission boundary (v9.7.195 — closes workflow-report Gaps 1–3)

An autonomous Claude/ChatGPT session cannot click the NCBI web UI, so the submit→ingest loop needs
to be explicit. Three points that were under-specified:

### Gap 1 — scoping a full ZIP (RESOLVED in code; message was stale)
`mamey blastp-online --package <full_antismash.zip> --bgc <BGC_ID>` **does** scope the ZIP to that
one BGC's proteins (v9.7.185 P7 onward). You do NOT have to extract the region GBK first. Passing a
single region GBK as `--package` also works. The unscoped guard fires only when neither a region GBK
nor `--bgc`/`--region` is given (it refuses to submit a whole proteome to NCBI).

### Gap 2 — `blastp-online` submits LIVE (it is not only a stager)
On a scoped input `blastp-online` submits to NCBI's URL API (CMD=Put), polls each RID, parses the
XML, and prints `RID <id>, <n> hits` per batch. "Fail-closed + offline-safe" means it never raises
and never fabricates: a network error yields `ok=False` with a reason, not a traceback and not
invented hits. It is not a dry-run — a successful call writes the §4 panel CSV. (`blastp-round` is
the phased-plan sibling and is dry-run by default; `--run` submits. `blastp-online` submits on the
spot.)

### Gap 3 — from a raw NCBI result back to `ingest-blastp`
If you go around the tool (submit the batch FASTA directly to the URL API), request **Tabular**, not
the web "Hit Table (CSV)" export — the API's `FORMAT_TYPE=CSV` can return a single collapsed line.
Poll the RID to READY, then GET `FORMAT_TYPE=Tabular`. `ingest-blastp --hit-table <file.csv>` expects
NCBI outfmt-10 columns in this order (header optional; parser is header-aware and also survives a
headerless file):

```
qseqid, sseqid, pident, length, mismatch, gapopen, qstart, qend, sstart, send, evalue, bitscore[, ppos]
```

The parser (`blastp_followup.parse_hit_table_csv`) recognises those header names (and common aliases
like `query_id`/`subject_id`/`percent_identity`); with no header it reads the 12 columns positionally.
`ppos` (percent-positive) is optional. Feed that CSV to `ingest-blastp` and it populates
`B5_BLASTp_Hits` — no web-UI step required.
