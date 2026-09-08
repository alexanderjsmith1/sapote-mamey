# DELIVERABLE — Subset Panel (cross-cohort / cohort-subset figure)

## 0. Header block
> **Filing.** `docs/modules/DELIVERABLE_SubsetPanel.md`.
> **Extends / references:** `FIGURE_STYLE.md` (data-only figures), `FIGURE_REPRODUCIBILITY` (CSV + `--replot`),
> `DELIVERABLE_INSTRUCTION_TEMPLATE.md` (tier palette + locus-label format), `GENERIC_PROMPT_LIBRARY.md` (G2, G6).
> Do not restate those rules here — they are inherited.
> **Precedence.** `DELIVERABLE_CONTRACT.md` wins over this module; the active parent monolith wins over everything.
> **Status:** `CODE_BACKED` — `tools/build_subset_panel.py` produces the artifact.
> **One-line purpose.** A grouped figure of every locus matching a product tag (or strain set), so a cross-cohort
> chemical theme reads at a glance — closing DLV-008 and making G2/G6 deterministic.

## 1. When it is offered (Deliverable Offer Protocol)
Offered whenever a user asks to *see* or *compare* "all the `{PRODUCT_TAG}` clusters", a habitat/cohort slice, or a
named strain set as a figure — and whenever G2 or G6 is invoked. Incomplete delivery = returning a count or a
table when a panel was the ask, or plotting the full cohort when a subset was requested. Per the contract, the
user need not know the tool exists: build the panel and hand it back, or offer it as the first next-path.

## 2. Inputs required
| File / field | Feeds | Required for |
|---|---|---|
| `bgc_data.json` (products, length_kb, edge_status, closest_kcb_product, closest_mibig) | locus rows + tier | always |
| `strains.json` (organism) | genus lane grouping | lane axis |
| `modeb_verdicts.csv` (status) | verdict + Confirmed tier | tier colouring |
| `tfbs_coupling.json` (per-BGC SARP coupling) | SARP y/n column | SARP annotation (per-BGC, not strain-level) |

**Skip-not-fake:** a field absent for a locus is left blank/`[EG]` and labelled, never invented; a verdict that
isn't in `modeb_verdicts.csv` is shown as `[EG]` (offline), not upgraded. **SARP is the per-BGC `tfbs_coupling.json`
set (canonical, per `KNOWLEDGE_Evidence_Axes`), not the strain-level `SARP_BTAD_like` count.**

## 3. Pipeline (exact, ordered commands)
```bash
# product-tag panel (G2)
python tools/build_subset_panel.py --banked-dir merged_cohort --tag {PRODUCT_TAG} --out-dir figures
# strain-set panel (G6 subset)
python tools/build_subset_panel.py --banked-dir merged_cohort --strain-set {SID####,SID####} --out-dir figures
# reproduce from the banked CSV
python tools/build_subset_panel.py --replot --csv figures/subset_{label}_loci.csv --out-dir figures
```
Reproducibility: `--replot` re-renders from the emitted `subset_{label}_loci.csv` with no recompute. Single source
of truth for tier assignment = `tier_of()` in `build_subset_panel.py` (shared logic with `generate_bgc_atlas.py`).

## 4. Outputs & manifest surface
- `fig_subset_{label}[_PRIVATE].png` — the panel (lanes = genera, chips = loci, colour = confidence tier).
- `subset_{label}_loci.csv` — the locus table (sid, region, genus, class, kcb, kb, edge, sarp, verdict, tier);
  this CSV is the stable, citable artifact and the `--replot` source. `_PRIVATE` suffix is set automatically when
  any AS strain is in the subset.

## 5. Acceptance checklist
- [ ] FIGURE_STYLE: data-only (no interpretive arrows); reading is in the caption.
- [ ] FIGURE_REPRODUCIBILITY: CSV emitted + `--replot` verified.
- [ ] Public/private: `_PRIVATE` set if any AS strain present; leak audit before any public use.
- [ ] Claim-safety caption: shared thread = `{TAG}` machinery / E-signal, **not one compound**; KCB anchors `~`.
- [ ] Every locus row carries strain / region / class / ~KCB anchor / edge-status / SARP / verdict.
- [ ] Tier palette + legend match `DELIVERABLE_INSTRUCTION_TEMPLATE.md`.
- [ ] Affiliation ; no retired codenames.
- [ ] Closes with exactly 8 unique plain-text numbered next-paths.

## 6. Tool / knowledge inventory
| Piece | Owner |
|---|---|
| filter + join + CSV + plot | `tools/build_subset_panel.py` |
| tier assignment logic | `tier_of()` in `build_subset_panel.py` (mirrors `generate_bgc_atlas.py`) |
| tier palette + locus label | `deliverables/DELIVERABLE_INSTRUCTION_TEMPLATE.md` |
| invoking prompts | `deliverables/GENERIC_PROMPT_LIBRARY.md` G2, G6 |
| board row | `deliverables/HIVE_Board.csv` HB-008 / DLV-008 |

## 7. Next-paths closer (worked example)
```
1. Panel a different product tag (e.g. lassopeptide, ectoine) to compare distributions.
2. Switch the lane axis to habitat once the merged cohort provides it (SID is genus-only).
3. Promote any Confirmed (green) chip in the panel to a full G4 single-BGC Mode B dive.
4. Fold this panel into the size-by-type analysis as a tag-specific inset.
5. Re-run on merged_cohort to include AS strains (output auto-marked PRIVATE).
```

---
*Validated this cycle: `--tag nrp-metallophore` (51 loci / 5 genera), `--tag phenazine` (7 loci), strain-set and
`--replot` paths all produce figure + CSV.*
