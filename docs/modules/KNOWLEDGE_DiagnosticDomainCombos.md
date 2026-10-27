# KNOWLEDGE — Diagnostic Domain Combinations (DDC)

Use this page when a product label leaves a class question unresolved. Start with the selected
region's extracted domain rows, then compare the historical lookup below with their gene tags,
scores and source coverage. Keep **strain / full node-or-contig / region / BGC alias** with the note.

The lookup is a prompt interpretation aid, not an executable classifier. `mamey/antismash_evidence.py`
owns extraction; `mamey/source_scans.py` and `mamey/scoring.py` own their implemented triggers and
ranking rules. Marker/cassette registry entries provide vocabulary; their presence does not
establish that a scan ran or that a proposed class is correct.

---

## 1. Why this exists / who reads it

A single domain rarely names a class; a combination often does. Mamey extracts the domains; this table is how a reader turns them into a class call. Apply it whenever a class call must go beyond the antiSMASH label (every Mode B §1/§4, every lead-board verdict).

**Skip-not-fake.** A combination is asserted only when *all* its required domains are present in Mamey's extraction at the stated tier. A partial match is reported as "partial — N of M diagnostic domains present," never rounded up to the class call.

---

## 2. Inputs required

| Field (Mamey package) | Feeds |
|---|---|
| `[strain]_AntiSMASH_Evidence_Parse.json → gbk_pfam_hits[region_key][]` | Read each row's `domain_name`, `pfam_acc`, `bitscore`, `locus_tag` and `tier1_diagnostic`; the outer object is keyed by region, not a flat hit list |
| `manifest.json → bgcs[].products` | the antiSMASH label this table refines or contradicts |
| `_4_triage_board.csv → CCTT_triggers` | cross-check against the cryptic-class trigger flags |

---

## 2a. Historical combination lookup: candidate assignments to review

| Domains present (all required) | Assignment | Claim ceiling |
|---|---|---|
| TIGR04462 + TIGR04460 | Enduracididine-type NRPS; **lipid II inhibitor** class | class-level; "consistent with" |
| TIGR03550 + TIGR03551 + TIGR03620 | F420-embedded polyketide | class-level |
| PF12029 + TIGR02353 | NAPAA / poly-amino-acid candidate | neutral under the current rules registry; no blanket comparative exclusion |
| TIGR04363 + TIGR04364 | FxLD class-I lanthipeptide | class-level |
| PF19402 ×3 | Triple-precursor class-III lanthipeptide | class-level |
| PF00109 + PF02514 + TIGR01181 + PF01041 | Glycosylated T2PKS | class-level |
| TIGR03604 ×2 | TOMM heterocyclic RiPP | class-level |
| PF00668 Cglyc-type + HHILLDG motif | Glycopeptide-type condensation | sub-class; flag for module review |
| ene_KS (high bitscore) + TIGR03604 + YcaO | **Enediyne chromoprotein** | class-level; **[E-signal] note** (cytotoxic; standard-SOP handling) |
| TfuA + YcaO | Thioamitide (thioviridamide-class) RiPP | class-level |
| PEP_mutase (PepM) | Phosphonate biosynthesis (committed) | class-level; **31P-NMR gate** before compound claim |
| CDPS (single gene) | Cyclodipeptide synthase / diketopiperazine | class-level |
| Trp_halogenase / Flavin halogenase | Halogenated scaffold | tailoring flag, not a standalone class |

Use the rows to frame a class hypothesis, then cite the actual domain records and the scientific source supporting the mapping. The earlier cohort example is not a complete source-bound locus record and does not establish diagnostic accuracy for a new input.

---

## 3. Outputs & contract surface

This module emits no file; it governs the **class-call cell** wherever a BGC is interpreted (Mode B §1/§4, lead board, Fermentation Card target). Each applied assignment must cite the domains and bitscores behind it (e.g. `enediyne — ene_KS 830.8 + TIGR03604 + YcaO`) so the call is auditable against `gbk_pfam_hits`.

---

## 4. Tool / knowledge inventory

| Piece | Owner |
|---|---|
| Saved upstream domain extraction | `mamey/antismash_evidence.py`: GBK `sec_met_domain` rows plus selected antiSMASH JSON TIGRFAM records merged into the region-keyed hit object |
| Marker/cassette vocabulary (descriptive) | `mamey/sapote_cassettes.py`, `mamey/mamey_markers.py` |
| Combination → class logic | **this module** (portable copy) |
| Optional HMM evidence | `run --hmm-scan` already calls `mamey/registry_detector.py::run_hmm_scan` and writes `[strain]_HMM_Scan.json`. Inspect its per-region status and bound source; `HMM_SCAN_UNAVAILABLE` is not a no-hit result. This route does not make the lookup table an automatic classifier. |
| Cross-check triggers | kernel MODULE 5 (§34), MODULE 6 (§43 CCTT) |

---

## 5. Turn one lookup into a review note

Copy the complete locus identity from one bound source record. Record the required domains,
the observed rows and scores, and which required components remain unobserved or unavailable.
For a partial match, retain the observed fraction rather than assigning the full class.
Then state the candidate interpretation and the source that would support or challenge it.

For an authored card, continue with [the Mode B walkthrough](../MODE_B_USER_WALKTHROUGH.md)
and its selected profile. The older redacted cohort examples lack complete locators and cannot
be reused as current locus evidence.
