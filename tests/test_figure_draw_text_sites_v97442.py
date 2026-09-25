"""Claim wording drawn straight onto figures, outside the checked save path.

`mamey/figure_save.py` refuses a figure whose visible text matches
`mamey.figure_policy.FIGURE_BANNED_TEXT`. Most renderers call `savefig` directly, so that
refusal never sees them. This test reads the source and lists every matplotlib draw call
that is given banned wording as a literal, or a `CLAIM*` constant. The list is a floor:
text built through other variables is not seen.

KNOWN is the debt still to remove. A new site fails the test. When a renderer is fixed,
delete its line from KNOWN.
"""
import ast
from collections import Counter
from pathlib import Path

from mamey.figure_policy import FIGURE_BANNED_TEXT

ROOT = Path(__file__).resolve().parents[1]
DRAW = {'set_title', 'suptitle', 'title', 'text', 'figtext', 'annotate', 'set_xlabel',
        'set_ylabel', 'xlabel', 'ylabel', 'legend', 'set_label'}

KNOWN = Counter({
    ('deliverable_tools/assembly_line_pdf.py', 'text', 'CLAIM_SAFETY'): 1,
    ('deliverable_tools/bgc_gene_map.py', 'text', 'CLAIM_SAFETY'): 1,
    ('deliverable_tools/bigscape_gene_domain_context.py', 'text', 'CLAIM_CEILING'): 1,
    ('deliverable_tools/render_mlsa_tree.py', 'text', 'literal'): 1,
    ('mamey/bigscape_figures.py', 'set_title', 'literal'): 1,
    ('mamey/cross_strain_threads.py', 'legend', 'literal'): 1,
    ('mamey/cross_strain_threads.py', 'set_title', 'literal'): 1,
    ('mamey/figure_theme.py', 'text', 'CLAIM_SAFETY'): 1,
    ('mamey/kcb_locusmap.py', 'text', 'CLAIM_CEILING'): 1,
    ('mamey/locus_map_v8.py', 'text', 'CLAIM_CEILING'): 1,
    ('tools/phylo_place.py', 'set_title', 'literal'): 1,
    ('tools/placement_figure.py', 'set_title', 'literal'): 1,
    ('tools/render_clean_tree.py', 'text', 'literal'): 1,
})


def _draw_sites():
    found = Counter()
    for top in ('mamey', 'tools', 'deliverable_tools'):
        for path in sorted((ROOT / top).rglob('*.py')):
            try:
                tree = ast.parse(path.read_text(errors='replace'))
            except SyntaxError:
                continue
            rel = path.relative_to(ROOT).as_posix()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', '')
                if name not in DRAW:
                    continue
                kinds = set()
                for arg in list(node.args) + [k.value for k in node.keywords]:
                    for sub in ast.walk(arg):
                        if (isinstance(sub, ast.Constant) and isinstance(sub.value, str)
                                and FIGURE_BANNED_TEXT.search(sub.value)):
                            kinds.add('literal')
                        ident = getattr(sub, 'id', None) or getattr(sub, 'attr', '')
                        if isinstance(sub, (ast.Name, ast.Attribute)) and ident.startswith('CLAIM'):
                            kinds.add(ident)
                for kind in kinds:
                    found[(rel, name, kind)] += 1
    return found


def test_no_new_figure_draws_claim_wording():
    new = _draw_sites() - KNOWN
    assert not new, f'new claim wording drawn on a figure: {sorted(new)}'


def test_known_list_matches_the_code():
    fixed = KNOWN - _draw_sites()
    assert not fixed, f'these sites no longer draw claim wording; delete them from KNOWN: {sorted(fixed)}'


def test_kcb_novelty_title_has_no_claim_wording():
    source = (ROOT / 'mamey/cohort_figures_extended.py').read_text()
    assert 'similarity, not identity' not in source
