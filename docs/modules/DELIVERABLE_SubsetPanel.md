# DELIVERABLE — Subset Panel (cross-cohort / cohort-subset figure)

## 0. Header block
> **Filing.** `docs/modules/DELIVERABLE_SubsetPanel.md`.
> **Extends / references:** [FIGURE_STYLE.md](../FIGURE_STYLE.md) (data-only figures), [FIGURE_REPRODUCIBILITY.md](../FIGURE_REPRODUCIBILITY.md) (CSV + `--replot`),
> [DELIVERABLE_INSTRUCTION_TEMPLATE.md](../../deliverables/DELIVERABLE_INSTRUCTION_TEMPLATE.md) (tier palette + locus-label format), [GENERIC_PROMPT_LIBRARY.md](../../deliverables/GENERIC_PROMPT_LIBRARY.md) (G2, G6).
> Do not restate those rules here — they are inherited.
> **Precedence.** The current user task and [assistant governance](../ASSISTANT_GOVERNANCE.md) govern actions. Use the selected figure contracts and actual source; the monolith is a design/history reference.
> **Status:** `CODE_BACKED` — `tools/build_subset_panel.py` produces the artifact.
> **One-line purpose.** A grouped figure of the loci matching a product tag (or strain set), after the figure
> policy removes pure-saccharide regions, so a cross-cohort chemical theme reads at a glance.

## 1. When to use it
Use it when you want to see or compare the `{PRODUCT_TAG}` clusters, a cohort slice or a named strain set as a
figure, and for G2 or G6. A count or a table does not replace a requested panel, and a full-cohort plot does not
replace a requested subset.

## 2. Inputs required
| File / field | Feeds | Required for |
|---|---|---|
| `bgc_data.json` (products, length_kb, edge_status, closest_kcb_product, closest_mibig) | locus rows + tier | always |
| `strains.json` (organism) | genus lane grouping | lane axis |
| `modeb_verdicts.csv` (status) | verdict + Confirmed tier | tier coloring |
| `tfbs_coupling.json` (per-BGC SARP coupling) | SARP y/n column | SARP annotation (per-BGC, not strain-level) |

**Missing values:** `sarp` is `y` or `n` only when `tfbs_coupling.json` has a record for that BGC; with no table,
strain or BGC record it is blank. A missing `length_kb` is blank in the CSV, the locus is not placed on the size
axis, and the run prints how many loci were left off; the panel title counts placed loci. A missing or unrecognized verdict is shown as `[EG]`, not upgraded. This is a display fallback, not proof an offline review occurred. A present null or empty coupling entry also yields `n`; inspect the assessment source before interpreting it as a tested negative.

**Which loci.** The figure policy removes pure-saccharide regions before the tag or strain filter, and the run
prints how many it removed. The panel is therefore the matching loci after that policy, not every matching locus.
Rows carry `sid`, `contig`, `region` and `bgc_id`; copy the full **strain / full node-or-contig / region / BGC alias**
from the bound inventory before citing one. **SARP is the per-BGC `tfbs_coupling.json`
set (canonical, per `KNOWLEDGE_Evidence_Axes`), not the strain-level `SARP_BTAD_like` count.**

## 3. Pipeline (exact, ordered commands)
```bash
# product-tag panel (G2)
# output names are fixed; an existing CSV or PNG is refused (exit 2, OUTPUT_REFUSED), so use a fresh --out-dir
python tools/build_subset_panel.py --banked-dir merged_cohort --tag phenazine --out-dir reviews/EXAMPLE-subset-tag
# strain-set panel (G6 subset)
python tools/build_subset_panel.py --banked-dir merged_cohort --strain-set "EXAMPLE_A,EXAMPLE_B" --out-dir reviews/EXAMPLE-subset-strains
# reproduce from the banked CSV
python tools/build_subset_panel.py --replot --csv reviews/EXAMPLE-subset-tag/subset_phenazine_loci.csv --tag phenazine --out-dir reviews/EXAMPLE-subset-replot
```
Substitute the selected tag, exact bound strain roster and fresh paths; quote spaces. `--replot` reads saved locus rows without recomputing their bank joins, but title/footer context also depends on the original tag and command. Preserve both and compare the resulting outputs before claiming reproduction. `Candidate-novel` is a display rule from selected fields, not demonstrated novelty. A missing CSV is
refused (exit 2, `REPLOT_INPUT_MISSING`); it is never rebuilt from the bank. Single source
of truth for tier assignment = `tier_of()` in `build_subset_panel.py` (a separate copy of the atlas function in `generate_bgc_atlas.py`; the two differ, because this one also treats a missing `closest_mibig` as dark).

## 4. Outputs & manifest surface
- `fig_subset_{label}[_PRIVATE].png` — the panel (lanes = genera, chips = loci, color = confidence tier).
- `subset_{label}_loci.csv` — the locus table (sid, region, contig, bgc_id, genus, class, kcb, kb, edge, sarp, verdict, tier);
  this CSV is the stable, citable artifact and the `--replot` source. The `_PRIVATE` suffix is added when any
  row's strain ID starts with `AS` (case-insensitive). That is a name-prefix rule, not a privacy check.

## 5. Acceptance checklist
- [ ] FIGURE_STYLE: data-only (no interpretive arrows); reading is in the caption.
- [ ] FIGURE_REPRODUCIBILITY: CSV emitted + `--replot` verified.
- [ ] Independently verify authorization and disclosure for every included identity and the full output before public use. The AS-prefix suffix is not clearance; retain the selected privacy profile and actual review scope.
- [ ] Claim-safety caption: shared thread = `{TAG}` machinery / E-signal, **not one compound**; KCB anchors `~`.
- [ ] Every locus row carries strain / region / class / ~KCB anchor / edge-status / SARP / verdict.
- [ ] Tier palette + legend match `DELIVERABLE_INSTRUCTION_TEMPLATE.md`.
- [ ] No retired codenames.
- [ ] Hand back the result, its evidence and open holds.

## 6. Tool / knowledge inventory
| Piece | Owner |
|---|---|
| filter + join + CSV + plot | `tools/build_subset_panel.py` |
| tier assignment logic | `tier_of()` in `build_subset_panel.py` (a separate copy of the one in `generate_bgc_atlas.py`; the two differ) |
| tier palette + locus label | `deliverables/DELIVERABLE_INSTRUCTION_TEMPLATE.md` |
| invoking prompts | `deliverables/GENERIC_PROMPT_LIBRARY.md` G2, G6 |

## 7. Possible follow-ups
- Panel a different product tag to compare distributions.
- Take a Confirmed (green) chip to a G4 single-BGC Mode B card.

