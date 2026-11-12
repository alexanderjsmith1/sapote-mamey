"""emit-modeb-template --bgc must refuse a BGC id that is not on the package's triage board.

It used to exit 0 and write a card headed "<strain> / ? / ? / <id>" carrying package facts that
belong to no locus.
"""
import csv
from types import SimpleNamespace

from mamey.mode_b_receipt import emit_modeb_template_command


def _pkg(tmp_path, rows):
    pkg = tmp_path / "S1" / "package"
    pkg.mkdir(parents=True)
    if rows is not None:
        with open(pkg / "S1_4_triage_board.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["BGC_ID", "Contig", "antiSMASH_Region"])
            w.writeheader()
            w.writerows(rows)
    return pkg


def _args(pkg, bgc, out):
    return SimpleNamespace(package=str(pkg), bgc=bgc, batch=False, out=str(out), contract=None,
                           blastp_waiver="test fixture", scope="all", top_n=None)


def test_unknown_bgc_is_refused_and_nothing_written(tmp_path, capsys):
    pkg = _pkg(tmp_path, [{"BGC_ID": "BGC001", "Contig": "NODE_1", "antiSMASH_Region": "region001"}])
    out = tmp_path / "card.md"
    assert emit_modeb_template_command(_args(pkg, "BGC999", out)) == 2
    assert not out.exists()
    err = capsys.readouterr().err
    assert "BGC999" in err and "not on the triage board" in err and "No template was written" in err


def test_package_without_triage_rows_is_refused(tmp_path, capsys):
    pkg = _pkg(tmp_path, None)
    out = tmp_path / "card.md"
    assert emit_modeb_template_command(_args(pkg, "BGC001", out)) == 2
    assert not out.exists()
    assert "no triage-board rows" in capsys.readouterr().err
