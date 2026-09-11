"""BC2-PC-01 (v9.7.396): check_provenance_columns.py must not go silently blind when a table's
real delimiter doesn't match its file extension.

_sniff() picked its CSV/TSV delimiter solely from the file suffix (.tsv/.tab -> tab, else comma),
with no check that the file's actual content agreed. A genuinely per-BGC table missing its
provenance anchor (bare "bgc" column, no strain/contig/region — exactly the AS-421 2026-07-05
failure this gate's own docstring/test suite says it exists to catch) was misparsed into a single
garbled header when its real delimiter didn't match its extension (e.g. a comma-delimited export
saved with a .tsv extension). csv.DictReader then returned one nonsense fieldname matching no
BGC_ID_COLS and no cell matching the BGC### pattern, so the table was silently judged "not a
per-BGC table; gate does not apply" — this fail-closed gate's own promise broken by a naming
mismatch, not a real absence of the anchor columns.

Reproduced live against the unpatched tools/check_provenance_columns.py before this fix.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "tools" / "check_provenance_columns.py"


def _run(path: Path):
    return subprocess.run([sys.executable, str(GATE), str(path)], capture_output=True, text=True)


def test_comma_content_with_tsv_extension_still_caught(tmp_path):
    # Real content is comma-delimited; extension says tab. A genuine violation (no
    # strain/contig/region) must still be caught, not silently waved through as "not per-BGC".
    p = tmp_path / "status.tsv"
    p.write_text("bgc,note\nBGC001,pending review\nBGC002,pending review\n")
    r = _run(p)
    assert r.returncode == 1, (
        f"a comma-delimited per-BGC violation saved with a .tsv extension must still fail closed; "
        f"stdout={r.stdout!r} stderr={r.stderr!r}"
    )
    assert "missing a strain column" in r.stderr


def test_tab_content_with_csv_extension_still_caught(tmp_path):
    # The reverse mismatch direction.
    p = tmp_path / "status.csv"
    p.write_text("bgc\tnote\nBGC003\tpending\n")
    r = _run(p)
    assert r.returncode == 1, (
        f"a tab-delimited per-BGC violation saved with a .csv extension must still fail closed; "
        f"stdout={r.stdout!r} stderr={r.stderr!r}"
    )
    assert "missing a strain column" in r.stderr


def test_correctly_matched_tsv_with_full_provenance_still_clean(tmp_path):
    # Regression guard: the ordinary, correctly-matched case must keep passing.
    p = tmp_path / "good.tsv"
    p.write_text("strain\tcontig\tregion\tbgc_id\nAS-1\tNODE_1\t1\tBGC001\n")
    r = _run(p)
    assert r.returncode == 0, r.stderr


def test_correctly_matched_csv_with_full_provenance_still_clean(tmp_path):
    p = tmp_path / "good.csv"
    p.write_text("strain,contig,region,bgc_id\nAS-1,NODE_1,1,BGC001\n")
    r = _run(p)
    assert r.returncode == 0, r.stderr


def test_legitimately_single_column_non_per_bgc_file_stays_clean(tmp_path):
    # Regression guard: a genuinely single-column file with no delimiter character inside its
    # one field must not be mistakenly re-parsed.
    p = tmp_path / "single.tsv"
    p.write_text("notes\nsome random text\n")
    r = _run(p)
    assert r.returncode == 0, r.stderr
