"""cluster_discovery admits only complete versioned accessions and never builds shell from raw service text."""
import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cluster_discovery.py"


def _module():
    spec = importlib.util.spec_from_file_location("cd_464r3", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_parse_ipg_refuses_prefix_only_values():
    m = _module()
    text = ("Id\tAssembly\tOrganism\tStrain\n"
            "1\tGCF_000000001.1;touch_SYNTHETIC_MARKER\tOrg a\ts1\n"
            "2\tGCF_000000002\tOrg b\ts2\n"
            "3\tGCA_000000003.2\tOrg c\ts3\n")
    assert m.parse_ipg(text) == [("GCA_000000003.2", "Org c", "s3")]


def test_script_contains_only_quoted_valid_accessions(tmp_path):
    m = _module()
    rows = [{"assembly": "GCF_000000001.1", "organism": "", "strain": "", "marker_identity_pct": 90,
             "marker_protein": "X"},
            {"assembly": "GCF_000000009.1;echo SYNTHETIC", "organism": "", "strain": "",
             "marker_identity_pct": 80, "marker_protein": "Y"}]
    m.write_table(rows, tmp_path)
    script = (tmp_path / "download_genomes.sh").read_text()
    assert "GCF_000000001.1" in script
    assert ";" not in script.split("\n", 3)[3]


def test_missing_marker_file_exits_2_without_traceback(tmp_path, capsys):
    m = _module()
    assert m.main(["--marker", str(tmp_path / "absent.faa"), "--outdir", str(tmp_path / "o")]) == 2
    assert "INPUT_FAILED" in capsys.readouterr().err
