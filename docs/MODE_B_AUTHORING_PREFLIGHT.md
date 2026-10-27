# Mode B authoring preflight: draft eligibility, evidence readiness, finished promotion

## Three states, three different bars
Missing evidence does not mean the same thing at every stage. Check which state you are claiming.

| State | Permitted when | A missing channel means |
|---|---|---|
| **Draft (gap-aware)** | `PASS_FOR_GAP_AWARE_AUTHORING` (`MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md` §5): an exact canonical locus, plus a gene-level source bound at exact-locus or alias level. | Write the gap explicitly with its typed state: absent, available but not ingested, unbound, or adjudicated terminal hold. Never fill it with Pfam prose. |
| **Evidence readiness** | Each channel the selected profile needs has been obtained or ingested and bound to the exact sequence; see Step 1. | A result that exists but is not ingested is work to do, not a gap to declare. Ingest it before calling the channel missing. |
| **Finished (current evidence)** | The selected profile's contract and reconciliation are complete for the evidence that exists (`MODEB_PROFILE_MATRIX.md`). | A finished card may still carry `OBSERVED_UNBOUND` rows (`MODEB_STATUS_VOCABULARY_RATIFIED_v9_7_373.md`). Promotion stays held while required evidence is available but uningested, attainable but unobtained, active, or freshness-unverified. An adjudicated terminal limitation may remain only with its reason, typed state and claim ceiling; an unbound row cannot support a protein/function assertion (availability contract §5). |

The checklist below governs **readiness and promotion**. A draft may start after Step 0 with its gaps typed;
it may not be called finished until Steps 1–2 hold for the selected profile. Remote search requirements do not by
themselves authorize submitting sequences.

## Checklist for readiness and promotion

## The failure this stops

A card can pass `verify-modeb` + `claim-safety` while being authored on thin evidence — a §4 built from
antiSMASH-Pfam calls with no per-gene BLASTp, in a format that ignores the class exemplar. That is not a
finished card; it is a skeleton with prose. The steps below are ordered, and mandatory before promotion.

## Step 0 — Read the class exemplar (before writing anything)

- [ ] Identify the BGC's product class (antiSMASH `product` labels).
- [ ] Read the [exemplar reader guide](reference/modeb_exemplars/README.md), then the closest class sketch
      (`nrps`, `nrps_pks_hybrid`, `t1pks`, `t2pks`, `terpene`, `siderophore`, `ripp`). If the class has no
      exemplar, use the nearest for writing register and consult `docs/modules/MODE_B_DEPTH_POLICY.md`.
      The class sketches are legacy teaching examples, not complete full48/current50 v2 templates;
      their old FULL/OK labels do not establish current-profile completion.
- [ ] Learn how the sketch connects its gene evidence to prose, but build the new card from the selected
      emitted template. Use that profile's complete-roster, channel-separated table requirements rather
      than copying a legacy nr-only grid. Preserve protein lengths, actual database/channel and transport,
      named matches and reconciliation; do not relabel EBI/UniProt as nr or merge nr, ClusteredNR and Swiss-Prot.

## Step 1 — Prepare per-gene evidence before promotion

Start with the target BGC's **rule-based biosynthetic cores** and their real per-gene BLASTp evidence,
keeping unavailable channels as typed draft gaps. The finished-card evidence table is §4 in full48 and
§50 in current50 v2. It must account for the complete canonical gene roster with the selected profile's
separate channel pairs; a selected-core table, panel summary or Pfam-only explanation does not complete it.

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
- [ ] Reconcile every hit as CONFIRM / REFINE / OVERTURN against the antiSMASH call. Retain the actual
      source provenance and its query/sequence, exact-locus, channel and receipt bindings. A provenance
      label alone does not establish those bindings.

Escalation triggers (large modular proteins, repeated comparator hits, split/composite BGCs) are in
`docs/MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md`.

## Step 2 — Author to the contract + exemplar

- [ ] Select the intended named profile and its actual contract/verifier before authoring.
      Use [the profile matrix](MODEB_PROFILE_MATRIX.md): the native default is full48;
      opt-in current50 v2 uses `--contract current50_v2` on both emit and verify. Its evidence
      table is §50 rather than §4; apply the table checks below to that selected-profile section.
      The native corrective contract `mamey/data/mode_b/modeb_full30_corrective_contract.json`
      defines 48 sections despite its historical filename. Use the emitted template's exact titles
      and selected profile requirements. The separate 50-section reference and its specific
      consumers are described in `docs/MODEB_FULL50_CONTRACT_USAGE.md`; do not treat that reference
      as universal native 50-section producer/verifier support.
- [ ] Bind every individual locus as `strain / full node-or-contig / region / BGC alias` from one
      selected source record. Hold missing/conflicting fields; do not shorten or reconstruct them.
- [ ] Frame source-derived locus claims as "capacity consistent with" rather than measured production;
      KCB/BLASTp similarity does not identify a product, and extract bioactivity does not establish a locus phenotype.
      Inspect identity-overclaim findings in context: the linter uses production/copula patterns, compound-name
      context and capacity/negation guards. A clean heuristic result does not substantiate a compound claim.

## Step 3 — Run the selected mechanical gates and retain their actual outputs

- [ ] Before a full48 finished-card check, include the active declaration
      `**Document state:** FINISHED_FULL48_CURRENT_EVIDENCE` in the saved authored file; `--contract full48`
      alone does not activate publication checks. For current50 v2, preserve the emitted canonical
      identity/contract/profile header as the first line. These declarations select checks rather than certify evidence.
- [ ] From the bundle root, run `python mamey_run.py verify-modeb <authored-card.md>
      --package <pkg> --bgc <BGC> --contract full48`; for current50 v2 substitute `--contract current50_v2`.
      Use the same contract as `emit-modeb-template`, and retain actual findings and exit status.
      See the [walkthrough](MODE_B_USER_WALKTHROUGH.md) for saving verification receipts and source bindings.
      This is mechanical verification, not scientific acceptance.
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

`verify-modeb`/`claim-safety` findings are mechanical outputs, not an independent auditor receipt.
The claim-safety command prints findings; it writes a CSV only when --report is selected, and warn mode
returns zero with findings. Preserve the actual output and destination rather than assuming an automatic
persistent receipt. The additive library depth check does not replace the selected profile’s full review
path. The availability planner’s CURRENT/promotion label is an aggregate indicator, not sequence/admission
or complete-channel verification; review the actual source rows and profile requirements.

Default structure lint treats §31–§48 as optional or conditional, so its exit 0 does not mean all 48 sections are complete. Verify against the finished profile you selected.
