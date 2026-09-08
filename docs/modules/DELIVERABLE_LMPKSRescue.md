# DELIVERABLE — Large Modular PKS Rescue (LMPKS-RW)

> **Filing.** `docs/modules/DELIVERABLE_LMPKSRescue.md`.
> **Extends / references:** `mamey/source_scans.py` + `mamey/antismash_evidence.py` (KS-subtype + reductive-loop + AT-substrate extraction — the live evidence), `mamey/models.py` (KS-domain fields), `prompts/reuse/SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md` (standalone rescue prompt), `DELIVERABLE_WetLabMatrix.md` (where the LMPKS bonus is applied — §33.3 LMPKS table), kernel MODULE 3 (§31 architecture). **Do not restate the WL bonus table — point to it.**
> **Precedence.** Parent monolith wins. This module owns the rescue *grades and report format*; the *domain extraction* it consumes is owned by Mamey code and must not be re-derived by hand.
> **Status:** `CODE_BACKED` (fragment detection / KS inventory) **+ `PROMPT_BACKED`** (module reconstruction narrative, grade assignment, split-pathway hypothesis). This is the one genuinely hybrid module.
> **One-line purpose.** Rescue large modular type-I PKS, macrolide, polyene, trans-AT, and linear-polyketide pathways that antiSMASH labels and KCB scores miss, undercall, or split across contigs — and grade each so the Wet-Lab Matrix can route it.

---

## 1. When it is offered (Deliverable Offer Protocol)

Runs **alongside the KCB sweep**, not after — auto-fire on any §2 trigger. Per `DELIVERABLE_CONTRACT.md`, never make the user ask.

- **Auto-build** when any trigger below fires.
- **Null result is mandatory, not optional:** if no trigger fires, emit a one-page LMPKS null result listing each criterion checked and its outcome. A run with no LMPKS section at all is **incomplete delivery**, even when the answer is "nothing to rescue."

### Trigger conditions (§42.2)

| Trigger | Condition | Action |
|---|---|---|
| 1 — Weak-KCB T1PKS | Interior T1PKS, KCB cumulative <1,500 (incl. 0) | full module reconstruction |
| 2 — Truncated fragment | FC/Edge T1PKS with ≥1 mod_KS/hyb_KS/tra_KS ≥300 bits | fragment rescue |
| 3 — Genome-wide accumulation | genome-wide mod_KS+hyb_KS+tra_KS ≥4 | report `LMPKS_FRAGMENT_SET`; seq priority ↑ |
| 4 — Possible trans-AT | KS/KR/DH/ER present, in-cis PKS_AT absent | trans-AT protocol |
| 5 — Possible polyene | ≥3 DH domains (esp. ER-poor) | polyene rescue |
| 6 — Chemistry mismatch | published PKS chemistry but no clean antiSMASH BGC | map chemistry → domains |

---

## 2. Inputs required

| Field | Feeds | Skip-not-fake |
|---|---|---|
| `gbk_pfam_hits` KS subtypes (mod_KS/hyb_KS/tra_KS/ene_KS/itr_KS), PKS_AT/KR/DH/ER, ACP, docking, TE/Abhydrolase | the domain signature library (§42.3) + module string | a missing reductive domain is shown absent, not inferred present |
| `nrps_pks_consensus` AT substrate (mal/mmal/mxmal) — **requires `--json-evidence bounded/full`** | AT-pattern call (§42.5) | if JSON off, AT substrate = `unscanned`, not guessed |
| `active_site_pairings` (AT specificity, KR L/D config, TE serine) | module completeness + stereochem | — |
| `_4A_RGGMCI_ranked_pairs.csv` | split-pathway grouping (§42.7) | linkage = homology hypothesis, never asserted nucleotide join |
| `manifest.json → bgcs[].edge_status` | `[missing start]`/`[missing terminus]` prefixes | — |

---

## 3. Pipeline

KS inventory + fragment accumulation are `CODE_BACKED` (Mamey scans). Module reconstruction and grading are Sapote judgment over those fields.

```text
1. (Mamey) extract genome-wide KS inventory + reductive loops + AT substrates + docking + TE.
2. (Sapote) per triggered BGC, reconstruct the module string in gene order (§42.4).
3. (Sapote) estimate broad class only — chain length is a LOWER BOUND from module count (§42.5).
4. (Sapote) group cross-contig fragments by KS subtype/AT pattern/docking (§42.7); cite RGGMCI.
5. (Sapote) assign exactly one rescue grade (§42.11).
```

Required claim-safety sentence for any split model:
> "Split-pathway rescue hypothesis based on modular PKS domain architecture across contigs; long-read sequencing is required to confirm physical linkage and module order."

---

## 3a. Rescue grades (PORTABLE COPY; authority: monolith §42.11)

| Grade | Definition | WL bonus (applied in `DELIVERABLE_WetLabMatrix.md`) |
|---|---|---:|
| LMPKS-A | ≥3 complete modules + TE + classifiable AT/reductive | +2 |
| LMPKS-B | ≥2 modules + docking/split evidence, incomplete termini | +1 |
| LMPKS-C | fragment accumulation ≥4 KS, insufficient ordering | +1 (seq priority only) |
| LMPKS-D | single high-bitscore fragment, no joining evidence | 0 |
| LMPKS-T | trans-AT confirmed/strongly supported | +2 |
| LMPKS-P | polyene confirmed/strongly supported | +2 |
| LMPKS-L | linear PKS ≥3 modules, no TE recovered | +1 |
| LMPKS-X | trigger fired, evidence fails rescue | 0 (null) |

Highest-applicable only; LMPKS bonuses do not stack with each other.

---

## 4. Outputs & contract surface

| Artifact | Stable id |
|---|---|
| LMPKS Rescue Report PDF (or 1-page null) `[Strain]_LMPKS_Rescue_Report_YYYY-MM-DD.pdf` | `LMPKS_report` |
| Genome-wide KS inventory table | `LMPKS_ks_inventory` |
| Per-BGC module string + grade | `LMPKS_modules` (carries into WL sheet) |
| Split-pathway model (if any) | `LMPKS_split` |

---

## 5. Acceptance checklist (= §42.12)

- [ ] Every Interior T1PKS with KCB <1,500 evaluated; every FC/Edge T1PKS with KS ≥300 evaluated.
- [ ] Genome-wide KS count reported; `LMPKS_FRAGMENT_SET` set when ≥4.
- [ ] Docking domains + TE/Abhydrolase searched and reported.
- [ ] AT predictions summarized (mal/mmal/mxmal) where JSON evidence present; else `unscanned`.
- [ ] trans-AT criteria checked for AT-missing PKS; polyene criteria for DH-rich.
- [ ] Exactly one grade per triggered BGC/fragment set; null result page if no trigger.
- [ ] Long-read recommendation updated where fragment accumulation/split evidence exists.
- [ ] Contig-ID locators; no compound named without chemistry; affiliation = .
- [ ] exactly 8 unique plain-text next-paths.

---

## 6. Tool / knowledge inventory

| Piece | Owner |
|---|---|
| KS subtype / reductive / AT extraction | `mamey/source_scans.py`, `mamey/antismash_evidence.py`, `mamey/models.py` |
| Grades & report format | this module (portable copy of monolith §42.11) |
| WL bonus application | `DELIVERABLE_WetLabMatrix.md` §3a |
| Standalone rescue prompt | `prompts/reuse/SAPOTE_FRAGMENT_RESCUE_REUSE_PROMPT.md` |

---

## 7. Worked next-paths closer (SID-XXX)

> LMPKS run: genome-wide KS accumulation flags the 017/035/072 NRPS-PKS megaset (`LMPKS_FRAGMENT_SET`, ≥3 contigs → long-read Priority 1). BGC036/038/056 = malonyl-specific reducing modules (036 all-L KR ×3). No clean LMPKS-A; megaset graded LMPKS-C pending long read. Next paths:
> 1. Reconstruct the 036/056 split module string with the JSON active-site calls now available.
> 2. Apply the resulting LMPKS-C +1 seq-priority adjustment in the Wet-Lab Matrix.
> 3. Run trans-AT protocol on any AT-missing module in the megaset.
> 4. Generate the LMPKS Rescue Report PDF.
> 5. Long-read the strain to convert the fragment set into a real module order.
