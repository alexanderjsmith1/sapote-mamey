"""Regression test for --chatgpt-safe propagation into multi-strain runs (v9.7.128)."""
import sys
from pathlib import Path
from types import SimpleNamespace

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from mamey import cli


def test_chatgpt_safe_batch_propagates_require_workbook(monkeypatch, tmp_path):
    calls = []

    def fake_run_one_strain(**kwargs):
        calls.append(kwargs)
        return {"strain_id": kwargs["strain_id"], "status": "PASS", "raw_bgcs": 0, "assembly_tier": "TEST"}

    monkeypatch.setattr(cli, "run_one_strain", fake_run_one_strain)
    args = SimpleNamespace(
        chatgpt_safe=True,
        brief="standard",
        json_evidence="bounded",
        require_workbook=False,
        locus_maps="auto",
        mode="smoke",
        strains=["SID_A.zip", "SID_B.zip"],
        outdir=str(tmp_path),
        master=str(tmp_path / "master.xlsx"),
        taxonomy="Streptomyces|Streptomyces",
        source="SID|SID",
        bioactivity="unknown",
        release=None,
    )

    rc = cli.run_command(args)
    assert rc == 0
    assert args.brief == "none"
    assert args.json_evidence == "off"
    assert args.require_workbook is True
    assert args.locus_maps == "off"
    assert calls and all(c["json_mode"] == "off" for c in calls)
    assert all(c["brief"] == "none" for c in calls)
    assert all(c["require_workbook"] is True for c in calls)
    assert all(c["locus_maps"] == "off" for c in calls)
