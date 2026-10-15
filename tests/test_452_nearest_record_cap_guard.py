"""Review every literal BLAST target cap; new nearest-record call sites must count the DB."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Exact reviewed exceptions. These are not nearest-record nucleotide decisions.
EXCEPTIONS = {
    ('tools/build_mlsa.py', '_run_pipeline_worker', 1): 'protein seed ortholog BLASTp',
    ('tools/comparator_select.py', 'extract_16s_from_genome', 5): 'candidate seed span extraction',
    ('tools/phylo_16s_from_genome.py', 'extract', 5): 'heuristic candidate span extraction',
    ('tools/phylo_refset.py', 'dedup', 50): 'Tier-2 duplicate graph; separately measured and held',
}
PROTEIN_KEYWORD_FILES = {
    'tools/multi_reference_comparison_strain.py', 'tools/multi_reference_comparison.py',
    'tools/pcoa_bgc_explorer.py', 'mamey/ref_completion.py',
}


def literal_caps(source):
    found = []

    class Scan(ast.NodeVisitor):
        function = '<module>'

        def visit_FunctionDef(self, node):
            old, self.function = self.function, node.name
            self.generic_visit(node)
            self.function = old

        def visit_List(self, node):
            for flag, value in zip(node.elts, node.elts[1:]):
                if isinstance(flag, ast.Constant) and flag.value == '-max_target_seqs':
                    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'str' and len(value.args) == 1:
                        value = value.args[0]
                    if isinstance(value, ast.Constant) and str(value.value).isdigit():
                        found.append((self.function, int(value.value), 'argv', ''))
            self.generic_visit(node)

        visit_Tuple = visit_List

        def visit_Call(self, node):
            for kw in node.keywords:
                if kw.arg == 'max_target_seqs' and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
                    found.append((self.function, kw.value.value, 'keyword', ''))
            self.generic_visit(node)

        def visit_JoinedStr(self, node):
            text = ''.join(str(v.value) if isinstance(v, ast.Constant) else '{}' for v in node.values)
            for value in re.findall(r'-max_target_seqs\s+(\d+)', text):
                found.append((self.function, int(value), 'shell', text))
            # Constants are already included above.

        def visit_Constant(self, node):
            if isinstance(node.value, str):
                for value in re.findall(r'-max_target_seqs\s+(\d+)', node.value):
                    found.append((self.function, int(value), 'shell', node.value))

    Scan().visit(ast.parse(source))
    return found


def test_no_unreviewed_literal_subject_caps():
    violations = []
    for directory in ('tools', 'deliverable_tools', 'mamey'):
        for path in (ROOT / directory).rglob('*.py'):
            rel = path.relative_to(ROOT).as_posix()
            for function, value, kind, text in literal_caps(path.read_text()):
                if (rel, function, value) in EXCEPTIONS:
                    continue
                if kind == 'keyword' and rel in PROTEIN_KEYWORD_FILES:
                    continue
                if rel == 'tools/marker_candidate_search.py' and function == 'cmd_plan_blast' and kind == 'shell':
                    if 'blastp ' in text or ('-remote' in text and 'exploratory capped search' in text):
                        continue
                violations.append((rel, function, value, kind))
    assert not violations, 'Count the local database or document a reviewed non-nearest exception: ' + repr(violations)


def test_guard_detects_new_argv_keyword_and_planned_caps():
    source = '''
def nearest():
    run(["blastn", "-max_target_seqs", "10"])
    run(["blastn", "-max_target_seqs", str(5)])
    search(max_target_seqs=25)
    emit(f"blastn -query {query} -max_target_seqs 50")
'''
    assert [v for _, v, _, _ in literal_caps(source)] == [10, 5, 25, 50]


def test_guard_allows_database_derived_counts():
    assert literal_caps('run(["blastn", "-max_target_seqs", str(record_count)])') == []
