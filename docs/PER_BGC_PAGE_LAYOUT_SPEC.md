# Per-BGC page units: reading guidance

For the per-BGC report card (the short evidence summary per cluster), see the [report card spec](PER_BGC_REPORT_CARD_SPEC.md). This page covers how a locus map and its Mode B card (the per-locus interpretive write-up) sit together in a compiled report. Terms are in the [glossary](GLOSSARY.md).

## Review contract

Use one continuous exact-locus review unit. It carries:

- the full identity, `strain / full node-or-contig / region / BGC alias`;
- the bound locus map and gene roster;
- the predicted-class and boundary line;
- the interpretation for the selected [profile](MODEB_PROFILE_MATRIX.md).

A filename is not the identity. A stored card is named `<strain>_<BGC alias>_mode_b.md` (`mamey/judgment_store.py:277-280`), with no contig or region. Take the identity from the bound source record, and keep a list that pairs each file with its full identity.

Place the map with the start of its analysis, at reader size. If the card runs onto more pages, mark each continuation with the same complete identity. Do not put a bare map on one page and unrelated or ambiguous text after it.

A full48 or current50 card can run past two pages. Never cut sections, and never shrink text below the minimum size in the [figure house rules](FIGURE_HOUSE_RULES.md), to fit a page count. If a work order asks for a fixed one-page or two-page limit, record a layout hold and ask the project owner. Keep the full card and its evidence while that is decided.

## What the report compiler does

`compile_report` collects the figure images it finds into report section 6. It puts into section 9 the card file for each alias the package's card register marks `COMPLETE`. Each card is preceded by an `AUTHORED_CARD_LINK_UNVERIFIED` hold. A register `COMPLETE` entry with no card file prints a "card file missing" notice instead. Register status is a selection signal only: it does not show that the card is bound to the current locus identity or that it passed `verify-modeb`. It tries to include locus maps for the top five clusters.

It does not place each map beside its card, and it does not check that each image belongs to a completed card. A PNG and an SVG of the same figure can both appear. The card register is separate from `verify-modeb`.

Do not call a compiled report layout-compliant because the files exist. Instead:

1. Make a list that pairs each figure file with its locus and its card.
2. Open the final pages and check each map, its card, and any continuation pages.

Related pages: [locus-map review](LOCUS_MAP_REVIEW_CONTRACT.md) and [export boundary](MODEB_EXPORT_HOOK.md).
