# Prepare to write a Mode B card

Check whether you can begin a draft and what is still needed to finish it.
You need the package, the complete locus identity and a gene-level source.
Use the [walkthrough](MODE_B_USER_WALKTHROUGH.md) to emit a template, write the
card and run its checks. This page explains the evidence decisions along that path.

## Begin a draft

`PASS_FOR_GAP_AWARE_AUTHORING` requires an exact canonical locus and a gene-level
source bound at exact-locus or alias level. Identify the locus as **strain / full
node-or-contig / region / BGC alias** from one source record. Keep missing or
conflicting identity fields unresolved.

Read the closest class sketch in the [exemplar guide](reference/modeb_exemplars/README.md)
and the [depth policy](modules/MODE_B_DEPTH_POLICY.md). Use the sketch for writing
style, then write in the current emitted template. Legacy FULL/OK labels describe
those older examples, not completion under the current profile.

Mark gaps as absent, available but not ingested, unbound, or an adjudicated terminal
hold. A result you already have should be ingested and checked before calling that
channel missing. See the [availability contract](MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md).

## Assemble the gene evidence

Start with the rule-based biosynthetic cores in the region GBK or package
`cds_table`. Get translations together with their gene tags. If using cohort-DB
`aa_seq`, reconcile region-relative ORFs to the source contig tags first.

For each search, keep the sequence, database, transport, result and source binding.
The EBI transport defaults to `uniprotkb_bacteria`; label it that way rather than
as nr. Keep nr, ClusteredNR and Swiss-Prot channels separate. Read the
[online-search protocol](ONLINE_BLASTP_PROTOCOL.md) before sending sequences.

Reconcile each hit as CONFIRM, REFINE or OVERTURN against the antiSMASH call.
Include protein lengths and named matches. The finished evidence table covers
the complete canonical gene roster: §4 for full48 or §50 for current50 v2.
A core-only table or Pfam-only explanation leaves that work unfinished.

When evidence cannot be obtained, name the exact sequence or source file needed
and record the gap. The [escalation workflow](MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md)
covers large modular proteins, repeated matches and split/composite candidates.

## Use the selected profile

The native default is **full48**. Its historical contract filename contains
`full30`, but it defines 48 sections. Copy the emitted titles.
Choose `--contract current50_v2` on both emit and verify only when using that
profile. The separate [50-section reference](MODEB_FULL50_CONTRACT_USAGE.md)
has its own consumers; use the [profile matrix](MODEB_PROFILE_MATRIX.md) to
check which contract the producer and verifier actually support.

Keep source-derived capacity and similarity separate from measured production
or activity in the written conclusion. Check a claimed product against the
corresponding evidence, including contradictory results.

## Check the saved draft

Run the walkthrough's `verify-modeb` and `claim-safety` commands on the saved
file and keep the findings. `claim-safety` defaults to warn mode, which exits 0
even with findings. Use `--report` when you need its CSV; otherwise it prints
to the terminal. Select `--mode fail` only when you want findings to fail that check.

For a full48 finished-card check, add the active declaration
`**Document state:** FINISHED_FULL48_CURRENT_EVIDENCE` when the authored file
is ready for that check. The ordinary structure lint treats §31–§48 as optional
or conditional, so its exit status alone cannot answer whether the card is finished.
For current50 v2, keep the emitted canonical identity/contract/profile header
as the first line.

The optional Python API `mamey.mode_b_quality_gate.evaluate_card` takes the full
authored text and the selected record's rank, edge status and CDS count. Report
its tier (FULL/SHALLOW/STUB), priority (HIGH/MID/LOW) and floor separately.
Omitting rank selects the most lenient priority. Keep this result alongside the
selected profile's checks and the actual evidence review.

## Finish and save


Evidence that is available but not ingested, attainable but unobtained, active,
or freshness-unverified keeps completion open. An adjudicated terminal limitation
can remain with its reason, typed state and scope. `OBSERVED_UNBOUND` rows may
remain, but cannot support a protein/function assertion.

Save the card with its full source identity, source hashes, selected profile,
actual check outputs and unresolved questions in the agreed destination. Use
the walkthrough's receipt steps. Keep evidence review separate from mechanical
findings and from permission to integrate or publish. Review the actual channel
rows before relying on an availability planner's aggregate CURRENT label.

<a id="three-states-three-different-bars"></a>
<a id="checklist-for-readiness-and-promotion"></a>
<a id="the-failure-this-stops"></a>
<a id="step-0--read-the-class-exemplar-before-writing-anything"></a>
<a id="step-1--prepare-per-gene-evidence-before-promotion"></a>
<a id="step-2--author-to-the-contract--exemplar"></a>
<a id="step-3--run-the-selected-mechanical-gates-and-retain-their-actual-outputs"></a>
<a id="explicitly-selected-handoff"></a>
