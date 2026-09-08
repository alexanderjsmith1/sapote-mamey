"""v9.7.281 (patch 47): no test module may hard-import an optional dep (biopython, DIAMOND
bindings) at module scope — one missing optional dep must not abort pytest collection (F-04)."""
from __future__ import annotations
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
OPTIONAL = ("Bio", "Bio.Seq", "Bio.SeqIO", "diamond", "pydiamond")
# module-scope import of an optional dep, NOT guarded by importorskip earlier in the file
IMPORT_RE = re.compile(r"^(?:from|import)\s+(Bio\b|diamond\b|pydiamond\b)", re.M)


def test_no_unguarded_optional_imports_at_module_scope():
    offenders = []
    for f in sorted(TESTS.glob("test_*.py")):
        text = f.read_text(encoding="utf-8", errors="ignore")
        if IMPORT_RE.search(text) and "importorskip" not in text.split("from Bio")[0][-400:] \
           and "importorskip" not in text[:text.find("Bio") if "Bio" in text else 0]:
            # be lenient: only flag if there's an unguarded Bio import with no importorskip anywhere above it
            first_bio = min([m.start() for m in re.finditer(r"\bBio\b|\bdiamond\b", text)] or [len(text)])
            if "importorskip" not in text[:first_bio]:
                offenders.append(f.name)
    assert not offenders, f"module-scope optional imports (add pytest.importorskip): {offenders}"
