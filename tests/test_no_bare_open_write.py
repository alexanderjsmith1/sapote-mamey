"""test_no_bare_open_write.py — BH-CG-02 static guard (v9.7.122).

A bare ``open(path, "w").write(...)`` or ``path.open("w").write(...)`` leaks the file
handle (no context manager) and the prior S3 sweep only caught the ``Path.open().write()``
form, missing the built-in ``open().write()`` form. Two production sites
(render_brief.py CNBU sidecar, figures_sapote.py figure-pack markdown) were fixed; this
test keeps the whole ``mamey/`` core free of the pattern so it cannot reappear.
"""
import pathlib
import re


def test_no_bare_open_write_in_mamey_core():
    root = pathlib.Path(__file__).resolve().parents[1] / "mamey"
    patterns = [
        re.compile(r"\.open\s*\([^\n]*\)\.write\s*\("),          # Path.open(...).write(
        re.compile(r"(?<![\w.])open\s*\([^\n]*\)\.write\s*\("),  # bare open(...).write(
    ]
    bad = []
    for p in root.rglob("*.py"):
        if "_vendor" in p.parts:
            continue
        for i, line in enumerate(
            p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            if any(pat.search(line) for pat in patterns):
                bad.append(f"{p.relative_to(root.parent)}:{i}: {line.strip()}")
    assert not bad, "bare open/write calls found (use a with-block):\n" + "\n".join(bad)
