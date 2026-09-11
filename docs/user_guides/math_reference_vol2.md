# Sapote–Mamey: Mathematical Reference — Volume II
## Engine Subsystems: Triggers, Architecture, KCB/RiQ, Compound Class, Rescue, Enrichment
**Source document:** `docs/reference/02_Math_Reference_VolII.md` (Mamey engine v1.9.110 · bundle v9.7.319, 2026-06-23)
**Compiled for:** bundle v9.7.243 · engine 1.9.110 · 2026-07-09


*This document reorganises and extends the Vol II source for cross-session reference. All formulas, constants, and thresholds are transcribed verbatim from source code with `module.py:symbol` citations. No values are reconstructed from memory. Two invariant rules apply throughout: (1) scores are routing priors, not biological proof; (2) KCB = similarity, not identity.*

*Companion to: Vol I (core counting, assembly tiers, AB/AF/novelty scoring, lead tiers, RG-GMCI) and the Plumbing Reference (CLI, workbook, figures, packaging).*

---

## Part A — The CCTT / Source-Scan Trigger Engine

**Source module:** `mamey/source_scans.py` (1,586 lines) + `mamey/mamey_markers.py` · `mamey/mamey_cassettes.py` · `mamey/sapote_markers.py`

### A.1 The annotation haystack (`_hay`)

Before any pattern can match, each CDS is reduced to a single lowercase search string:

```python
vals = [cds.product or "", cds.locus_tag or ""]
skip = {"translation", "nucleotide_seq", "sequence"}
for k, v in cds.qualifiers.items():
    if str(k).lower() not in skip:
        vals.append(str(k))
        vals.extend(str(x) for x in v[:8])   # cap: 8 values per qualifier
return " ".join(vals).lower()
```

The 8-value cap and the exclusion of translation/sequence fields are performance guards. HMMER/DIAMOND domain profiles are **not** run in this layer — domain evidence comes from antiSMASH's `sec_met_domain` GBK features, parsed separately in `antismash_evidence.py`.

### A.2 Generic scan + BGC coupling

All pattern groups go through the same two-step machinery:

```python
# Step 1 — per-CDS match
def _scan_patterns(cds_list, patterns):
    buckets = {k: [] for k in patterns}
    for cds in cds_list:
        h = _hay(cds)
        for group, pats in patterns.items():
            if any(re.search(p, h, flags=re.I) for p in pats):
                buckets[group].append(...)
    return {status, counts, hits, claim_safety}

# Step 2 — spatial coupling to BGC records  
def bgc_coupling(bgcs, scan_hits, flank=10000):
    for group, hits in scan_hits["hits"].items():
        for h in hits:
            for bgc in bgcs:
                if cds.contig == bgc.contig and within_flank(cds, bgc, flank):
                    by_bgc[bgc_id].append(group)
    return {bgc_id: sorted(set(groups))}
```

**Flank values by scan type:**
- CCTT, most scans: **10,000 bp**
- Cassettes, UMED: **5,000 bp**
- Primary-metabolism scan: **0 bp** (only genes inside the BGC's own coordinates)

### A.3 The 14 CCTT triggers and their MMK registry IDs

| Code key | MMK ID | What it detects | Design notes |
|---|---|---|---|
| T43-HAL_halogenase | MMK-CCTT-001 | Flavin-dependent halogenases | `(?<!de)halogenase` — negative lookbehind excludes dehalogenases |
| T43-XHAL_fluorinase_chlorinase | MMK-CCTT-002 | SAM-dependent organohalogen enzymes (SalL/FlA) | — |
| T43-PHO_phosphonate | MMK-CCTT-003 / SMK-PHO-001 | Phosphonate commitment: PEP mutase | 4 nested negative lookaheads; see §A.9 |
| T43-NUC_nucleoside | MMK-CCTT-004 / SMK-NUC-001 | Peptidyl-nucleoside (nikkomycin/polyoxin-like) | — |
| T43-BLA_betalactam | (no standalone marker) | Committed β-lactam biosynthesis | — |
| T43-AMC_aminocyclitol | MMK-CCTT-005 / SMK-AMC-001 | 2-deoxystreptamine aminocyclitol: DOIS/BtrC | — |
| T43-ENE_enediyne | MMK-CCTT-006 / SMK-ENE-001 | Enediyne pathway | Simple `enediyne` token; PREV-001 discrimination is downstream in misanchor guards |
| T43-LAN_lanthipeptide | MMK-CCTT-007 | Lanthipeptide/RiPP | `lanthipeptide`, `lantibiotic`, `\blanc\b`, `\blanm\b` |
| T43-LASSO_lassopeptide | MMK-CCTT-008 | Lasso peptide RiPP | — |
| T43-THA_thioamide | MMK-CCTT-009 / SMK-THA-001 | Thioamide/thioamitide RiPP (YcaO-based) | — |
| T43-DKP_cdps | MMK-CCTT-010 | Cyclodipeptide synthase / DKP | Requires copalyl-terpene veto (§A.7) |
| T43-IDC_indolocarbazole | MMK-CCTT-011 | Indolocarbazole | `indsynth`, `rebeccamycin`, `staurosporine` |
| T43-PTM_hsaf_tetramate | MMK-CCTT-012 | HSAF/PTM polycyclic tetramate macrolactam | Two detection routes (§A.8) |
| T43-TET_tetronate_spirotetronate | MMK-CCTT-013 / SMK-TET-001 | Tetronate/spirotetronate | — |
| T43-NN_n_n_bond | MMK-CCTT-014 / SMK-NN-001 | N–N bond/diazo/azoxy/hydrazine (CreE/CreD-like) | — |

**AF diagnostic triggers:** T43-NUC, T43-PTM (grant +25 AF diagnostic bonus when corroborated)
**AB diagnostic triggers:** T43-LAN, T43-LASSO, T43-THA, T43-PHO, T43-AMC, T43-BLA
**NOT diagnostic floor triggers:** T43-HAL, T43-XHAL (tailoring-only; defined in `TIER1_FLOOR_EXCLUDED_PREFIXES`)

### A.4 Per-trigger BGC-carrying count vs. raw hit count

Two fields reported; they answer different questions:

- `cctt["counts"]["T43-PHO_phosphonate"]` — raw annotation hits across all CDS
- `cctt["trigger_bgc_counts"]["T43-PHO_phosphonate"]` — BGCs carrying at least one hit

"T43-PHO 8 hits / 1 BGC" = one dedicated phosphonate locus, not a phosphonate-rich strain.

```python
_carry = Counter()
for _trigs in cctt["per_bgc"].values():
    for _t in set(_trigs):   # set: deduplicate per BGC
        _carry[_t] += 1
cctt["trigger_bgc_counts"] = dict(_carry)
```

### A.5 Promiscuous triggers and class-compatibility gate

```python
CCTT_PROMISCUOUS = {
    "T43-HAL_halogenase",
    "T43-XHAL_fluorinase_chlorinase",
    "T43-NN_n_n_bond"
}
```

Promiscuous triggers are never challenged for class incompatibility. All other CCTT triggers are class-defining and subject to the `cctt_trigger_corroborated()` check:

```python
def cctt_trigger_corroborated(trigger, products):
    if trigger in CCTT_PROMISCUOUS: return True
    compat = CCTT_CLASS_COMPAT.get(trigger)
    if not compat: return True
    blob = " ".join(products or []).lower()
    return any(k in blob for k in compat)
```

**Selected compatibility sets:**

| Trigger | Expected product tokens |
|---|---|
| T43-LAN_lanthipeptide | lanthipeptide, lanthi, ripp |
| T43-PHO_phosphonate | phosphonate, phosph |
| T43-NUC_nucleoside | nucleoside, amglyccycl, ripp, ccna |
| T43-PTM_hsaf_tetramate | pks, nrps, transat, hybrid, t1pks, t2pks |
| T43-ENE_enediyne | pks, t1pks, enediyne, transat |
| T43-DKP_cdps | nrps, cdps, diketopiperazine, other, cyclodipeptide |

**Known asymmetry (flagged in code, A3 note):** T43-PTM self-corroborates on broad labels (`pks`, `nrps`); T43-NUC does not. HSAF clusters are frequently typed as generic NRPS/PKS by antiSMASH — intentional design choice, but harder to flag as uncorroborated.

### A.6 Three CCTT vetoes (CCTT_VETOES)

Triggers that fire spuriously on phylogenetically related but biosynthetically distinct gene families:

| Trigger | Veto context | Pattern family |
|---|---|---|
| T43-NUC_nucleoside | glycogen_trehalose | APH sugar-kinase misreads as nucleoside |
| T43-ENE_enediyne | hglE_hglD | hglE/hglD glycolipid KS cross-reacts with ene_KS (PREV-001) |
| T43-DKP_cdps | copalyl_terpene | Copalyl diphosphate synthase (ent-CDPS, a terpene cyclase) |

When the veto fires: trigger removed from `bgc_coupling` for that BGC. Logged in `cctt["related_family_vetoes"]`. **Hard deletion**, unlike the class-compatibility flag which only marks.

### A.7 HSAF/PTM KCB coupling — two routes (`couple_kcb_ptm`)

T43-PTM is injected by a second mechanism for clusters with generic antiSMASH labels:

```python
# Route A — KCB-name-driven
ev = " ".join([bgc.products, bgc.mibig_hits, bgc.kcb_top, bgc.closest_candidate_kcb_product])
route_a = ptm_re.search(ev)   # ptm_re = CCTT_PATTERNS["T43-PTM_hsaf_tetramate"]

# Route B — architecture-driven (conservative)
fl = FLBR coupling for this BGC
lone_hybrid = ("hyb_KS" in fl) and ("mod_KS" not in fl)
route_b = lone_hybrid and re.search(r"tetramate|macrolactam", ev)
# gated: lone hybrid megasynthase + tetramate/macrolactam term
```

### A.8 T43-PHO precision design (4 negative lookaheads)

```python
r"(?<!carboxy)phosphonate(?!.*transporter)(?!.*utilization)(?!.*c-?p lyase)(?!.*phn[g-m]\b)"
```

- `(?<!carboxy)` — excludes carboxyphosphonate (metabolic intermediate)
- `(?!.*transporter)` — excludes phosphonate transporters
- `(?!.*utilization)` — excludes phosphonate utilization regulons
- `(?!.*c-?p lyase)` — excludes C–P lyase operon (catabolism)
- `(?!.*phn[g-m]\b)` — excludes `phnG` through `phnM` (C–P lyase structural genes)
- Plus: `pep mutase(?!\s*family)` and `phosphoenolpyruvate mutase(?!\s*family)` exclude generic database annotations

### A.9 FLBR megasynthase census

```python
FLBR_PATTERNS = {
    "mod_KS":   [r"modular.?ks", r"ketosynthase", r"pks ks", r"beta-ketoacyl synthase"],
    "hyb_KS":   [r"hybrid.?ks", r"nrps.*pks", r"pks.*nrps"],
    "tra_KS":   [r"trans.?at", r"trans-acyltransferase"],
    "mega_NRPS":[r"nonribosomal peptide synthetase"],
}

total_ks   = mod_KS + hyb_KS + tra_KS
total_mega = total_ks + mega_NRPS

if total_ks >= 4 AND fragmented_bgcs:    → "LMPKS_FRAGMENT_SET", "STRONG"
elif total_mega >= 4 OR fragmented_bgcs: → "MEGASYNTHASE_FRAGMENT_SUSPECT", "WEAK"
else:                                    → "NULL", "NULL"
```

**Rescue-readiness tiers:**

```python
if interior_frac < 0.70 AND orphan_ks >= 3 AND fragmented >= 5: → HIGH
elif interior_frac < 0.70 AND (orphan_ks >= 1 OR fragmented >= 3): → MODERATE
else: → LOW
```

**Orphan KS active-site detection (annotation-independent):**

```python
_KS_ACTIVE_SITE = re.compile(r"[DE]TAC[ST]S")   # beta-ketoacyl synthase catalytic cysteine
_AT_ACTIVE_SITE = re.compile(r"GHS[LIVMFQAW]G")  # AT nucleophile elbow (also lipases/esterases)
```

AT-only orphans (GHSxG but no KS motif) are listed separately as Tier-2 alpha/beta-hydrolase-ambiguous and do NOT constitute megasynthase evidence. A CDS ≤400 aa with only the AT motif is flagged `likely_standalone_hydrolase = True`.

### A.10 Resistance tiering

**Four tiers:**

| Tier code | Conditions |
|---|---|
| T1_DIAGNOSTIC_SELF_PROTECTION | Diagnostic groups: Erm_methylase / VanHAX_like / APH_AAC / Fosfomycin |
| T2_RESISTANCE_LIKE | Generic groups only: Beta_lactamase_fold / Self_resistance_general |
| T3_TRANSPORTER_ONLY_ROUTING | Transporter/efflux only, no resistance groups |
| NULL_NO_SOURCE_DERIVED_RESISTANCE | Nothing |

**Class concordance (RES_CLASS_CONCORDANCE):**

```python
"VanHAX_like":        ["glycopeptide"],
"Erm_methylase":      ["macrolide", "lincosamide", "lanthipeptide", "ripp", ...],
"APH_AAC":            ["aminoglycoside", "aminocyclitol", "nucleoside"],
"Fosfomycin":         ["phosphonate"],
"Beta_lactamase_fold":["betalactone", "beta-lactone", "betalactam", "beta-lactam"],
```

**Mobile dominance threshold:**

```python
MOBILE_ELEMENT_CORE = {"integrase", "recombinase", "transposase"}
mobile_dominant = (core_hit AND len(mobile_fams) >= 2) OR (len(mobile_fams) >= 3)
```

A lone flanking IS element (1 mobile family) is NOT dominant.

**APH_AAC veto:** when `APH_AAC` fires AND ±10 kb contains glycogen/trehalose/sugar-kinase context → removed from resistance group set before tiering.

### A.11 Mis-anchor guards (`scan_misanchor_guards`)

**1. Aminoglycoside / DOIS guard:**

```python
aminoglycoside_misanchor = aminoglycoside_anchor AND NOT any(_DOIS_GENE in own CDS)
# _DOIS_GENE = 2-deoxy-scyllo-inosose synthase / BtrC family
```

**2. Polyene macrolide / KS count guard:**

```python
_POLYENE_MIN_KS = 4
polyene_misanchor = polyene_macrolide_anchor AND (ks_domain_count < 4)
```

**3. Enediyne discrimination (PREV-001):**

```python
if ene_specific AND ene_ks >= 1:    → "GENUINE_E_SIGNAL"
elif ene_specific:                   → "ENEDIYNE_MISANCHOR"
elif ene_generic AND prev001:        → "PREV001_ARTIFACT"     # hglE/hglD cross-reaction
elif ene_generic:                    → "E_SIGNAL_UNRESOLVED"
```

Only `GENUINE_E_SIGNAL` (named compound + real ene_KS) is treated as actual enediyne evidence.

### A.12 Per-BGC Diagnostic Signal Score (DSS 0–5)

```python
DSS = min(5,
    +2  if any Tier-1 domain class present (PKS_KS / NRPS_A / TE_release /
            YcaO_TOMM / Halogenase / RiPP_precursor)
    +1  if KCB protein_hits >= 5
    +1  if resistance tier starts with "T1"
    +1  if any CCTT trigger coupled to this BGC
)
```

Marked "source-derived DSS; Sapote §34.3 applies the authoritative formula." Routing precompute only.

### A.13 UMED maturation-gap detection (5,000 bp flank)

```python
UMED_PATTERNS = {
    "LanP_S8_protease":              [r"lanp", r"subtilisin", r"peptidase s8", r"serine protease"],
    "LanT_C39_transporter_peptidase":[r"lant", r"c39", r"peptidase.*abc", r"abc.*peptidase"],
    "FlaP_AplP_S9_protease":         [r"flap", r"aplp", r"peptidase s9"],
    "M16B_metalloprotease":          [r"m16", r"metalloprotease", r"pitrilysin"],
    "YcaO_TfuA_thioamide":           [r"ycao", r"tfua", r"thioamide"],
    "RiPP_RRE":                      [r"ripp recognition element", r"\brre\b"],
    "nucleoside_maturation":         [r"nik", r"nucleoside", r"radical sam", r"aminotransferase"],
}
needs_maturation = any(x in product_text for x in
    ["ripp", "lanthipeptide", "lassopeptide", "thioamide", "azole", "nucleoside"])
```

A **MATURATION_GAP** does not lower the BGC's score — it raises interest. A pathway with a clear precursor architecture and no in-cluster maturation enzyme is a candidate for an off-cluster or split-locus enzyme.

### A.14 EFLS (Edge-Flank Linkage Scan)

```python
+1 per shared antiSMASH product-class token
+2 per shared MIBiG reference hit      ← double weight
+1 per shared cassette family
+1 per shared CCTT trigger

relation = "COMPLEMENTARY_OR_SHARED_EVIDENCE"  if score >= 3
           "WEAK_SHARED_EVIDENCE"               if score < 3 (but > 0)
```

Scope: all-vs-all BGC pairs, **only when at least one member is Edge or Full-contig**. Interior–Interior pairs excluded. Output capped at top 500 scored pairs.

### A.15 bldA/TTA tiering

```python
# actinomycete-gated only
if not actinomycete: tier = "NOT_APPLICABLE"   # GC-noise in non-actinos

if tta_codons == 0:   tier = "T1"
elif tta_codons <= 2: tier = "T2"
elif tta_codons <= 5: tier = "T3"
else:                 tier = "T4"   # >= 6 codons; strongly bldA-sensitive
```

### A.16 TFBS motif scan (12 families, 300 bp upstream window)

| MMK ID | Family | Motif(s) |
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

Claim-safety string (code): "Simple motif scan; replace with calibrated TFBS models/background scoring before manuscript use."

### A.17 15 Cassette families (5,000 bp flank, MMC-001 to MMC-015)

| ID | Family | Tier |
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

The `CASSETTE_REGISTRY_MAP` is hard-coded positional (not name-token join) to prevent `tomm_azole_ripp` from resolving to an indolocarbazole marker on the "carb-AZOLE" substring.

---

## Part B — Architecture-First Assessment

**Source:** `mamey/architecture_first.py` (1,327 lines, v9.7.107 patch v2.2)

### B.1 Purpose and three-step pipeline

Architecture-first prevents KCB confirmation bias — it assesses gene content before reading the KCB hit.

```python
arch, concordance, assignment = architecture_first_assessment(
    genes, boundary_status,
    kcb_compound="", kcb_n_genes=0, kcb_mibig_class=""
)
```

### B.2 Gene classification rules (`_classify_gene`)

- **Megasynthase:** aa > 800 AND (has_ks OR has_amp)
- **has_ks:** PKS_KS, ketoacyl-synt, Ketoacyl-synt, KAsynt_C_assoc, tra_KS
- **has_amp:** AMP-binding, FAAL_cds, FAAL
- **has_cond:** Condensation, C1_LCL through C67_
- **has_at_embedded:** gene has KS AND an AT domain (cis-AT PKS signature)

### B.3 Architecture classification priority order (23 levels, first match wins)

| Priority | Class | Key evidence |
|---|---|---|
| 1 | PTM | Single protein 2,500–4,000 aa with BOTH KS AND AMP-binding; ≤1 other KS, ≤1 other AMP |
| 2 | T2PKS | ≥2 small KS genes (300–550 aa) OR ≥2 t2pks-annotated genes + small ACP |
| 3 | Trans-AT PKS / Hybrid | `tra_KS` OR FkbH OR ≥2 AT-less megasynthases + standalone AT (<600 aa) |
| 4 | T3PKS | Chal_sti_synt |
| 5 | Lanthipeptide | LANC_like or Lant_dehydr |
| 6 | LAP / Ranthipeptide | YcaO alone → LAP; YcaO + SSF → ranthipeptide |
| 7 | Ranthipeptide (YcaO-independent) | SPASM + TIGR03962 |
| 8 | Lassopeptide | Asn_synthase + (Lasso_RRE or no KS) |
| 9 | Mycofactocin | TIGR02109 |
| 10 | DUF692 RiPP | DUF692 |
| 11 | Indolocarbazole | indsynth / StaD / RebC |
| 12 | NAPAA | DUF3516 |
| 13 | Ectoine | Ectoine_synth |
| 14 | NI-siderophore | IucA_IucC WITHOUT NRPS |
| 15 | Butyrolactone | AfsA |
| 16 | Nucleoside | TruD / EPSP_synthase / nikJ |
| 17 | Betalactone | PEP-utilizer + biotin carboxylase |
| 18 | Terpene subtypes | Only when NO megasynthases; linear + PG_binding → PRIMARY_METABOLISM |
| 19 | NRPS siderophore | NRPS + chorismate_bind |
| 20 | PKS/NRPS hybrid | ≥2 megasynthases with both KS and AMP |
| 21 | Pure NRPS | AMP without KS; requires real AMP-binding (FAAL guard) |
| 22 | Cis-AT PKS | KS without AMP |
| 23 | UNKNOWN | Falls through all |

**Boundary adjustment:** Edge or Full-contig → downgrade confidence one tier (HIGH → MEDIUM → LOW). Stored separately in `confidence` (adjusted) and `confidence_raw` (pre-adjustment).

**Module count estimation:**
- PKS modules: `sum(megasynthase_aa with KS) ÷ 1500`
- NRPS modules: `sum(megasynthase_aa with AMP but not KS) ÷ 1100`

### B.4 KCB concordance check

**Coverage check:** `kcb_coverage_pct = kcb_n_genes / query_n_genes × 100`. If < 30% → WEAK_SIGNAL.

**Concordance verdicts:**

| Verdict | Condition |
|---|---|
| CONCORDANT | Architecture matches expected class; or 4 fuzzy-compatible pairs (TRANS_AT_HYBRID↔PKS_NRPS_HYBRID, NRPS_SIDEROPHORE↔NRPS, THIOPEPTIDE↔LAP, TERPENE_CYCLIZED↔HOPANOID) |
| DISCORDANT | Mismatch; architecture wins |
| ARCHITECTURE_DEFERS | Architecture = UNKNOWN AND coverage ≥ 60% → use KCB provisionally at LOW confidence |
| WEAK_SIGNAL | Coverage < 30%, or compound not in class map, or UNKNOWN + coverage < 60% |
| NO_KCB | Empty/null KCB compound |

**Architecture wins in all cases except ARCHITECTURE_DEFERS.**

---

## Part C — KCB / RiQ Extraction

**Source:** `mamey/antismash_evidence.py` (1,081 lines) · `mamey/clusterblast_genes.py` (317 lines)

### C.1 Streaming architecture

```python
_STREAM_JSON_MIN_BYTES = 20 * 1024 * 1024   # 20 MB threshold

def _should_stream(zf, name):
    if not _HAVE_IJSON: return False
    # auto mode: stream >= 20 MB; full-load < 20 MB
    return zf.getinfo(name).file_size >= _STREAM_JSON_MIN_BYTES
```

The 20 MB threshold separates real genome JSONs (55–130 MB → stream) from test fixtures (KB–low MB → full-load). `use_float=True` required for byte-identical output with `json.loads` (ijson defaults to `Decimal`).

### C.2 JSON evidence modes and capacity constants

| Constant | Value | Context |
|---|---|---|
| `BOUNDED_MAX_RECORDS` | 5,000 | Bounded, no streaming |
| `BOUNDED_MAX_RECORDS_STREAMING` | 200,000 | Bounded, streaming |
| `BOUNDED_MAX_JSON_BYTES` | 25 MB | Bounded, no streaming |
| `BOUNDED_MAX_JSON_BYTES_STREAMING` | 250 MB | Bounded, streaming |
| `FULL_MAX_JSON_BYTES` | 20 MB | Full mode hard refusal |

### C.3 KCB extraction from TXT

Best block selection: `max(block_records, key=lambda r: r["score"])`. Only the highest cumulative BLAST score block's protein-hit count is taken. Two-step overwrite for `kcb_top`:

1. Raw rank-1 candidate line. *(Overlay self-hit exclusion, v9.7.252: the nr overlay drops a hit whose subject binomial equals the query genome **and** whose identity is ≥ 99.0%, taking the best hit to another organism instead, so `conservation_median_id` — which feeds `scan_divergence` and the `NOVELTY_CONTRADICTION` guard — no longer reports the genome against itself. Unnamed AS-series strains carry a bare "sp." rather than a binomial, so nothing matches for exclusion and they correctly keep 100.0.)*
2. If a MIBiG significant-hits line exists → overwrite with compound identity: `"{accession} | {product} | knownclusterblast #{rank}"`

**Product provenance hierarchy:**

| Provenance | Condition | Confidence |
|---|---|---|
| MIBIG_REFERENCE_LINE | Significant-hits line found | HIGH |
| KCB_TOP_FIELD | Candidate lines only | MEDIUM |
| UNRESOLVED | No evidence | LOW |

### C.4 KCB recycling audit (structural sanity check)

**Score recycling threshold:**

```python
# Fail if: >= 20 assigned BGCs AND distinct pairs <= max(3, total // 5)
if total >= 20 and distinct <= max(3, total // 5):
    status = "FAIL_SUSPICIOUS_RECYCLING"
```

**Accession-tail mismatch:**

```python
m = re.search(r"[A-Za-z]+0*([0-9]+(?:\.[0-9]+)?)$", contig)
if abs(float(m.group(1)) - float(score)) < 1e-6:
    → FAIL_ACCESSION_TAIL_MISPARSE
```

Catches the specific bug where `CP073042.1 → 73042.1` was extracted as a cumulative score.

### C.5 RiQ label thresholds

```python
if score >= 0.85: return "Likely known"
if score >= 0.50: return "Possibly novel / structural variant"
                  return "Potentially novel"
```

RiQ is captured **before the record cap** to ensure large genomes never lose RiQ scores.

### C.6 Diagnostic TIGRFAM families

| TIGRFAM | Chemotype | Description | Tier-1? |
|---|---|---|---|
| TIGR01454 | ansamycin | AHBA_synth_RP | Yes |
| TIGR03604 | thiopeptide | TOMM/thiopeptide cyclodehydratase | Yes |
| TIGR03828 | enediyne | ene_KS: enediyne PKS | Yes |
| TIGR04186 | nucleoside | NikJ-family | Yes |
| TIGR04462/04460 | enduracididine | Lipid II inhibitor marker | Yes |
| TIGR03550/03551/03620 | F420_polyketide | F420-embedded polyketide | Yes |
| TIGR04363/04364 | lanthipeptide_FxLD | FxLD class-I lanthipeptide | Yes |
| TIGR01181 | glyco_T2PKS | Glycosylated T2PKS | Yes |
| TIGR02353 | NAPAA_marker | ε-poly-L-lysine synthetase | **No** (§8 combo only) |

TIGRFAM hits live in `records[].modules["antismash.detection.tigrfam"].hits[]` — NOT in GBK `sec_met_domain` qualifiers.

### C.7 Functional role profiling (rescue complementarity)

```python
FRC_ASYMMETRY_MIN    = 0.20   # min core-fraction gap to call split complementary
FRC_ACCESSORY_CEILING = 0.30  # fragment with core-fraction <= this is accessory-dominated
FRC_CORE_FLOOR       = 0.35   # both sides above this → both carry a real core

gap = hi_core_fraction - lo_core_fraction

if gap >= 0.20 AND lo <= 0.30:    → COMPLEMENTARY
elif fa >= 0.35 AND fb >= 0.35 AND gap < 0.20: → BOTH_CORE (paralogous, not a split)
elif hi <= 0.30:                   → ACCESSORY_ONLY
else:                              → AMBIGUOUS
```

Calibrated on real AS-series HIGH pairs (genuine paralogs: core-fraction ~0.4–0.55 on both sides; real splits: one fragment accessory-dominated).

---

## Part D — Compound-Class Annotation and Domain-Level Enrichment

**Source:** `mamey/compound_class.py` · `mamey/domain_level.py` · `mamey/dkp_cdps.py`

### D.1 Compound-class chemotype taxonomy (17 named chemotypes)

**Scored chemotypes** (carry explicit axis + weight):

| Chemotype | Axis | Weight | Notes |
|---|---|---|---|
| polyene_macrolide | af | **22** | Calibrated, 3 refs; highest single AF bonus; arylpolyene exclusion mandatory |
| anthracycline | anthracycline | **0** | Routing flag only; cytotoxic; no AF/AB score increment |
| ionophore | ab | **14** | Single reference; conservative; `single_reference=True, confidence="MODERATE"` |

**Annotate-only chemotypes (cytotoxic):** diazofluorene (kinamycin, lomaiviticin), cytotoxic_aromatic_other

**Annotate-only antibacterial/aromatic:** tetracycline, angucycline, pyranonaphthoquinone, ansamycin, macrolide_other, aromatic_t2pks_other

**Annotate-only new families (LOW confidence, 1-ref):** glycopeptide, phenazine, nucleoside_antibiotic, halogenated_phenolic, prenylated_indole

**Hard non-lead exclusion (NONLEAD_EXCLUSION):** patulin, solanapyrone, yanuthone, eicosapentaenoic, fatty acid, spore pigment — `annotate_bgc` returns immediately.

**Polyene-macrolide pigment trap (PIGMENT_EXCLUSION):** arylpolyene, ape , flaviolin, spore pigment, whie, pentangular polyphenol — skips only the polyene_macrolide chemotype, falls through to next.

**antiSMASH class map:** anthracycline always wins when present in the T2PKS prediction set. A chemotype derived from the antiSMASH class alone (not a resolved product name) is stepped down one confidence tier.

### D.2 Domain-level architecture archetype

Two functions with divergent `min_required_hits` defaults — **a known divergence:**
- `architecture_for_roles` uses `min_required_hits=1` (fires on any single required-role hit)
- `classify_architecture` uses `min_required_hits=len(req)` (all required roles must match)

Same templates file, different conservatism. A BGC can receive a different archetype from the two functions when a template's `min_required_hits` is absent. Different deliverables, never directly compared — but a consumer reading both CSV columns expecting consistency would see a silent divergence.

### D.3 DKP/CDPS scanner grades

| Grade | Condition | Confidence |
|---|---|---|
| DKP-A_candidate_dehydro_DKP | CDO/AlbA-like oxidase present nearby | HIGH (Interior) or MEDIUM (Edge) |
| DKP-C_boundary_uncertain | No CDO, BGC is Edge | MEDIUM |
| DKP-B_bare_or_saturated_CDP | No CDO, not Edge | MEDIUM (if product/nearby CDS hit) or LOW (domain only) |

**Hardcoded claim ceiling** (unconditional regardless of grade):

```
"candidate DKP-scaffold BGC; specific dipeptide/product requires isolation"
"same-family-not-same-product; do not assert purincyclamide/albonoursin without chemistry"
```

**Known bugs to document:**

1. `"alba"` in `CDO_CONTEXT_TERMS` is a bare 4-character substring token — matches `"calibration"`, `"ALBA-domain protein"`. Should use `r"\balba\b"`.
2. `"dehydrogenase"` in `HOUSEKEEPING_TERMS` matches all dehydrogenases including biosynthetically relevant ones.
3. `_ROLE_PATTERNS` in `s3_census_generator.py` uses bare substring matching — the same vulnerability fixed in `singleton_filter.py` v9.7.117 is present here.

---

## Part E — Rescue, Concordance, Fragment Ceiling

**Source:** `mamey/diagnostic_rescue.py` · `mamey/concordance.py` · `mamey/fragment_ceiling.py` · `mamey/comparative_pairs.py`

### E.1 Diagnostic rescue claim ceiling (hardcoded, non-negotiable)

```python
CLAIM_CEILING = (
    "Clusterblast-scaffolded reconstruction hypothesis: a homology-guided split-pathway "
    "linkage, NOT a nucleotide-level contig join and NOT a product-identity claim. "
    "Confirm physical linkage by long-read resequencing or PCR across the contig boundary."
)
```

### E.2 Rescue precision floors and tier assignment

```python
COVERED_FLOOR  = 8    # total reference genes both arms must tile
PER_ARM_FLOOR  = 2    # each arm must contribute >= 2 reference genes
TRUNCATED_EDGE = {"Edge", "Full-contig"}

arm_is_diagnostic = arm_roles["hal_trigger"]   # HAL/XHAL only (not bare saccharide)

if has_core AND arm_is_diagnostic AND has_shared AND complementary AND meets_floor:
    → DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE
elif has_core AND has_arm AND has_shared AND complementary:
    → DIAGNOSTIC_RESCUE_MODERATE
elif has_core AND has_arm AND has_shared:
    → DIAGNOSTIC_RESCUE_MODERATE
elif has_core AND has_arm:
    → DIAGNOSTIC_RESCUE_LOW
```

**Complementarity:** `verdict == "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY"` AND `overlap == 0 OR overlap_fraction <= 0.15`.

**Concordance gate effects on tier:**

```
concordant    → tier unchanged
discordant    → HIGH → LOW
indeterminate → HIGH → MODERATE
```

**Adjacency thresholds (heuristic locus-number proxies — code-flagged for tuning):**

```python
ADJ_MAX_LOCUS_GAP = 60    # max gap between locus number ranges
ADJ_MAX_SPAN      = 400   # max span across both arms' locus numbers
```

### E.3 Fragment ceiling

Applies when: (a) Edge or Full-contig, AND (b) `0 < length_kb < 45.0` (`BACKBONE_MIN_KB`), AND (c) product name matches `LARGE_BACKBONE_KEYWORDS` OR `reference_size_kb >= 45.0`.

Ceiling → "class-capacity only (fragment too small for named backbone; do not use product name)."

### E.4 KCB similarity bands (`precision.py:similarity_band`)

| Band | Score range |
|---|---|
| high | ≥ 70 |
| moderate | 40–70 |
| low | 0–40 |
| none | 0 |
| unresolved | None |

**Flagged parallel implementation (B-F1):** `precision.py` uses percent-based thresholds; `chatgpt_commands.py:mode_b_command` uses raw bitscore thresholds (>100k, >50k, >5k, >0). Different scales — a consumer comparing a Mode B card's band to `verdicts.json` band may see a discrepancy.

---

## Part F — Mode B Enrichment Stack

**Source:** `mamey/singleton_filter.py` · `mamey/s3_census_generator.py` · `mamey/enrichment_sections.py` · `mamey/nominal_length.py`

### F.1 Singleton filter — three-tier token-bounded matching (v9.7.117)

Three match tiers, applied in order:
1. **Biosynthetic override** (`_BIOSYNTHETIC_OVERRIDE`) — always KEEP regardless of blocklist
2. **PREFIX** (`r"(?:^|[_-]){stem}"`) — delimited prefix, stem ≥5 chars or clearly housekeeping
3. **EXACT** (`r"(?:^|[_-]){stem}(?=[_-]|$)"`) — complete delimited token
4. **WHOLE** (`domain_lower == stem`) — only when stem is the entire domain name

**Biosynthetic override (7 families, cannot be dropped):**

```python
_BIOSYNTHETIC_OVERRIDE = frozenset({
    "RHS",             # contact-dependent toxins
    "Ntox30",          # RHS-associated toxin
    "Hemerythrin",     # non-heme di-iron tailoring enzyme
    "Spermine_synth",  # polyamine in RiPP scaffolds
    "Peptidase_M23",   # cell-wall enzyme in antifungal BGCs
    "LysM",            # cell-wall binding in antifungal BGCs
    "Transglycosylas", # transglycosylase in antifungal BGCs
})
```

**Fixed false drops (v9.7.117):** `Trans_AT_S1`, `PKS_Docking_S1`, `Peptidase_S1` (caught by bare `"s1"`), `NADHpyr_redox` (caught by `"nadh"`), `GtrA_like` (caught by `"gtra"`), `ABC1_kinase` (caught by `"abc1"`). All six are biosynthetically meaningful domains that were previously silently discarded.

### F.2 §3 size-scaled floor formula

```
§3 floor = 600 + 60 × domain_gene_count
```

The enforcement is in `mode_b_quality_gate.py`; this module generates content to meet it.

### F.3 Enrichment sections composition order and floor

```python
MIN_ENRICHMENT_CHARS = 1000   # character floor for §11–§20 combined content

# Composition order: universal anchors first, then class-specific, then filler
rarest_domains → rarest_genes → halogenase_subtyping → peptide_precursor → nrps_pks_typing → domain_inventory
```

Composition uses a character-count accumulator — adds sections until combined text reaches floor, then stops.

**Two-level sort key for rarity ranking (v9.7.117):**

```python
# For genes: (is_housekeeping_only, min_genome_frequency_of_any_domain)
def gene_rank(g):
    rarity = min((freq.get(dm, 1) for dm in g.domains), default=9999)
    return (_is_housekeeping(g), rarity)
```

`False < True` → biosynthetically relevant singletons (is_housekeeping=False) sort before housekeeping at the same frequency.

**Domain frequency scope:** genome-wide (all BGCs). `freq[dm] == 1` = genome-unique singleton.

### F.4 Nominal length registry (one entry, DRAFT)

```python
polyoxin-class:
  nominal_kb       = 30.0   # mean of JN674503.1 (32.0) and EU158805.1 (27.9)
  confidence       = MODERATE
  confirmed        = False   # n=2, both from Deng/Bai lineage
  nominal_range_kb = (27.9, 32.0)  # ~14% spread
```

Recovery fraction: `frac = lk / ref.nominal_kb; recovery_pct = round(100 * frac, 1)`.

For `frac > 1.0` → "exceeds nominal; reference may be smaller than this cluster."

`[unconfirmed ref]` appended whenever `not ref.confirmed` — always present for the current single entry.

---

## Part G — Flagged Bugs (Bug Log from Vol II Source)

These are defects documented in the Vol II source that may affect output quality. None is critical-path blocking; all are noted for prioritised attention.

| ID | File | Description | Severity |
|---|---|---|---|
| BG-01 | `clusterblast_genes.py` | `min_signal=1` filter in `comparative_pairs` is vacuous at default — the shared-products pre-filter already guarantees signal_count ≥ 1 | Low |
| BG-02 | `antismash_evidence.py` | `riq_score` takes first element, not max, for multi-record region keys | Low |
| BG-03 | `clusterblast_genes.py` | `transport` priority over `regulatory` in `_role_of` is implicit, not documented | Low |
| BG-04 | `diagnostic_rescue.py` | `ADJ_MAX_LOCUS_GAP=60`, `ADJ_MAX_SPAN=400` are heuristic locus-number proxies, not physical distance; code-flagged for tuning | Medium |
| BG-05 | `fragment_ceiling.py` | `_REFERENCE_SIZES` is module-level mutable global with lazy init — stale on patched data directories | Low |
| BG-06 | `concordance.py` | Size uses raw coordinate span (overestimates Edge/FC) vs the corrected BGC size | Low |
| BG-07 | `domain_level.py` | Two `classify_architecture` / `architecture_for_roles` functions with divergent `min_required_hits` defaults | Medium |
| BG-08 | `dkp_cdps.py` | `"alba"` in `CDO_CONTEXT_TERMS` is a bare 4-char substring; should be `r"\balba\b"` | Low |
| BG-09 | `dkp_cdps.py` | `"dehydrogenase"` in `HOUSEKEEPING_TERMS` matches biosynthetically relevant dehydrogenases | Low |
| BG-10 | `s3_census_generator.py` | `_ROLE_PATTERNS` uses bare substring (not token-bounded); same vulnerability fixed in `singleton_filter.py` v9.7.117 | Medium |
| BG-11 | `precision.py` / `chatgpt_commands.py` | Parallel KCB band implementations on different scales (percent vs raw bitscore) | Medium |
| BG-12 | `enrichment_sections.py` | `emit_domain_inventory` top-12 cap is a display heuristic; per-gene supplement only fires for ≤12 domain-bearing genes | Low |
| BG-13 | `nominal_length.py` | Single unconfirmed entry (n=2, same lineage); DRAFT status; all outputs carry `[unconfirmed ref]` | Documented |

**Cluster G** (crosswalk / dedup / merge policy / quality gates) was pending in the Vol II source at time of compilation (v9.7.119). **It is written up below**, transcribed from the live modules at bundle v9.7.250 / engine 1.9.110 — not from the Vol II source, which never covered it.

---

*Sources: `docs/reference/02_Math_Reference_VolII.md` (2,748 lines, Mamey engine v1.9.98 · bundle v9.7.119 · 2026-06-23). All formulas transcribed; all constants cited to `module.py:symbol`. Capacity-level language throughout; KCB = similarity, not identity. Compiled for bundle v9.7.243 · 2026-07-09.*


---

## Part G — Crosswalk, Dedup, Merge Policy, Quality Gates

*Marked **pending** in the Vol II source (v9.7.119). Written here from the live modules at bundle v9.7.250 / engine 1.9.110. Values are read from the running code, not transcribed from the source document — several have drifted (see G.4.6).*

**Source modules:** `mamey/crosswalk.py` (238 lines, **fan-in 11**) · `mamey/dedup_and_guard.py` (100) · `mamey/merge_policy.py` (78) · `mamey/mode_b_quality_gate.py` (359)

---

### G.1 `crosswalk.py` — BGC ↔ contig/node identity

The highest-fan-in module in `mamey/` (eleven importers). Every BGC locator in every deliverable resolves through it. Hardened at v9.7.244–245 after three latent defects; all three are documented here because they define the contract.

#### G.1.1 `region_label(region_number) -> str`

Region numbers are **1-based**. The function is deliberately tolerant of an already-formatted label, because callers read `antismash_region`, whose value *is* the string `"region003"`.

| Input | Output | Rule |
|---|---|---|
| `3`, `"3"`, `"region003"` | `region003` | digits extracted, zero-padded to 3 |
| `0`, `"0"` | `region_unknown` | 0 is invalid, **not** zero |
| `-1`, `"-1"`, `" -12 "` | `region_unknown` | leading minus rejected **before** digits are read |
| `None`, `""` | `region_unknown` | — |
| `"abc"` | `region_unknown` | no digits |

**The `-1` defect (v9.7.245).** `re.search(r"(\d+)", "-1")` matches `"1"` — the sign is not part of `\d+` — so the negative was dropped before the `n > 0` check could see it, and `region_label(-1)` returned `region001`. The function contradicted its own docstring. The guard is now `if re.match(r"^\s*-\s*\d", raw): return "region_unknown"`, applied first.

**The `"region003"` defect (v9.7.244).** Raised `ValueError`. Latent only because every caller happened to pass an `int` — with fan-in 11, a single caller reading `antismash_region` directly would have crashed the run.

#### G.1.2 `contig_key(contig) -> str`

Normalises a SPAdes contig name for use as a dict key. The `_cov_` field is a float whose textual representation varies (`_cov_80.858698` and `_cov_80.0858698` are the same contig); GenBank accessions are left alone, because the type-strain cohort keys on them verbatim.

#### G.1.3 `assembly_locator(row) -> str`

Produces the canonical `NODE_1_length_406707 · region001` citation. The v9.7.244 defect:

```python
# BEFORE — `or` treats 0 as absent, so region 0 silently answered from a different field
region = row.get("region_number") or row.get("Region")
# AFTER — explicit None/"" check
```

**Class:** the `x or y` fallback idiom is unsafe whenever `x` can legitimately be `0`, `""`, `[]`, or `False`. Use `x if x is not None else y`. This is the same class as `DEFAULT_BATCH` never being read — a value that is legitimately falsy, silently discarded.

#### G.1.4 The rest of the surface

`infer_node_id` (contig → `NODE_n`) · `enrich_bgc_crosswalk` / `build_bgc_crosswalk` (emit `*_2b_bgc_crosswalk.csv`) · `bgc_proteins` (per-BGC protein set) · `kcb_closest_gene` and `candidate_blastp_rows` (rank BLASTp candidates via `_BLASTP_PRIORITY_TERMS`, skipping `_KCB_SKIP` annotations).

---

### G.2 `dedup_and_guard.py` — release tiering and the leak audit

#### G.2.1 Identifier patterns (live values)

```python
AS_PATTERN      = r"\bAS-?\d{2,}\b"
AJS_PATTERN     = r"\bAJS-?\d{2,}\b"
PENDING_PATTERN = r"\bPENDING\b"
PUBLIC_PATTERN  = r"^(SID\d+|PSEUDO|AGLAU|ACITR|AGRAE|MHUMI|SPHIL|SCLAV|SDROZ)$"
```

#### G.2.2 `derive_release` — fail-closed by default

Verified live at v9.7.250:

| Strain | `derive_release` | `_trips_private_guard` | Why |
|---|---|---|---|
| `AS-XXX` | **PUBLIC** | False | AS cohort public since the 2026-07-06 PI decision |
| `SID3343` | **PUBLIC** | False | matches `PUBLIC_PATTERN` |
| `AS-XXX` | **PRIVATE** | False | matches no public pattern → **fail-closed default** |
| `AS-XXX` | PRIVATE | — | `AJS_PATTERN` (fail-safe derivation only — AS-XXX is in fact a published genome; the operator asserts `--release PUBLIC` for it) |
| `PENDING-XXX` | **PRIVATE** | **True** | `PENDING_PATTERN`, and it trips the guard |
| `WW-12` | **PRIVATE** | False | unrecognised → fail-closed default |

**Note the asymmetry, and that it is correct.** `AS-XXX` has one digit, so `AJS_PATTERN` (`\d{2,}`) does not match it — yet `derive_release` still returns PRIVATE, because *nothing matches `PUBLIC_PATTERN` either* and the default is PRIVATE. **The tiering is safe by default; only the redaction regex needed the single-digit carve-out**, which is why v9.7.237's P02 fix landed in `tools/redact_public_tier.py` and not here. A strain that is unrecognised is private. `WW-12` demonstrates the same fail-safe.

#### G.2.3 `leak_audit(text)`

Scans a candidate public artifact for unpublished identifiers. The release cut refuses to zip on a hit. Distinct from `redact_public_tier.py`, which *rewrites*; `leak_audit` only *detects*.

#### G.2.4 `fragment_claim_ceiling`

```python
FRAGMENT_BOUNDARIES = {"FC", "Full-contig", "Edge"}
BACKBONE_MIN_KB     = 45.0
```

A fragment on a truncated boundary, shorter than 45 kb, whose product name implies a large backbone (or whose MIBiG reference is ≥45 kb), is capped at **class-capacity only** — "do not use the product name." See Part E for the keyword list and the size-ratio path.

---

### G.3 `merge_policy.py` — supersedure by Pareto dominance

When the same strain arrives from two sources, which one is authoritative? The answer is decided by **Pareto dominance over richness signals**, not by timestamp or by source precedence.

```python
def dominates(a, b):
    keys = set(a) | set(b)
    return (all(a.get(k, 0) >= b.get(k, 0) for k in keys)      # >= on every shared axis
            and any(a.get(k, 0) >  b.get(k, 0) for k in keys))  # >  on at least one
```

`choose_authoritative_source(sources)` returns one of three verdicts:

| Verdict | Condition | Action |
|---|---|---|
| `NOOP` | 0 or 1 source | nothing to de-dup |
| `SUPERSEDE` | exactly one source dominates all others | keep it (schema-normalise the survivor), drop the rest |
| `CONSULT` | **no single source dominates** — each is richer on some axis | **surface the fork to the user** |

`CONSULT` is the design point. A merge that silently picks a winner when neither source dominates loses whichever axis the loser was richer on. **The engine refuses to choose and asks.** This is the same posture as `PHANTOM_LOCUS` fail-silent-without-a-CDS-table: when the machine cannot answer honestly, it says so rather than guessing.

#### G.3.1 Summary-row sentinel

```python
SUMMARY_ROW_SENTINEL = "__SUMMARY__"
_SUMMARY_TOKENS = {"SUM", "TOTAL", "TOTALS", "GRAND TOTAL", "ALL", "ALL STRAINS", "__SUMMARY__"}
```

`is_summary_row(row)` prevents a spreadsheet total row from being ingested as a strain. A `TOTAL` row merged as a strain would carry the sum of every BGC count in the cohort — and would then dominate every real strain on every richness axis.

---

### G.4 `mode_b_quality_gate.py` — depth enforcement

This is the gate that enforces the `§11–§20` enrichment floor that Part F's generators exist to clear.

#### G.4.1 Priority tier from triage rank

```python
def priority_tier(rank):
    if rank is None: return "LOW"   # unknown rank -> the most lenient floor
    if rank <= 10:   return "HIGH"
    if rank <= 25:   return "MID"
    return "LOW"
```

An unknown rank gets the **most lenient** floor. A gate that punished missing metadata would push authors to fabricate a rank.

#### G.4.2 Character floors (live values, v9.7.250)

| Constant | Value | Role |
|---|---|---|
| `FLOORS["HIGH"]` | **12,000** | rank ≤ 10 |
| `FLOORS["MID"]` | **11,000** | rank ≤ 25 |
| `FLOORS["LOW"]` | **10,000** | rank > 25 or unknown |
| `FLOOR_STUB` | **2,000** | below this ⇒ `STUB` regardless of tier |
| `MIN_ENRICHMENT_CHARS` | **2,000** | combined §11–§20 content |
| `FRAGMENT_FLOOR` | **2,500** | replaces the tier floor for a genuine fragment |
| `FRAGMENT_CDS_MAX` | **22** | a fragment is Edge/FC **and** ≤ 22 CDS |

`_FRAGMENT_EDGE_STATUSES = {"edge", "full_contig", "full-contig", "fullcontig"}`

**The fragment exemption (v9.7.114) is the honest part of this gate.** A genuine boundary fragment with three CDS cannot honestly carry 12,000 characters. Demanding it produces padding, which is what the anti-padding rule below exists to catch. So a card that is Edge/Full-contig **and** has ≤ 22 CDS is measured against `FRAGMENT_FLOOR = 2,500` instead.

#### G.4.3 Anti-padding: density, not length

```python
MIN_GENE_MENTIONS  = 12     # absolute floor of gene/domain-specific tokens for FULL
MIN_DOMAIN_DENSITY = 1.0    # gene/domain mentions per 1,000 chars
MIN_SECTIONS       = 4
```

Length alone is trivially gamed. `MIN_DOMAIN_DENSITY` requires that specific gene and domain mentions **scale with the card's length**: a long card with few gene-level tokens is prose padding, not domain-heavy analysis.

**The calibration is stated in the source and is worth repeating**: the real AS-XXX BGC007 card runs at **1.7 mentions per 1,000 chars**, so a floor of **1.0** passes genuine work and rejects padding. The constant is marked *provisional; recalibrate vs exemplars* — and the exemplars are the two files that, until this cut, each carried a foreign locus (Part G.5).

#### G.4.4 Required sections by number

```python
REQUIRED_SECTION_NUMBERS = (9, 10)
```

§9 (alternative hypotheses) and §10 (fragmentation / co-capture risks) are **the two the judgment layer historically omitted**. Checking for them *by number* means a card can no longer reach `FULL` by padding §1–§8 and skipping the two sections that force the author to argue against themselves.

#### G.4.5 The `_RE_LOCUS` regression (v9.7.111)

The gene-mention counter's regex used `\d{4,6}`. Real antiSMASH locus tags are `ctgN_M`, where `M` is typically 1–3 digits. **The regex matched 0% of real locus tags across 5 strains / 3,916 tags**, so every genuinely deep card graded `SHALLOW`. Rewritten to match the structural `ctgN_M` form plus RiPP-precursor suffixes: 100% match, 0 false positives on the validation set.

Note that this is the *same regex family* as `PHANTOM_LOCUS`'s `\bctg\d+_\d+\b` — one counts loci, the other validates them.

#### G.4.6 **Vol II is stale on this module**

The Vol II source (compiled at engine v1.9.98 / bundle v9.7.119) records `MIN_ENRICHMENT_CHARS = 1000` and describes it as "the character floor for §11–§20 combined content," with Part F's composer defaulting to `floor=1000`.

**Live at v9.7.250 the value is 2,000** — raised at v9.7.125 and calibrated against a real 13-card authored batch whose enrichment ran 2,045–7,297 chars (mean 3,809). The thinnest honest card was 2,045, so 2,000 rejects thin enrichment without punishing real work; the source comment notes 2,500+ *would* reject honest cards. That is the padding-pressure line, located empirically.

Similarly, Vol II's Part F describes the tier floors as 9k/8k/6k; live values are **12k/11k/10k**.

**Do not cite Vol II for these constants.** Read `mamey/mode_b_quality_gate.py`. This is exactly the drift that `tools/check_monolith_freshness.py` was built to catch in the monolith — the reference document's *content* was correct when written and is wrong now, with no signal. A constants table in a reference document is a claim, and claims rot.

---

### G.5 Quality gate vs. structure gate vs. referent lint — three different questions

Three modules validate a Mode B card. They are routinely confused. Each asks a different question, and none subsumes another.

| Module | Question | Failure mode it catches |
|---|---|---|
| `mode_b_quality_gate.py` | **Is it deep enough?** | Padding; skipped §9/§10; thin enrichment |
| `modeb_structure_gate.py` | **Is it shaped right, and is it self-consistent?** | Missing sections; `FACT_MISMATCH`; `INTERNAL_CONTRADICTION` |
| `_phantom_locus_findings` (in the structure gate) | **Do the things it cites exist?** | A locus from another organism |

The v9.7.246 fabrication passed the first two. It was a 12,000-character card with §9 and §10 present, adequate density, no internal contradiction — and a gene from *Amycolatopsis* sp. NPDC004378 in §4. **Depth is not accuracy, and shape is not truth.**

---

*Part G compiled 2026-07-09 from `mamey/crosswalk.py`, `mamey/dedup_and_guard.py`, `mamey/merge_policy.py`, `mamey/mode_b_quality_gate.py` at bundle v9.7.250 / engine 1.9.110. Constants read from the running modules. Where these disagree with the Vol II source, the running module is authoritative and the disagreement is noted.*

