# Locus-map review contract

**Status:** normative content and presentation contract.  
**Applies to:** all single-BGC and paired locus maps used in Mode B cards, per-BGC dossiers, atlases, and compiled reports.

## 1. Identity and scope

Every map must state the strain or public reference label, full assembly node/contig, antiSMASH region, and secondary `BGC###` alias. The rendered map, companion data, source inventory, and card must resolve to the same exact locus.

Atlas selection scope must be explicit: full inventory, ranked subset, top N, conditional class set, or paired reconstruction set. The number of filesystem copies is never the atlas denominator.

## 2. Required base layer

Every map must include:

- all genes in the selected region or declared plotted window;
- gene direction and scaled coordinates;
- a legible locus tag or an unambiguous numbered label for every gene when geometry permits;
- an on-figure shown/total label count when any labels are suppressed;
- a companion CSV/TSV containing every gene and a `label_visible_on_figure` field;
- a role legend, coordinate scale, boundary/truncation state, and capacity-level claim note;
- source/provenance sufficient to reproduce the plotted rows.

Label collision management may rotate or suppress labels, but suppression must never be silent. Every suppressed gene remains in the companion data and is counted on the figure.

## 3. Review overlays

A review-grade map should add each available overlay as a distinct, provenance-tagged layer:

1. antiSMASH gene kind and rule/smCOG role;
2. domain architecture or HMM calls for core and selected genes;
3. per-gene BLASTp subject, percent identity, and query coverage;
4. KnownClusterBlast/MIBiG or other comparator alignment context;
5. selected-gene, contradiction, or refine flags;
6. transport, regulation, resistance/self-protection, and tailoring groupings;
7. explicit missing/unbound markers for expected but unavailable layers.

An overlay may be omitted when unavailable, but the map or its dossier must name the gap. A cleaner figure is not automatically a better review artifact if it removes evidence layers needed to adjudicate the card.

## 4. Companion-data requirements

The sidecar is the lossless record. At minimum it contains:

`panel, strain/reference, bgc_alias, full_node, region, locus_tag, order, start, end, strand, length_aa, role, label_visible_on_figure, source`

Overlay columns are additive and must preserve their channel provenance. Per-gene identity and coverage must not be collapsed into a cluster-level similarity score.

## 5. Visual QA

Before acceptance, render the final output and inspect it at intended reading size. Fail the presentation gate for clipped arrows, overlapping labels, unreadable type, missing legends, hidden suppression, ambiguous region identity, or absent companion data.

The existence of a PNG/SVG is only a mechanical completion check. Review-grade acceptance additionally requires identity parity, content-layer accounting, and visual inspection.

## 6. Scaling to large atlases

Large runs must be deterministic and resumable:

- derive the worklist from the canonical per-BGC inventory;
- emit one map plus sidecar per exact locus;
- use stable filenames containing the secondary alias and a portable exact-locus token or manifest row;
- write a manifest with rank/scope, hashes, byte counts, renderer version, layer coverage, and label shown/total counts;
- rerun by missing or failed manifest rows rather than restarting the atlas;
- never infer biological absence from an unrendered or failed map.

The same renderer and contract apply whether the run covers 10, 1,200, or the full inventory. Selection size changes the worklist, not the evidence or presentation standard.

## 7. Claim ceiling

Gene roles, domain calls, BLASTp, KCB/MIBiG, and GCF context are evidence channels. They support class-level hypotheses and experimental prioritization; they do not by themselves establish compound identity, production, activity, novelty, or causality.

## 8. Contract checks versus current renderer guarantees

This is an acceptance contract, not a claim that every renderer enforces all requirements. The v8 sidecar uses `label_displayed=YES` and includes complete identity in `panel`; it does not provide each required identity component as a separate column. An adapter may derive explicit columns only from the verified receipt/package crosswalk, preserving the original panel and source binding. Do not infer identity from a BGC alias or shortened filename.

For v8, reconcile raw source rows with accepted CSV rows because malformed gene rows may be skipped. Check recorded identity and source hashes independently of output-triple validation, inspect the non-blocking adapter's skipped results, and retain the exact ranked/full-inventory scope. R arrow redraws lack the v8 evidence panel and receipt, so acceptance requires their own layer accounting and visual review. See [current v8 limits and recovery](LOCUS_MAP_V8.md).

The required capacity-level note here and the [house rules](FIGURE_HOUSE_RULES.md) placement policy need an explicit per-delivery decision: preserve the scientific ceiling in the caption/methods and review receipt, and record any on-artwork note requirement as a policy hold if its renderer's text gate refuses it. Do not silently remove required evidence wording or declare all policies passed.

Source owners: `mamey/locus_map_v8.py:352–398,748–788,815–853,894–908`; `tools/sapote_locus_map.R:36–57,130–143`.
