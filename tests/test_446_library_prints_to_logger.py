"""Library progress lines moved from print to the engine logger (mamey.logging_setup) stay byte-identical and still follow a
swapped sys.stdout (pytest capture, contextlib.redirect_stdout), the way print did."""
import contextlib
import importlib
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _fresh_logger(name):
    import mamey.logging_setup as ls
    ls.configure()
    return ls.get_logger(name)


def _via_print(*args, sep=" "):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(*args, sep=sep)
    return buf.getvalue()


def _via_logger(fmt, *args):
    log = _fresh_logger("mamey.test_446")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):      # the stdout swap happens AFTER the handler exists
        log.info(fmt, *args)
    return buf.getvalue()


def test_converted_forms_are_byte_identical():
    cases = [
        (("plain line",), " "),
        ((f"  wrote {3} files to /tmp/x",), " "),
        (("a", 1, 2.5, None), " "),
        (("head", "body", "tail"), "\n"),
        (({"k": 1},), " "),                     # a lone mapping argument
        ((("t", 1),), " "),                     # a lone tuple argument
        (("100% done", "x"), " | "),
    ]
    for args, sep in cases:
        fmt = sep.replace("%", "%%").join(["%s"] * len(args))
        assert _via_logger(fmt, *args) == _via_print(*args, sep=sep), (args, sep)


def test_handler_follows_a_swapped_stdout(capsys):
    log = _fresh_logger("mamey.test_446_capsys")
    log.info("%s", "reaches the captured stdout")
    assert capsys.readouterr().out == "reaches the captured stdout\n"


def test_explicit_stream_is_still_honoured():
    import mamey.logging_setup as ls
    buf = io.StringIO()
    ls.configure(stream=buf)
    try:
        ls.get_logger("mamey.test_446_stream").info("%s", "to the given stream")
        assert buf.getvalue() == "to the given stream\n"
    finally:
        ls.configure()


def test_converted_modules_import_and_use_the_engine_logger():
    converted = [p for p in (ROOT / "mamey").rglob("*.py")
                 if "_OUT = _get_logger(__name__)" in p.read_text()]
    assert len(converted) >= 20   # modules whose command RESULTS print were left on emit (Task 198 review, F1)
    for p in converted:
        mod = ".".join(p.relative_to(ROOT).with_suffix("").parts)
        m = importlib.import_module(mod)
        assert m._OUT.name.startswith("mamey."), mod
        assert re.search(r"_OUT\.(info|warning|error)\(", p.read_text()), mod


# ---- results stay on the deliverable channel (Task 198 review, F1) -------------------------------
# A command's result (JSON, a typed refusal, a markdown report, a lookup answer) is the deliverable and
# must reach stdout whatever MAMEY_LOG says. Only progress chatter moved to the logger.

def test_no_json_result_rides_the_logger():
    offenders = []
    for p in (ROOT / "mamey").rglob("*.py"):
        for n, line in enumerate(p.read_text().splitlines(), 1):
            if "_OUT." in line and "json.dumps(" in line:
                offenders.append(f"{p.relative_to(ROOT)}:{n}")
    assert not offenders, offenders


def test_markdown_and_lookup_results_use_emit():
    must_emit = {
        "mamey/session_resume.py": "emit(result['markdown'])",
        "mamey/report_card.py": 'emit(res["markdown"])',
        "mamey/af_dossier.py": 'emit(res["markdown"])',
        "mamey/good_guesses.py": 'emit(res["markdown"])',
        "mamey/blastp_availability.py": "emit(render_table(agg))",
        "mamey/literature_lookup.py": 'emit(f"PMID {args.pmid}: not in corpus")',
        "mamey/packaging.py": "emit(f\"repro_fingerprint: {fp['fingerprint']}\")",
    }
    for rel, needle in must_emit.items():
        assert needle in (ROOT / rel).read_text(), rel


def test_tool_database_refusal_json_survives_warning_level(monkeypatch, capsys, tmp_path):
    import argparse
    import mamey.logging_setup as ls
    from mamey import tool_database_reader as tdr
    monkeypatch.setenv("MAMEY_LOG", "warning")
    ls.configure()
    try:
        def refuse(*a, **k):
            raise tdr.ToolDatabaseInspectionError("TEST_HOLD")
        monkeypatch.setattr(tdr, "inspect_tool_database", refuse)
        fn = tdr.inspection_command
        args = argparse.Namespace(root=tmp_path, manifest="M", adapter="a", locus=None, limit=1, offset=0,
                                  manifest_sha256=None)
        assert fn(args) == 2
        out = capsys.readouterr().out
        import json
        assert json.loads(out)["status"] == "HELD"
    finally:
        monkeypatch.delenv("MAMEY_LOG")
        ls.configure()


def test_warning_and_error_lines_survive_warning_level():
    src = (ROOT / "mamey/bgc_guide.py").read_text() + (ROOT / "mamey/modeb_round.py").read_text()
    assert "_OUT.error('%s', f\"        ERROR: {e}\")" in src
    assert "_OUT.warning('%s', f\"[modeb-round] WARNING:" in src
