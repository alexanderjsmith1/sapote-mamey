"""v9.7.422 — cohort_tree_ggtree.R must not clip tip labels or the caption.

Premise (live-observed on the AS-103 Sciscionella IQ-TREE figure, 2026-09-09, rendering the sealed
v9.7.420 template through R 4.5.3 / ggtree 4.0.4):

  1. RIGHT edge. `xlim(0, max_depth * (1 + 0.035 * longest))` reserves label room proportional to the
     longest label, but ignores the `nudge_x` the tip labels are drawn with. The outgroup tip
     "Streptosporangium amethystogenes" lost its final character at the panel edge.
  2. LEFT edge. The lower bound `0` is the root's x-position, while node-support labels are drawn
     with `hjust = 1.15` (i.e. extending LEFT of the node), so near-root supports clip. This is the
     defect the pending v9.7.412 lane found; v9.7.421 does not carry that fix, so this lane absorbs
     it — see the patch card, and do not apply both lanes.
  3. CAPTION. The caption is one long unwrapped line at 8pt; on the 3.5-inch SINGLE_COLUMN profile it
     ran off the panel, truncating mid-word at "rooted on Streptosporangium_".
  4. WRAPPING IS BYTE-UNSAFE. `sapote_wrap_labels()` calls `strwrap()`, which splits on bytes under a
     C locale (Rscript's default here), so the caption's middle dots rendered as "<c2><b7>".

Text-contract tests in the style of tests/test_410_r_figure_templates.py: parse the R sources, do not
require an R runtime. Topology, rooting, support values and colours are untouched by this lane.
"""
from __future__ import annotations

import re
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
_TREE_R = _TOOLS / "cohort_tree_ggtree.R"
_THEME_R = _TOOLS / "sapote_figure_theme.R"


def _xlim_args() -> tuple[str, str]:
    """Return the two arguments of the ggplot2::xlim(...) call.

    Parsed by paren depth rather than a regex: the upper bound itself contains parentheses, and a
    non-greedy regex silently stops at the first inner ')' — which would hide a missing term.
    """
    src = _TREE_R.read_text(encoding="utf-8")
    marker = "ggplot2::xlim("
    assert marker in src, "no ggplot2::xlim(...) call found in cohort_tree_ggtree.R"
    i = src.index(marker) + len(marker)
    depth, split_at = 0, None
    for j in range(i, len(src)):
        c = src[j]
        if c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                end = j
                break
            depth -= 1
        elif c == "," and depth == 0 and split_at is None:
            split_at = j
    else:  # pragma: no cover - unbalanced source
        raise AssertionError("unbalanced parentheses in the ggplot2::xlim(...) call")
    assert split_at is not None, "ggplot2::xlim() should take a lower and an upper bound"
    return src[i:split_at].strip(), src[split_at + 1:end].strip()


def test_nodelabels_are_left_justified_so_they_need_left_room():
    """The coupling the left margin exists for. Passes before and after; documents why."""
    src = _TREE_R.read_text(encoding="utf-8")
    assert "geom_nodelab" in src, "cohort tree should draw node-support labels"
    seg = src[src.index("geom_nodelab"):][:400]
    m = re.search(r"hjust\s*=\s*([0-9.]+)", seg)
    assert m and float(m.group(1)) > 1.0, "node-support labels should be left-justified (hjust > 1)"


def test_xlim_reserves_left_margin_not_zero():
    lower, _ = _xlim_args()
    assert lower.startswith("-"), (
        f"xlim lower bound is {lower!r}; it must be negative so near-root node-support "
        f"labels (hjust>1) are not clipped at the left panel edge"
    )
    assert "max_depth" in lower, f"left margin should scale with max_depth, got {lower!r}"


def test_xlim_right_bound_accounts_for_the_tip_label_nudge():
    """Tip labels start at the tip x PLUS nudge_x, so the right bound must include the nudge."""
    _, upper = _xlim_args()
    assert "nudge" in upper, (
        f"xlim upper bound is {upper!r}; tip labels are drawn with nudge_x = nudge, so the "
        f"reserved right margin must account for that offset or the longest label clips"
    )
    assert "longest" in upper, "right margin should still scale with the longest label"


def test_caption_is_wrapped_to_the_profile_width():
    src = _TREE_R.read_text(encoding="utf-8")
    m = re.search(r"labs\(caption\s*=\s*(\w+)", src)
    assert m, "no labs(caption = ...) found"
    assert m.group(1) == "sapote_wrap_labels", (
        f"caption is built with {m.group(1)!r}; it must go through sapote_wrap_labels() or it "
        f"runs off the panel edge on the narrow SINGLE_COLUMN profile"
    )
    assert "sapote_caption_wrap(profile)" in src, "caption wrap width should come from the profile"


def test_caption_wrap_width_is_profile_aware():
    theme = _THEME_R.read_text(encoding="utf-8")
    m = re.search(r"sapote_caption_wrap\s*<-\s*function\(profile\)(.+)", theme)
    assert m, "sapote_figure_theme.R should define sapote_caption_wrap(profile)"
    body = m.group(1)
    assert "SINGLE_COLUMN" in body, "caption wrap width must differ by profile"


def test_wrap_helper_is_utf8_safe():
    """strwrap() is byte-based under a C locale; the caption carries multi-byte characters."""
    theme = _THEME_R.read_text(encoding="utf-8")
    i = theme.index("sapote_wrap_labels <- function")
    body = theme[i:i + 900]
    assert "Sys.setlocale" in body and "LC_CTYPE" in body, (
        "sapote_wrap_labels() must borrow a UTF-8 LC_CTYPE around strwrap(), or multi-byte "
        "characters are split into raw bytes (the middle dot rendered as '<c2><b7>')"
    )
    assert "on.exit" in body, "the borrowed locale must be restored with on.exit()"
    assert "enc2utf8" in body, "the wrapped string should be marked UTF-8 before strwrap()"
