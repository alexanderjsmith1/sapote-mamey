# Mode B authoring preflight — do NOT write a card until every box is checked

*New doc (v9.7.321 candidate). Referenced from `skills/sapote-mamey/SKILL.md`. Exists because multiple
chats have authored Mode B cards without reading the class exemplar, without running BLASTp, or without
requesting the data from the operator. The gates check the output; this checklist governs the workflow.*

## The failure this stops

A card can pass `verify-modeb` + `claim-safety` while being authored on thin evidence — a §4 built from
antiSMASH-Pfam calls with no per-gene BLASTp, in a format that ignores the class exemplar. That is not a
finished card; it is a skeleton with prose. The three steps below are ordered and mandatory.

## Step 0 — Read the class exemplar (before writing anything)

- [ ] Identify the BGC's product class (antiSMASH `product` labels).
- [ ] Open `docs/reference/modeb_exemplars/<class>_exemplar.md` for the closest class
      (`nrps`, `nrps_pks_hybrid`, `t1pks`, `t2pks`, `terpene`, `siderophore`, `ripp`; check
      `modeb_exemplars/README.md` for slot status). If no exemplar exists for the class, use the nearest
      and hold to `docs/modules/MODE_B_DEPTH_POLICY.md`.
- [ ] Note the depth bar: the exemplar's §4 is an **evidence grid**
      `| Locus | aa | antiSMASH domains | BLASTp top hit (nr) | %id | Reconciliation |` with **●** core
      markers, followed by a **prose walkthrough**. Mirror that shape (do not copy verbatim).

## Step 1 — Get the per-gene BLASTp (before §4 exists)

The §4 reconciliation must rest on REAL per-gene BLASTp of the target BGC's **rule-based-biosynthetic
cores** — never panel-only, never Pfam-only.

- [ ] List the BGC's rule-based cores (the `biosynthetic (rule-based-clusters)` CDS in the package
      `cds_table` / region GBK).
- [ ] Obtain each core's sequence from the **region GBK** (gold tags + translations together — the clean
      source) or the cohort DB `aa_seq` **with** the region→gold-tag reconciliation (region-relative DB
      ORFs ≠ gold contig tags for sliced regions).
- [ ] Run BLASTp: NCBI, or **EBI** (`mamey/blastp_ebi.py`) when NCBI throttles.
- [ ] **If you cannot run it, request it from the operator** — name the strain + the region GBKs you need,
      or the exact cores to BLASTp — and record the gap in §4 / §16 as an explicit request. Do NOT fill
      the gap with Pfam prose and present the card as done.
- [ ] Reconcile every hit as CONFIRM / REFINE / OVERTURN against the antiSMASH call; tag provenance
      (store-backed vs reconstructed; gbk_verified is the highest-confidence tag).

Escalation triggers (large modular proteins, repeated comparator hits, split/composite BGCs) are in
`docs/MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md`.

## Step 2 — Author to the contract + exemplar

- [ ] Full §1–§30 (no compact entries). §4 as the evidence grid + prose walkthrough from Step 0.
- [ ] Cite BGCs by node·region; loci must be the strain's own package loci (PHANTOM_LOCUS guard).
- [ ] Claim language: "capacity consistent with," never "produces"; KCB/BLASTp = similarity not identity;
      bioactivity extract-level only. Keep certainty copulas away from KCB compound names
      (`identity_overclaim` fires on "class is robust/known(<compound>)", "<compound>-like product").

## Step 3 — Run all THREE gates and report receipts

- [ ] `mamey verify-modeb <card> --package <pkg> --bgc <BGC>` → **OK** (structure + depth).
- [ ] `mamey claim-safety <card> --package <pkg> --card-id <BGC> --mode warn` → **0 HIGH/0 MEDIUM**.
- [ ] `mamey.mode_b_quality_gate.evaluate_card(<BGC>, <md>)` → tier **FULL** (MID/LOW = not done).
- [ ] Report the numbers (char count, gene mentions, gate output), not "passes / clean / solid."

## Hub handoff (if a producer chat)

Drop `AS-XXX_BGCNNN_ModeB_card.md` + `AS-XXX_BGCNNN_ModeB_card.meta.json`
(`{author_chat, depth, blastp_core_coverage, gates}`) into the integrator's `incoming/<STRAIN>/`. The
integrator re-runs all three gates as the single authority — a producer's "passed on my end" is not
sufficient.
