# Read current and proposed lead tiers together

Make the table with `python tools/build_lead_tiers.py --banked-dir cohort --out ChemistryFirst_Recall.csv`.
`--banked-dir` is the banked cohort folder; `--bioactivity antifungal` limits it to one axis.

Start with one row in `ChemistryFirst_Recall.csv` and ask why it is present and whether its
`current_tier` differs from `proposed_tier`. Copy the complete **strain / full node-or-contig /
region / BGC alias** from the bound inventory before citing the row: this CSV uses bank-local
`sid` and `bgc` selectors and does not export the full locus identity.

## What the two tier columns mean

For stored `CONFIRM` verdicts, `tools/build_lead_tiers.py` computes:

- **Current A:** the selected per-locus coupling entry contains exact `SARP`; otherwise the writer assigns B. Missing/unresolved coupling keys are not assessed negatives.
- **Proposed A:** that SARP entry or the writer's self-protection condition is present; otherwise B.
- **HOLD-QC:** the strain is in the available assembly-QC hold set; both tier columns remain held.

The self-protection condition accepts a profile `resistance_tier` beginning
`T1_DIAGNOSTIC_SELF_PROTECTION` or one of the selected resistance-coupling families. This is
source annotation evidence used for a proposed review order, not proof of expression, measured
activity or independent physical linkage. The proposed column does not change the canonical
`tools/build_priority_leads.py` A/B/C rule. Read
[the composite-score guide](KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md) for that writer.

Check that every verdict and coupling key resolves uniquely to the same admitted BGC inventory and full locus identity. Hold missing, conflicting or duplicate bindings even when a tier is emitted. The writer treats an absent strain/locus coupling key like an empty list; verify assessment coverage before interpreting `n` or B. A malformed present value can instead fail.

## What can be missing from the recall view

The writer reads cohort `bgc_data.json`, `tfbs_coupling.json` and a cohort-level
`modeb_verdicts.csv`. It selects stored `CONFIRM` rows only. The verdict CSV is optional in the
current implementation: if missing, the output can be header-only. That is not evidence that
no pathway could pass an authored review. Missing optional `deep_data.json` and
`resistance_coupling.json` also change available self-protection support. A present but malformed
`assembly_qc.json` stops this writer. That includes a file that parses but has no `held_qc` key,
or whose `held_qc` is not a list of nonempty strain names. An absent file does not establish
that QC passed.

When a row is absent, check those input states and any `--bioactivity` filter before drawing a
biological conclusion. Keep the source bank/version and exact command with the saved output.
The writer replaces the requested CSV and writes through a fixed `<out>.tmp` path. Use a fresh authorized directory and verify that both paths are unoccupied and not links; preserve earlier files before a rerun. Atomic replacement of one file is not full identity admission or a transaction over the inputs.

## Read the activity label as a lookup result

`bioactivity_axis` comes from the first matching keyword group in
`resources/bioactivity_axes.json`, applied to stored class, note and KCB-anchor text. The
fallback label is `antibacterial (general)`, given when no keyword group matches. If the table
cannot be read, or has no valid `axes_in_priority_order` list, the writer stops instead of
labeling rows. A generic nucleoside phrase without an earlier
keyword match is gated by the stored strain chitin-context flag; that flag is not an assay.
The table is deterministic for the same inputs, but it does not verify the compound, target or
biological activity. In particular, a default activity label does not establish an observed hit.

`--bioactivity antifungal` is a substring filter on those assigned labels. It removes other rows
from that output rather than exporting a separate adjacent partition. Read the unfiltered view
when the question is what was left out. Sorting first favors the nucleoside priority flag, then
promoted proposed-A rows, then the configured activity order; it is not a measured potency ranking.

## Use a difference to choose the next review question

For a current-B/proposed-A row, inspect the self-protection record and competing explanations.
For a current-A row, inspect both the stored CONFIRM and per-locus SARP source. Keep candidate
regulator coupling separate from a demonstrated regulatory effect. For a selected authored
interpretation, follow [the Mode B walkthrough](../MODE_B_USER_WALKTHROUGH.md), carrying the
same complete locus identity, admitted evidence and unresolved gaps into the card.

## Historical cohort context

The earlier module reported **12 Class-A leads** under the CONFIRM-and-SARP rule
and a **6 → 11** proposed change in its recall view for one reference cohort. Those figures are historical reports;
they do not define a new cohort's counts or authorize adoption of the proposed rule. The older
redacted locus examples, target claims and azoxy/strictness theme lack complete bindings in this
page. Recover their same-run evidence before using those individual cases in a paper. The
original archived module retains that history; it is not a verified current locus roster.
