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
      with each match's actual database/channel and transport, plus locus, protein length,
      antiSMASH domains, identity and reconciliation, with **●** core markers and a prose
      walkthrough. Use the selected profile's current table contract; do not relabel EBI/UniProt
      matches as nr or merge nr, ClusteredNR and Swiss-Prot evidence.

## Step 1 — Get the per-gene BLASTp (before §4 exists)

The §4 reconciliation must rest on REAL per-gene BLASTp of the target BGC's **rule-based-biosynthetic
cores** — never panel-only, never Pfam-only.

- [ ] List the BGC's rule-based cores (the `biosynthetic (rule-based-clusters)` CDS in the package
      `cds_table` / region GBK).
- [ ] Obtain each core's sequence from the **region GBK** (gold tags + translations together — the clean
      source) or the cohort DB `aa_seq` **with** the region→gold-tag reconciliation (region-relative DB
      ORFs ≠ gold contig tags for sliced regions).
- [ ] Bind each sequence and search's actual database, transport and provenance before using
      results. The bundled EBI transport (`mamey/blastp_ebi.py`) defaults to `uniprotkb_bacteria`,
      not nr. Follow `docs/ONLINE_BLASTP_PROTOCOL.md` and the selected transport's admission
      requirements; keep later nr confirmation or other unresolved channel gaps explicit.
- [ ] **If you cannot run it, request it from the operator** — give the complete
      `strain / full node-or-contig / region / BGC alias` and source-bound region GBKs you need,
      or the exact cores to BLASTp — and record the gap in §4 / §16 as an explicit request. Do NOT fill
      the gap with Pfam prose and present the card as done.
- [ ] Reconcile every hit as CONFIRM / REFINE / OVERTURN against the antiSMASH call; tag provenance
      (store-backed vs reconstructed; gbk_verified is the highest-confidence tag).

Escalation triggers (large modular proteins, repeated comparator hits, split/composite BGCs) are in
`docs/MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md`.

## Step 2 — Author to the contract + exemplar

- [ ] Select the intended named profile and its actual contract/verifier before authoring.
      The native corrective contract `mamey/data/mode_b/modeb_full30_corrective_contract.json`
      defines 48 sections despite its historical filename. Use the emitted template's exact titles
      and selected profile requirements. The separate 50-section reference and its specific
      consumers are described in `docs/MODEB_FULL50_CONTRACT_USAGE.md`; do not treat that reference
      as universal native 50-section producer/verifier support.
- [ ] Bind every individual locus as `strain / full node-or-contig / region / BGC alias` from one
      selected source record. Hold missing/conflicting fields; do not shorten or reconstruct them.
- [ ] Claim language: "capacity consistent with," never "produces"; KCB/BLASTp = similarity not identity;
      bioactivity extract-level only. Keep certainty copulas away from KCB compound names
      (`identity_overclaim` fires on "class is robust/known(<compound>)", "<compound>-like product").

## Step 3 — Run all THREE gates and report receipts

- [ ] From the bundle root, use `python mamey_run.py verify-modeb <authored-card.md>
      --package <pkg> --bgc <BGC>` under the selected installed profile and gates; retain the
      actual findings and exit status. This is mechanical verification, not scientific acceptance.
- [ ] Run `python mamey_run.py claim-safety <authored-card.md> --package <pkg> --card-id <BGC>
      --mode warn` and inspect the finding counts: warn mode exits 0 even when findings exist.
- [ ] If using the additional library depth checker, call
      `mamey.mode_b_quality_gate.evaluate_card(bgc_id, authored_markdown_text, rank=rank,
      edge_status=edge_status, cds_count=cds_count)` from Python with the full text and the
      selected source record's context. It is an API, not a shell command. Report its `tier`
      (`FULL`, `SHALLOW`, `STUB`) separately from `priority` (`HIGH`, `MID`, `LOW`) and `floor`;
      omitted rank selects the most lenient priority. A FULL depth verdict is not science acceptance.
- [ ] Retain selected contract/profile identity, character count, gene mentions, gate findings,
      priority/floor context and unresolved holds; do not replace them with “passes/clean/solid.”

## Explicitly selected handoff

Select the recipient and authorized output destination before writing. A previous receipt path,
chat label or folder name does not authorize that destination. Use a filesystem-safe complete
identity such as `STRAIN__FULL_CONTIG__REGION__BGC_ALIAS__ModeB_card.md` and a companion receipt
binding source files/hashes, the selected profile, actual gate outputs and unresolved holds.
The recipient checks those bindings and any required gates. Mechanical gate results do not grant
scientific acceptance, integration, publication or sealing authority.
