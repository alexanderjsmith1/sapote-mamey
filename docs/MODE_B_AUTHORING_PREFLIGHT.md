# Prepare to write a Mode B card

Check whether you can start a draft and what you still need to finish the card. You need a package, the complete locus identity and a gene-level evidence source. To emit the template, write the card and run its checks, use the [walkthrough](MODE_B_USER_WALKTHROUGH.md). This page explains the evidence decisions along that path. Terms are in the [glossary](GLOSSARY.md).

## Begin a draft

You can start a draft when the planner reports `PASS_FOR_GAP_AWARE_AUTHORING` for the locus. That needs an exact locus and a gene-level source tied to it by exact locus or by alias. The state comes from the `modeb-availability` command. It reads a per-BGC inventory table (CSV or TSV) and writes `modeb_bgc_availability.tsv` and a summary into `--out`. Its `writing_gate` column holds the state. A `HOLD_` value in that column means you cannot start yet. Run `python mamey_run.py modeb-availability --help` for the arguments.

Write the locus as **strain / full node-or-contig / region / BGC alias**, copied from one source record. If a field is missing or two sources disagree, leave it unresolved and say so.

Read the closest class sketch in the [exemplar guide](reference/modeb_exemplars/README.md), and the [profile matrix](MODEB_PROFILE_MATRIX.md) for what each profile requires. Use the sketch for writing style only. Write in the template you emitted. The FULL and OK labels in the older examples do not mean a card is complete under the current profile.

Name each gap as one of four things: absent, available but not ingested, unbound, or an adjudicated terminal hold. If you already have a result, ingest it and check it before you call that channel missing. See the [availability contract](MODEB_DATA_AVAILABILITY_AND_WRITING_CONTRACT.md).

## Assemble the gene evidence

Start with the rule-based biosynthetic core genes in the region GenBank file (GBK) or the package `cds_table`. Take the translations together with their gene tags.

For each search, keep the sequence, database, transport, result and source. The EBI transport defaults to `uniprotkb_bacteria`. Label it that way, not as nr. Keep nr, ClusteredNR and Swiss-Prot results in separate channels. Read the [online-search protocol](ONLINE_BLASTP_PROTOCOL.md) before you send sequences.

Mark each hit CONFIRM, REFINE or OVERTURN against the antiSMASH call. Give protein lengths and named matches. The finished evidence table covers the whole gene roster: section 4 for full48, section 50 for current50_v2. A table of core genes only, or an explanation from Pfam alone, leaves that work unfinished.

When you cannot get evidence, name the exact sequence or source file you need and record the gap. For large modular proteins, repeated matches and split or composite candidates, use the [escalation workflow](MODEB_EVIDENCE_ESCALATION_WORKFLOW_v97143a.md).

## Use the selected profile

Choose the profile once, in the [profile guide](MODEB_PROFILE_MATRIX.md), and copy the emitted section titles. Add `--contract current50_v2` to both emit and verify only if you chose that profile. The [50-section reference](MODEB_FULL50_CONTRACT_USAGE.md) lists which tools read it.

Keep what the sequence suggests separate from what was measured. A gene set shows capacity. A database match shows similarity. Neither shows production or activity. If you name a product, check it against the evidence, including results that disagree.

## Check the saved draft

Run `verify-modeb` as the walkthrough's step 5 shows. Then run the claim check on the same saved file and keep both outputs:

```bash
python mamey_run.py claim-safety <card.md> --package <package>
```

The claim check runs in warn mode by default, so it exits 0 even with findings. Add `--report <new-file.csv>` to write its CSV. The path must not exist yet, and it cannot be the card itself; a refused path prints `REFUSED:` and exits 2. Add `--append-report` only when you mean to add rows to an existing report. Add `--mode fail` to make findings fail the check.

For a full48 finished-card check, add the line `**Document state:** FINISHED_FULL48_CURRENT_EVIDENCE` when the card is ready. The walkthrough, step 5, shows where it goes. Without it, the structure check treats sections 31 to 48 as optional, so a zero exit does not show the card is finished. For current50_v2, keep the emitted first line (the identity, contract and profile header) as it is.

## Finish and save

These keep the card open: evidence that exists but is not ingested, evidence you could get but have not, evidence still being produced, and evidence whose freshness is unchecked. An adjudicated terminal limitation can stay if you give its reason, its type and its scope. Rows marked `OBSERVED_UNBOUND` can stay, but they cannot support a claim about a protein's function.

Save the card with its full identity, the source hashes, the profile, the real check output and the open questions, as the walkthrough's step 6 says. Review the evidence yourself. Do not treat a clean check as permission to integrate or publish. Before you trust a planner's overall CURRENT label, read the channel rows behind it.
