# KNOWLEDGE — Diagnostic Domain Combinations (DDC)

> **Filing.** `docs/modules/KNOWLEDGE_DiagnosticDomainCombos.md`.
> **Extends / references:** `antismash_evidence.py` (GBK `sec_met_domain` Pfam/TIGRFAM extraction — the live source of domain hits), `mamey/sapote_cassettes.py` + `mamey/mamey_markers.py` (the *descriptive* registry of markers/cassettes), `SAPOTE_SLIM_JUDGMENT_KERNEL.md` MODULE 5 (§34 Hallucination-Trap) and MODULE 6 (§43 CCTT). **Do not restate the registry — point to it.**
> **Precedence.** Parent monolith wins. Where this table and a registry `Cassette` disagree, the registry's stable IDs win on naming; this table wins on *combination logic* until the Release-2 HMM backend makes the registry authoritative.
> **Status:** `PROMPT_BACKED` (Sapote applies this lookup to Mamey's already-extracted domains). **Activation note:** the registry's Pfam profiles are *not scanned* in the current pipeline (regex + GBK Pfam only); a pyhmmer/HMMER backend would make these combinations `CODE_BACKED` — see §6.
> **One-line purpose.** Turn a list of extracted domains into a defensible compound-class call, using the fixed "combination → assignment" table that v7.5.2 §8 carried and the v9 kernel never surfaced.

---

## 1. Why this exists / who reads it

A single domain rarely names a class; a *combination* often does. Mamey reliably extracts domains (bitscore, locus tag, Pfam/TIGRFAM accession) but stops short of the class inference — by design, since inference is judgment. This module is the judgment table the Sapote layer applies. It is read whenever a BGC's class call needs to rise above the bare antiSMASH product label (every Mode B §1/§4, every lead-board verdict).

**Skip-not-fake.** A combination is asserted only when *all* its required domains are present in Mamey's extraction at the stated tier. A partial match is reported as "partial — N of M diagnostic domains present," never rounded up to the class call.

---

## 2. Inputs required

| Field (Mamey package) | Feeds |
|---|---|
| `AntiSMASH_Evidence_Parse.json → gbk_pfam_hits[].{domain_name, pfam_acc, bitscore, locus_tag, tier1_diagnostic}` | the domain set per region |
| `manifest.json → bgcs[].products` | the antiSMASH label this table refines or contradicts |
| `_4_triage_board.csv → CCTT_triggers` | cross-check against the cryptic-class trigger flags |

---

## 2a. Combination → assignment table (PORTABLE COPY; authority: registry once HMM-backed)

| Domains present (all required) | Assignment | Claim ceiling |
|---|---|---|
| TIGR04462 + TIGR04460 | Enduracididine-type NRPS; **lipid II inhibitor** class | class-level; "consistent with" |
| TIGR03550 + TIGR03551 + TIGR03620 | F420-embedded polyketide | class-level |
| PF12029 + TIGR02353 | NAPAA / poly-amino-acid candidate | **comparative-EXCLUDED** per NAPAA standing constraint |
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

The last five rows extend §8 with combinations the SID-XXX run proved diagnostic; they are folded in here so the table reflects current practice.

---

## 4. Outputs & contract surface

This module emits no file; it governs the **class-call cell** wherever a BGC is interpreted (Mode B §1/§4, lead board, Fermentation Card target). Each applied assignment must cite the domains and bitscores behind it (e.g. `enediyne — ene_KS 830.8 + TIGR03604 + YcaO`) so the call is auditable against `gbk_pfam_hits`.

---

## 6. Tool / knowledge inventory

| Piece | Owner |
|---|---|
| Live domain extraction | `mamey/antismash_evidence.py` (regex + GBK Pfam) |
| Marker/cassette vocabulary (descriptive) | `mamey/sapote_cassettes.py`, `mamey/mamey_markers.py` |
| Combination → class logic | **this module** (portable copy) |
| Future scanning backend | Release-2 HMMER/DIAMOND — **pyhmmer + targeted `.hmm` set would activate it in-sandbox** |
| Cross-check triggers | kernel MODULE 5 (§34), MODULE 6 (§43 CCTT) |

---

## 7. Worked next-paths closer (SID-XXX)

> Applied DDC to SID-XXX: BGC047 → enediyne (ene_KS 830.8 + TIGR03604 + YcaO; [E-signal]), BGC012 → thioamitide (TfuA+YcaO), BGC063 → phosphonate (PepM; 31P-NMR gate), BGC007/024/032/041 → CDPS/DKP, BGC003/019/042 → NAPAA (comparative-excluded). Next paths:
> 1. Feed these class calls into the Mode B §1 tables for the top leads.
> 2. Activate the §8 HMM backend with a targeted pyhmmer profile set (enediyne/PepM/TfuA-YcaO/CDPS).
> 3. Cross-check each call against its §34 Hallucination-Trap row.
> 4. Add any new diagnostic combination this strain reveals back into this table.
> 5. Bank a second strain to test the enediyne+phosphonate co-occurrence.
