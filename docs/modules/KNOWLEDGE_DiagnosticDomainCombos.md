# Diagnostic domain combinations

Use this page when an antiSMASH product label leaves the class of a cluster unclear. A single protein domain rarely names a class. A combination often points to one. The table below lists combinations to check against a cluster's domain rows. It is a lookup for a person to read. No code applies it. For terms such as BGC and package, see the [glossary](../GLOSSARY.md).

## Where the domain rows come from

The engine reads domains from the antiSMASH region GBKs and from antiSMASH's TIGRFAM results. It saves them in `<strain>_AntiSMASH_Evidence_Parse.json`, under `gbk_pfam_hits`. That object is keyed by region. Each row has `domain_name`, `pfam_acc`, `bitscore`, `evalue`, `locus_tag` and `tier1_diagnostic`.

Three things limit the table.
- `TIGR02353` is recorded for combination checks only. It is not a tier-1 diagnostic.
- TIGRFAM rows (`TIGR#####`) are recorded for the accessions in `DIAGNOSTIC_TIGRFAM` in `mamey/antismash_evidence.py`. Pfam rows appear only if antiSMASH wrote them as `sec_met_domain` text in the GBK.
- No code scans for sequence motifs. A row that names a motif needs a manual check of the protein.

`run --hmm-scan` adds HMM evidence in `<strain>_HMM_Scan.json`. `HMM_SCAN_UNAVAILABLE` means no scan result exists for that scope, for different reasons: as the file's top-level status, the scan could not start (its `reason` says why); on a row, the scan of that region was attempted and failed or returned no usable result (read the row's `reason`). `SOURCE_GBK_UNBOUND` on a row means its region file was not found exactly once. When any row is not `PASS`, the top-level status is `PASS_WITH_DEGRADATION`. None of these is a no-hit result.

## The lookup

Count a combination only when every listed domain is present in the selected region. If some are missing, write "partial: N of M domains present". Do not round a partial match up to the class.

Check how each TIGRFAM row was placed before you trust its region. Its `region_assignment` is `COORDINATE_RESOLVED` when the hit's location falls inside one region's span. A hit outside every recorded region is keyed `<record>_unassigned` (`OUTSIDE_ALL_REGIONS`). A hit with no readable location, or from a record without region spans, is keyed to region 1 by fallback (`UNRESOLVED_FALLBACK_REGION1`); hold that row until you have checked its source location.

"Copies" in the table means separate source genes. The rows are per feature and can repeat a gene, so a row count is not a copy count. Count distinct locus tags with their source coordinates, and hold repeated or missing tags.

| Domains present (all required) | Candidate class | Claim ceiling |
|---|---|---|
| TIGR04462 + TIGR04460 | Enduracididine-type NRPS (lipid II inhibitor class) | class-level, "consistent with" |
| TIGR03550 + TIGR03551 + TIGR03620 | F420-embedded polyketide | class-level |
| PF12029 + TIGR02353 | NAPAA (non-alpha poly-amino acid), poly-amino-acid candidate | class-level. The rules registry (`mamey/data/rules_registry.json`) scores NAPAA as neutral: not downgraded, not excluded. The project leaves NAPAA out of cohort BiG-SCAPE comparisons and strain decks. |
| TIGR04363 + TIGR04364 | FxLD class-I lanthipeptide | class-level |
| PF19402, three copies | Triple-precursor class-III lanthipeptide | class-level |
| PF00109 + PF02514 + TIGR01181 + PF01041 | Glycosylated type II PKS | class-level |
| TIGR03604, two copies | TOMM heterocyclic RiPP | class-level |
| PF00668 (Cglyc-type) + HHILLDG motif | Glycopeptide-type condensation | sub-class; motif is a manual check; send for module review |
| ene_KS (TIGR03828) alone | Enediyne | class-level. The engine treats `ene_KS` alone as the defining enediyne marker (`mamey/sapote_markers.py:37`, `SMK-ENE-001`). A genuine call also counts antiSMASH `PKS_KS` Enediyne-KS domains (`ene_ks_count`, `mamey/source_scans.py:1843`). Confirm a real `ene_KS` against an hglE-KS glycolipid cross-reaction (`mamey/source_scans.py:1688-1694`). Cytotoxic class: handle with care. |
| TfuA + YcaO | Thioamitide-type RiPP | class-level |
| PEP mutase (PepM) | Phosphonate biosynthesis | class-level; a compound claim needs 31P-NMR evidence |
| CDPS, single gene | Cyclodipeptide synthase, diketopiperazine | class-level |
| Tryptophan or flavin halogenase | Halogenated scaffold | tailoring flag, not a class |

A class-level ceiling means the note says what the domains are consistent with. It never names a compound or an activity.

## Turn a lookup into a review note

1. Copy the full identity from one record: **strain / full node-or-contig / region / BGC alias**.
2. List the required domains, the rows you found, and their bitscores. For example: `ene_KS 830.8`.
3. Say which required domains are missing or unavailable. For a partial match, keep the fraction.
4. State the candidate class and the source that would support or challenge it.

To use the note in a card, follow the [Mode B walkthrough](../MODE_B_USER_WALKTHROUGH.md).
