"""
E2: GBK shim standing rule — any tool in tools/ that imports Bio.SeqIO must also use
mamey._gbk_shim as a fallback. A bare 'from Bio import SeqIO' without '_gbk_shim'
means the tool will crash on environments without biopython installed (the v9.7.56
propagation bug). This lint test fails the suite if a new tool violates the rule.

Standing rule from v9.7.56 CHANGELOG: "any new tool touching GBKs must use the
_gbk_shim fallback, never a bare Bio import."
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_no_bare_bio_seqio_in_tools():
    """Every tools/*.py that imports Bio.SeqIO must also reference _gbk_shim."""
    violations = []
    for py in sorted((ROOT / "tools").glob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        has_bio = bool(re.search(r"from Bio import SeqIO", text))
        has_shim = bool(re.search(r"_gbk_shim", text))
        if has_bio and not has_shim:
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
