import argparse
import zipfile

from mamey.cli import run_command, _chatgpt_safe_strain_guess


def _zip_with_regions(path, n):
    with zipfile.ZipFile(path, "w") as zf:
        for i in range(1, n + 1):
            zf.writestr(f"region{i:03d}.gbk", "LOCUS       TEST\n")


def test_chatgpt_safe_refuses_large_multistrain_batch_before_running(tmp_path, capsys):
    z1 = tmp_path / "TESTSTRAIN385(4).zip"
    z2 = tmp_path / "TESTSTRAIN441 loose(6).zip"
    _zip_with_regions(z1, 30)
    _zip_with_regions(z2, 20)
    args = argparse.Namespace(
        chatgpt_safe=True, brief="standard", json_evidence="bounded",
        require_workbook=False, locus_maps="auto", heartbeat_seconds=5,
        mode="smoke", chatgpt_followup=False, strains=[str(z1), str(z2)],
        outdir=str(tmp_path / "runs"), master=None, taxonomy="", source="",
        bioactivity="MRSA+Candida", release=None, token_budget="standard",
        input_zip=None, strain=None, display_name=None, metadata_csv=None,
        antismash_profile="unknown",
    )
    rc = run_command(args)
    err = capsys.readouterr().err
    assert rc == 2
    assert "multi-strain batch is too large" in err
    assert "TESTSTRAIN385" in err
    assert "TESTSTRAIN441" in err
    assert "(4)" not in _chatgpt_safe_strain_guess(str(z1))
