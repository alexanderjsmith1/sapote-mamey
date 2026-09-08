# The Mathematics of Sapote-Mamey — Volume II

### Engine subsystems: triggers, architecture, KCB/RiQ, compound class, rescue, and enrichment

**Version of record:** Mamey engine v1.9.110 · bundle v9.7.319 · compiled 2026-06-23
**Author:** Alexander J. Smith
**Companion to:** *The Mathematics of Sapote-Mamey* (Volume I — core counting, assembly tiers, AB/AF/novelty scoring, lead tiers, guards, RG-GMCI, completeness) and *The Plumbing Reference* (CLI, workbook, figures, packaging).
**Status:** Methods reference. Every formula is transcribed from engine source and cited to `module.py:symbol`; nothing is reconstructed from memory. Each cluster was verified against source before inclusion; corrections made during review are noted inline.

---

## How to read this volume

Volume I covered the engine's *core* quantitative pipeline. Volume II documents the subsystems that feed and surround it: the CCTT trigger engine the scoring math depends on, the architecture-first assessment, KCB/RiQ extraction, compound-class annotation, the rescue and concordance layers, and the deterministic enrichment generators.

The two standing interpretive rules from Volume I apply throughout and should be read into every number here:

1. **Scores are routing priors, not biological proof.** No value — no trigger, no score, no rescue link — is evidence that a strain *produces* a compound. Capacity-level language ("biosynthetic capacity consistent with…") is mandatory downstream.
2. **KCB is similarity, not identity.** Every known-cluster-blast signal is sequence similarity against a reference; it informs novelty and display but never confirms a product.

**A note on overlap with Volume I.** Cluster B documents `architecture_first.py` (new to this volume) and also revisits parts of `scoring.py` already covered in Volume I §4–§6. Where they touch the same code, Volume I is the authority for the AB/AF/novelty formulas and Volume II Cluster B gives the architecture-first context that precedes them; the two are consistent and cross-referenced, not contradictory.

---

## Volume II — Cluster A: The CCTT / Source-Scan Trigger Engine

**Source module:** `mamey/source_scans.py` (1,586 lines)  
**Registry companions:** `mamey/mamey_markers.py` · `mamey/mamey_cassettes.py` · `mamey/sapote_markers.py`  
**Engine:** Mamey v1.9.98 · Bundle: v9.7.117  
**Affiliation:** 

---

### Preamble: two standing interpretive rules

These apply to every number and result in this cluster:

- **Scores are routing priors, not biological proof.** No CCTT trigger — singly or in combination — is evidence that a strain *produces* a compound. All capacity language applies: "biosynthetic capacity consistent with," never "produces."
- **KCB = similarity, not identity.** Every known-cluster-blast signal is a sequence-similarity hit against a MIBiG reference, not product confirmation. The mis-anchor guards below exist precisely because KCB similarity is easy to over-read.

---

### A.1 Overview: what the source-scan engine does

`run_source_scans()` (`source_scans.py:run_source_scans`) is the single entry point called by the Mamey engine on every `mamey run`. It fires all pattern scans against the genome's CDS list and domain list, then packages the results into a `SourceScanBundle`. Nothing in this module calls antiSMASH again; it works entirely from the cached parse of the GenBank files.

The scan sequence is:

```
annotate_architecture(bgcs, cds_list, domains)   # per-BGC class-capacity stamp
chitin, regulators, transporters, resistance = _scan_patterns × 4
cctt = _scan_patterns(cds_list, CCTT_PATTERNS)
cctt = apply_cctt_vetoes(cctt, bgcs, cds_list)    # related-family vetoes
cctt = couple_kcb_ptm(bgcs, cctt, flbr)           # v9.7.19: HSAF/PTM Route A/B
cctt["per_bgc"] = mirror of bgc_coupling          # v9.7.19 bridge fix
cctt["trigger_bgc_counts"] = per-trigger distinct-BGC count
cctt["context_uncorroborated"] = class-compat flags (N-05/A-04)
cassettes, umed, efls, domain_architecture, resistance_tiers = ...
```

The seven outputs that feed downstream scoring are `cctt`, `resistance_tiers`, `domain_architecture`, `per_bgc_dss`, `misanchor_guards`, `primary_metabolism`, and `concordance_per_bgc`.

---

### A.2 The annotation haystack

**Source:** `source_scans.py:_hay`

Before any pattern can match, each CDS is reduced to a single lowercase search string:

```python
vals = [cds.product or "", cds.locus_tag or ""]
## skip translation / nucleotide_seq / sequence — slow + catastrophic-backtracking risk
skip = {"translation", "nucleotide_seq", "sequence"}
for k, v in cds.qualifiers.items():
    if str(k).lower() not in skip:
        vals.append(str(k))
        vals.extend(str(x) for x in v[:8])   # cap at 8 values per qualifier
return " ".join(vals).lower()
```

The cap at 8 qualifier values and the exclusion of translation/sequence fields are performance guards, not knowledge cutoffs. Matching is case-insensitive (`re.I`). Importantly, HMMER/DIAMOND domain profiles are **not** run in this layer; domain evidence comes from antiSMASH's `sec_met_domain` GBK features parsed separately in `antismash_evidence.py`.

---

### A.3 Generic scan + BGC coupling

**Source:** `source_scans.py:_scan_patterns`, `source_scans.py:bgc_coupling`

All pattern groups (CCTT, resistance, chitinase, etc.) go through the same two-step machinery:

```python
## Step 1 — per-CDS match
def _scan_patterns(cds_list, patterns):
    buckets = {k: [] for k in patterns}
    for cds in cds_list:
        h = _hay(cds)
        for group, pats in patterns.items():
            if any(re.search(p, h, flags=re.I) for p in pats):
                buckets[group].append({contig, start, end, strand, locus_tag, product})
    return {status, counts, hits, claim_safety}

## Step 2 — spatial coupling to BGC records
def bgc_coupling(bgcs, scan_hits, flank=10000):
    # for each hit: is it within flank bp of any BGC?
    for group, hits in scan_hits["hits"].items():
        for h in hits:
            for bgc in bgcs:
                if cds.contig == bgc.contig and not (
                    cds.end < bgc.start - flank or cds.start > bgc.end + flank):
                    by_bgc[bgc_id].append(group)
    return {bgc_id: sorted(set(groups))}
```

Default coupling flank: **10,000 bp** for CCTT and most scans. Cassettes and UMED use **5,000 bp** (explicit in `scan_cassettes` and `scan_umed`). The primary-metabolism scan uses **flank=0** (only genes inside the BGC's own coordinates count, because the false-positive it guards against is genes *inside* a mis-called region, not flanking neighbours).

---

### A.4 The 14 CCTT triggers

**Source:** `source_scans.py:CCTT_PATTERNS`

The CCTT ("cryptic-class trigger table") is a dict of 14 named triggers, each a list of annotation-derived regex patterns. A trigger fires when any of its patterns matches in the haystack of any CDS within 10 kb of a BGC. The table below gives each trigger's stable code key, its registry IDs (from `mamey_markers.py:MAMEY_MARKERS` and `mamey/sapote_markers.py:SAPOTE_MARKERS`), and what it is detecting.

| Code key | Marker ID | What it detects | Representative patterns |
|---|---|---|---|
| `T43-HAL_halogenase` | MMK-CCTT-001 | Flavin-dependent halogenases (promiscuous tailoring) | `(?<!de)halogenase`, `flavin-dependent halogenase`, `tryptophan halogenase` |
| `T43-XHAL_fluorinase_chlorinase` | MMK-CCTT-002 | SAM-dependent organohalogen building-block enzymes (SalL/FlA) | `fluorinase`, `chlorinase`, `\bsall\b`, `\bfla\b`, `sam-dependent halogenase` |
| `T43-PHO_phosphonate` | MMK-CCTT-003 / SMK-PHO-001 | Phosphonate commitment step: PEP mutase activity | `(?<!carboxy)phosphonate(?!.*transporter)(?!.*utilization)(?!.*c-?p lyase)(?!.*phn[g-m]\b)`, `\bpep_mutase\b`, `pep mutase(?!\s*family)`, `phosphoenolpyruvate mutase(?!\s*family)` |
| `T43-NUC_nucleoside` | MMK-CCTT-004 / SMK-NUC-001 | Peptidyl-nucleoside biosynthesis (nikkomycin/polyoxin-like) | `nikkomycin`, `polyoxin`, `\bnikj\b`, `\bnikd\b`, `\bnikc\b`, `peptidyl[- ]nucleoside`, `chitin synthase inhibit` |
| `T43-BLA_betalactam` | (no standalone marker — subsumed by class logic) | Committed β-lactam biosynthesis | `\bnocardicin\b`, `isopenicillin n synthase(?!\s*family)`, `\bpcbab\b`, `\bpcbc\b`, `acv synthetase`, `beta-lactam synthetase`, `\bbls\b`, `clavaminate synthase`, `deacetoxycephalosporin`, `monobactam` |
| `T43-AMC_aminocyclitol` | MMK-CCTT-005 / SMK-AMC-001 | Committed 2-deoxystreptamine aminocyclitol biosynthesis | `aminocyclitol`, `dois`, `btrc`, `2-deoxy-scyllo-inosose` |
| `T43-ENE_enediyne` | MMK-CCTT-006 / SMK-ENE-001 | Enediyne natural-product pathway | `enediyne` |
| `T43-LAN_lanthipeptide` | MMK-CCTT-007 | Lanthipeptide/RiPP pathway | `lanthipeptide`, `lantibiotic`, `\blanc\b`, `\blanm\b` |
| `T43-LASSO_lassopeptide` | MMK-CCTT-008 | Lasso peptide RiPP pathway | `lassopeptide`, `lasso peptide` |
| `T43-THA_thioamide` | MMK-CCTT-009 / SMK-THA-001 | Thioamide/thioamitide RiPP pathway (YcaO-based) | `thioamide`, `ycaO` |
| `T43-DKP_cdps` | MMK-CCTT-010 | Cyclodipeptide synthase / diketopiperazine pathway | `cyclodipeptide synthase`, `\bcdps\b`, `diketopiperazine` |
| `T43-IDC_indolocarbazole` | MMK-CCTT-011 | Indolocarbazole pathway (rebeccamycin/staurosporine-like) | `indolocarbazole`, `rebeccamycin`, `staurosporine`, `indsynth` |
| `T43-PTM_hsaf_tetramate` | MMK-CCTT-012 | HSAF/PTM polycyclic tetramate macrolactam (PKS-NRPS hybrid antifungal class) | `\bhsaf\b`, `maltophilin`, `dihydromaltophilin`, `heat.?stable.?antifungal`, `tetramate`, `tetramic acid`, `xanthobaccin`, `frontalamide`, `alteramide`, `clifednamide`, `ikarugamycin`, `combamide`, `polycyclic tetramate macrolactam` |
| `T43-TET_tetronate_spirotetronate` | MMK-CCTT-013 / SMK-TET-001 | Tetronate/spirotetronate polyketide class | `tetronate`, `spirotetronate`, `fkbh`, `(?<!acyl)glyceryl` |
| `T43-NN_n_n_bond` | MMK-CCTT-014 / SMK-NN-001 | N–N bond/diazo/azoxy/hydrazine chemistry (CreE/CreD-like) | `n-n bond`, `diazo`, `\bcreE\b`, `\bcreD\b`, `azoxy`, `hydrazine` |

**Pattern design notes:**
- T43-PHO uses four nested negative lookaheads to avoid firing on phosphonate *transporters*, phosphonate *utilization* regulons, C–P *lyase* operons, and `phnG-M` family genes — all contexts where "phosphonate" appears but is metabolic, not biosynthetic-core.
- T43-PHO also guards `pep_mutase` against "pep mutase *family*" annotations (the family wording hits generic protein-family databases, not the committed enzyme).
- T43-HAL uses a negative lookbehind `(?<!de)` to exclude *de*halogenases.
- T43-ENE's pattern (`enediyne`) is intentionally simple because discrimination (genuine enediyne vs. PREV-001 hglE-KS artifact) is handled downstream by `scan_misanchor_guards`, not here.
- T43-DKP's `\bcdps\b` token requires the copalyl-diphosphate-synthase veto (§A.7) because that terpene enzyme abbreviates identically.

---

### A.5 Promiscuous triggers and the class-compatibility gate (CCTT_PROMISCUOUS / CCTT_CLASS_COMPAT)

**Source:** `source_scans.py:CCTT_PROMISCUOUS`, `source_scans.py:CCTT_CLASS_COMPAT`, `source_scans.py:cctt_trigger_corroborated`

Not all CCTT triggers carry equal interpretive weight. Three are **promiscuous by biology**: halogenases and N–N bond enzymes are tailoring functions that appear legitimately across many different biosynthetic classes, so they are never challenged for class incompatibility.

```python
CCTT_PROMISCUOUS = {
    "T43-HAL_halogenase",
    "T43-XHAL_fluorinase_chlorinase",
    "T43-NN_n_n_bond"
}
```

All other CCTT triggers are **class-defining** — they imply a specific biosynthetic scaffold that should be reflected in the antiSMASH product-class label for the BGC. When a class-defining trigger fires on a BGC whose product class is incompatible, the firing is flagged as **context-uncorroborated** (evidence-preserving, not deleted). A context-uncorroborated trigger is treated as ambiguous at the claim layer — it does not contribute class-capacity language.

The compatibility sets are:

```python
CCTT_CLASS_COMPAT = {
    "T43-BLA_betalactam":          {"nrps", "beta-lactam", "betalactam", "lactam"},
    "T43-LAN_lanthipeptide":       {"lanthipeptide", "lanthi", "ripp"},
    "T43-LASSO_lassopeptide":      {"lassopeptide", "lasso", "ripp"},
    "T43-DKP_cdps":                {"nrps", "cdps", "diketopiperazine", "other", "cyclodipeptide"},
    "T43-PHO_phosphonate":         {"phosphonate", "phosph"},
    "T43-NUC_nucleoside":          {"nucleoside", "amglyccycl", "ripp", "ccna"},
    "T43-PTM_hsaf_tetramate":      {"pks", "nrps", "transat", "hybrid", "t1pks", "t2pks"},
    "T43-TET_tetronate_spirotetronate": {"pks", "t1pks", "tetronate", "transat"},
    "T43-IDC_indolocarbazole":     {"nrps", "indole", "indolocarbazole"},
    "T43-AMC_aminocyclitol":       {"amglyccycl", "aminoglycoside", "aminocyclitol", "saccharide"},
    "T43-ENE_enediyne":            {"pks", "t1pks", "enediyne", "transat"},
    "T43-THA_thioamide":           {"ripp", "nrps", "thioamitides", "lap", "thiopeptide"},
}
```

Note that `T43-BLA_betalactam` is absent from the corroboration gate code comment's "gated" list but present in `CCTT_CLASS_COMPAT`. Absent triggers (those with no entry in `CCTT_CLASS_COMPAT`) are treated as corroborated (`compat = None → return True`).

**The corroboration check:**

```python
def cctt_trigger_corroborated(trigger, products):
    if trigger in CCTT_PROMISCUOUS:
        return True
    compat = CCTT_CLASS_COMPAT.get(trigger)
    if not compat:
        return True
    blob = " ".join(products or []).lower()
    return any(k in blob for k in compat)
```

Matching is substring (`k in blob`), not word-boundary. An uncorroborated firing list is computed at the end of `run_source_scans` and stored in `cctt["context_uncorroborated"]` for audit. It is evidence-preserving: the trigger stays in `bgc_coupling`, it just carries an ambiguity flag.

**Known asymmetry flagged in code (A3 note):** T43-PTM's compatibility set includes generic tokens (`pks`, `nrps`, `t1pks`) so it self-corroborates on broad antiSMASH labels; T43-NUC's set (`nucleoside`, `amglyccycl`, `ripp`, `ccna`) does not. This means T43-PTM is harder to flag as uncorroborated than T43-NUC on ambiguous antiSMASH calls. The asymmetry is by design (HSAF clusters are frequently typed as generic NRPS/PKS), but was noted in audit as a potential false-pass on generic hybrid BGCs.

---

### A.6 Per-trigger BGC-carrying count vs. raw hit count

**Source:** `source_scans.py:run_source_scans` (W27 block)

```python
_carry = Counter()
for _trigs in cctt["per_bgc"].values():
    for _t in set(_trigs):   # set: deduplicate per-BGC
        _carry[_t] += 1
cctt["trigger_bgc_counts"] = dict(_carry)
```

`cctt["counts"]` counts raw annotation hits (gene/motif level). A phosphonate BGC with 8 PEP-mutase-like CDS annotations contributes 8 to `counts["T43-PHO_phosphonate"]` but only 1 to `trigger_bgc_counts["T43-PHO_phosphonate"]`. The latter is the correct measure for asking "how many distinct phosphonate BGCs does this strain carry"; the former inflates on tandem-repeat annotations.

---

### A.7 Related-family vetoes (CCTT_VETOES)

**Source:** `source_scans.py:CCTT_VETOES`, `source_scans.py:apply_cctt_vetoes`

Three CCTT triggers can fire spuriously on phylogenetically related but biosynthetically distinct gene families. Rather than tightening the regex (which risks missing real examples), the engine maintains explicit veto contexts:

```python
CCTT_VETOES = {
    "T43-NUC_nucleoside":  ("glycogen_trehalose", "nucleoside",
                            "sugar-kinase/glycogen-trehalose context (APH misreads as nucleoside)"),
    "T43-ENE_enediyne":    ("hglE_hglD", "enediyne",
                            "hglE/hglD glycolipid ketosynthase cross-reacts with ene_KS (PREV-001)"),
    "T43-DKP_cdps":        ("copalyl_terpene", "cyclodipeptide",
                            "copalyl diphosphate synthase (ent-CDPS, a terpene cyclase) collides with "
                            "CDPS gene token"),
}
```

For each vetoed trigger, `apply_cctt_vetoes` calls `_region_context()` to check whether the BGC's own ±10 kb neighbourhood contains the veto family's genes. If it does *and* the BGC's own product class does not independently name the expected compound class (the `v[1] not in " ".join(bgc.products).lower()` check), the trigger is removed from `bgc_coupling` for that BGC and logged in `cctt["related_family_vetoes"]`. This is a **veto** (hard deletion of the coupling for this BGC), stronger than the class-compatibility flag (which preserves but marks the trigger).

The veto context families are defined in `VETO_CONTEXT_PATTERNS`:

```python
VETO_CONTEXT_PATTERNS = {
    "glycogen_trehalose": [r"glycogen", r"trehalose", r"malto-?oligosyl", r"\btrey\b", r"\btres\b",
                           r"\bglgx\b", r"\bglgb\b", r"\bglge\b", ...],
    "hglE_hglD":          [r"\bhgle\b", r"\bhgld\b", r"hgle-ks", r"heterocyst glycolipid"],
    "sugar_kinase":        [r"sugar kinase", r"carbohydrate kinase", r"hexokinase", r"fructokinase", ...],
    "copalyl_terpene":     [r"copalyl", r"\bcdps\b.{0,4}diphosphate", r"diphosphate synthase",
                            r"geranylgeranyl", ...],
}
```

The APH/AAC sugar-kinase veto also fires in `resistance_tier_classification` (§A.11), removing `APH_AAC` from the resistance tier calculation when glycogen/trehalose/sugar-kinase context is present.

---

### A.8 HSAF/PTM KCB coupling (couple_kcb_ptm) — two routes

**Source:** `source_scans.py:couple_kcb_ptm`

T43-PTM is also injected by a second mechanism that operates on KCB similarity evidence rather than CDS annotation. This is needed because HSAF-class clusters are frequently annotated by antiSMASH as generic `NRPS,T1PKS` without any compound-specific gene names. Two routes:

```
Route A — KCB-name-driven
  ev = " ".join([bgc.products, bgc.mibig_hits, bgc.kcb_top, bgc.closest_candidate_kcb_product])
  route_a = ptm_re.search(ev)    # ptm_re = CCTT_PATTERNS["T43-PTM_hsaf_tetramate"] compiled

Route B — architecture-driven
  fl = FLBR coupling for this BGC
  lone_hybrid = ("hyb_KS" in fl) and ("mod_KS" not in fl)
  route_b = lone_hybrid and re.search(r"tetramate|macrolactam", ev)
  # gated: lone hybrid megasynthase (not a multi-module assembly line)
  # + at least one tetramate/macrolactam term anywhere in the evidence string
```

Route A fires when any PTM compound name appears in the KCB evidence. Route B fires when the BGC is a *lone* hybrid KS (no modular-KS co-occurring — a single large PKS-NRPS) and at least one tetramate/macrolactam-class token is present. Route B is intentionally conservative: a generic multi-module hybrid does not trigger it.

Both routes add `T43-PTM_hsaf_tetramate` to `cctt["bgc_coupling"]` for the BGC. The route taken is recorded in `cctt["ptm_kcb_coupling"]` for audit.

---

### A.9 The T43-PHO phosphonate pattern: precision design

T43-PHO carries the most complex single regex in the engine:

```python
r"(?<!carboxy)phosphonate(?!.*transporter)(?!.*utilization)(?!.*c-?p lyase)(?!.*phn[g-m]\b)"
```

One positive match plus four negative lookaheads, left to right:

- `(?<!carboxy)` — excludes *carboxy*phosphonate (a metabolic intermediate, not committed biosynthesis)
- `(?!.*transporter)` — excludes phosphonate *transporters* (uptake machinery)
- `(?!.*utilization)` — excludes "phosphonate utilization" regulons (catabolism not biosynthesis)
- `(?!.*c-?p lyase)` — excludes the C–P lyase operon (phosphonate catabolism)
- `(?!.*phn[g-m]\b)` — excludes `phnG` through `phnM` (the C–P lyase structural genes)

Additionally, `pep mutase(?!\s*family)` and `phosphoenolpyruvate mutase(?!\s*family)` exclude generic "family" database annotations.

These guards collectively distinguish the committed PEP-mutase-based biosynthesis step (the T43-PHO target) from the far more abundant phosphonate catabolism and transport genes that share vocabulary.

---

### A.10 The FLBR megasynthase census

**Source:** `source_scans.py:FLBR_PATTERNS`, `source_scans.py:scan_flbr`, `source_scans.py:scan_orphan_megasynthase_motifs`

FLBR ("fragment-locus-BGC-rescue") detects whether the genome contains more megasynthase-like sequences than the called BGC set can account for — a sign that fragmentation has split large PKS/NRPS loci across multiple BGCs or left pieces as unannotated orphan contigs.

**Pattern groups:**

```python
FLBR_PATTERNS = {
    "mod_KS":   [r"modular.?ks", r"ketosynthase", r"pks ks", r"beta-ketoacyl synthase"],
    "hyb_KS":   [r"hybrid.?ks", r"nrps.*pks", r"pks.*nrps"],
    "tra_KS":   [r"trans.?at", r"trans-acyltransferase"],
    "mega_NRPS":[r"nonribosomal peptide synthetase"],
}
```

**Classification thresholds:**

```python
total_ks   = mod_KS + hyb_KS + tra_KS   (raw genome-wide CDS-annotation counts)
total_mega = total_ks + mega_NRPS

fragmented_bgcs = BGCs with edge_status in {Edge, Full-contig}
                  AND ("pks" or "nrps" or "transat") in products

if total_ks >= 4 AND fragmented_bgcs:
    flag, grade = "LMPKS_FRAGMENT_SET",        "STRONG"
elif total_mega >= 4 OR fragmented_bgcs:
    flag, grade = "MEGASYNTHASE_FRAGMENT_SUSPECT", "WEAK"
else:
    flag, grade = "NULL", "NULL"
```

**Rescue-readiness tiers:**

```python
## interior_frac = Interior BGCs / total BGCs
not_good = interior_frac < 0.70   # rescue only meaningful below Good assembly

if not_good AND orphan_ks_count >= 3 AND fragmented_count >= 5:  → HIGH
elif not_good AND (orphan_ks_count >= 1 OR fragmented_count >= 3):  → MODERATE
else:  → LOW

rescue_priority_score = fragmented_count + orphan_ks_count   (Tier-1 KS only)
```

The 0.70 interior-fraction threshold matches the GOOD assembly tier definition from `assembly.py` (Volume I §3.1).

**Orphan KS detection — annotation-independent:**

```python
_KS_ACTIVE_SITE = re.compile(r"[DE]TAC[ST]S")   # beta-ketoacyl synthase catalytic cysteine
_AT_ACTIVE_SITE = re.compile(r"GHS[LIVMFQAW]G")  # alpha/beta-hydrolase nucleophile elbow
_ORPHAN_FLANK   = 20000                           # bp exclusion around called BGC cores
```

Any CDS ≥200 aa, outside every called BGC core ±20 kb, without an existing PKS/NRPS/esterase/hydrolase annotation, is tested for these motifs. KS-bearing orphans (carry `[DE]TACS[TS]`) are Tier-1 evidential signals; AT-only orphans (`GHSxG` but no KS) are listed separately as Tier-2 alpha/beta-hydrolase-ambiguous and explicitly do *not* constitute megasynthase evidence (the `GHSxG` motif is shared with standalone esterases, lipases, and peptidases). A CDS meeting the AT-only criterion and ≤400 aa is flagged `likely_standalone_hydrolase = True`.

---

### A.11 Resistance tiering

**Source:** `source_scans.py:RES_CLASS_CONCORDANCE`, `source_scans.py:resistance_tier_classification`

Resistance/self-protection calls go through a four-tier classifier:

| Tier code | Conditions | Confidence |
|---|---|---|
| `T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED` | Diagnostic groups present (Erm_methylase / VanHAX_like / APH_AAC / Fosfomycin) | HIGH if class-concordant, MODERATE if not |
| `T2_RESISTANCE_LIKE_SOURCE_DERIVED` | Generic groups only (Beta_lactamase_fold / Self_resistance_general) | MODERATE if class-concordant, LOW if not |
| `T3_TRANSPORTER_ONLY_ROUTING` | Transporter/efflux only, no resistance groups | LOW |
| `NULL_NO_SOURCE_DERIVED_RESISTANCE` | Nothing | NONE |

Class concordance is checked against `RES_CLASS_CONCORDANCE`:

```python
RES_CLASS_CONCORDANCE = {
    "VanHAX_like":       ["glycopeptide"],
    "Erm_methylase":     ["macrolide", "lincosamide", "lanthipeptide", "ripp",
                          "lassopeptide", "thiopeptide"],
    "APH_AAC":           ["aminoglycoside", "aminocyclitol", "nucleoside"],
    "Fosfomycin":        ["phosphonate"],
    "Beta_lactamase_fold":["betalactone", "beta-lactone", "betalactam", "beta-lactam"],
}
```

A BGC is class-concordant if *any* of the resistance group's expected product-class tokens appear in the BGC's own `products` text.

**HGT guard (v9.7.33 #28):** The mobile-dominance check is gene-level, not just product-label:

```python
MOBILE_ELEMENT_CORE = {"integrase", "recombinase", "transposase"}
mobile_dominant = (core_hit and len(mobile_fams) >= 2) or (len(mobile_fams) >= 3)
```

A lone flanking IS element (1 mobile family) is *not* dominant. An ICE-like element needs a core mobility determinant (integrase/recombinase/transposase) *plus* at least one further mobile family, or three mobile families total, to qualify as mobile-dominant.

**APH_AAC veto:** When `APH_AAC` fires and the BGC's ±10 kb contains glycogen/trehalose/sugar-kinase context, `APH_AAC` is removed from the resistance group set before tiering. This guards the same SID-XXX false-positive caught by the T43-NUC CCTT veto.

---

### A.12 Mis-anchor guards

**Source:** `source_scans.py:scan_misanchor_guards`

Three KCB anchor families have known failure modes where sequence similarity is high enough to produce a hit but the biosynthetic context is incompletely matched. The guards are gene-level, annotation-based, and operate on the **KCB anchor** (not the antiSMASH product class):

**1. Aminoglycoside / DOIS guard**

```python
aminoglycoside_misanchor = (aminoglycoside anchor found)
                           AND NOT (any _DOIS_GENE in own CDS)
## _DOIS_GENE = 2-deoxy-scyllo-inosose synthase / BtrC family
```

A 2-deoxystreptamine aminoglycoside anchor is only credible when the committed first step of the pathway (DOIS/BtrC) is present in the BGC's own genes. Without it, the KCB hit is spurious for this locus.

**2. Polyene macrolide / KS count guard**

```python
_POLYENE_MIN_KS = 4
polyene_misanchor = (polyene-macrolide anchor found)
                    AND (ks_domain_count < 4)
```

A genuine polyene macrolide backbone requires a large modular PKS (≥4 PKS_KS domains). Fewer than 4 is inconsistent with polyene biosynthesis.

**3. Enediyne discrimination (§4.3 / PREV-001)**

```python
if ene_specific AND ene_ks >= 1:       verdict = "GENUINE_E_SIGNAL"
elif ene_specific:                      verdict = "ENEDIYNE_MISANCHOR"   # named enediyne, no ene_KS
elif ene_generic AND prev001:           verdict = "PREV001_ARTIFACT"     # hglE/hexacosalactone cross-reaction
elif ene_generic:                       verdict = "E_SIGNAL_UNRESOLVED"  # generic, no hglE
else:                                   verdict = ""
```

`ene_specific` is a named enediyne natural product (calicheamicin, dynemicin, esperamicin, etc.) in the KCB anchor. `ene_generic` is any "enediyne" or "ene_KS"/"ene-ks" token. `prev001` is any hglE/hglD/hexacosalactone signal. The combination matrix produces four verdicts; only `GENUINE_E_SIGNAL` (named compound + real ene_KS domain) is treated as actual enediyne evidence. `PREV001_ARTIFACT` is the PREV-001 standing rule: the hglE glycolipid domain cross-reacts with ene_KS signatures and should be treated as a false-positive.

**4. KCB class-level mismatch (`_KCB_CLASS_COMPAT`)**

A v9.7.63 addition: compound-specific rules for known cases where a named KCB compound is chemically incompatible with the BGC's own antiSMASH product class. The check returns `(mismatch=True, reason)` when:

- the KCB compound name matches one of the ~12 compound patterns (kinamycin, prejadomycin, cyphomycin, difficidin, showdomycin, etc.), AND
- the BGC's own product class set has **zero** overlap with the expected class tokens for that compound family.

For example: a kinamycin KCB hit on a BGC typed purely as terpene is flagged because kinamycin is an aromatic T2PKS diazobenzofluorene — terpene loci lack the T2PKS backbone. The mismatch suppresses the anchor-derived AB/AF/novelty credit unless a Tier-1 diagnostic independently fires.

---

### A.13 Per-BGC Diagnostic Signal Score (DSS 0–5)

**Source:** `source_scans.py:compute_per_bgc_dss`

A source-derived precompute for Sapote §34.3:

```
DSS = min(5,
    +2  if any Tier-1 domain class present (PKS_KS / NRPS_A / TE_release /
            YcaO_TOMM / Halogenase / RiPP_precursor) — from domain_architecture
    +1  if KCB protein_hits >= 5
    +1  if resistance tier starts with "T1" for this BGC
    +1  if any CCTT trigger coupled to this BGC
)
```

The score is capped at 5. The comment in the code notes that the Tier-1 domain class hit list is sorted before producing reasons (for deterministic manifest output, since the underlying set is unordered). This score is marked "source-derived DSS; Sapote §34.3 applies the authoritative formula" — it is a precompute for routing, not a final judgment.

---

### A.14 UMED maturation-gap detection

**Source:** `source_scans.py:UMED_PATTERNS`, `source_scans.py:scan_umed`

UMED detects whether a BGC that *needs* a post-translational maturation enzyme has one within 5,000 bp:

```python
UMED_PATTERNS = {
    "LanP_S8_protease":             [r"lanp", r"subtilisin", r"peptidase s8", r"serine protease"],
    "LanT_C39_transporter_peptidase":[r"lant", r"c39", r"peptidase.*abc", r"abc.*peptidase"],
    "FlaP_AplP_S9_protease":        [r"flap", r"aplp", r"peptidase s9"],
    "M16B_metalloprotease":         [r"m16", r"metalloprotease", r"pitrilysin"],
    "YcaO_TfuA_thioamide":          [r"ycao", r"tfua", r"thioamide"],
    "RiPP_RRE":                     [r"ripp recognition element", r"\brre\b"],
    "nucleoside_maturation":        [r"nik", r"nucleoside", r"radical sam", r"aminotransferase"],
}

needs_maturation = any(x in product_text for x in
    ["ripp", "lanthipeptide", "lassopeptide", "thioamide", "azole", "nucleoside"])
```

Verdicts: `IN_CLUSTER_OR_PROXIMAL_MATURATION_SOURCE_SUPPORTED` (needs + found), `MATURATION_GAP_SOURCE_DERIVED` (needs + not found), `NOT_MATURATION_GATED` (class does not require maturation). The gap verdict does not suppress the BGC's lead score — it raises it (a pathway with clear precursor logic but a missing maturation enzyme is a candidate for an off-cluster or split-locus enzyme, and is worth noting).

---

### A.15 EFLS — preliminary shared-evidence linkage

**Source:** `source_scans.py:scan_efls`

EFLS (Evidence-Fragmentation-Linkage-Scan) nominates BGC pairs that may represent physically linked fragments of a single pathway split by assembly gaps.

```
Scoring (additive):
  +1 per shared antiSMASH product-class token
  +2 per shared MIBiG reference hit    ← weighted double (known reference > product-class text)
  +1 per shared cassette family
  +1 per shared CCTT trigger

relation = "COMPLEMENTARY_OR_SHARED_EVIDENCE"  if score >= 3
           "WEAK_SHARED_EVIDENCE"               if score < 3 (but score > 0)
```

Scope: all-vs-all BGC pairs, filtered to pairs where **at least one member is Edge or Full-contig** (Interior–Interior pairs are excluded because two fully interior clusters sharing vocabulary are more likely to be paralogous than split). Output is capped at the top 500 scored pairs. This score is explicitly marked as "preliminary shared-evidence linkage only; not physical contig linkage or Jaccard protein-overlap confirmation."

---

### A.16 bldA/TTA tiering

**Source:** `source_scans.py:scan_blda_tta`

TTA codon counting for the bldA-dependent translational control system in actinomycetes:

```python
## actinomycete-gated (v9.7.87 Item A)
if not actinomycete:
    tier = "NOT_APPLICABLE"   # TTA counts are GC-content noise, not a developmental signal

## TTA codons within BGC CDS (flank=0)
if tta_codons == 0:   tier = "T1"   # no bldA sensitivity
elif tta_codons <= 2: tier = "T2"   # low burden
elif tta_codons <= 5: tier = "T3"   # moderate; bldA-sensitive expression plausible
else:                 tier = "T4"   # high (>=6); strongly bldA-sensitive lead flag
```

Thresholds: T2 ≤ 2, T3 ≤ 5, T4 > 5 TTA codons in the BGC's own CDS set. The NOT_APPLICABLE gate fires when `cohort_resolver.actino_status()` returns `non_actinomycete` for the organism string — this prevents meaningless T4 calls on non-actino genomes where TTA frequency is a GC-composition artifact, not a developmental regulatory signal.

---

### A.17 TFBS motif scan

**Source:** `source_scans.py:TFBS_MOTIFS`, `source_scans.py:scan_tfbs`

12 upstream motif families are scanned in a 300-bp upstream window of every CDS:

```python
upstream_bp = 300   # window size

## strand-corrected:
if cds.strand >= 0:
    window = seq[max(0, start - 301) : max(0, start - 1)]
else:
    window = reverse_complement(seq[end : end + 300])
```

IUPAC ambiguity codes in the motifs (`N` → `[ACGT]`, `W` → `[AT]`, `S` → `[GC]`, `R` → `[AG]`, `Y` → `[CT]`) are expanded before matching. All 12 families are scanned against every upstream window; output is capped at 1,000 hits for space reasons.

The claim-safety string is explicit: "Simple motif scan; replace with calibrated TFBS models/background scoring before manuscript use." These counts are induction-planning evidence, not expression proof.

**Motif table:**

| Marker ID | Family | Motif(s) |
|---|---|---|
| MMK-TFBS-001 | DasR-like palindrome | `TGTCTAGACNA` / `TGTNANNNNNNTNACA` |
| MMK-TFBS-002 | DmdR iron-box-like | `TTAGGTTAGGCTAACCTAA` |
| MMK-TFBS-003 | LexA/SOS-like | `CTGTATATATATACAG` / `CGAACNNNNGTTCG` |
| MMK-TFBS-004 | BldD-like | `GTCTAGAC` |
| MMK-TFBS-005 | FuR-like | `GATAATGATAATCATTATC` |
| MMK-TFBS-006 | Zur-like | `AAATGTTATAACATTT` |
| MMK-TFBS-007 | IolR-like | `TGTGANNNNNNTCACA` |
| MMK-TFBS-008 | PhoP-box-like | `GTTCANNNNNGTTC` |
| MMK-TFBS-009 | ANR/FNR-like | `TTGATNNNNATCAA` |
| MMK-TFBS-010 | GBL/AdpA-like | `TGGCSNGWWY` |
| MMK-TFBS-011 | SARP/BTAD-like | `TCGAGNNNNCTCGA` |
| MMK-TFBS-012 | PAS-LuxR-like | `ACCTGTNNNNACAGGT` |

---

### A.18 QS signal and NAPAA routing

**Source:** `source_scans.py:scan_qs_signals`

BGCs whose products or CDS annotations indicate a quorum-sensing signal compound are flagged for ecology-only routing and excluded from AB/AF mechanistic-link wet-lab bonus:

```python
QS_PRODUCT_LABELS = {
    "butyrolactone", "hserlactone", "bdsf", "furan",
    "gamma-butyrolactone", "autoinducer",
}
QS_CDS_PATTERNS = [r"luxI", r"afsA", r"rpfF", r"autoinducer synthase",
                   r"acyl-homoserine lactone synthase", r"AHL synthase",
                   r"gamma-butyrolactone synthase"]
```

NAPAA (poly-amino acid) BGCs are also flagged:
```python
if "napaa" in product_text or "poly-amino acid" in product_text or "polyamino acid" in product_text:
    napaa_bgc_ids.append(bgc.bgc_id)
```

NAPAA flagging is neutral (the NAPAA Nosema hypothesis is retired), not a downgrade. QS flagging routes to ecology-only.

---

### A.19 Glycosylation-arm trap (§34.5)

**Source:** `source_scans.py:scan_glycosylation_arm_candidates`

Saccharide-typed BGCs with KCB hits against glycosylated-compound references are candidates for a glycosylation-arm sub-cluster (an aglycone core residing on a separate BGC/contig):

```python
## fires when:
## (a) product label contains "saccharide"
## (b) KCB top hit names a glycosylated-compound family (macrolide / erythromycin /
##     angucycline / anthracycline / aminoglycoside / glycopeptide / etc.)
## (c) kcb_protein_hits >= 3

if protein_hits >= 3:  → GLYCOSYLATION_ARM_TRAP_FIRED
elif protein_hits >= 1:  → INCIDENTAL_OVERLAP (note only)
```

The threshold of **≥3 protein hits** (v8.10.2) distinguishes an authentic sugar-cassette arm from an incidental KCB overlap. 1–2 hits are noted but do not fire the full sub-rule.

---

### A.20 Primary metabolism suppression

**Source:** `source_scans.py:PRIMARY_METABOLISM_PATTERNS`, `source_scans.py:scan_primary_metabolism`

Three families of non-bioactivity genes trigger suppression of AB/AF keyword credit when the BGC's own antiSMASH product class is a weak/over-call label:

```python
PRIMARY_METABOLISM_PATTERNS = {
    "housekeeping":    [topoisomerases, gyrase, ribosomal proteins, DNA polymerase,
                        aminoacyl-tRNA synthetases, elongation factors, thymidylate kinase],
    "pigment":         [lycopene, carotenoid, phytoene, CrtI/CrtB/CrtE, squalene-hopene,
                        hopanoid, spore pigment WhiE, melanin/tyrosinase, arylpolyene-specific],
    "replication_core":[replicative helicase DnaB, DNA primase DnaG, chromosome replication
                        initiator, DnaE/DnaN/sliding clamp, single-stranded DNA-binding,
                        ligase, replisome],
}
```

Suppression applies only when the BGC's **own** product class is a weak label (`nrps-like`, `terpene`, `saccharide`, `arylpolyene`) **and** no Tier-1 CCTT diagnostic fires. A committed biosynthetic class (full NRPS/PKS/RiPP) or a Tier-1 trigger overrides the flag. Coupling uses `flank=0` so only the BGC's internal CDS contribute.

---

### A.21 Registry wiring status (B2 Phase 1)

**Source:** `source_scans.py` lines 297–328, `mamey/mamey_markers.py`, `mamey/mamey_cassettes.py`, `mamey/sapote_markers.py`

The `CCTT_PATTERNS` and other pattern dictionaries can be backed by `registry_inventory_v1.9.4.json` at runtime. On import, the module attempts to load the registry detector:

```python
if not os.environ.get("MAMEY_DISABLE_REGISTRY_DETECTOR") == "1":
    _built = registry_detector.build_pattern_dicts()
    for _name, _dict in _built.items():
        globals()[_name] = _dict
    REGISTRY_DETECTOR_ACTIVE = True
```

If the registry is absent or inconsistent, the module falls back silently to the hardcoded literal dicts above. The startup banner reports `registry_detector✓` or `registry_detector—(fallback)`. Parity between registry-derived and hardcoded dicts is asserted by `tests/test_b2_registry_parity.py`.

The `mamey_markers.py` and `mamey_cassettes.py` files formalise the detection vocabulary (marker names, Pfam accessions, evidence tiers, claim ceilings) as `Marker` and `Cassette` objects, but the Pfam/HMM **scanning** is deferred to a Release 2 HMMER/Diamond backend that does not yet run in the current pipeline. Live detection is entirely regex-based via `source_scans.py`. The registry objects are currently used for crosswalk naming and catalog generation only.

---

### A.22 Cassette families (CASSETTE_PATTERNS / MMC-001 through MMC-015)

**Source:** `source_scans.py:CASSETTE_PATTERNS`, `source_scans.py:CASSETTE_REGISTRY_MAP`, `mamey/mamey_cassettes.py:MAMEY_CASSETTES`

15 cassette families are scanned at a 5,000-bp coupling flank (tighter than the CCTT 10,000-bp flank, because cassette genes are typically more proximal to the BGC core). The `CASSETTE_REGISTRY_MAP` is a hard-coded positional mapping from cassette family name to registry ID — the code comment explicitly warns that a naive name-token join would mis-resolve `tomm_azole_ripp` to the indolocarbazole marker on the "carb-AZOLE" substring. The explicit map is the single source of truth.

| Registry ID | Family name | Tier |
|---|---|---|
| MMC-001 | release_macrocyclization | TIER_3 |
| MMC-002 | glycosylation | TIER_3 |
| MMC-003 | halogenation | TIER_2 |
| MMC-004 | phosphonate | TIER_1 |
| MMC-005 | nucleoside | TIER_1 |
| MMC-006 | aminoglycoside_aminocyclitol | TIER_1 |
| MMC-007 | tetronate_spirotetronate | TIER_1 |
| MMC-008 | thioamide_ycao | TIER_1 |
| MMC-009 | lanthipeptide | TIER_2 |
| MMC-010 | lassopeptide | TIER_1 |
| MMC-011 | tomm_azole_ripp | TIER_1 |
| MMC-012 | polyene_ptm_hsaf | TIER_1 |
| MMC-013 | siderophore_metallophore | TIER_2 |
| MMC-014 | transporter_resistance | TIER_5 (inventory only) |
| MMC-015 | chitin_glycan_ecology | TIER_2 |

---

*End of Cluster A. Sources: `mamey/source_scans.py`, `mamey/mamey_markers.py`, `mamey/mamey_cassettes.py`, `mamey/sapote_markers.py`. Every constant is transcribed from the source with module:symbol citations.*
## Volume II — Math & Algorithms: Cluster B — Architecture, Scoring, and Rules

**Source modules:** `architecture_first.py` (1327), `scoring.py` (582), `source_scans.py` (1733), `antismash_evidence.py` (1081), `class_architecture.py` (176), `parsers.py` (504), `rules.py` (157), `adjudication.py` (47), `fragment_ceiling.py` (138), `genus_reference.py` (131), `precision.py` (65), `assembly.py` (101), `boundary_audit.py` (141)  
**Engine version:** Mamey v1.9.98 · Bundle v9.7.117  
**Cross-reference:** Cluster A (CCTT triggers) — see the "Cluster A: The CCTT / Source-Scan Trigger Engine" section of this volume

---

### 1. The Architecture-First Pipeline (`architecture_first.py`)

**Version:** v9.7.107 patch (v2.2)  
**Problem solved:** KCB confirmation bias — letting a KnownClusterBlast hit determine the product class label before the gene content is assessed. Architecture-first prevents this: gene content is assessed KCB-blind first, then the KCB hit is checked for concordance.

#### 1.1 Three-step pipeline

```python
arch, concordance, assignment = architecture_first_assessment(
    genes, boundary_status="Interior",
    kcb_compound="", kcb_n_genes=0, kcb_mibig_class=""
)
```

Each step can also be called independently via `assess_architecture()`, `check_kcb_concordance()`, `make_assignment()`.

#### 1.2 Step 1: `assess_architecture(genes, boundary_status)` — KCB-blind

Input: a list of gene dicts each with `locus_tag`, `aa_length`, `sec_met_domains`.

**Gene classification** (`_classify_gene`):
- **Megasynthase**: `aa > 800` AND (`has_ks` OR `has_amp`)
- **has_ks**: any of `PKS_KS`, `ketoacyl-synt`, `Ketoacyl-synt`, `KAsynt_C_assoc`, `tra_KS`
- **has_amp**: any of `AMP-binding`, `FAAL_cds`, `FAAL`
- **has_cond**: any of `Condensation`, `C1_LCL`, `C2_LCL`, `C2_DCL`, `C3_…`, `C4_…`, `C5_…`, `C67_`
- **has_at_embedded**: gene has KS AND an AT domain (cis-AT PKS signature)
- **Biosynthetic core**: any domain from `BIOSYNTHETIC_CORE_DOMAINS` (27 entries: PKS_KS, AMP-binding, Condensation, Chal_sti_synt, Terpene_syn_C_2, IucA_IucC, Ectoine_synth, AfsA, LANC_like, Lant_dehydr_N/C, YcaO, Polyketide_cyc, p450, Trp_halogenase, Radical_SAM, DUF692, Asn_synthase, and others)

**Classification priority order** (first match wins, returns via `_apply_boundary_adjustment`):

| Priority | Class | Key evidence |
|---|---|---|
| 1 | **PTM** | Single protein 2500–4000 aa with BOTH KS AND AMP-binding; ≤1 other KS, ≤1 other AMP |
| 2 | **T2PKS** | ≥2 small KS genes (300–550 aa) OR ≥2 t2pks-annotated genes + small ACP |
| 3 | **Trans-AT PKS / Hybrid** | `tra_KS` domains, OR FkbH, OR ≥2 AT-less megasynthases + standalone AT (<600 aa); if NRPS present → TRANS_AT_HYBRID |
| 4 | **T3PKS** | `Chal_sti_synt` |
| 5 | **Lanthipeptide** | `LANC_like` or `Lant_dehydr` |
| 6 | **LAP / Ranthipeptide** | YcaO alone → LAP; YcaO + SSF → ranthipeptide |
| 7 | **Ranthipeptide (YcaO-independent)** | SPASM + TIGR03962 |
| 8 | **Lassopeptide** | Asn_synthase + (Lasso_RRE or no KS); `Transglut_core3` also counts |
| 9 | **Mycofactocin** | TIGR02109 |
| 10 | **DUF692 RiPP** | DUF692 |
| 11 | **Indolocarbazole** | `indsynth` / StaD / RebC |
| 12 | **NAPAA** | DUF3516 |
| 13 | **Ectoine** | Ectoine_synth |
| 14 | **NI-siderophore** | IucA_IucC WITHOUT NRPS |
| 15 | **Butyrolactone** | AfsA |
| 16 | **Nucleoside** | TruD / EPSP_synthase / nikJ |
| 17 | **Betalactone** | PEP-utilizer + biotin carboxylase |
| 18 | **Terpene subtypes** | Only when NO megasynthases. Carotenoid (phytoene/lycopene), Hopanoid (SQHop), Cyclized (Terpene_syn_C_2), Linear (polyprenyl without cyclase); linear + PG_binding/YkuD → PRIMARY_METABOLISM |
| 19 | **NRPS siderophore** | NRPS + chorismate_bind |
| 20 | **PKS/NRPS hybrid** | ≥2 megasynthases with both KS and AMP |
| 21 | **Pure NRPS** | AMP without KS; requires real AMP-binding or Condensation (FAAL guard) |
| 22 | **Cis-AT PKS** | KS without AMP |
| 23 | **UNKNOWN** | Falls through all |

**Boundary adjustment** (`_apply_boundary_adjustment`): Edge or Full-contig → downgrade confidence one tier (HIGH → MEDIUM → LOW). Stored in both `confidence` (adjusted) and `confidence_raw` (pre-adjustment) with a reasoning note.

**Module count estimation:**
- PKS modules: `sum(megasynthase_aa with KS) ÷ 1500`
- NRPS modules: `sum(megasynthase_aa with AMP but not KS) ÷ 1100`
- Total = sum of both

**Known diagnostic markers captured in `ArchitectureReport.diagnostic_markers`:** all hits listed with locus_tag, domain name, and chemotype context.

**31 `PathwayType` enum values:** TRANS_AT_PKS, CIS_AT_PKS, NRPS, PKS_NRPS_HYBRID, TRANS_AT_HYBRID, T2PKS, T3PKS, LANTHIPEPTIDE, LASSOPEPTIDE, LAP, THIOPEPTIDE, RANTHIPEPTIDE, MYCOFACTOCIN, DUF692_RIPP, OTHER_RIPP, TERPENE_CYCLIZED, TERPENE_LINEAR, HOPANOID, CAROTENOID, NI_SIDEROPHORE, NRPS_SIDEROPHORE, BUTYROLACTONE, ECTOINE, NAPAA, NUCLEOSIDE, INDOLOCARBAZOLE, PTM, BETALACTONE, PHOSPHONATE, AMINOGLYCOSIDE, PRIMARY_METABOLISM, UNKNOWN.

#### 1.3 Step 2: `check_kcb_concordance(arch, kcb_compound, kcb_n_genes, query_n_genes, kcb_mibig_class)`

**Coverage check:** `kcb_coverage_pct = kcb_n_genes / query_n_genes × 100`. If < 30% → `WEAK_SIGNAL` immediately.

**Class lookup order:**
1. `MIBIG_CLASS_MAP` by `kcb_mibig_class` (structured MIBiG class tag, e.g. "Polyketide:Trans-AT type I") — 15 entries
2. `KCB_COMPOUND_MAP` by compound name substring (lowercase) — 60+ entries covering PTM, trans-AT, cis-AT PKS, T2PKS, NRPS, siderophores, terpene misanchors, nucleosides

**Concordance verdicts:**

| Verdict | Condition |
|---|---|
| `CONCORDANT` | architecture matches expected; also 4 fuzzy-compatible pairs (TRANS_AT_HYBRID↔PKS_NRPS_HYBRID, NRPS_SIDEROPHORE↔NRPS, THIOPEPTIDE↔LAP, TERPENE_CYCLIZED↔HOPANOID) |
| `DISCORDANT` | Mismatch and architecture ≠ UNKNOWN → **architecture wins** |
| `ARCHITECTURE_DEFERS` | Architecture = UNKNOWN AND coverage ≥ 60% → use KCB provisionally at LOW confidence |
| `WEAK_SIGNAL` | Coverage < 30%, or compound not in class map, or UNKNOWN + coverage < 60% |
| `NO_KCB` | Empty/null KCB compound |

#### 1.4 Step 3: `make_assignment(arch, concordance)` — Final Product Class

**Architecture wins in all cases except ARCHITECTURE_DEFERS.** When DISCORDANT, the kcb_note explicitly flags that architecture overrides KCB.

| Concordance | `product_class` source | `confidence` |
|---|---|---|
| CONCORDANT | architecture.pathway_type.value | arch.confidence |
| DISCORDANT | architecture.pathway_type.value | arch.confidence |
| ARCHITECTURE_DEFERS | concordance.kcb_class | LOW |
| WEAK_SIGNAL | architecture.pathway_type.value | arch.confidence |
| NO_KCB | architecture.pathway_type.value | arch.confidence |

#### 1.5 Known misanchor patterns (from `SAPOTE_INSTRUCTIONS`)

- **T2PKS KCB** (chlortetracycline, prejadomycin) on a terpene BGC: matches shared flanking genes, not the terpene core
- **PTM KCB** (clifednamide, HSAF) on a collinear trans-AT PKS: matches a KS subdomain, not the iterative iPKS-NRPS
- **Macrolide KCB** (spiramycin, niddamycin) on a Full-contig fragment: the captured module matches many macrolide references generically

---

### 2. The Triage Scoring Engine (`scoring.py`)

#### 2.1 Score accumulation formula

For each BGC:

```
base_ab  = 25 + score_keywords(class_txt, AB_KEYWORDS)
base_af  = 20 + score_keywords(class_txt, AF_KEYWORDS)
novelty  = 30 + score_keywords(class_txt, NOVELTY_KEYWORDS)
```

`class_txt` = `scoring_class_text(bgc)` = own `products` + `mibig_hits` + `closest_candidate_kcb_product` (when resolved). **NOT** the raw `kcb_top` genome-description blob (v9.7.85 P-7 contamination fix: `kcb_top` contains the reference organism's entire class vocabulary, which falsely credits those classes to this BGC).

**Compound-class scored consequence** (v9.7.86): if the BGC's `compound_class_annotation` carries a `scored_axis` ("af" or "ab"), add `scored_weight` to that axis. Covers polyene_macrolide (AF), ionophore (AB); anthracycline has weight 0 (routing flag only).

#### 2.2 Keyword weight tables

**`AB_KEYWORDS`** (17 classes): nrps=12, t1pks=10, t2pks=12, hr-t2pks=14, transat-pks=14, lanthipeptide=12, lassopeptide=10, thioamide=14, thiopeptide=14, thiazolylpeptide=14, phosphonate=15, aminoglycoside=14, saccharide=8, phenazine=10, carbapenem=18, halogenated=8, ripp=8, azole=8

**`AF_KEYWORDS`** (16 classes): t1pks=10, transat-pks=12, nrps=8, hsaf=20, polyene=18, nystatin=20, candicidin=18, tetramate=16, terpene=6, siderophore=4, metallophore=4, nucleoside=18, nikkomycin=20, polyoxin=20, chitin=12, ptm=12, sgr ptm=14

**`NOVELTY_KEYWORDS`** (11 classes): transat-pks=18, thioamide=15, phosphonate=15, enediyne=18, azoxy=18, ranthipeptide=12, ripp=10, nrps=8, t1pks=8, t2pks=8, hgle=12

**`DIAGNOSTIC_BONUS`** = 25: added to the relevant axis when an AF or AB diagnostic trigger fires.

**AF diagnostic triggers:** T43-NUC, T43-PTM  
**AB diagnostic triggers:** T43-LAN, T43-LASSO, T43-THA, T43-PHO, T43-AMC, T43-BLA

**`TIER1_FLOOR_EXCLUDED_PREFIXES`**: `T43-HAL_`, `T43-XHAL_` — halogenases/fluorinase-chlorinases are tailoring modifications, not class calls. A lone halogenase trigger does NOT floor the tier.

#### 2.3 `score_keywords` — delimiter-bounded, subsumption-aware

```python
def score_keywords(text, weights):
    matched = {key for key in weights if _key_present(key, text) and key not in PIGMENT_NONLEAD_CLASSES}
    for sub, generic in SUBCLASS_SUBSUMES.items():
        if sub in matched and generic in matched:
            matched.discard(generic)  # hr-t2pks subsumes t2pks; transat-pks subsumes t1pks
    return float(sum(weights[k] for k in matched))
```

`_key_present` uses regex `r"(?<![a-z0-9])" + key + r"(?![a-z0-9])"` — prevents "polyene" inside "arylpolyene" from matching the AF polyene keyword.

**`PIGMENT_NONLEAD_CLASSES`**: arylpolyene, ladderane — explicitly excluded from scoring.

#### 2.4 Guards, suppressions, and flags applied per BGC

All guards are applied before final score clamping.

**Primary-metabolism guard (v9.7.7 P0):** if `pm_families` non-empty AND `own_classes ⊆ WEAK_OVERCALL_CLASSES` AND no tier1_diag → suppress AB/AF to their floor values (25, 20). Requires the BGC's own product class to be exclusively weak/over-call — a committed backbone class (nrps/t1pks/lanthipeptide) exempts it.

**`WEAK_OVERCALL_CLASSES`:** nrps-like, terpene, terpene-precursor, saccharide, arylpolyene, other, t2pks, t3pks, pks-like, fatty_acid, redox-cofactor, quinone_isoprenoid_chain

**Mobile-element demotion (#28 v9.7.33):** if `mobile_dominant` AND no corroborated tier1_diag → suppress AB/AF to floor. A corroborated class signal exempts (genuine clusters with incidental flanking mobile genes).

**Mis-anchor guards (v9.7.15):** if KCB anchor lacks its committed class diagnostic AND no tier1_diag:
- Aminoglycoside misanchor (no DOIS synthase): suppress AB to 25
- Polyene misanchor (< 4 PKS_KS): suppress AF to 20
- Enediyne misanchor (no ene_KS): strip the +18 enediyne novelty bonus; add [E-signal] note — no BSL-2 lab-safety flag

**N-05 uncorroborated trigger (v9.7.56+):** a class-defining CCTT trigger on a class-incompatible BGC is marked uncorroborated (`cctt_uncorrob_by_bgc`). Uncorroborated triggers do NOT grant the diagnostic bonus, do NOT exempt primary_metab/misanchor guards, and do NOT floor the tier. Evidence is conserved (the trigger is still recorded for the judgment layer).

**#28 mobile composition corroboration (v9.7.35):** on a MOBILE_DOMINANT region with LOW architecture_class_confidence, all gated class-defining triggers (from `CCTT_CLASS_COMPAT`) are marked uncorroborated.

**T1 self-protection cargo guard (v9.7.37 PC-12):** a T1 self-protection resistance tier on a MOBILE_DOMINANT region WITHOUT class-concordant groups is demoted to `t1_self_protection = False`. Prevents an ICE cargo resistance from floating an impostor BGC to Medium.

#### 2.5 RG-GMCI rescue bonus

```python
rescue_bonus = 0 if primary_flag else (8 if high_rg else 4 if mod_rg else 0)
```

HIGH_RG_GMCI_RESCUE → +8; MODERATE_RG_GMCI_CANDIDATE → +4. Never applied to primary_flag or mobile_flag BGCs.

#### 2.6 Edge penalty

`edge_penalty()` returns **0.0** (neutralized v9.7.84). Empirical rationale: mean base AB for Interior 34.7 vs Edge 35.7 vs FC 35.3 — no truncation signature in base scores. Truncation uncertainty is preserved as `architecture_confidence` (Edge/FC → C/D) and `edge_status` in rationale. The function is retained so call sites are intact.

#### 2.7 Final score clamping and tier assignment

```python
ab  = max(0, min(100, base_ab  + rescue_bonus - effective_penalty * 0.35))
af  = max(0, min(100, base_af  + rescue_bonus - effective_penalty * 0.35))
nov = max(0, min(100, novelty  + rescue_bonus - effective_penalty * 0.20))
best = max(ab, af, nov)
tier = "Exceptional" if best >= 85 else "High" if best >= 70 else "Medium" if best >= 50 else bottom_tier(bgc)
```

For `best < 50`, `bottom_tier(bgc)` returns **Low** when at least one resolved product-class token is outside the governed Inventory allow-list; it returns **Inventory** for allow-listed-only or unresolved regions. This changes the routing label only, not `ab`, `af`, or `nov`.

**`effective_penalty = max(0, edge_penalty - rescue_offset)`**: since edge_penalty = 0, effective_penalty = 0 always. The formula is retained for future re-introduction.

#### 2.8 TIER_1 diagnostic floor

If `tier in ("Low", "Inventory")` AND `tier1_floor` (corroborated triggers OR t1_self_protection):
```python
tier = "Medium"; floored = True
```

Exceptions excluded by `TIER1_FLOOR_EXCLUDED_PREFIXES` (lone halogenase/fluorinase-chlorinase alone does not floor).

#### 2.9 Standing-rule permanent-exclusion downgrade

`standing_rule_for(own_products_text, full_text)` reads from `rules_registry.json` (SSOT). Rules with `action=downgrade AND lead_blocking=True`.

- **Committed-class guard:** if the BGC's own products contain a committed backbone class (anything not in `WEAK_OVERCALL_CLASSES`), standing rules do not apply — **except** `_BYPASS_COMMITTED_CLASS_GUARD = {"NAPAA", "HGLE-KS-PREV-001"}` which fire even on committed-class clusters (annotation-domain flags, not label-only).
- `_OWN_PRODUCTS_ONLY = {"SACCHARIDE"}` — saccharide is checked against own products only, not the full product+MIBiG+KCB text.

Standing-rule downgrade: tier → Inventory; `corrected_rank = None`.

#### 2.10 RiPP fragment floor (F2)

If BGC is in `RIPP_FAMILY_CLASSES` AND (Edge or Full-contig) AND `0 < span_kb < 8.0 (RIPP_FRAGMENT_MAX_KB)` AND tier ∈ {Exceptional, High, Medium}:
```python
tier = "Inventory"; ripp_floored = True
```

A truncated sub-8 kb RiPP fragment with no precursor captured cannot be evaluated as a product.

#### 2.11 `corrected_rank`

Sequential lead rank over rows NOT flagged with `standing_rule_flag`, `primary_metabolism_flag`, or `mobile_element_flag`. Downgraded rows keep raw scores; `corrected_rank = None`.

#### 2.12 Scoring coverage invariant

`assert_full_scoring_coverage(bgcs, triage)` fails loudly if any BGC lacks an ab/af/novelty assessment. Every BGC — including Edge/FC fragments — is scored; no BGC is skipped.

#### 2.13 KCB novelty adjustments

```python
if bgc.kcb_cumulative > 10000: novelty -= 15   # strong KCB → less novel
if bgc.kcb_cumulative is None:  novelty += 5    # no KCB → slightly more novel
if bgc.riq_score < 0.5:         novelty += 10   # low RiQ → novel signal
```

---

### 3. `rules.py` — Standing-Rules Registry

**Source:** `mamey/data/rules_registry.json` (single source of truth)

Every rule has: `id`, `label`, `status` (active | retired | excluded | gate), `action` (downgrade | drop | flag | exclude), `scope`, `rationale`, `date`, `lead_blocking`, `patterns` (compiled regexes), `false_positive_guard`.

**`lint_text(text)`** scans any text for registry hits — used by Sapote to catch retired claims re-entering verdict prose. Returns `Hit` objects with rule_id, status, action, lead_blocking, matched substring, context.

**`has_blocking_hit(text)`** returns True if any hit is lead-blocking.

CLI: `python3 -m mamey.rules <file>` — exit 1 on blocking hit, else 0.

The `false_positive_guard` (list of longer words) prevents substring false-positives: "saccharide" would not incorrectly trigger on "polysaccharide".

---

### 4. `assembly.py` — Assembly Metrics and Tiers

**Corrected BGC count (the canonical formula):**
```python
def corrected_bgc_count(interior, edge, full_contig):
    return round(interior + 0.5 * edge + 0.25 * full_contig, 2)
```

**Assembly tiers:**
```python
interior_pct >= 70 → GOOD
interior_pct >= 45 → MODERATE
interior_pct >= 20 → POOR
interior_pct < 20  → VERY_POOR
None               → UNKNOWN
```

**Assembly sanity check (PC-A2, v9.7.101):** non-blocking heuristic for contamination / co-assembly. Flags `CONTAMINATION_SUSPECT` when per-contig GC standard deviation ≥ 5% (clean genomes ~1-2%; contaminated drafts 7-12%). Flags `ASSEMBLY_SANITY` on strong GC or size deviation from taxon prior (if provided). Returns measured stats; extraction is unaffected.

---

### 5. `precision.py` — KCB Similarity Bands (W26)

**`similarity_band(score)`** — bins a KCB cumulative score into:

| Band | Score range |
|---|---|
| high | ≥ 70 |
| moderate | 40–70 |
| low | 0–40 |
| none | 0 |
| unresolved | None |

**Purpose:** prevents a 2-significant-figure KCB score from implying 2-significant-figure certainty in judgment-facing outputs. Carried on `verdicts.json` alongside the mandatory "similarity, not identity" qualifier.

**`round_identity(pct)`** → nearest 5%. **`round_bitscore(bs)`** → nearest integer.

---

### 6. `fragment_ceiling.py` — Fragment Claim Ceiling

**`fragment_claim_ceiling(product_name, edge_status, length_kb, reference_size_kb)`:**

Downgrade condition: (a) `edge_status ∈ {"Edge", "Full-contig", "FC"}` AND (b) `0 < length_kb < 45.0 (BACKBONE_MIN_KB)` AND (c) `product_name` matches `LARGE_BACKBONE_KEYWORDS` (38 keywords: teicoplanin, vancomycin, glycopeptides, lipopeptides, large polyenes, modular PKS macrolides) OR `reference_size_kb ≥ 45.0`.

The size-ratio path (v9.7.99+) reads real MIBiG cluster sizes from `mibig_reference_index.bacterial.json` and `.fungal.json`, generalizing beyond the keyword list. `reference_size_kb_for(accession)` looks up the size by MIBiG accession (version-suffix tolerant).

When triggered: ceiling → "class-capacity only (fragment too small for named backbone; do not use product name)".

---

### 7. `genus_reference.py` — Nocardia Reference Bank

**Source:** `mamey/data/nocardia/` — 7 published Nocardia genomes scored at engine v1.9.96.

**`STANDING_EXCLUSIONS`** — derived at module load from `rules_registry.json` (PC-A5 SSOT fix, v9.7.101). Previously hardcoded as `{saccharide, fatty_acid, NAPAA, hgle-ks}` — this drifted from the registry (NAPAA now registry-neutral, hgle-ks now "noted/flag" not excluded). Now: `{saccharide, fatty_acid}` + any class whose registry entry has `status=="excluded"` or `action=="drop"`. Used by `cohort_class_heatmap.py` and comparative consumers.

**`assert_comparable_with(current_engine)`** gates AB/AF capacity-score pooling by engine version. Class-prevalence baselines are engine-robust; capacity scores are engine-pinned (a boundary bump → re-score before pooling).

**`genus_core_classes()`** returns classes present in all 7 Nocardia reference strains, excluding the "other" residual bucket (7/7 on "other" reflects "every strain has unclassified loci", not shared biosynthesis).

---

### 8. `class_architecture.py` — Architecture-Based Capacity Layer

**Source:** `class_architecture.py:classify_architecture`

Classifies a BGC by PKS/NRPS module counts and tailoring constellation into a claim-safe class-capacity label. Complements the CCTT T43 keyword layer (which covers ~30% of antimicrobial classes); architecture classification is annotation-robust because it survives gene-symbol divergence.

Key capacity calls (selected):
- ≥6 NRPS-C + halogenase + glycosyltransferase → **glycopeptide** (HIGH)
- ≥3 PKS_KS + polyene/macrolide products + ≥1 thioesterase → **polyene macrolide** (HIGH)
- Trans-AT KS + FkbH → **trans-AT PKS** (HIGH)
- 1 PKS_KS + 1 NRPS adenylation (fused or same operon) → **diketopiperazine/CDPS** (MEDIUM)
- ≥2 NRPS-C, no PKS_KS, + siderophore product label → **NRP-metallophore** (HIGH)

**Multi-class guard:** ≥3 distinct real biosynthetic product classes (excluding saccharide/other/terpene-precursor) → capacity = "complex hybrid locus; class-capacity unresolvable by single label" (MEDIUM).

`ArchitectureCall.as_capacity_line()` returns: "BGCnnn: biosynthetic capacity consistent with <capacity> [<confidence>] — <evidence>"

---

### 9. `boundary_audit.py` — Deterministic↔Judgment Boundary Checker

**Source:** `boundary_audit.py:audit_payloads`

Diffs `<strain>_records.json` (BGCRecord side) against `<strain>_verdicts.json` (TriageRecord side) and reports seven failure classes:

| Check | What it catches |
|---|---|
| DROPPED | BGC in records with no verdict — the AS-XXX silent-omission class |
| ORPHAN | Verdict for a bgc_id the extractor never produced |
| STRAIN | The two payloads describe different strains (copy-paste bus error) |
| TIER | Verdict lead_tier / claim_confidence outside known vocabulary |
| DOWNGRADE | Standing-rule / primary-metab verdict that kept a corrected_rank |
| EXCLUSION | BGC products trip a lead-blocking excluded rule but verdict shows no downgrade |
| RETIRED | BGC carrying a retired rule ID |

CLI: `python3 -m mamey.boundary_audit STRAIN_records.json STRAIN_verdicts.json` — exit 1 on any problem.

**Relation to existing tools:** complements `sapote_judgment_receipt.py` (count-level completeness) and `evidence_conservation_audit.py` (source→package conservation). The genuinely new checks are DOWNGRADE and EXCLUSION.

---

### 10. `precision.py` — Parallel KCB Band Implementations (Patch Flag)

**Patch flag B-F1 (new):** Two parallel KCB similarity-band implementations exist:
1. `precision.py:similarity_band` — used by `serialize.py` for `verdicts.json`
2. Inline banding in `scoring.py:preferred_kcb_anchor` and `chatgpt_commands.py:mode_b_command` — used for Mode B card labels

The `precision.py` bands use numeric thresholds (≥70 = high, ≥40 = moderate, >0 = low). The inline banding in `chatgpt_commands.py` uses different thresholds and labels: >100k → "very high", >50k → "high", >5k → "moderate", >0 → "low". These are on different scales (percent vs raw bitscore). A reviewer comparing a Mode B card's band to the `verdicts.json` band may see a discrepancy. **Action:** confirm which scale each consumer receives and whether the thresholds are intentionally different.

---

*Mamey engine v1.9.98 · Bundle v9.7.117*  
*All classification rules, weight constants, and formula values cited from source.*
## Volume II — Cluster C: KCB / RiQ Extraction and ClusterBlast Gene Correspondence

**Source modules:** `mamey/antismash_evidence.py` (1,081 lines) · `mamey/clusterblast_genes.py` (317 lines)  
**Engine:** Mamey v1.9.98 · Bundle: v9.7.117  
**Affiliation:** 

---

### Preamble

KCB = similarity, not identity. Every number extracted by these modules is a BLAST/HMMER similarity score against a reference database. No extracted value constitutes evidence of production or compound identity.

`antismash_evidence.py` is the primary evidence-extraction layer: it reads antiSMASH's TXT clusterblast files (primary KCB source) and optionally the JSON (secondary, for RiQ and substrate predictions), surfaces the TIGRFAM diagnostics that live only in the JSON, and applies the extracted evidence to `BGCRecord` objects. `clusterblast_genes.py` adds a per-gene correspondence layer (query→reference gene mapping with %identity, %coverage, BLAST score) that the base KCB extraction discards.

---

### C.1 Streaming architecture

**Source:** `antismash_evidence.py:_STREAM_JSON_MODE`, `antismash_evidence.py:_STREAM_JSON_MIN_BYTES`, `antismash_evidence.py:_should_stream`, `antismash_evidence.py:_iter_records`

The module uses a size-adaptive streaming decision to avoid the ~1 GB peak memory that occurs when json.loads-ing a full antiSMASH JSON for a large actinomycete genome:

```python
_STREAM_JSON_MIN_BYTES = 20 * 1024 * 1024   # 20 MB threshold

def _should_stream(zf, name):
    if not _HAVE_IJSON:
        return False
    if _STREAM_JSON_MODE in ("0","off","false","no","never"):
        return False
    if _STREAM_JSON_MODE in ("1","on","true","yes","always"):
        return True
    # auto (default): stream >= 20 MB; full-load < 20 MB
    return zf.getinfo(name).file_size >= _STREAM_JSON_MIN_BYTES
```

The 20 MB threshold cleanly separates real genome JSONs (55–130 MB → stream) from test fixtures (KB–low MB → full-load). The decision is per-file and consistent: both `_iter_records` and `_parse_json_bounded` call `_should_stream` for the same file, so they always agree on mode. The env var `MAMEY_STREAM_JSON` can force either path.

Streaming uses `ijson.items(stream, "records.item", use_float=True)`, yielding individual record dicts without materialising the full document. The `use_float=True` flag is required for byte-identical output with the `json.loads` path (ijson defaults to `Decimal` for JSON numbers, which are not `json.dumps`-serialisable and would crash package write).

ijson is loaded under two names for two code paths:
- `_ijson` / `_HAVE_IJSON` — the record-streaming path (`_iter_records`)
- `ijson` (top-level) — the leaf-streaming path (`_parse_json_bounded`)

If the system ijson is absent, a vendored pure-Python fallback is loaded from `mamey/_vendor/ijson/`. If both are absent, both paths degrade gracefully: `_should_stream` returns False, and `_parse_json_bounded` logs an advisory and falls back to the off mode.

---

### C.2 JSON evidence modes and capacity limits

**Source:** `antismash_evidence.py:JSON_MODE_DEFAULT`, `antismash_evidence.py:BOUNDED_MAX_RECORDS`, `antismash_evidence.py:BOUNDED_MAX_RECORDS_STREAMING`, `antismash_evidence.py:BOUNDED_MAX_JSON_BYTES`, `antismash_evidence.py:BOUNDED_MAX_JSON_BYTES_STREAMING`, `antismash_evidence.py:FULL_MAX_JSON_BYTES`

Three JSON evidence modes are available:

```
"off"      — TXT clusterblast only; JSON never opened. Default-safe for any genome.
"bounded"  — Stream JSON with ijson; extract only KCB/RiQ/MIBiG leaves; caps apply.
             Falls back to "off" if ijson unavailable (recorded in json_skipped).
"full"     — Legacy: json.loads the whole file and flatten. Refuses files > 20 MB.
```

The default is `"bounded"` (`JSON_MODE_DEFAULT = "bounded"`).

Capacity constants:

| Constant | Value | Applies when |
|---|---|---|
| `BOUNDED_MAX_RECORDS` | 5,000 | Bounded mode, no streaming parser |
| `BOUNDED_MAX_RECORDS_STREAMING` | 200,000 | Bounded mode, streaming parser present |
| `BOUNDED_MAX_JSON_BYTES` | 25,000,000 (25 MB) | Bounded mode, no streaming parser |
| `BOUNDED_MAX_JSON_BYTES_STREAMING` | 250,000,000 (250 MB) | Bounded mode, streaming parser present |
| `FULL_MAX_JSON_BYTES` | 20,000,000 (20 MB) | Full mode hard refusal |

The non-streaming caps were sized against the retired 25 MB legacy regime; the streaming caps are sized against real actinomycete JSONs (55–90 MB typical). The record cap in bounded streaming mode (200,000) is sized to never truncate RiQ on large genomes.

---

### C.3 Single-pass record extraction

**Source:** `antismash_evidence.py:_run_record_extractors`, `antismash_evidence.py:_extract_record_evidence`

Rather than four independent full-JSON parses (each ~1 GB peak on large genomes), all JSON record-level extractions are done in a single shared pass:

```python
def _run_record_extractors(zip_path, handlers):
    # handlers: list of (handler_fn, out_container)
    # One pass; per-handler try/except isolates failures
    for rec in _iter_records(zf, name):
        for fn, out in handlers:
            try:
                fn(rec, name, out)   # never aborts siblings on failure
            except Exception:
                continue
```

Five handlers run in one pass: `_tigrfam_from_rec`, `_nrps_pks_from_rec`, `_active_site_from_rec`, `_product_class_from_rec`, `_ripp_from_rec`. Whether all five run in a given call depends on the flags passed to `_extract_record_evidence`:

- `want_tigrfam=True` — add the TIGRFAM handler (used by the CLI path that feeds the GBK/Pfam merge)
- `include_extras=True` — add the four JSON-evidence handlers (used when json_mode != 'off')

If neither is set, no pass runs at all.

---

### C.4 KCB extraction from TXT — primary source

**Source:** `antismash_evidence.py:_parse_txt_evidence`

The TXT clusterblast/knownclusterblast files are the primary KCB source — fast regardless of genome size, no streaming required. The parser processes each BGC's TXT with a block-splitting strategy introduced in v1.9.2+ to fix two old bugs: (1) the previous parser treated any line containing "score" as numeric evidence and incorrectly extracted contig accession tails (e.g. `CP073042.1 → 73042.1`) as cumulative scores; (2) it summed protein hits across all reference clusters rather than reading the count from the best single cluster.

**Block splitting:**

```python
blocks = re.split(r"\n>>\s*\n", text)
## Each block is one subject-cluster section in the antiSMASH ClusterBlast output
```

**Best block selection (highest cumulative score):**

```python
for block in blocks:
    score_m = re.search(
        r"Cumulative\s+BLAST\s+score:\s*([0-9][0-9,]*(?:\.\d+)?)", block, re.I)
    prot_m = re.search(
        r"Number\s+of\s+proteins\s+with\s+BLAST\s+hits\s+to\s+this\s+cluster:\s*(\d+)", block, re.I)

best = max(block_records, key=lambda r: r["score"])
```

Only the best (highest cumulative BLAST score) block's protein-hit count is taken. This means `kcb_protein_hits` always reflects the top-scoring reference cluster, not an aggregate.

**Significant hits section:**

```python
m_hit = re.match(r"\s*(\d+)\.\s+(BGC\d{7,}(?:\.\d+)?)\s+(.+?)\s*$", line)
## Captures: rank, BGC accession, product name
```

The significant hits section (`Significant hits:` → `Details:`) is parsed separately to obtain the MIBiG accession and compound name for the rank-1 reference. This becomes `bgc.kcb_top`, formatted as `"{accession} | {product} | knownclusterblast #{rank}"`.

**Region key construction:**

```python
## Standard region GBK: <contig>.region001.gbk → "{contig}_c{region}"
m = re.match(r"(.+?)\.region0*(\d+)\.[^.]+$", base, re.I)
## ClusterBlast TXT: <contig>_c1.txt → "{contig}_c{region}"
m = re.match(r"(.+?)_c0*(\d+)\.txt$", base, re.I)
```

The stable region key includes the full contig identifier because antiSMASH restarts the `_cN`/`regionNNN` counter on every contig. A bare region number is not a valid key for multi-contig assemblies and is only used as a last resort for single-contig assemblies.

---

### C.5 Resolved MIBiG provenance — the `kcb_top` overwrite

**Source:** `antismash_evidence.py:apply_evidence_to_bgcs`

All BGC fields are initialised to `"UNRESOLVED"` before evidence is applied. This is the fail-closed default: if the evidence application fails or finds nothing, the BGC carries explicit `"UNRESOLVED"` strings rather than None or empty, so downstream claim-safety checks can distinguish "no evidence found" from "evidence not yet applied."

The `kcb_top` field goes through a two-step overwrite:

```python
## Step 1: raw rank-1 candidate line from the TXT (may be a genome self-hit)
bgc.clusterblast_top = candidate_lines[0][:120]
bgc.kcb_top = candidate_lines[0][:120]

## Step 2: if a MIBiG significant-hits line exists, overwrite kcb_top with the
## compound identity (not the self-hit genome accession)
if first_reference:
    bgc.kcb_top = f"{accession} | {product} | knownclusterblast #{rank}"
    bgc.parse_confidence = "HIGH"
```

The raw rank-1 line is preserved in `bgc.clusterblast_top` for audit purposes (gates and claim-safety checks that need the raw value can still read it). The overwrite ensures that for clusters in the KCB database where antiSMASH's top hit is its own genome, the compound-name-carrying MIBiG reference line surfaces in `kcb_top` rather than the genome self-hit.

**KCB cumulative score and protein hits:**

```python
bgc.kcb_cumulative = max(score_vals)      # best across all TXT records for this region key
bgc.kcb_protein_hits = max(prot_hits)     # ditto
```

Both take the maximum across all records assigned to the same region key. In practice a region typically has one TXT, but the max handles cases where multiple TXT files contribute to the same key.

**Product provenance hierarchy:**

| `closest_product_provenance` | Condition | `parse_confidence` |
|---|---|---|
| `MIBIG_REFERENCE_LINE` | Significant-hits line found with accession + product | HIGH |
| `KCB_TOP_FIELD` | No reference line, but `kcb_top` set from candidate lines | MEDIUM |
| `UNRESOLVED` | No evidence records for this region key | LOW |

The fragment ceiling is applied at both `MIBIG_REFERENCE_LINE` and `KCB_TOP_FIELD` provenance levels (via `_apply_fragment_ceiling`). At LOW provenance, no ceiling is applied because there is no product name to qualify.

---

### C.6 KCB recycling audit

**Source:** `antismash_evidence.py:_kcb_recycling_audit`

After evidence is applied, a structural sanity check flags suspicious patterns that indicate parser or keying errors. Two failure modes:

**1. Score recycling:**

```python
pairs = Counter((b.kcb_cumulative, b.kcb_protein_hits) for b in bgcs
                if b.kcb_cumulative is not None or b.kcb_protein_hits is not None)

## Fail if: >= 20 assigned BGCs AND distinct pairs <= max(3, total // 5)
if total >= 20 and distinct <= max(3, total // 5):
    status = "FAIL_SUSPICIOUS_RECYCLING"
```

The threshold `max(3, total // 5)` requires at least one distinct score pair per five BGCs. A run where 40 BGCs all carry the same (cumulative_score, protein_hits) pair would trigger this (40 total, 1 distinct, threshold = max(3, 8) = 8). This guards against the region-key misalignment that previously recycled one BGC's KCB bundle across the whole strain.

**2. Accession-tail mismatch:**

```python
## Detect if kcb_cumulative suspiciously equals the numeric suffix of the contig accession
m = re.search(r"[A-Za-z]+0*([0-9]+(?:\.[0-9]+)?)$", contig)
if abs(float(m.group(1)) - float(score)) < 1e-6:
    → FAIL_ACCESSION_TAIL_MISPARSE
```

This catches the specific bug class where the old parser extracted `CP073042.1 → 73042.1` as a cumulative score. The check compares the numeric tail of the contig accession string against the recorded score to within floating-point epsilon.

---

### C.7 RiQ region mapping

**Source:** `antismash_evidence.py:_parse_json_bounded`, `antismash_evidence.py:riq_label`

RiQ (Region-to-region Quotient) scores are extracted from the JSON's `region_to_region.RegionToRegion_RiQ.scores_by_region` subtree. Extraction logic:

```python
## Capture: scores_by_region leaf AND value in [0.0, 1.0] range
if ("scores_by_region" in prefix.lower()
        and isinstance(value, (int, float, Decimal))
        and 0.0 <= float(value) <= 1.0):
    m = re.search(r"by_region\.(\d+)\.", prefix)
    if m and current_rec_id:
        rk = f"{current_rec_id}_c{int(m.group(1))}"
        riq_by_region[rk] = max(prev, float(value)) if prev is not None else float(value)
```

Key design decisions:
- **RiQ is captured before the record cap** (`matched >= cap`): the cap truncates bulky clusterblast leaf strings, but a large genome should never lose RiQ scores because they accumulate early in the JSON structure. RiQ is a small number of (score, region) pairs; the clusterblast strings are the volume.
- **Best (max) RiQ per region key** is retained when multiple scores appear for the same region (the surrounding subtree carries coordinates and bitscores alongside the genuine 0–1 ratio; only the ratio is accepted).
- **`_riq` suffix filter**: hit-detail strings under `*_RiQ` subtree paths (coordinate matrices, similarity matrices) are skipped to prevent flooding the record cap with unused similarity data. KCB/MIBiG compound-name strings, which live outside the `*_riq` subtree, still pass.
- Mapped RiQ is folded into `evidence["by_region"]` so the per-BGC assignment loop in `apply_evidence_to_bgcs` reads it without a separate code path.

**RiQ label thresholds** (`antismash_evidence.py:riq_label`):

```python
if score >= 0.85:  return "Likely known"
if score >= 0.50:  return "Possibly novel / structural variant"
                   return "Potentially novel"
```

These three tiers were established in Volume I §4 and are sourced here for completeness. The labels are capacity-level signals for routing triage; they are not manuscript claims.

---

### C.8 TIGRFAM diagnostic extraction

**Source:** `antismash_evidence.py:extract_tigrfam_hits`, `antismash_evidence.py:DIAGNOSTIC_TIGRFAM`, `antismash_evidence.py:_tigrfam_from_rec`

TIGRFAM hits live in `records[].modules["antismash.detection.tigrfam"].hits[]` in the JSON — not in the GBK `sec_met_domain` qualifiers. This means they were silently dropped by the GBK-only extraction path until v9.4.1 (the `tigrfix` defect). Only the diagnostics in `DIAGNOSTIC_TIGRFAM` are surfaced; the full TIGRFAM set is large and mostly housekeeping.

```python
DIAGNOSTIC_TIGRFAM = {
    "TIGR01454": ("ansamycin",         "AHBA_synth_RP: AHBA synthesis associated protein",   True),
    "TIGR03604": ("thiopeptide",       "TOMM/thiopeptide cyclodehydratase",                   True),
    "TIGR03828": ("enediyne",          "ene_KS: enediyne polyketide synthase",                True),
    "TIGR04186": ("nucleoside",        "NikJ-family nucleoside antibiotic enzyme",            True),
    # §8 diagnostic-combination markers (v9.6.15-tigr8):
    "TIGR04462": ("enduracididine",    "enduracididine-type NRPS marker (lipid II inhibitor)", True),
    "TIGR04460": ("enduracididine",    "enduracididine-type NRPS marker (lipid II inhibitor)", True),
    "TIGR03550": ("F420_polyketide",   "F420-embedded polyketide marker",                     True),
    "TIGR03551": ("F420_polyketide",   "F420-embedded polyketide marker",                     True),
    "TIGR03620": ("F420_polyketide",   "F420-embedded polyketide marker",                     True),
    "TIGR04363": ("lanthipeptide_FxLD","FxLD class-I lanthipeptide marker",                   True),
    "TIGR04364": ("lanthipeptide_FxLD","FxLD class-I lanthipeptide marker",                   True),
    "TIGR01181": ("glyco_T2PKS",       "glycosylated T2PKS marker",                           True),
    "TIGR02353": ("NAPAA_marker",      "ε-poly-L-lysine synthetase — NAPAA (neutral)",         False),
}
```

TIGR02353 (NAPAA) is `tier1_diagnostic = False` — it is present for §8 combo detection only and is not weighted as a tier-1 diagnostic signal. All other entries are `True`.

TIGRFAM hits are keyed by `f"{rec_id}_c1"` (contig + first region) because TIGRFAM hits are not region-scoped in the JSON. The downstream `apply_evidence` step resolves these by locus tag rather than by strict region key.

The `_TIER1_DOMAIN_NAMES` frozenset governs tier-1 classification in `extract_gbk_pfam_hits` and includes all TIGRFAM accessions above (minus TIGR02353):

```python
_TIER1_DOMAIN_NAMES: frozenset = frozenset({
    "YcaO", "PF02624", "TOMM_dh", "PF04825",
    "FkbH", "PF04113", "Diels_aldr", "PF13570",
    "PEP_mutase", "PF05042", "Radical_SAM", "PF04055",
    "LANC_like", "PF05147", "DUF4135", "PF13575",
    "HMGL-like", "PF00682", "AMP-binding", "PF00501",
    "lant_dehyd_N", "lant_dehyd_C", "DUF4218", "PF13927",
    "Trp_halogenase", "PF04820",
    # TIGRFAM diagnostics (v9.4.1-tigrfix + v9.6.15-tigr8):
    "TIGR01454", "TIGR03604", "TIGR03828", "TIGR04186",
    "TIGR04462", "TIGR04460",
    "TIGR03550", "TIGR03551", "TIGR03620",
    "TIGR04363", "TIGR04364",
    "TIGR01181",
})
```

---

### C.9 sec_met_domain Pfam hits — the GBK extraction layer

**Source:** `antismash_evidence.py:DIAGNOSTIC_SEC_MET_DOMAINS`, `antismash_evidence.py:_SEC_MET_RE`, `antismash_evidence.py:extract_gbk_pfam_hits`

antiSMASH stores its internal HMMER results as `/sec_met_domain` qualifiers in every region GBK:

```
e.g. "YcaO (E-value: 3.2e-64, bitscore: 206.5, seeds: 57, tool: rule-based-clusters)"
```

The parser:

```python
_SEC_MET_RE = re.compile(
    r'^([A-Za-z0-9_\-\.]+(?:\s+[A-Za-z0-9_\-\.]+)?)\s*\(E-value:\s*([\d.e+\-]+)'
    r'(?:,\s*bitscore:\s*([\d.]+))?'
)
```

Extracts domain name, e-value, and bitscore (bitscore is optional; old antiSMASH versions omit it). The domain name is looked up in `DIAGNOSTIC_SEC_MET_DOMAINS` for a human-readable description and Pfam accession. If not in the dict, `pfam_acc` and `description` are None — the hit is still recorded but without annotation.

`DIAGNOSTIC_SEC_MET_DOMAINS` covers 34 named domains including the core assembly-line markers (PKS_KS, AMP-binding, Condensation, Thioesterase, FkbH, Diels_aldr), class-specific markers (LANC_like, DUF4135, YcaO, PEP_mutase, Trp_halogenase), and the carrier domain (PP-binding / PF00550). TIGR02353 (NAPAA ε-poly-L-lysine synthetase) is present in the dict with an explicit housekeeping note.

---

### C.10 ClusterBlast per-gene correspondence layer

**Source:** `clusterblast_genes.py:parse_clusterblast_gene_map`, `clusterblast_genes.py:_parse_hit_rows`, `clusterblast_genes.py:ReferenceBlock`

The standard KCB extraction (`apply_evidence_to_bgcs`) retains only the cumulative score and protein-hit count for the best reference cluster. `clusterblast_genes.py` parses the full 6-column BLAST hit table from each reference block, retaining per-gene correspondence:

**Hit table columns (tab-separated):**

```
query_gene  subject_gene  %identity  blast_score  %coverage  evalue
```

Parsing:
```python
def _parse_hit_rows(block):
    m = _HIT_TABLE_RE.search(block)   # "Table of Blast hits.*?\n(.*)"
    for line in m.group(1).splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        try:
            pid = float(parts[2])   # %identity: non-numeric = header/blank → skip
        except ValueError:
            continue
        # columns: query, subject, %id, blast_score, %coverage, evalue
```

**Per-gene best hit aggregation:**

```python
top_refs = 5   # default; how many top-ranked references contribute to per-gene best-hit search

## For each query CDS, select the hit with the highest blast_score across top_refs references
if cur is None or (h.blast_score or 0) > (cur["blast_score"] or 0):
    best[h.query_gene] = cand
```

The full reference block set is parsed; only the best-hit aggregation caps at `top_refs`. The output is sorted by trailing gene number (`_gene_sort_key`) so the per-gene table reads in 5'→3' CDS order.

Two deliverables are produced per BGC:
- `per_gene_best_hit`: for each query CDS, its single best reference-gene hit across the top-5 references
- `reference_correspondence`: for each of the top-5 references, the complete ordered query→subject gene map

---

### C.11 Functional role profiling for rescue complementarity

**Source:** `clusterblast_genes.py:rescue_functional_complementarity`, `clusterblast_genes.py:FRC_ASYMMETRY_MIN`, `clusterblast_genes.py:FRC_ACCESSORY_CEILING`, `clusterblast_genes.py:FRC_CORE_FLOOR`

A contig-rescue pair (two BGC fragments hypothesised to be split from one cluster) is only credible when the two fragments are functionally complementary rather than both carrying the same core genes. The complementarity score uses the relative core fraction rather than a binary has-core test:

```python
core_fraction = core_count / (core + tailoring + transport + regulatory)
## (ignores "other" as uninformative)
```

**Role classification** (`_role_of`): gene_kind qualifier + text blob from gene_functions + sec_met_domains + product:

```
"biosynthetic" gene_kind OR any(_CORE_DOMAIN_HINTS) → "core"
any(_TRANSPORT_HINTS)                               → "transport"   (checked before regulatory)
any(_REGULATORY_HINTS) OR "regulatory" gene_kind   → "regulatory"
"biosynthetic-additional" OR any(_TAILORING_HINTS) → "tailoring"
"transport" gene_kind                               → "transport"
else                                                 → "other"
```

**Complementarity decision thresholds (calibrated on AS-XXX HIGH pairs):**

```python
FRC_ASYMMETRY_MIN   = 0.20   # min core-fraction gap to call split complementary
FRC_ACCESSORY_CEILING = 0.30 # a fragment with core-fraction <= this is accessory-dominated
FRC_CORE_FLOOR      = 0.35   # both sides above this (and similar) => both carry a real core

gap = hi_core_fraction - lo_core_fraction

if gap >= 0.20 AND lo <= 0.30:           → COMPLEMENTARY  (core fragment + accessory fragment)
elif fa >= 0.35 AND fb >= 0.35
     AND gap < 0.20:                     → BOTH_CORE       (paralogous cores, not a split)
elif hi <= 0.30:                         → ACCESSORY_ONLY  (two tailoring fragments, weak rescue)
else:                                    → AMBIGUOUS
```

The code comment explicitly notes these thresholds were calibrated on the AS-XXX HIGH pairs (genuine paralogs sit at core-fraction ~0.4–0.55 on both sides; real splits show one fragment accessory-dominated). The thresholds are engineering calibration, not literature-derived constants.

The output `functional_rescue_class` feeds the RG-GMCI ranking (Volume I §7), where COMPLEMENTARY > BOTH_CORE > ACCESSORY_ONLY > AMBIGUOUS in the rescue priority ordering. The `functional_rescue_class` is also the first sort key in the `mamey ingest-receipts` output per the SESSION_START_MANIFEST §0.5 notes.

---

### C.12 Data-driven RiPP extraction

**Source:** `antismash_evidence.py:_ripp_from_rec`, `antismash_evidence.py:_RIPP_MODULES`

Prior to v9.7.99, RiPP extraction was hardcoded to four families: `("lanthipeptides", "lassopeptides", "sactipeptides", "thiopeptides")`. The v9.7.99 fix made extraction data-driven, iterating every `antismash.modules.<family>` key in the modules dict that carries a non-empty `motifs` dict:

```python
for mod_key, mod_val in modules.items():
    if not mod_key.startswith("antismash.modules."):
        continue
    motifs = mod_val.get("motifs", {})
    if not isinstance(motifs, dict) or not motifs:
        continue
    # process any family carrying a motifs dict
```

Non-RiPP modules (NRPS/PKS, active-site finder, etc.) do not carry a `motifs` dict with a `core` key and are naturally excluded by the `if not core: continue` guard. The old `_RIPP_MODULES` tuple is retained as a documentation reference but is no longer an extraction allowlist.

Core sequence extraction tries two keys for backward compatibility: `motif.get("core") or motif.get("core_sequence")`. A motif with neither is skipped.

---

### C.13 Product-class prediction coordinate matching

**Source:** `antismash_evidence.py:_product_class_from_rec`

The T2PKS and terpene protocluster predictions include `start` and `end` coordinates (added in v9.7.87, P-10). The rationale from the code comment: on a closed single-contig genome, the contig key collapses all predictions to one bucket and would mislabel every BGC on that contig with every prediction. Coordinate overlap is the correct granularity for matching a prediction to the BGC it actually falls in. This field was not present in older antiSMASH output; the caller must handle `None` start/end gracefully.

---

### C.14 Concerns flagged for the bug log

1. **`riq_score` takes first element, not max** (`antismash_evidence.py:apply_evidence_to_bgcs`, line 1064): `bgc.riq_score = float(riq_vals[0])` takes the first RiQ value from the list rather than the maximum. For a region key that appears in multiple records (unusual but possible when both TXT and JSON contribute a `riq_score` for the same key), this is not guaranteed to be the best value. The RiQ computation in `_parse_json_bounded` does take the max per region key before folding into `by_region`, so in the typical single-JSON-per-region case this is harmless. But in a degenerate case where both JSON bounded mode and some future TXT-derived RiQ contribute to the same `recs` list, the first-element read could miss a higher value.

2. **`transport` priority over `regulatory` in `_role_of`** (`clusterblast_genes.py`, lines 234–244): The `_TRANSPORT_HINTS` check runs before the `_REGULATORY_HINTS` check. A gene with both "transporter" and "regulator" in its annotation text will be classified as `transport`, not `regulatory`. This is likely intentional (transporters are operationally more important for the rescue complementarity metric), but the priority is implicit rather than documented.
## Volume II — Cluster D: Compound-Class Annotation, Domain-Level Enrichment, and DKP/CDPS Detection

**Source modules:** `mamey/compound_class.py` (333 lines, v9.7.86) · `mamey/domain_level.py` (537 lines, v9.7.89) · `mamey/dkp_cdps.py` (230 lines)  
**Engine:** Mamey v1.9.98 · Bundle: v9.7.117  
**Affiliation:** 

---

### Preamble

All three modules are annotation and capacity layers, not scoring engines. The distinction is precise and worth stating up front: `compound_class.py` is the one module in this cluster that *does* carry a scored consequence for a small number of well-anchored chemotypes, but even there the score is a routing prior, not biological proof. `domain_level.py` and `dkp_cdps.py` are annotation-only. No module in this cluster makes product-identity claims.

---

### D.1 compound_class.py — chemotype annotation

#### D.1.1 What it is and what it is not

**Source:** `compound_class.py` module docstring

This module is an **annotation layer**, not a general scoring engine. It records the chemotype the BGC's own evidence is consistent with — polyene macrolide, anthracycline, ionophore, tetracycline, and so on — as structured fields on the BGC record. The majority of chemotypes are **annotate-only** (record the label + evidence trail, zero score change). Only three chemotypes carry a scored consequence, and those are well-calibrated against 32 MIBiG reference clusters.

#### D.1.2 Evidence priority

**Source:** `compound_class.py:annotate_bgc`, `compound_class.py:_own_evidence_text`

Three evidence levels in descending priority:

```
1. Specific resolved product name  — closest_candidate_kcb_product + bgc.products
   matched against curated term sets. Raw kcb_top is NEVER used here (P-7 clean).

2. antiSMASH t2pks.product_classes — machinery-based class prediction from the JSON
   (only when JSON evidence is on and the resolved product name did not resolve).

3. products only                   — coarse fallback via term matching.
```

The own-evidence text function:

```python
def _own_evidence_text(bgc) -> str:
    parts = list(bgc.products or [])
    rp = bgc.closest_candidate_kcb_product or ""
    if rp and rp != "UNRESOLVED":
        parts.append(rp)
    return " ".join(parts).lower()
```

The explicit guard `rp != "UNRESOLVED"` prevents the literal string "UNRESOLVED" from ever appearing in the match text. Raw `kcb_top` is excluded by design: it can contain a genome self-hit or a first-rank ClusterBlast line that doesn't name a compound, and using it here would break the P-7 own-evidence boundary.

#### D.1.3 Chemotype taxonomy

**Source:** `compound_class.py:CHEMOTYPES`

17 named chemotypes defined as frozen dataclass instances, ordered by specificity (more specific / higher-consequence first; first match wins in term scanning):

```
Scored chemotypes (well-anchored, carry explicit axis + weight):
  polyene_macrolide     → pharmacology = antifungal     → scored ("af", 22)
  anthracycline         → pharmacology = cytotoxic       → scored ("anthracycline", 0)
  ionophore             → pharmacology = antibacterial   → scored ("ab", 14)

Annotate-only cytotoxic chemotypes (record + cytotoxic_flag=True, no score):
  diazofluorene         (kinamycin, lomaiviticin)
  cytotoxic_aromatic_other  (fredericamycin, azinomycin)

Annotate-only antibacterial / aromatic:
  tetracycline, angucycline, pyranonaphthoquinone, ansamycin, macrolide_other,
  aromatic_t2pks_other

Annotate-only new families (LOW confidence, 1-ref labels):
  glycopeptide, phenazine, nucleoside_antibiotic, halogenated_phenolic, prenylated_indole
```

The anthracycline `scored` tuple is `("anthracycline", 0)` — the weight is zero. Anthracycline gets its own scored axis purely for routing (cytotoxic/antitumor category, flagged off the clean antibacterial board), not for scoring the AB or AF axis. This is an intentional design choice: anthracyclines are DNA-intercalating cytotoxins, not antibacterials in the sense targeted by MRSA screens.

The ionophore entry has `single_reference=True` and `confidence="MODERATE"` — the code comment notes one reference calibration point. This is explicitly documented in the module header: "conservative, single-reference-flagged."

Confidence levels per chemotype:

| Tier | Examples | Reference count |
|---|---|---|
| HIGH | polyene_macrolide, anthracycline | ≥3 references calibrated 2026-06-19 |
| MODERATE | tetracycline, angucycline, ionophore | moderate evidence |
| LOW | glycopeptide, phenazine, nucleoside_antibiotic | 1-ref labels |

#### D.1.4 Term matching and exclusion traps

**Source:** `compound_class.py:_chemotype_by_terms`, `compound_class.py:PIGMENT_EXCLUSION`, `compound_class.py:NONLEAD_EXCLUSION`

Term matching is substring (lowercased), first chemotype in the CHEMOTYPES tuple that has a matching term wins:

```python
for ct in CHEMOTYPES:
    if ct.name == "polyene_macrolide" and pigment:
        continue   # arylpolyene pigment trap
    for term in ct.terms:
        if term in text:
            return ct
```

Two exclusion guards run before term matching:

**Hard non-lead exclusion** (abstain entirely, return empty annotation):
```python
NONLEAD_EXCLUSION = ("patulin", "solanapyrone", "yanuthone", "eicosapentaenoic",
                     "fatty acid", "spore pigment")
```
Fungal mycotoxins, phytotoxins, and primary metabolites. If any of these appear in the own-evidence text, `annotate_bgc` returns immediately with `evidence_source = "none"`.

**Polyene-macrolide pigment trap** (skip this specific chemotype, fall through to the next):
```python
PIGMENT_EXCLUSION = ("arylpolyene", "aryl-polyene", "ape ", "flaviolin",
                     "spore pigment", "spore-pigment", "whie", "pentangular polyphenol",
                     "tetracenomycin")
```
Only blocks the polyene_macrolide chemotype, not all chemotypes. An arylpolyene-typed BGC can still match a different annotate-only chemotype if evidence warrants. The `ape ` token (trailing space) is deliberately narrow — it targets the "APE KS2" / "aryl-polyene-specific" antiSMASH shorthand without catching unrelated strings.

#### D.1.5 antiSMASH class map and anthracycline priority

**Source:** `compound_class.py:ANTISMASH_CLASS_MAP`, `compound_class.py:_chemotype_from_antismash`

```python
ANTISMASH_CLASS_MAP = {
    "anthracycline":      "anthracycline",
    "tetracycline":       "tetracycline",
    "angucycline":        "angucycline",
    "aureolic acid":      "aromatic_t2pks_other",
    "pyranonaphthoquinone":"pyranonaphthoquinone",
}
```

When antiSMASH's T2PKS prediction returns a list of candidate product classes, anthracycline wins if present — it is the most structurally and clinically consequential call in the set, and a real anthracycline cluster can legitimately resemble others:

```python
if "anthracycline" in pcs:
    target = "anthracycline"
else:
    target = next((ANTISMASH_CLASS_MAP[p] for p in pcs if p in ANTISMASH_CLASS_MAP), None)
```

An antiSMASH-class-only call (no specific MIBiG compound name resolved) is stepped down one confidence tier: a chemotype that would be HIGH from a resolved product name becomes MODERATE when derived from the antiSMASH class set alone (`evidence_source == "antismash_t2pks" and ct.confidence == "HIGH" → "MODERATE"`).

#### D.1.6 Scored weight values

The three scored chemotypes and their axis/weight pairs, sourced directly from the `CHEMOTYPES` tuple:

| Chemotype | Axis | Weight | Note |
|---|---|---|---|
| polyene_macrolide | af | **22** | Calibrated, 3 refs; arylpolyene exclusion mandatory |
| anthracycline | anthracycline | **0** | Routing flag only; no AF/AB score increment |
| ionophore | ab | **14** | Single reference; conservative |

Weight 22 for polyene_macrolide places it as the highest single compound-class bonus in the AF scoring axis — larger than most CCTT trigger bonuses. This is intentional: a confirmed polyene macrolide KCB anchor is strong antifungal evidence. The calibration note (3 references) should be cited whenever this weight is discussed.

---

### D.2 domain_level.py — the domain enrichment layer

#### D.2.1 Architecture and input paths

**Source:** `domain_level.py` module docstring, `domain_level.py:run_domain_level`

This module is post-seal and never blocks the deterministic package. Two input paths:

```
Full source path   — --source-antismash <zip>: full domain detail (name, description, evalue)
                     via parsers.extract_domain_features. Complete view.

Limited fallback   — sealed package only: gene_context.jsonl domain NAMES per CDS,
                     no descriptions or evalues. Clearly marked LIMITED in the receipt
                     and in the OPEN_ME_FIRST report.
```

On any failure, a named failure receipt (e.g. `DOMAIN_LEVEL_SKIPPED_NO_GBK.md`) is written and the function returns a status dict without raising — the core package remains valid. This is the module's explicit design contract.

#### D.2.2 Role taxonomy

**Source:** `domain_level.py:_CORE_ROLES`, `domain_level.py:_TAILORING_ROLES`, `domain_level.py:_TRANSPORT_ROLES`, `domain_level.py:_REGULATORY_ROLES`

Domains are mapped to controlled role categories by substring matching against a versioned taxonomy file (`domain_level/domain_role_taxonomy.v1.json`). The role sets used for complexity metrics:

```python
_CORE_ROLES = {
    "NRPS A-domain / loading", "NRPS condensation",
    "Carrier protein / PP-binding", "ACP / acyl carrier",
    "PKS ketosynthase", "PKS acyltransferase/loading",
    "PKS reductive loop", "PKS cyclase/aromatase",
    "Lanthipeptide maturation", "Lasso/RiPP maturation",
    "Azole/crocagin/RiPP tailoring",
}
_TAILORING_ROLES = {
    "Sugar/glycosyl tailoring", "Redox tailoring",
    "Methylation/alkylation", "Amino/amide tailoring",
    "Release/editing hydrolase",
}
_TRANSPORT_ROLES  = {"Transport/export/uptake", "Siderophore uptake/export"}
_REGULATORY_ROLES = {"Regulatory/sensor"}
```

The role for a given domain name is determined by `role_for_domain`, which does case-insensitive substring matching against the taxonomy categories in order (first match wins), with two special cases:
- A trailing e-value annotation `(e=2.10E-52)` is stripped before matching.
- Bare `TIGR####` identifiers (opaque — no substring signal) are routed to `fallback_unknown_repeat` rather than `fallback_other`, distinguishing "unknown repeat element" from "genuinely uncharacterised domain".

#### D.2.3 Complexity metrics

**Source:** `domain_level.py:build_complexity_metrics`

Per-BGC complexity metrics computed from the domain rows:

```
Domain_total                  — total domain rows for the BGC
Unique_domain_names           — cardinality of distinct domain names (set)
Domain_CDS_count              — number of distinct locus_tags carrying domains
Biosynthetic_core_domain_count— sum of domain rows whose role is in _CORE_ROLES
Tailoring_domain_count        — sum of domain rows whose role is in _TAILORING_ROLES
Transport_domain_count        — sum of domain rows whose role is in _TRANSPORT_ROLES
Regulatory_domain_count       — sum of domain rows whose role is in _REGULATORY_ROLES
Architecture_archetype        — from architecture_for_roles() via templates file
```

These are **count-based burden metrics**, not normalised fractions. A BGC with 20 core domains and 2 tailoring domains has a different profile from one with 2 core domains and 20 tailoring domains; both are recorded as raw counts so the Sapote judgment layer can assess relative weight.

#### D.2.4 Architecture archetype assignment

**Source:** `domain_level.py:architecture_for_roles`, `domain_level.py:classify_architecture`

Two functions with the same logic, accessed from two call sites:

```python
def architecture_for_roles(roles_present: set[str], templates: dict) -> str:
    """Used by build_complexity_metrics — returns archetype string only."""
    best, best_score = templates.get("fallback_archetype", "unclassified"), 0
    for t in templates["templates"]:
        if set(t.get("forbidden_roles", [])) & roles_present:
            continue   # disqualified by a forbidden role
        hits = len(set(t.get("required_roles", [])) & roles_present)
        if hits >= t.get("min_required_hits", 1) and hits > best_score:
            best, best_score = t["archetype"], hits
    return best

def classify_architecture(roles_present: set[str], templates: dict) -> tuple[str, str]:
    """Used by build_architecture_rows — returns (archetype, note)."""
    for t in templates["templates"]:
        req = set(t.get("required_roles", []))
        forb = set(t.get("forbidden_roles", []))
        hits = len(req & roles_present)
        if hits >= t.get("min_required_hits", len(req)) and not (forb & roles_present):
            return t["archetype"], t.get("note", "")
    return templates["fallback_archetype"], "no template matched"
```

The two functions differ in their tie-breaking default: `architecture_for_roles` uses `min_required_hits=1` as the fallback minimum (any single required-role hit is sufficient if nothing better scores), while `classify_architecture` uses `min_required_hits=len(req)` (all required roles must match). This means `classify_architecture` is strictly more conservative — it only fires a template when all required roles are satisfied, whereas `architecture_for_roles` can fire on a partial match.

The actual threshold values come from the template JSON file (`domain_architecture_templates.v1.json`), not from literals in this module. The templates file is loaded at runtime; if it is absent, `architecture_for_roles` returns `""` (empty string) and `classify_architecture` is not called.

#### D.2.5 Claim-safety verdict

**Source:** `domain_level.py:_claim_for_roles`, `domain_level.py:build_claim_rows`

The claim-safety verdict is derived from the set of roles present in a BGC, matched against a versioned rule file (`domain_claim_safety.v1.json`). The matcher:

```python
for rule in claim_rules["rules"]:
    if rule.get("is_default_floor"):
        floor = rule
        continue           # floor only used if nothing else matched
    need_all = rule.get("trigger_roles_all")
    need_any = rule.get("trigger_roles_any")
    min_core = rule.get("require_min_core", 0)
    if need_all and not set(need_all).issubset(roles_present):
        continue
    if need_any and not (set(need_any) & roles_present):
        continue
    if min_core and core_count < min_core:
        continue
    return {"safe": rule["safe_claim"], "unsafe": rule["unsafe_claim"],
            "ceiling": rule["ceiling"], "rule_id": rule["id"]}
## fallback to floor if no rule matched
```

Rules are evaluated in order; the first matching rule returns. The floor rule is skipped during iteration and used only if no other rule fires. Each rule can require: all of a set of roles (`trigger_roles_all`), any of a set of roles (`trigger_roles_any`), or a minimum biosynthetic-core domain count (`require_min_core`). The specific rule thresholds live in the JSON file and are not hardcoded here; the logic of the matcher is what is documented.

Output per BGC: `Safe_domain_claims`, `Unsafe_domain_claims`, `Domain_claim_ceiling`. These feed Mode B §2 (claim-safety review) and the `domain_safe_unsafe_claims.csv` deliverable.

#### D.2.6 Top-BGC selection

**Source:** `domain_level.py:_top_bgcs_from_package`

The module operates on the top `top_n` BGCs by AB+AF score from the sealed package's triage board CSV, not on all BGCs. Excluded from consideration: BGCs with a `Standing_rule` flag or `Primary_metab_flag == "YES"`. Default `top_n = 10`.

---

### D.3 dkp_cdps.py — DKP/CDPS scanner and grader

#### D.3.1 Detection terms

**Source:** `dkp_cdps.py:CDPS_TERMS`, `dkp_cdps.py:CDO_CONTEXT_TERMS`, `dkp_cdps.py:TAILORING_TERMS`

Four term sets define the scanner vocabulary. Detection is substring-based, case-insensitive, against the combined locus_tag + product + qualifiers text of each CDS/domain:

```python
CDPS_TERMS = ("cdps", "cyclodipeptide synthase", "cyclodipeptide-synthase",
              "cyclodipeptide_synthase", "diketopiperazine synthase", "pf16715")

CDO_CONTEXT_TERMS = ("cyclodipeptide oxidase", "albonoursin biosynthesis",
                     "alba", "nitroreductase", "pf00881")

TAILORING_TERMS  = ("prenyltransferase", "cytochrome p450", "p450",
                    "methyltransferase", "flavin-dependent monooxygenase",
                    "fmo", "oxygenase")

REGULATOR_TERMS  = ("regulator", "transcriptional", "luxr", "tetr",
                    "sarp", "laci", "gntr", "response regulator")

HOUSEKEEPING_TERMS = ("glutamate dehydrogenase", "nadp-specific glutamate dehydrogenase",
                      "dehydrogenase", "kinase", "ribosomal", "dna polymerase",
                      "rna polymerase", "transposase", "integrase", "housekeeping")
```

The coupling flank used for all `_nearby` calls is **10,000 bp** (same as the CCTT coupling flank in `source_scans.py`). Domain hits use the same flank.

`pf16715` (Pfam accession for the cyclodipeptide synthase family) and `pf00881` (nitroreductase fold — CDO context) are included as raw accession strings, matching directly in the qualifiers/domain text.

#### D.3.2 Gene-hit classification

**Source:** `dkp_cdps.py:classify_query_gene`

When a per-gene KCB/MIBiG hit is evaluated before it can influence DKP confidence, a five-way classification is applied:

```python
def classify_query_gene(label, product, qualifiers, pct_identity, coverage,
                        subject_accession, query_accession) -> str:

    # Self-hit: pct_identity >= 99.0 AND coverage >= 98.0
    if pct_identity >= 99.0 and coverage >= 98.0:
        if query_accession == subject_accession:
            return "self-hit"
        if "putative" not in h and _has_any(h, CDPS_TERMS + CDO_CONTEXT_TERMS):
            return "self-hit_or_exact_reference"

    if _has_any(h, CDPS_TERMS + CDO_CONTEXT_TERMS):
        return "biosynthetic-diagnostic"
    if _has_any(h, TAILORING_TERMS):
        return "biosynthetic-tailoring"
    if _has_any(h, HOUSEKEEPING_TERMS):
        return "housekeeping/conserved"
    return "unclassified_context"
```

The self-hit threshold (≥99% identity AND ≥98% coverage) is the operational definition of "this query gene is essentially identical to the reference gene." Self-hits are excluded from product confidence. The `"putative" not in h` guard for the `self-hit_or_exact_reference` branch is notable: a gene annotated as "putative cyclodipeptide synthase" at ≥99% identity is not classified as a self-hit because the "putative" qualification introduces uncertainty about the annotation itself.

#### D.3.3 DKP grade assignment

**Source:** `dkp_cdps.py:scan_dkp_cdps`

Three grades are assigned based on the presence of CDO context and boundary status:

```
DKP-A_candidate_dehydro_DKP  — CDO/AlbA-like oxidase present nearby
                                confidence = HIGH (Interior) or MEDIUM (Edge)

DKP-C_boundary_uncertain     — no CDO, BGC is Edge
                                confidence = MEDIUM

DKP-B_bare_or_saturated_CDP  — no CDO, not Edge
                                confidence = MEDIUM (if product_cdps or nearby_cdps)
                                             LOW   (if only domain hit, no CDS hit)
```

The grade taxonomy reflects chemical interpretation: a CDO-adjacent CDPS (DKP-A) gives rise to a dehydrogenated/oxidised DKP scaffold (an indolyl diketopiperazine or similar), which is a more specific and actionable lead than a bare saturated cyclodipeptide (DKP-B). DKP-C flags boundary uncertainty without making a structural prediction.

The trigger for a BGC to enter the scanner at all requires at least one of:
- Product label contains `\bCDPS\b`, `cyclodipeptide`, or `diketopiperazine` (antiSMASH typed it directly)
- A CDS within 10 kb matches any CDPS_TERMS pattern
- A domain feature within 10 kb matches any CDPS_TERMS pattern

#### D.3.4 Claim ceiling

Both `claim_ceiling` and `product_claim_ceiling` are explicit string literals in the `DKPCall` dataclass, set unconditionally regardless of grade:

```python
claim_ceiling = "candidate DKP-scaffold BGC; specific dipeptide/product requires isolation"
product_claim_ceiling = "same-family-not-same-product; do not assert purincyclamide/albonoursin without chemistry"
```

The second string explicitly names two compounds (purincyclamide and albonoursin) as examples of claims that must not be made without chemistry. This is a claim-safety guard against the most common over-interpretation of CDPS/CDO-containing BGCs.

---

### D.4 Relationship between the three modules

These three modules operate at different stages and with different inputs:

`compound_class.py` runs during the scoring phase on the BGC's own evidence (antiSMASH product class + resolved MIBiG product name). Its output (`scored_axis`, `scored_weight`) feeds the AB/AF scoring machinery documented in Volume I.

`domain_level.py` runs post-seal, as an enrichment step for the top-N BGCs. It consumes per-domain structural evidence to generate claim ceilings and complexity metrics independently of the AB/AF scores. It is the only module in this cluster that writes deliverable files.

`dkp_cdps.py` runs inside `run_source_scans` (called as `scan_dkp_cdps`, result stored as `cctt["dkp_cdps_context"]`). Its output complements the T43-DKP CCTT trigger: the CCTT scan fires on any CDPS annotation, while `dkp_cdps.py` adds the grade (A/B/C), confidence level, CDO adjacency, and claim ceilings.

---

### D.5 Concerns flagged for the bug log

1. **Two `classify_architecture` / `architecture_for_roles` functions with divergent `min_required_hits` defaults** (`domain_level.py` lines 74–87 and 230–239): `architecture_for_roles` defaults `min_required_hits` to 1 (fires on any single required-role hit); `classify_architecture` defaults it to `len(req)` (all required roles must match). A BGC could receive a different archetype from the two functions when the template's `min_required_hits` field is absent — one returns the template archetype, the other falls through to the fallback. The two functions are called from different places (`build_complexity_metrics` and `build_architecture_rows` respectively) so their outputs appear in different deliverables and are never directly compared in the same downstream assertion. If a consumer ever reads both CSV columns and expects them to be consistent for the same BGC, the divergence would be silent.

2. **`CDPS_TERMS` contains `"alba"` as a bare 4-character token** (`dkp_cdps.py:CDO_CONTEXT_TERMS` line 28): `"alba"` matches as a substring anywhere — in "albonoursin biosynthesis" as intended, but also in "ALBA-domain protein," "calibration," or any annotation containing that substring. Given the CDO_CONTEXT_TERMS are for context enrichment only (they don't trigger the scan, they only upgrade the DKP grade), this is a low-severity over-firing risk; a false CDO match would upgrade a DKP-B to DKP-A. Worth a word-boundary anchor: `r"\balba\b"` or replacement with the full "albonoursin" token.

3. **`"dehydrogenase"` in HOUSEKEEPING_TERMS** (`dkp_cdps.py:HOUSEKEEPING_TERMS` line 55): This is a broad substring that will match any dehydrogenase annotation, including biosynthetically relevant ones (dihydrodiol dehydrogenase, ketoreductase, etc.). HOUSEKEEPING_TERMS are used in `classify_query_gene` to suppress KCB confidence, so a biosynthetically relevant dehydrogenase hit would be mis-classified as housekeeping/conserved. The risk is proportional to how frequently non-housekeeping dehydrogenases appear in DKP KCB reference hits. Low severity in the DKP context (dehydrogenases are unusual in CDPS-centred clusters) but worth documenting.
## Volume II — Cluster E: Rescue, Concordance, Fragment Ceiling, and Comparative Pairs

**Source modules:** `mamey/diagnostic_rescue.py` (433 lines, v9.7.24) · `mamey/concordance.py` (144 lines) · `mamey/fragment_ceiling.py` (138 lines) · `mamey/comparative_pairs.py` (152 lines, v9.7.88)  
**Engine:** Mamey v1.9.98 · Bundle: v9.7.117  
**Affiliation:** 

---

### Preamble

Cluster E covers four modules that all operate *after* the main scoring pass, applying guards, ceilings, and supplementary evidence layers rather than driving the primary AB/AF scores. Three of the four (`diagnostic_rescue.py`, `concordance.py`, `comparative_pairs.py`) are purely advisory — they generate evidence the Sapote judgment layer reasons over, changing no triage scores. One (`fragment_ceiling.py`) does mutate BGCRecord fields, but only downward: it enforces a claim-ceiling that prevents product-level over-calls on physical fragments that cannot encode the named backbone.

---

### E.1 diagnostic_rescue.py — class-aware split-pathway rescue

#### E.1.1 Motivation and claim ceiling

**Source:** `diagnostic_rescue.py` module docstring, `diagnostic_rescue.py:CLAIM_CEILING`

This module was built to handle a specific failure mode of RG-GMCI's generic geometry gate: a split pathway where the core biosynthetic fragment and the tailoring arm sit on separate contigs (the expected topology in a fragmented assembly) gets demoted to LOW_SHARED_REFERENCE_SIGNAL because no adjacency geometry exists. The motivating case — a *Bombus*-associated *Streptomyces* indolocarbazole split — had BGC013 (T43-IDC core, NODE_182) and BGC001 (halogenase/saccharide arm, NODE_105) tiling complementarily onto the same reference cluster with zero gene overlap, but on separate contigs.

Every lead produced carries a fixed, non-negotiable claim ceiling:

```python
CLAIM_CEILING = (
    "Clusterblast-scaffolded reconstruction hypothesis: a homology-guided split-pathway "
    "linkage, NOT a nucleotide-level contig join and NOT a product-identity claim. "
    "Confirm physical linkage by long-read resequencing or PCR across the contig boundary."
)
```

#### E.1.2 Core / arm role taxonomy

**Source:** `diagnostic_rescue.py:CORE_TRIGGERS`, `diagnostic_rescue.py:ARM_TRIGGERS`, `diagnostic_rescue.py:ARM_PRODUCT_TOKENS`

```python
CORE_TRIGGERS = (
    "T43-IDC", "T43-PTM", "T43-NUC", "T43-BLA", "T43-AMC", "T43-NN",
    "T43-ENE", "T43-LAN", "T43-LASSO", "T43-THA", "T43-DKP", "T43-TET", "T43-PHO",
)
ARM_TRIGGERS    = ("T43-HAL", "T43-XHAL")
ARM_PRODUCT_TOKENS = ("saccharide", "glycosyl", "halogenated")
```

The logic: a genuine split pathway has one fragment that carries the class-defining backbone (CORE) and a complementary fragment that carries a tailoring function (ARM). Halogenation (T43-HAL, T43-XHAL) is the ARM trigger; saccharide/glycosyl product tokens are also ARM signals but carry lower weight (see §E.1.4 below).

#### E.1.3 Precision floors

**Source:** `diagnostic_rescue.py:COVERED_FLOOR`, `diagnostic_rescue.py:PER_ARM_FLOOR`, `diagnostic_rescue.py:TRUNCATED_EDGE`

```python
COVERED_FLOOR  = 8    # total reference genes both arms must tile (floor from the motivating case)
PER_ARM_FLOOR  = 2    # each arm must contribute >= 2 reference genes individually
TRUNCATED_EDGE = {"Edge", "Full-contig"}
```

**Edge gate:** Only truncated (Edge or Full-contig) fragments can be halves of a split pathway. An Interior cluster is complete — an Interior+Interior pair is co-occurrence on a shared reference, not a split. This gate was validated on public GOOD-assembly genomes where Interior+Interior pairs flooded false HIGH leads before the gate was added.

The `COVERED_FLOOR = 8` and `PER_ARM_FLOOR = 2` values are calibrated from the motivating BGC013+BGC001 case (8 reference genes, 0 overlap). They apply only when deep tiling data is available (`covered is not None`). When only the shallow RG-GMCI best-sources scaffold is available, floors are not enforced (`meets_floor` is True when `covered is None`).

#### E.1.4 Tier assignment

**Source:** `diagnostic_rescue.py:assess_pair`

Tier assignment is a priority-ordered conditional. `arm_is_diagnostic` is True only when a HAL/XHAL CCTT trigger is present — a bare-saccharide arm (glycosylation noise) cannot drive a HIGH rescue on its own:

```python
arm_is_diagnostic = arm_roles["hal_trigger"]   # HAL/XHAL trigger, not just saccharide product

if has_core AND arm_is_diagnostic AND has_shared AND complementary AND meets_floor:
    → DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE

elif has_core AND has_arm AND has_shared AND complementary:
    # arm is saccharide-only (glycosylation noise) OR below floor
    → DIAGNOSTIC_RESCUE_MODERATE

elif has_core AND has_arm AND has_shared:
    # shared scaffold but tiling is not complementary
    → DIAGNOSTIC_RESCUE_MODERATE

elif has_core AND has_arm:
    # no shared scaffold at all
    → DIAGNOSTIC_RESCUE_LOW

else:
    → None (not a rescue candidate)
```

`complementary` requires both conditions: `verdict == "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY"` AND (`overlap == 0 OR overlap_fraction <= 0.15`). The overlap fraction cap of 0.15 means up to 15% shared reference genes is tolerated before complementarity fails — small incidental overlaps from shared housekeeping genes near cluster boundaries don't block the call.

#### E.1.5 KCB-class concordance gate

**Source:** `diagnostic_rescue.py:_concordance`, `diagnostic_rescue.py:load_family_map`

A HIGH rescue requires the core and arm to KCB-hit compatible biosynthetic families. The family map is loaded from `mamey/data/families/kcb_compound_family.json` (curated; the MIBiG index subclasses are too coarse — AT2433 and loonamycin both read "other").

```python
def _concordance(cf, af, fmap) -> str:
    if cf is None or af is None:
        return "indeterminate"  # a side lacks a KCB family — evaluated but family-less
    if cf == af:
        return "concordant"
    compat = {tuple(sorted(p)) for p in fmap.get("compatible_pairs") or []}
    return "concordant" if tuple(sorted((cf, af))) in compat else "discordant"
```

Concordance gate effects on tier:

```
concordant    → tier unchanged
discordant    → HIGH → LOW  (cross-family tiling is co-occurrence, not a split)
indeterminate → HIGH → MODERATE  (cannot confirm class concordance)
```

When the family map is absent or fails to load, `_skipped` is set and concordance is recorded as `"not_evaluated"` — tier is not degraded, but the gap is auditable. The loader uses `fail-loud` (prints a warning to stderr) rather than silent fallback.

#### E.1.6 Complementary tiling algorithm

**Source:** `diagnostic_rescue.py:tile_pair`, `diagnostic_rescue.py:_adjacent`, `diagnostic_rescue.py:ADJ_MAX_LOCUS_GAP`, `diagnostic_rescue.py:ADJ_MAX_SPAN`

The tiling verdict is computed over the best shared ClusterBlast reference between two fragments, scored by total hit count + cumulative BLAST score:

```python
## Best shared reference: highest (len(hits_a) + len(hits_b), cum_score_a + cum_score_b)
best = max(shared, key=lambda acc: (len(cb_a[acc]["hits"]) + len(cb_b[acc]["hits"]),
                                    cb_a[acc]["cum_score"] + cb_b[acc]["cum_score"]))

sa = {h["subject"] for h in cb_a[best]["hits"]}
sb = {h["subject"] for h in cb_b[best]["hits"]}
overlap = sa & sb
smaller = min(len(sa), len(sb))
overlap_fraction = round(len(overlap) / smaller, 3) if smaller else 1.0
```

Adjacency check (locus-number proxy for genomic position in the reference):

```python
ADJ_MAX_LOCUS_GAP = 60    # ENGINEERING ESTIMATE, untuned (no physical-distance derivation)
ADJ_MAX_SPAN      = 400   # ENGINEERING ESTIMATE, untuned (no physical-distance derivation)

gap  = min(abs(a - b) for a in na for b in nb)
span = max(na | nb) - min(na | nb)
adjacent = (gap <= 60 and span <= 400)
```

These thresholds are heuristic (code comment: "tune via cross-strain retest") and not tied to a physical distance in bp — they use the numeric suffix of reference gene locus tags as a proxy. The SSOT note is important: `_locus_num` imports `_locus_key` from `rggmci` (for namespace-aware prefix+number splitting) when available, with a fallback to the old last-digit-run approach.

Four tiling verdicts:

```
overlap_fraction <= 0.15 AND adjacent     → RECONSTRUCTION_SUPPORTED_COMPLEMENTARY
overlap_fraction <= 0.15 AND NOT adjacent → RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI
overlap_fraction <= 0.50                  → RECONSTRUCTION_WEAK_PARTIAL_OVERLAP
overlap_fraction >  0.50                  → RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP
```

#### E.1.7 Competing-hypothesis annotation

**Source:** `diagnostic_rescue.py:build_leads`

After ranking, HIGH leads that share a BGC with another HIGH lead are annotated as competing hypotheses rather than silently dropped:

```python
l["competing_hypothesis_count"] = len(competitors)
l["mutually_exclusive_best"] = (
    len(part.get(l["core_bgc"], [])) == 1 and
    len(part.get(l["arm_bgc"], [])) == 1
)
```

`mutually_exclusive_best = True` means neither the core BGC nor the arm BGC appears in any other HIGH lead — this pair is the only HIGH-tier split hypothesis for both fragments. This is the honest annotation: a fragment has at most one true complement, so multiple HIGH leads sharing a BGC are competing, not independent.

---

### E.2 concordance.py — reference marker concordance check

#### E.2.1 Purpose and non-scoring status

**Source:** `concordance.py` module docstring

This module checks how many of a reference compound's expected biosynthetic markers are present in the queried BGC's CCTT/marker set, and whether the locus is the right size. It is **advisory only** — it does not change triage scoring. Its output is evidence the judgment layer reasons over.

Five verdicts:

| Verdict | Condition |
|---|---|
| `NO_REFERENCE` | KCB anchor does not resolve to a library entry |
| `EXPECTED_PENDING_LIT` | Library entry exists but reference markers/size not yet populated |
| `CONCORDANT` | ≥50% of expected markers present AND size within 0.5–2.0× |
| `PARTIAL` | Some markers present but < 50% |
| `DISCORDANT` | Anchor matches but zero expected markers present → misanchor warning |

#### E.2.2 Thresholds

**Source:** `concordance.py:CONCORDANT_MARKER_FRAC`, `concordance.py:SIZE_LO`, `concordance.py:SIZE_HI`

```python
CONCORDANT_MARKER_FRAC = 0.5         # >= 50% of expected markers required for CONCORDANT
SIZE_LO, SIZE_HI = 0.5, 2.0          # locus must be 0.5× to 2.0× reference size for size_ok=True
```

Size is not a hard gate — `size_ok = (size_ratio is None) or (0.5 <= size_ratio <= 2.0)`. When no size data is available (`size_ratio is None`), the size check passes permissively. The separate note threshold for extreme sizes:

```python
if size_ratio < 0.3 or size_ratio > 3.0:
    res.notes = "locus size far from reference — possible fragment or over-bounded boundary."
```

This note fires at 0.3× or 3.0× — substantially wider than the 0.5–2.0× concordance window — flagging genuinely anomalous sizes without failing the verdict on its own.

#### E.2.3 Anchor field discipline

**Source:** `concordance.py:concordance_for_bgc`

The anchor field is mandated as `closest_candidate_kcb_product` (the MIBiG reference product), not `kcb_top`. For clusters excised from a sequenced reference genome, `kcb_top` can be a genome self-hit; `closest_candidate_kcb_product` is always the MIBiG compound line. The wrapper function `concordance_for_bgc` enforces this — it exists specifically so callers cannot pick the wrong field.

#### E.2.4 Anchor resolution algorithm

**Source:** `concordance.py:resolve_anchor`

Anchors are matched to library entries by longest-alias-wins substring matching:

```python
for e in library["entries"]:
    for alias in e.get("aliases", []) + [e["compound"].lower()]:
        if alias and alias in anchor_lower and len(alias) > best_len:
            best, best_len = e, len(alias)
```

Longest-alias-wins prevents a short alias (e.g. "nik") from swallowing a more specific longer one (e.g. "nikkomycin") when both appear in the anchor text. The T43-class prefix abbreviation: marker strings starting with "T43-" are shortened to their prefix token before comparison (`_short(m)` strips everything after the first `_`), so "T43-IDC_indolocarbazole" becomes "T43-IDC" for set intersection purposes.

#### E.2.5 PENDING_LIT state

A library entry can have an empty `expected_marker_set` and `expected_size_kb = "PENDING_LIT"` or `None`. These indicate a reference that is in the library but whose ground truth has not yet been populated from literature. The verdict is `EXPECTED_PENDING_LIT` — explicitly distinct from `NO_REFERENCE` — so the audit trail shows the entry was found but is awaiting curation, not that it was absent.

---

### E.3 fragment_ceiling.py — backbone-size claim ceiling

#### E.3.1 Purpose

**Source:** `fragment_ceiling.py` module docstring, `fragment_ceiling.py:BACKBONE_MIN_KB`

When a large-backbone compound is named on a sub-45kb Edge or Full-contig fragment, the fragment physically cannot encode the full backbone. The module downgrades `product_claim_ceiling` to class-capacity at extraction time, preventing product-level over-calls before the Sapote judgment layer sees the BGC.

```python
BACKBONE_MIN_KB   = 45.0              # kb floor below which a fragment cannot encode a large backbone
FRAGMENT_BOUNDARIES = frozenset({"Edge", "Full-contig", "FC"})
DOWNGRADE_CEILING = "class-capacity only (fragment too small for named backbone; do not use product name)"
```

#### E.3.2 Two-path ceiling check

**Source:** `fragment_ceiling.py:fragment_claim_ceiling`

```python
## Path 1 (preferred): reference-size path
## The matched MIBiG reference is itself >= 45kb AND the fragment is < 45kb
if ref >= BACKBONE_MIN_KB and frag and 0 < kb < BACKBONE_MIN_KB:
    → downgrade (reference-size path)

## Path 2 (fallback): keyword path
## No reference size available, but a curated large-backbone compound name is present
if any(kw in name for kw in LARGE_BACKBONE_KEYWORDS) and frag and 0 < kb < BACKBONE_MIN_KB:
    → downgrade (keyword path)
```

Path 1 is preferred because it is self-maintaining: as MIBiG reference clusters are added to the index, the ceiling automatically extends without requiring keyword updates. Path 2 catches named compounds whose reference size is not in the index.

`LARGE_BACKBONE_KEYWORDS` covers 28 named compound families in three groups: glycopeptides (teicoplanin, vancomycin, balhimycin, UK-68, a47934, chloroeremomycin, ristocetin, complestatin, kistamicin), lipo/Ca-dependent lipopeptides (enduracidin, ramoplanin, friulimicin, daptomycin, a54145, CDA1–4, calcium-dependent antibiotic, skyllamycin), and large polyene/modular PKS macrolides (nystatin, amphotericin, candicidin, pimaricin, rapamycin, FK506, niddamycin, nanchangmycin, avermectin, rimocidin, filipin, stambomycin, lydicamycin, notonesomycin, clethramycin, linearmycin, stenothricin).

The check is applied only to fragments (Edge/Full-contig). Interior clusters and small compounds (lanthipeptides, lasso peptides, etc.) never trip regardless of their size.

#### E.3.3 Mutation behaviour

**Source:** `fragment_ceiling.py:apply_to_bgc`

`apply_to_bgc` mutates the BGCRecord in place when the ceiling trips:

```python
bgc.product_claim_ceiling = DOWNGRADE_CEILING
bgc.needs_manual_kcb_check = "yes"
## note appended type-safely (bgc.notes can be list or str)
```

The named product and MIBiG accession are preserved — only the `product_claim_ceiling` field is downgraded, so the provenance trail is intact for audit. The `notes` field append handles two BGCRecord variants: `list` (append) and `str` (join with ` | `).

The reference size is loaded lazily from `mamey/data/mibig/mibig_reference_index.bacterial.json` and `.fungal.json`. The module-level `_REFERENCE_SIZES` dict is populated on the first call to `_load_reference_sizes()` and cached for the process lifetime. Only entries with `size_kb_is_proxy=False` are loaded — proxy sizes (estimated, not directly measured) are excluded.

---

### E.4 comparative_pairs.py — cross-strain BGC similarity layer

#### E.4.1 What it computes

**Source:** `comparative_pairs.py` module docstring, `comparative_pairs.py:build_comparative_pairs`

This module populates the `E2_Comparative_Pairs` schema sheet, which was declared in the master workbook schema but had no populator until v9.7.88. It is a deterministic **similarity** layer, not a sequence-identity layer. Three signals contribute:

```
shared product classes     — antiSMASH product class tokens shared between the two BGCs
shared A-domain count      — adenylation/PKS-carrier domain names shared in the domain signature
KCB anchor overlap         — identical kcb_top strings (lowest-weight signal; similarity only)
```

`mean_pct_id_core` and `mean_pct_id_all` are explicitly `"not_computed"` (not blank, not zero) — the distinction matters because `"not_computed"` tells a consumer "no alignment was run," while a blank or zero would be ambiguous. The `a_domain_match` column is populated with a real count when gene context is available, and `"not_computed"` otherwise.

#### E.4.2 Domain signature and A-domain set

**Source:** `comparative_pairs.py:_ADENYLATION`, `comparative_pairs.py:_domain_signature`, `comparative_pairs.py:_shared_a_domains`

```python
_ADENYLATION = {
    "AMP-binding", "AMP-binding_C", "A_domain", "Condensation", "ACP",
    "PCP", "PP-binding", "Thioesterase",
}
```

`_domain_signature` builds the full set of all domain names from a BGC's gene context rows (each CDS contributes its `sec_met_domains` list). `_shared_a_domains` counts the intersection of the two domain signature sets filtered to the `_ADENYLATION` family — a concrete signal for comparing NRPS/PKS BGCs without requiring a sequence alignment.

`diverged_genes` is computed as `max(len(sig_a), len(sig_b)) - len(sig_a & sig_b)` — the count of domains present in the larger signature but not shared. This is a rough proxy for domain-level divergence, not a gene count.

#### E.4.3 Pair filtering

**Source:** `comparative_pairs.py:build_comparative_pairs`

Cross-strain only (same-strain pairs belong to RG-GMCI). A cheap pre-filter rejects any pair with no shared product classes before the domain work runs. Then:

```python
signal_count = (1 if shared_prod else 0) + (1 if shared_dom else 0) + (1 if kcb_overlap else 0)
if signal_count < min_signal:
    continue   # default min_signal = 1
```

With `min_signal = 1` (the default), any pair sharing at least one product class passes — since `shared_prod` being non-empty is the pre-filter condition, every pair that reaches this check already has signal_count ≥ 1 and will pass. The `min_signal` parameter exists to allow callers to require two or three corroborating signals for higher-confidence output.

#### E.4.4 KCB overlap definition

**Source:** `comparative_pairs.py:build_comparative_pairs` lines 110–112

```python
kcb_overlap = bool(kcb_a and kcb_a == kcb_b)
```

This is an **exact string match** on the lowercased `kcb_top` field. Two BGCs must have identical `kcb_top` strings to count as a KCB overlap — similar but not identical strings (e.g. the same compound named slightly differently) will not match. This is conservative and prevents false positives from partial string similarity, but it means the KCB overlap signal fires rarely in practice.

---

### E.5 Concerns flagged for the bug log

1. **`min_signal` filter is vacuous at default value** (`comparative_pairs.py:build_comparative_pairs` line 114–116): Because the shared-products pre-filter (line 99–100) already rejects pairs with no shared products, every pair reaching the `min_signal` check has `signal_count >= 1`. The `min_signal` guard only becomes meaningful when set to 2 or 3 by the caller. This is not a bug, but the docstring's "minimum number of similarity signals" framing implies the default of 1 actually filters something — it does not. Worth documenting or changing the default.

2. **Adjacency thresholds are heuristic locus-number proxies** (`diagnostic_rescue.py:ADJ_MAX_LOCUS_GAP`, `ADJ_MAX_SPAN`): `ADJ_MAX_LOCUS_GAP = 60` and `ADJ_MAX_SPAN = 400` are stated as heuristic (code comment: "tune via cross-strain retest") and have no physical-distance derivation. Locus numbers are sequential integers in the annotation, not genomic positions, so the threshold is an approximation of how many ORFs apart two reference genes can be. The code comment explicitly flags these for tuning. Not a bug: both are now tagged as engineering estimates (untuned; no physical-distance derivation) at the constants block above and cite `diagnostic_rescue.py:208-209`. (Self-flagged TODO resolved in v9.7.319.)

3. **`_REFERENCE_SIZES` is a module-level mutable global with lazy initialization** (`fragment_ceiling.py` lines 43–65): Loaded once on the first call and cached for the process lifetime. In a long-running process where the MIBiG index files change between calls (unlikely but possible in a development workflow), the stale cache would serve old sizes. Not a production concern but worth noting for test isolation: tests that patch the data directory may need to reset `_REFERENCE_SIZES = None` between runs.

4. **`concordance_for_bgc` size calculation uses coordinate subtraction** (`concordance.py` line 143): `size = round((bgc.end - bgc.start) / 1000, 1)`. This is the called locus size, not the corrected BGC size (corrected count = Interior + ½·Edge + ¼·Full-contig, Volume I §3). For Edge and Full-contig BGCs, the raw coordinate span overestimates the actual contained sequence. The size check in `concordance_check` (`SIZE_LO=0.5, SIZE_HI=2.0`) is permissive enough that this is unlikely to flip verdicts in practice, but a fragment whose true sequence is 30kb might report a 45kb coordinate span and pass the size check when it should not. Low-severity given the wide ratio window.
## Volume II — Cluster F: Singleton Filter, §3 Census Generator, Enrichment Sections, Nominal Length

**Source modules:** `mamey/singleton_filter.py` (265 lines, v9.7.117) · `mamey/s3_census_generator.py` (108 lines) · `mamey/enrichment_sections.py` (272 lines) · `mamey/nominal_length.py` (148 lines, DRAFT v9.7.104)  
**Engine:** Mamey v1.9.98 · Bundle: v9.7.117  
**Affiliation:** 

---

### Preamble

Cluster F covers the Mode B enrichment stack — the deterministic generators that ensure every card reaches the `MIN_ENRICHMENT_CHARS` floor from data, never from padding. These modules are all annotation layers: none changes a triage score or BGC rank. The singleton filter and rarity rankers feed the §11–§20 enrichment sections; `s3_census_generator.py` feeds the §3 Biosynthetic Core section; `nominal_length.py` provides the fragment-size yardstick. The quality gate that enforces the floor (`mode_b_quality_gate.py`) is covered in Cluster G.

---

### F.1 singleton_filter.py — biosynthetic-relevance filter

#### F.1.1 The problem it solves

**Source:** `singleton_filter.py` module docstring

The rarity metric in `enrichment_sections.py` ranks domains by genome-wide frequency; a "genome-unique singleton" (frequency == 1) is a novelty signal. On a fragmented genome, housekeeping genes captured at contig edges are also genome-unique singletons — not because they are biosynthetically distinctive, but because they are single-copy. Concrete cases from AS-XXX (v9.7.114) quantify the over-count: BGC045 had 10 raw singletons, 4 of which were ribosomal proteins or EF-G; BGC052 had 7 raw singletons all from the α-glucan/glycogen GlgE pathway (primary metabolism — a DROP not a lead); BGC015 had 11 raw singletons, mostly regulatory and MEP-isoprenoid. Without filtering, BGC015 (11 singletons, mostly noise) mis-ranked above BGC007 (7 singletons, nearly all genuine RiPP maturation machinery).

#### F.1.2 Three-tier token-bounded matching (v9.7.117 fix)

**Source:** `singleton_filter.py:_HOUSEKEEPING_PREFIX`, `_HOUSEKEEPING_EXACT`, `_HOUSEKEEPING_WHOLE`

The original module used bare case-insensitive substring matching (`stem in domain`). This is the same substring-containment bug class fixed across multiple modules in v9.7.115–116. Confirmed false drops under the old rule: `Trans_AT_S1`, `PKS_Docking_S1`, `Peptidase_S1` (all caught by bare `"s1"`), `NADHpyr_redox` (caught by `"nadh"`), `GtrA_like` (caught by `"gtra"`), `ABC1_kinase` (caught by `"abc1"`). All six are biosynthetically meaningful domains that were being silently discarded.

The fix introduces three matching tiers:

```python
## PREFIX: stem >= 5 chars or clearly housekeeping; match as a delimited token prefix
## Pattern: (?:^|[_-]){stem}
## Example: "Ribosom" matches "Ribosomal_S7" and "Ribosom_S12" but NOT "AutoribosomX"

## EXACT: specific identifier; match as a complete delimited token
## Pattern: (?:^|[_-]){stem}(?=[_-]|$)
## Example: "EFG" matches "EFG" or "X_EFG_Y" but NOT "EFGH_domain"

## WHOLE: short/ambiguous; match ONLY when the stem IS the entire domain name
## Test: domain_lower == stem
## Example: "S1" matches only a domain named exactly "S1", not "Peptidase_S1"
```

```python
def _prefix_hit(domain_l):
    for stem in _PREFIX_SET:
        if re.search(rf"(?:^|[_-]){re.escape(stem)}", domain_l):
            return stem
    return None

def _exact_hit(domain_l):
    for stem in _EXACT_SET:
        if re.search(rf"(?:^|[_-]){re.escape(stem)}(?=[_-]|$)", domain_l):
            return stem
    return None

def _whole_hit(domain_l):
    return domain_l if domain_l in _WHOLE_SET else None
```

The three sets are collapsed into frozensets at module load (`_PREFIX_SET`, `_EXACT_SET`, `_WHOLE_SET`) for O(1) membership testing before the regex. The matching order in `classify_singleton` is: prefix → exact → whole — no particular reason for this ordering beyond the fact that prefix covers the most entries and is most likely to match early.

#### F.1.3 Housekeeping blocklist — categories and entries

**Source:** `singleton_filter.py:_HOUSEKEEPING_PREFIX`, `_HOUSEKEEPING_EXACT`, `_HOUSEKEEPING_WHOLE`

Six functional categories across the three tiers:

| Category | Example PREFIX entries | Example EXACT entries | WHOLE entries |
|---|---|---|---|
| translation | Ribosom, tRNA, GTP_EFTU, LepA | EFG, EF-Tu, EF_Ts | S1 |
| dna_replication_repair | DnaB, Helicase, UvrD, UvrA, Topoisom, Primase, Resolvase, Integrase | HHH_3, RecA | DEAD |
| mobile_element_defense | CRISPR, Cas_Cas, DDE_Tnp, Transposase | Uma2 | — |
| central_metabolism | GlgE, Malt_amylase, VitK2, GcpE, IspD, IspG, PHB_acc | Dxr, Dxs, DHDPS | NADH, ABC1, PCLP, GtrA |
| chaperone_stress | GroEL, GroES, DnaK, DnaJ, ClpB, Ferritin | DSBA, OsmC, AHSA1 | ABC1 |
| general_transport_regulation | Cation_efflux, ECF_trnsprt, Mg_trans | FtsX, EamA | — |

Note that `ABC1` appears in both `_HOUSEKEEPING_WHOLE["central_metabolism"]` and `_HOUSEKEEPING_WHOLE["chaperone_stress"]`. This is redundant but harmless — both route to the same `WHOLE_SET` frozenset.

#### F.1.4 Biosynthetic override allowlist

**Source:** `singleton_filter.py:_BIOSYNTHETIC_OVERRIDE`

Seven domain families are explicitly protected from the blocklist — they look housekeeping by name but are biosynthetically meaningful in a BGC context:

```python
_BIOSYNTHETIC_OVERRIDE = frozenset({
    "RHS",             # RHS contact-dependent toxins — ecological weapons
    "Ntox30",          # RHS-associated toxin
    "Hemerythrin",     # non-heme di-iron tailoring enzyme
    "Spermine_synth",  # polyamine incorporation into RiPP scaffolds
    "Peptidase_M23",   # cell-wall enzyme inside antifungal BGCs
    "LysM",            # cell-wall binding inside antifungal BGCs
    "Transglycosylas", # transglycosylase inside antifungal BGCs
})
```

The override check runs first (step 1 in `classify_singleton`), before the blocklist. This means a domain in `_BIOSYNTHETIC_OVERRIDE` can never be dropped, even if a blocklist stem would otherwise match it.

#### F.1.5 Decision order in `classify_singleton`

**Source:** `singleton_filter.py:classify_singleton`

```
1. Biosynthetic override (curated)              → always KEEP
2. Housekeeping blocklist (token-bounded)       → always DROP (authoritative over antiSMASH tag)
   Note: antiSMASH tags an entire rule-based cluster; a glycogen enzyme inside a saccharide
   cluster carries a 'biosynthetic (saccharide)' tag but is still primary metabolism.
   The Pfam identity is authoritative for clear housekeeping families.
3. antiSMASH biosynthetic tag                   → KEEP (protects Pfam-ambiguous tailoring enzymes)
   Tags: "biosynthetic (rule-based-clusters)", "biosynthetic-additional", "biosynthetic (core)"
4. antiSMASH regulatory/transport tag           → DROP (no biosynthetic role)
   Tags: "regulatory (smcogs)", "transport (smcogs)" — only when "biosynthetic" is absent
5. Default                                      → KEEP (conservative — unknown domains may be novel)
```

The inversion at step 2 (blocklist runs before the antiSMASH tag) is a deliberate design choice explicitly documented in the docstring.

#### F.1.6 Filtered vs raw singleton count

**Source:** `singleton_filter.py:filtered_singleton_count`

The unit of counting is the **gene**, not the domain: a gene contributes 1 to the raw count if it carries any genome-unique domain, and 1 to the filtered count if it retains at least one biosynthetic-relevant singleton after filtering. A gene where all domains are housekeeping contributes to raw but not to filtered.

```python
for domains, fn in gene_singletons:
    raw += 1              # any gene with >= 1 genome-unique domain
    keep, _ = filter_singletons(domains, fn)
    if keep:
        filtered += 1     # only if >= 1 domain survives
```

Both counts are reported alongside each other so the raw and filtered values are independently auditable.

---

### F.2 s3_census_generator.py — §3 size-scaled gene census

#### F.2.1 Purpose and floor formula

**Source:** `s3_census_generator.py` module docstring

This module generates the §3 Biosynthetic Core section content for Mode B cards when the §3 body falls below the size-scaled floor. The floor is:

```
§3 floor = 600 + 60 × domain_gene_count
```

This formula is referenced in the module docstring ("For gene-rich clusters whose §3 falls below the size-scaled floor (600 + 60*domain_genes)"). The actual enforcement of this floor is in `mode_b_quality_gate.py` (Cluster G); this module is the generator that produces content to meet it.

#### F.2.2 Role bucketing

**Source:** `s3_census_generator.py:_ROLE_PATTERNS`

Eight role buckets, matched first-match-wins in order against the semicolon-joined `sec_met_domains` string:

```python
_ROLE_PATTERNS = [
    ("assembly-line core (NRPS/PKS)", [
        "AMP-binding", "NRPS-A", "Condensation", "C1_LCL", "C2_LCL", "C2_DCL",
        "Heterocyclization",     # v9.7.117 Cy-domain fix: heterocycle-forming condensation domains;
                                 # match full name (distinctive) not bare CyN subtype tags
        "Ketoacyl-synt", "PKS_KS", "PKSI-KS", "Acyl_transf", "PKS_AT",
        "PP-binding", "PCP", "ACP", "Thioesterase", "NRPS-te", "Epimerization",
        "PKS_KR", "PKS_DH", "PKS_ER", "KR", "Aminotran_1_2"]),
    ("RiPP maturation", [...]),
    ("redox tailoring", [...]),
    ("group transfer / decoration", [...]),
    ("precursor / building-block supply", [...]),
    ("regulation", [...]),
    ("transport / resistance / efflux", [...]),
]
```

The `Heterocyclization` token addition in v9.7.117 is the Cy-domain census fix referenced in the v9.7.117 CHANGELOG. Before this fix, heterocyclization domains (which form thiazoline/oxazoline rings in TOMM/azole RiPP assembly lines) were not classified as assembly-line core, understating the core domain count for those BGCs.

Within the assembly-line core bucket, genes are sorted by descending amino-acid length (`key=lambda x: -x[1]`) so the largest protein (the principal biosynthetic engine) leads the listing.

#### F.2.3 Domain display cap

**Source:** `s3_census_generator.py:build_size_scaled_s3` line 97

```python
dom_show = ", ".join(doms[:6]) + ("…" if len(doms) > 6 else "")
```

Each gene's domain list is capped at 6 entries in the output prose with a trailing ellipsis when truncated. This is a display-only cap — all domains contribute to role assignment.

---

### F.3 enrichment_sections.py — §11–§20 deterministic generators

#### F.3.1 Floor and catch-all architecture

**Source:** `enrichment_sections.py` module docstring, `enrichment_sections.py:compose_enrichment`

The `MIN_ENRICHMENT_CHARS` floor (1,000 characters, enforced by `mode_b_quality_gate.py`) is reachable from data via two true catch-alls that fire on every card with at least one domain-bearing gene:

```
emit_rarest_genes      — always has content if >=1 gene
emit_rarest_domains    — always has content if >=1 gene
emit_domain_inventory  — always has content if >=1 gene (generic filler, last resort)
```

Broad sections fire on most cards:
```
emit_nrps_pks_typing   — fires when A-domain or KS genes are present
emit_peptide_precursor — fires when short ORFs (<=100 aa), RiPP maturation genes, or RiPP product label
```

Class-specific sections return an empty string when N/A (not counted toward the floor):
```
emit_halogenase_subtyping — fires only when a halogenase domain exists
```

Composition order in `compose_enrichment`: rarest_domains → rarest_genes → halogenase_subtyping → peptide_precursor → nrps_pks_typing → domain_inventory. The ordering principle is documented explicitly: universal anchors lead, then distinctive class-specific sections, then broad typing, then generic filler. This ensures a distinctive feature (e.g. a halogenase) is never dropped merely because an earlier generic section cleared the floor.

The composer uses a **character-count accumulator** — it adds sections until the combined text reaches `floor` characters, then stops:

```python
for name, text in candidates:
    if not text:
        continue
    used.append(name); blocks.append(text); total += len(text)
    if total >= floor:
        break
```

`floor` defaults to 1,000, matching `MIN_ENRICHMENT_CHARS` in the quality gate.

#### F.3.2 Rarity ranking with housekeeping down-weighting

**Source:** `enrichment_sections.py:emit_rarest_genes`, `emit_rarest_domains`

Both rarity sections use the same two-level sort key introduced in v9.7.117:

```python
## For genes: (is_housekeeping_only, min_genome_frequency_of_any_domain)
def gene_rank(g: Gene):
    rarity = min((freq.get(dm, 1) for dm in g.domains), default=9999)
    return (_is_housekeeping(g), rarity)

## For domains: (not biosynthetically_relevant, genome_frequency)
ranked = sorted(local, key=lambda d: (not classify_singleton(d).biosynthetic_relevant,
                                      freq.get(d, 1)))
```

In both cases `False < True` in Python tuple comparison, so `biosynthetic_relevant=True` (is_housekeeping=False, or the `not` version = False) sorts to a lower rank value and appears first. Genuine biosynthetic singletons rank above housekeeping genes/domains at the same genome frequency. Nothing is dropped — the ranking just prevents ribosomal proteins from appearing as the "rarest finding."

`_is_housekeeping(g)` returns True only when **none** of the gene's domains survive the `classify_singleton` filter — a gene must be all-housekeeping to be ranked last.

#### F.3.3 Genome-wide domain frequency

**Source:** `enrichment_sections.py:genome_domain_frequency`

```python
def genome_domain_frequency(all_genes_by_bgc: dict[str, list[Gene]]) -> Counter:
    freq = Counter()
    for genes in all_genes_by_bgc.values():
        for g in genes:
            for dm in g.domains:
                freq[dm] += 1
    return freq
```

The frequency counter is over individual domain-family instances, not genes. A domain appearing in 5 different genes in 3 different BGCs contributes 5 to its count. The scope is the full genome (all BGCs in `all_genes_by_bgc`), so the rarity is relative to the genome being analysed, not to any external database. A domain with `freq[dm] == 1` is genome-unique.

#### F.3.4 Common machinery exclusion in domain inventory

**Source:** `enrichment_sections.py:_COMMON_MACHINERY`

```python
_COMMON_MACHINERY = frozenset({
    "PP-binding", "AMP-binding", "AMP-binding_C", "PCP", "Condensation",
    "NRPS-A_a3", "NRPS-A_a6", "NRPS-A_a8", "NRPS-A_a2", "ACP", "Acyl_transf_1",
    "Ketoacyl-synt", "Ketoacyl-synt_C", "PKS_KS", "PKS_AT", "KR", "PKS_KR",
})
```

In `emit_domain_inventory`, domains in `_COMMON_MACHINERY` are excluded from the "distinctive tailoring/structural content" count:

```python
catalytic = [d for d in cnt if d not in _COMMON_MACHINERY]
...
f"Of these, {len(catalytic)} families sit outside the common NRPS/PKS carrier machinery "
"and represent the cluster's specific tailoring/structural content."
```

This is annotation only — the excluded domains still appear in the top-12 most-represented list (`top = sorted(cnt.items(), key=lambda x: -x[1])[:12]`); only the "distinctive content" count is filtered.

#### F.3.5 RiPP precursor key guard

**Source:** `enrichment_sections.py:_RIPP_PRECURSOR_KEYS`

```python
_RIPP_PRECURSOR_KEYS = ("leader", "precursor", "lanthi", "lasso", "sacti", "thiopeptide",
                        "thioamitide", "RiPP", "ranthi", "Nif11", "LanC", "LanB", "YcaO", "PqqD")
```

The code comment records the v9.7.112 Patch Chat fix: the bare `"thio"` substring was removed from this list because it matched `Thioesterase`, `Thioredoxin`, and `thiolation` (all common non-RiPP domains). The replacement terms anchor specifically to the RiPP thio-class forms: `"thiopeptide"` and `"thioamitide"`.

#### F.3.6 Per-gene line for small clusters

**Source:** `enrichment_sections.py:emit_domain_inventory` lines 161–163

```python
if len(genes) <= 12:
    out += " Per-gene domain content: " + "; ".join(
        f"{g.locus} → {', '.join(g.domains)}" for g in genes) + "."
```

For clusters with 12 or fewer domain-bearing genes, the inventory adds a complete per-gene locus-to-domain map. This serves two purposes: it makes the inventory a complete locus-by-locus reference for small BGCs, and it keeps the catch-all reliably above the enrichment floor on clusters with few genes (where the top-12 census would be very short).

---

### F.4 nominal_length.py — fragment-size yardstick

#### F.4.1 What it is and what it is not

**Source:** `nominal_length.py` module docstring

This module provides a nominal-length normalization for Edge/Full-contig fragments. The output is phrased as a fraction of a reference cluster's length — a yardstick for triage — never as a completeness claim about the strain's true cluster. The claim-safety design is the entire reason this is a guarded module rather than a bare ratio:

- "recovery fraction" = observed span ÷ reference nominal length. Not "fraction of the cluster present."
- The reference nominal length is a reference cluster's antiSMASH region span. The strain's real cluster may differ.
- Every entry carries `confirmed=False` until validated across multiple independent class members.
- A fragment longer than its reference reports `>100%` explicitly — never silently clipped.
- Interior BGCs are reported in kb only; nominal normalization is only for Edge/Full-contig fragments.

#### F.4.2 Registry structure

**Source:** `nominal_length.py:NominalReference`, `nominal_length.py:NOMINAL_REFERENCES`

```python
@dataclass(frozen=True)
class NominalReference:
    label: str           # human label
    nominal_kb: float    # nominal full-cluster length in kb
    classes: tuple       # antiSMASH product tokens (lowercased) that trigger this reference
    source_accession: str
    confidence: str      # HIGH / MODERATE / LOW
    confirmed: bool = False   # False = unconfirmed yardstick
    note: str = ""
    members: tuple = ()       # accessions the nominal is derived from
    nominal_range_kb: tuple = ()  # (min_kb, max_kb) observed across members
```

As of v9.7.104, one entry is seeded:

```
polyoxin-class (nucleoside / peptidyl-nucleoside)
  nominal_kb         = 30.0   (2-member mean of 27.9 and 32.0 kb)
  classes            = ("nucleoside", "polyoxin", "peptidyl-nucleoside")
  source_accession   = "EU158805.1; JN674503.1"
  confidence         = MODERATE
  confirmed          = False
  nominal_range_kb   = (27.9, 32.0)   (~14% spread across members)
```

The note is explicit about the limitations: n=2 only, both polyoxin (not nikkomycin or the broader peptidyl-nucleoside class), from the same Deng/Bai lineage. The confirmed flag must remain False until validated across independent class members.

The 30.0 kb nominal is the mean of two antiSMASH region spans (not the full GenBank records, which are 43.2–46.1 kb). This distinction matters: antiSMASH regions are coordinate-bounded and typically shorter than the full deposit.

#### F.4.3 Recovery fraction formula

**Source:** `nominal_length.py:measure_bgc`

```python
frac = lk / ref.nominal_kb
recovery_pct = round(100 * frac, 1)
```

For `frac <= 1.0`:
```
"{lk:.1f} kb ≈ {recovery_pct:.0f}% of ~{ref.nominal_kb:.0f} kb {ref.label} nominal
(yardstick, not a completeness claim) [unconfirmed ref]"
```

For `frac > 1.0`:
```
"{lk:.1f} kb · >100% of ~{ref.nominal_kb:.0f} kb {ref.label} nominal
(exceeds nominal; reference may be smaller than this cluster) [unconfirmed ref]"
```

The `[unconfirmed ref]` suffix is appended whenever `not ref.confirmed` — it is always present for the current single entry.

#### F.4.4 Length calculation

**Source:** `nominal_length.py:length_kb_of`

```python
## Preferred: pre-computed length_kb field
lk = bgc.get("length_kb") or getattr(bgc, "length_kb", None)

## Fallback: coordinate subtraction
s, e = bgc.start, bgc.end
return round(max(0, int(e) - int(s)) / 1000, 2)
```

Same as the concordance module (Cluster E §E.2.4): this is the raw coordinate span, not the corrected BGC size. For the nominal normalization use case this is the correct denominator — the observed antiSMASH region span is being compared against the reference antiSMASH region span, so both values are raw coordinate spans and the comparison is internally consistent.

---

### F.5 Concerns flagged for the bug log

1. **`_ROLE_PATTERNS` matching uses bare substring, not token-bounded** (`s3_census_generator.py:_role_of` line 50): `any(k.lower() in dt.lower() for k in keys)` where `dt` is the space-joined domain string. This is the same substring-containment pattern fixed in `singleton_filter.py` (v9.7.117). Short role-bucket keys like `"KR"`, `"KS"`, `"ACP"`, `"PCP"`, `"TE"`, `"sugar"` match anywhere in the concatenated domain string. For example, `"sugar"` would match `"2-deoxysugar_GlcNAc_dehydratase"` (intended) but also any domain name containing the substring `"sugar"` regardless of context. In practice the role buckets are used only to group genes in a prose section (not for scoring or claims), so false-bucket assignments produce incorrect prose labelling rather than incorrect scores. Still, the risk of a genuine biosynthetic domain being mis-routed to the wrong role bucket should be documented and the token-boundary fix applied.

2. **`_WHOLE_SET` construction iterates all three WHOLE category lists but `_PREFIX_SET` iterates `_HOUSEKEEPING_PREFIX` values** — these follow the same pattern but the `_WHOLE_SET` frozenset and `_PREFIX_SET` frozenset construction use different dict values. No bug, but note that `"ABC1"` appears in both `_HOUSEKEEPING_WHOLE["central_metabolism"]` and `_HOUSEKEEPING_WHOLE["chaperone_stress"]`, creating a duplicate entry in the source dict that collapses harmlessly in the frozenset. Worth a cleanup comment.

3. **`NOMINAL_REFERENCES` is a module-level tuple with a single unconfirmed entry** (`nominal_length.py`): The registry currently contains one entry (`polyoxin-class`, `confirmed=False`). All calls to `measure_bgc` that match this reference will include `[unconfirmed ref]` in the label. This is correct behaviour, but the DRAFT status of the whole module should be noted in Volume II: the nominal-length subsystem is in early population and its outputs should be read as exploratory yardsticks, not validated metrics.

4. **`emit_domain_inventory` top-12 cap is a display heuristic, not a coverage guarantee** (`enrichment_sections.py:emit_domain_inventory` line 151): `top = sorted(cnt.items(), key=lambda x: -x[1])[:12]` caps the "most-represented" list at 12 entries regardless of cluster size. A large complex BGC with 40+ domain families will only show the 12 most frequent in the main text; the per-gene supplement only fires for clusters with `len(genes) <= 12`. This is intentional (the inventory is a summary, not an exhaustive list) but should be documented as a display cap, not a completeness guarantee.

---

## Cluster G — pending

Cluster G (crosswalk / dedup / merge policy / quality gates) was still in preparation at the time of this compilation and will be folded into a subsequent revision. All other Volume II clusters (A–F) are complete and source-verified.

---

## Assembly status

| Cluster | Subsystem | Status |
|---|---|---|
| A | CCTT / source-scan trigger engine | folded, verified |
| B | Architecture-first, scoring context, rules | folded, verified |
| C | KCB / RiQ extraction, ClusterBlast genes | folded, verified |
| D | Compound class, domain-level, DKP/CDPS | folded, verified |
| E | Rescue, concordance, fragment ceiling, comparative pairs | folded, verified |
| F | Singleton filter, §3 census, enrichment, nominal length | folded, verified |
| G | Crosswalk, dedup, merge policy, gates | pending |

*The Mathematics of Sapote-Mamey, Volume II · Mamey engine v1.9.110 (frozen; the math tracks the engine, not the rolling bundle) · constants re-verified against source 2026-07-14 Every formula transcribed from engine source; capacity-level language throughout; KCB = similarity, not identity.*

> **Engine 1.9.111 note (v9.7.319):** the glycopeptide machinery floor + tailoring-detection widening landed in engine 1.9.111. Volume II's constants were verified against 1.9.110 and have NOT yet been re-verified against 1.9.111 — the scoring *thresholds* are unchanged, but the capacity-class routing now detects tailoring enzymes from gene_functions/SMCOG. A re-verification pass is pending; treat the class-routing sections as ahead of this document until then.
