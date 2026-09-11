"""
E2: GBK shim standing rule — any tool in tools/ that imports Bio.SeqIO must also use
mamey._gbk_shim as a fallback, or explicitly refuse a missing rich parser with a
guarded dependency error. Rich source qualifiers must not be silently downgraded. A bare 'from Bio import SeqIO' without '_gbk_shim'
means the tool will crash on environments without biopython installed (the v9.7.56
propagation bug). This lint test fails the suite if a new tool violates the rule.

Standing rule from v9.7.56 CHANGELOG: "any new tool touching GBKs must use the
_gbk_shim fallback, never a bare Bio import."
"""
import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _explicit_dependency_refusal(text):
    """A rich-parser function may refuse unavailable Bio, never silently degrade."""
    tree = ast.parse(text)
    imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
               and n.module == 'Bio' and any(a.name == 'SeqIO' for a in n.names)]
    if not imports:
        return False
    protected = set()
    for function in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        for node in (n for n in ast.walk(function) if isinstance(n, ast.Try)):
            for handler in node.handlers:
                if not isinstance(handler.type, ast.Name) or handler.type.id != 'ImportError':
                    continue
                if len(handler.body) != 1 or not isinstance(handler.body[0], ast.Raise):
                    continue
                call = handler.body[0].exc
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                        and call.func.id == 'RuntimeError' and call.args
                        and isinstance(call.args[0], ast.Constant)
                        and 'Biopython' in str(call.args[0].value)):
                    protected.update(n for stmt in node.body for n in ast.walk(stmt))
    return all(n in protected for n in imports)


def test_dependency_hold_requires_an_explicit_guarded_raise():
    good = "def parse():\n try:\n  from Bio import SeqIO\n except ImportError as exc:\n  raise RuntimeError('requires optional Biopython') from exc\n"
    assert _explicit_dependency_refusal(good)
    assert not _explicit_dependency_refusal('from Bio import SeqIO')
    assert not _explicit_dependency_refusal(good.replace("raise RuntimeError('requires optional Biopython') from exc", 'return []'))
    assert not _explicit_dependency_refusal(good.replace('except ImportError', 'except ValueError'))


def test_no_bare_bio_seqio_in_tools():
    """Require a shim fallback or an explicit guarded rich-parser dependency hold."""
    violations = []
    for py in sorted((ROOT / "tools").glob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        has_bio = bool(re.search(r"from Bio import SeqIO", text))
        has_shim = bool(re.search(r"_gbk_shim", text))
        if has_bio and not has_shim and not _explicit_dependency_refusal(text):
            violations.append(py.name)

    assert not violations, (
        "GBK shim rule violated — these tools use 'from Bio import SeqIO' without "
        "a _gbk_shim fallback (will crash when biopython is absent):\n"
        + "\n".join(f"  tools/{v}" for v in violations)
        + "\nFix: wrap the Bio import in try/except and fall back to mamey._gbk_shim.parse_genbank_text"
    )


def test_shim_itself_is_importable():
    """mamey._gbk_shim must be importable without biopython."""
    from mamey import _gbk_shim  # noqa: F401
    assert hasattr(_gbk_shim, "parse_genbank_text")
