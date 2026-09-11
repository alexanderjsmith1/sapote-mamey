"""P3/P4 acceptance: doc claims are truthful, deps agree with pyproject, package ships no cohort data."""
from pathlib import Path
import re
import pytest

pytestmark = pytest.mark.public
_MAMEY = Path(__import__("mamey").__file__).parent
_ROOT = _MAMEY.parent


def test_doc_path_claims_exist():
    """Every `path/like/this` a public doc claims to ship must exist (P3 doc-path-claim test)."""
    docs = ["README.md", "docs/INSTALL.md", "docs/PUBLIC_RELEASE_GUIDE.md", "docs/PUBLIC_RELEASE_DATA.md"]
    claim = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|md|json|toml|sh|cfg|txt|hmm))`")
    missing = []
    for d in docs:
        p = _ROOT / d
        if not p.exists():
            continue
        for m in claim.findall(p.read_text(encoding="utf-8", errors="ignore")):
            # only check repo-relative paths that look shipped, and skip the ones docs say are NOT bundled
            if m.startswith(("http", "/")) or ".." in m:
                continue
            cand = _ROOT / m
            # a path claimed present must exist; Pfam HMM is explicitly "not bundled" so skip it
            if "scanner_pfam" in m or "Pfam-A" in m:
                continue
            if not cand.exists() and (_MAMEY / m).exists() is False:
                # tolerate example/illustrative names that aren't repo-relative
                if m.count("/") >= 1 and m.split("/")[0] in {"mamey", "tools", "docs", "tests"}:
                    missing.append((d, m))
    assert not missing, f"docs claim these paths ship but they are absent: {missing}"


def test_dep_tables_agree_with_pyproject():
    """Core deps named in README must appear in pyproject (P3 dep-vs-pyproject)."""
    pp = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    readme = (_ROOT / "README.md").read_text(encoding="utf-8", errors="ignore")
    for dep in ("openpyxl", "ijson"):
        if dep in readme:
            assert dep in pp, f"README names {dep} but pyproject.toml does not"


def test_package_data_has_no_cohort_roster_or_ids():
    """The shipped mamey/data must carry no cohort roster and no AS-#### cohort identifier files."""
    data = _MAMEY / "data"
    assert not (data / "strain_genus.csv").exists()
    as_id = re.compile(r"\bAS-\d{2,4}\b")
    leaks = []
    for f in data.rglob("*"):
        if f.is_file() and f.suffix in {".csv", ".tsv", ".json"}:
            try:
                if as_id.search(f.read_text(encoding="utf-8", errors="ignore")):
                    leaks.append(str(f.relative_to(_MAMEY)))
            except Exception:
                pass
    assert not leaks, f"cohort AS-#### identifiers in shipped package data: {leaks}"
