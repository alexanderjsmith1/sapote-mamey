# Deliverable and knowledge modules

These pages describe optional outputs you can build after a validated package exists:
wet-lab priorities, metabolomics planning, figure suggestions, reviewer objections and similar.
These pages do not launch tools automatically. Pick a task in the [task router](../USER_TASK_ROUTER.md) first.

Each page says whether a Python tool makes the output or whether it is written by hand.
"Written by hand" means a person or an assistant writes it from the package.
There is no standalone builder for those pages; the chosen output format may still require a verifier.

| Page | Made by | Status |
|---|---|---|
| [ACTIVITY_DECISION_TREES.md](ACTIVITY_DECISION_TREES.md) | `tools/build_activity_decision_trees.py` | Tool |
| [DEEP_BGC_REPORT.md](DEEP_BGC_REPORT.md) | `tools/build_deep_bgc_report.py` | Tool |
| [DELIVERABLE_AssemblyQC.md](DELIVERABLE_AssemblyQC.md) | `tools/assembly_qc_check.py` | Tool |
| [DELIVERABLE_ContigRescueReconstruction.md](DELIVERABLE_ContigRescueReconstruction.md) | `tools/build_reconstruction.py` | Tool |
| [DELIVERABLE_MetabolomicsReadiness.md](DELIVERABLE_MetabolomicsReadiness.md) | `tools/build_metabolomics_readiness.py` | Tool |
| [DELIVERABLE_SubsetPanel.md](DELIVERABLE_SubsetPanel.md) | `tools/build_subset_panel.py` | Tool |
| [DELIVERABLE_WetLabMatrix.md](DELIVERABLE_WetLabMatrix.md) | `tools/build_wetlab_matrix.py` | Tool |
| [DOMAIN_LEVEL_MODE_B.md](DOMAIN_LEVEL_MODE_B.md) | `python mamey_run.py domain-level` | Tool |
| [THESIS_HANDOFF.md](THESIS_HANDOFF.md) | `tools/build_thesis_handoff.py` | Tool |
| [DELIVERABLE_FamilySeeds.md](DELIVERABLE_FamilySeeds.md) | `tools/build_gcf_tags.py` makes the tags; seed rows are written by hand | Tool + hand |
| [DELIVERABLE_LMPKSRescue.md](DELIVERABLE_LMPKSRescue.md) | Domain fields from `mamey/source_scans.py`; grades written by hand | Tool + hand |
| [KNOWLEDGE_DiagnosticDomainCombos.md](KNOWLEDGE_DiagnosticDomainCombos.md) | Domain fields from the package; class calls written by hand | Tool + hand |
| [KNOWLEDGE_JudgmentChecks.md](KNOWLEDGE_JudgmentChecks.md) | Rules in `resources/bioactivity_axes.json`, `mamey/scoring.py` and named tools | Tool + hand |
| [SAPOTE_LEAD_DETAIL_MODULE.md](SAPOTE_LEAD_DETAIL_MODULE.md) | `tools/build_lead_detail.py`; later passes written by hand | Tool + hand |
| [KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md](KNOWLEDGE_Evidence_Axes_and_Lead_Class_Logic.md) | `tools/build_priority_leads.py` | Tool; counts are from one older cohort |
| [KNOWLEDGE_LeadTiers.md](KNOWLEDGE_LeadTiers.md) | `tools/build_lead_tiers.py` | Tool; counts are from one older cohort |
| [MODE_B_BATCH_RUN.md](MODE_B_BATCH_RUN.md) | `mamey/judgment_store.py` | Batch progress; verify cards under the selected profile separately |
| [MODE_B_WRITE.md](MODE_B_WRITE.md) | `mamey/judgment_store.py` | Saving Mode B cards and tracking batches |
| [MODE_B_DEPTH_POLICY.md](MODE_B_DEPTH_POLICY.md) | `mamey/mode_b_quality_gate.py` | Older length-and-density check |
| [DELIVERABLE_EcologicalSynthesis.md](DELIVERABLE_EcologicalSynthesis.md) | Written by hand | Hand |
| [DELIVERABLE_FigureSuggestion.md](DELIVERABLE_FigureSuggestion.md) | Written by hand | Hand |
| [DELIVERABLE_ReviewerAttack.md](DELIVERABLE_ReviewerAttack.md) | Written by hand | Hand |
| [KNOWLEDGE_ConstellationReporting.md](KNOWLEDGE_ConstellationReporting.md) | Written by hand | Hand |
| [_TEMPLATE_Module.md](_TEMPLATE_Module.md) | Template for a new page | Template |

## Rules that apply to every module

- Cite each BGC as **strain / full node-or-contig / region / BGC alias**, copied from one package record.
  Several tool CSVs carry only the alias and region. Join them to the package locator before citing.
  If a part is missing, hold the citation.
- A KnownClusterBlast or MIBiG match is similarity, not compound identity.
- Biosynthetic capacity is not production.
- For a finished Mode B card, use the [Mode B walkthrough](../MODE_B_USER_WALKTHROUGH.md).
  The older section counts in some module examples are history.
- NAPAA follows the current rules registry (`mamey/data/rules_registry.json`).
  Older worked examples that exclude NAPAA outright are history.
