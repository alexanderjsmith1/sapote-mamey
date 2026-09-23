#!/usr/bin/env python3
"""bigscape_figure_labels.py -- canonical node-category labels/colours for BiG-SCAPE figures.

Fixes a real ambiguity: cohort **type strains** (S. venezuelae and the other genome-sequenced
reference taxa, classified `reference/type` by mamey_habitat_map) were being legended as bare
"Reference", which collides with the **MIBiG reference** (the anchoring BGC database) that figures
draw in red. A grey node is a *cohort strain*; a red node is a *MIBiG cluster* — different things.

This module is the single source of truth so no figure ever labels a node just "Reference":
  * host habitats keep their names (bee/wasp, attine, bryophyte, lichen, termite, clinical, environmental)
  * cohort reference/type taxa  -> **"type strain"** (grey)
  * MIBiG anchoring clusters     -> **"MIBiG reference"** (red)
The bare word "reference" is disallowed as a standalone category label (raises on request) so the
collision cannot reappear.

Use:
  from bigscape_figure_labels import category_of, STYLE, legend_handles, MIBIG
  cat = category_of(source_string_or_habitat)      # -> canonical category
  color = STYLE[cat]["color"]; label = STYLE[cat]["label"]
  handles = legend_handles(categories_present)      # matplotlib Line2D handles

Stdlib only (+ matplotlib only if legend_handles is called).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import re

MIBIG = "MIBiG reference"
TYPE_STRAIN = "type strain"

# canonical category -> display style
STYLE = {
    "bee/wasp":       {"color": "#2E6DA4", "label": "bee/wasp"},
    "attine":         {"color": "#B5651D", "label": "attine"},
    "bryophyte":      {"color": "#2E8B57", "label": "bryophyte"},
    "lichen":         {"color": "#8B008B", "label": "lichen"},
    "termite":        {"color": "#6B8E23", "label": "termite"},
    "clinical":       {"color": "#7D3C98", "label": "clinical"},
    "environmental":  {"color": "#7F8C8D", "label": "environmental"},
    TYPE_STRAIN:      {"color": "#AAAAAA", "label": "type strain (cohort)"},
    MIBIG:            {"color": "#C0392B", "label": "MIBiG reference"},
    "unassigned":     {"color": "#000000", "label": "unassigned"},
}

# host-habitat synonyms that map onto canonical categories
_HABITAT_ALIASES = {
    "bee": "bee/wasp", "wasp": "bee/wasp", "bee/wasp": "bee/wasp",
    "attine": "attine", "ant": "attine",
    "bryophyte": "bryophyte", "moss": "bryophyte", "liverwort": "bryophyte",
    "lichen": "lichen",
    "termite": "termite", "clinical": "clinical", "environmental": "environmental",
    # the collision sources -> explicit type-strain, never bare "reference"
    "reference": TYPE_STRAIN, "reference/type": TYPE_STRAIN,
    "type": TYPE_STRAIN, "type strain": TYPE_STRAIN, TYPE_STRAIN: TYPE_STRAIN,
}


# Keep host recognition in the same order as mamey_habitat_map.RULES.
# The parity test binds this stdlib-only consumer to the producer vocabulary.
# Environmental and bare-ant classification policies are unchanged.
_HOST_RULES = [
    ('bumblebee|bombus|honey ?bee|\\bapis\\b|\\bbee\\b|bee-assoc', 'bee/wasp'),
    ('\\bwasp\\b|vespul|polist|\\bvespa\\b|hornet', 'bee/wasp'),
    ('\\bmoss\\b|bryophyt|sphagnum|liverwort', 'bryophyte'),
    ('termite|macroterm', 'termite'),
    ('attine|acromyrmex|\\batta\\b|trachymyrmex|leaf.?cutter|fungus.?grow.*ant|attine ant', 'attine'),
    ('clinical|homo sapiens|human|sputum|patient|bronch|wound', 'clinical'),
]


def category_of(value, is_mibig=False):
    """Map a source string / habitat / gbk basename to a canonical figure category.

    is_mibig=True (or a BGC accession filename) -> MIBiG reference. Everything else is a cohort
    node: a known habitat, or a type/reference strain -> 'type strain' (never bare 'reference')."""
    s = (value or "").strip().lower()
    if is_mibig or s.startswith("bgc") and re.fullmatch(r"bgc\d{4,7}(\..*)?", s or ""):
        return MIBIG
    if s in _HABITAT_ALIASES:
        return _HABITAT_ALIASES[s]
    # accession-only / type-strain source strings (mirror mamey_habitat_map.classify)
    if re.search(r"gca_|nz_|type strain|reference", s) or not s:
        return TYPE_STRAIN
    # v9.7.438: this was a bare substring test, `if key in s`. `_HABITAT_ALIASES` contains
    # "ant" -> attine and "bee" -> bee/wasp, which are substrings of very ordinary words in an
    # actinomycete corpus. Measured on the shipped rule: "plant root", "rhizosphere of a plant",
    # "Antarctic soil", "Atlantic sediment", "plantation soil", "elephant dung" and "giant panda
    # faeces" all returned ATTINE, while "beech forest soil" returned BEE/WASP and the real host
    # "Apis mellifera" returned UNASSIGNED. On those inputs the rule was close to anti-correlated
    # with the truth.
    #
    # Nothing in the current corpus is mislabelled by it -- a census of the 176-row consolidated
    # metadata and the 71-row reference registry found every fallthrough assignment correct,
    # because the deposited strings there are "ant-associated (...)", "moss-associated (...)" and
    # the like. The defect is latent, and it bites on the next reference genome whose NCBI
    # isolation source happens to say "plant".
    #
    # Match on TOKEN BOUNDARIES instead. "ant-associated" and "attine ant" still match; "plant"
    # and "Antarctic" no longer do, because `ant` there is not a whole token. Isolation source is
    # reported as deposited and never inferred, so `unassigned` is the correct answer whenever the
    # deposited string does not actually name a known habitat.
    for pattern, category in _HOST_RULES:
        if re.search(pattern, s):
            return category
    for key, cat in _HABITAT_ALIASES.items():
        if re.search(rf"(?<![a-z]){re.escape(key)}(?![a-z])", s):
            return cat
    return "unassigned"


def assert_not_bare_reference(label):
    """Guard: refuse the ambiguous standalone label 'reference'. Use 'type strain' or 'MIBiG reference'."""
    if (label or "").strip().lower() == "reference":
        raise ValueError("ambiguous label 'reference': use 'type strain' (cohort) or 'MIBiG reference' (anchor DB)")
    return label


def legend_handles(categories):
    """Return matplotlib Line2D legend handles for the given categories, in canonical order."""
    from matplotlib.lines import Line2D
    order = list(STYLE.keys())
    seen = [c for c in order if c in set(categories)]
    return [Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=STYLE[c]["color"], markersize=9, label=STYLE[c]["label"])
            for c in seen]


if __name__ == "__main__":
    # tiny self-demo
    for v in ["cohort-strain bee host", "attine ant", "Streptomyces venezuelae type strain",
              "GCA_008639165", "BGC0001773.gbk"]:
        emit(f"{v!r:45} -> {category_of(v)}")
