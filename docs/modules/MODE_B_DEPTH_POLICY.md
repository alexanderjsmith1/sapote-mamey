# Mode B — depth policy, data sources, and per-class exemplars

*v9.7.205. Raises the depth bar and re-centers it on domain-level substance. Companion to
`DOMAIN_LEVEL_MODE_B.md` (the tool that surfaces the data) and the §1–§30 contract
(`mamey/data/mode_b/modeb_full30_corrective_contract.json`). Enforced by
`mamey.mode_b_quality_gate`.*

## The bar (v9.7.205)

A full Mode B card is now expected to be **heavy on aSDomain-level detail plus per-gene BLASTp**, not
prose. The gate enforces two things together:

- **Raised char floors, compressed across tiers:** HIGH 12,000 · MID 11,000 · LOW 10,000 (was 9k/8k/6k).
  Tiers are compressed so an important-but-**fragmented** BGC — which lands at a low rank because it sits
  on a short/edge contig, not because it's less interesting — is no longer dropped to a soft floor. A
  genuine boundary fragment still gets the `FRAGMENT_FLOOR` exemption (assembly reality, not a downgrade).
- **No padding — domain density:** a FULL card must carry **≥ 1.0 gene/domain·BLASTp mention per 1,000
  chars** (`MIN_DOMAIN_DENSITY`), and ≥ 12 absolute. A long card with thin domain content grades SHALLOW
  with the message *"looks padded; add aSDomain/BLASTp detail, don't pad prose."* Calibration anchor: the
  real verified §30 card AS-XXX BGC007 is 36k chars / 109 mentions (3.0/1k) — the floor sits well below
  genuine work and only catches padding.

> **Provisional calibration.** These numbers are anchored on one real §30 card + the depth directive. The
> per-class exemplars below are the real calibration set; expect to revisit whether small classes need a
> class-specific floor once they land.

## This makes multiple rounds/batches the norm — by design

A domain-heavy card **rarely completes in one pass.** When a card is short on domain substance, the fix is
**not** to pad — it is to **gather more evidence in another round**: run per-gene BLASTp on the un-BLASTed
core genes, re-parse the antiSMASH aSDomains for the region, pull KCB/MIBiG context. Author in **batches**
across BGCs so each evidence round (a BLASTp submission set, a domain re-parse) amortizes over many cards.
Making the domain-heavy standard the default *necessitates* this — accept it rather than shortcut it.

## Where to find the domain-level data (don't infer it — read it)

| Evidence | Source | How |
|---|---|---|
| **aSDomains** (KS/AT/KR/DH/ER/ACP, C/A/PCP/TE, e-values, descriptions) | antiSMASH region JSON / per-region GBK `aSDomain` features | `mamey domain-level --package … --source-antismash STRAIN.zip` (full path; see `DOMAIN_LEVEL_MODE_B.md`). Limited path (names only) from the sealed gene context when no zip. |
| **Per-gene BLASTp** (nearest homolog, % identity = similarity, sciname, e-value) | `blastp-online` output → `B5_BLASTp_Hits` / master workbook | run `mamey blastp-round` (representative per BGC) then full per-gene on the leads; ingest via `mamey ingest-blastp`. Absent until run — say so, don't invent. |
| **Domain roles / burden / claim ceiling** | `domain-level` module output | role category + per-BGC burden + safe/unsafe claim pair (architecture/family-level only). |
| **Gene table** (`sec_met_domains`, products) | `<strain>_gene_by_gene_all_bgcs.csv` | note the `sec_met_domains` re-tokenization caveat (micKC↔Pkinase etc.) — weakly-supported, never "lacks domain". |
| **KCB / MIBiG** (similarity, not identity) | `knownclusterblast` / triage `KCB_top` | corpus provenance; feeds §8 and the §24 novelty axis. |
| **Deep domain hits / active sites** | `deep_data.json` (`domain_hits`, `bgc_profile`) | note: `active_sites` is empty under `json_mode:off` — do not report 0% as measured. |

Cite every BGC **node·region**, tag provenance (**store-backed** vs **reconstructed** vs **corpus**), and
keep claim language capacity-level ("consistent with", never "produces"); BLASTp/KCB is similarity, not
identity; bioactivity is extract-level only.

## Per-class exemplars — the gold standard

`docs/reference/modeb_exemplars/` holds **one good card per BGC class** (NRPS, T1PKS, T2PKS, T3PKS, hybrid
NRPS-PKS, RiPP, terpene, siderophore/NRP-metallophore, saccharide/oligosaccharide, other). Each exemplar is
the concrete depth/format target for its class — mirror the exemplar for the class you're authoring rather
than guess the bar. See `modeb_exemplars/README.md` for the slot status. *(Exemplars are provided by the Developer or User;
until a class's exemplar lands, hold to the gate floor + this policy.)*

## Over-merged regions must address the co-captured class (expect CONTENT_GAP)

The depth gate keys off the region's **product labels**, so an over-merged region demands content about the
**co-captured** system even when you're scoping the product claim to one protocluster: a terpene co-capture
(e.g. BGC038) requires a GPP/FPP/GGPP mention; an NRPS co-capture (e.g. BGC036) requires an
adenylation/Stachelhaus mention. This is `CONTENT_GAP` firing correctly — it forces the author to acknowledge
the co-capture rather than silently ignore half the region. Address the co-captured class's diagnostic
(precursor / Stachelhaus / prenyltransferase / etc.), then scope the product claim to the intended protocluster.
