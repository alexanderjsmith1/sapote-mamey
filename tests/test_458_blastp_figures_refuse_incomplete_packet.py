"""The BLASTp identity figures refuse an extra CSV whose result packet is still incomplete.

The RID runner appends a stalled gene's rows to its packet CSV when the gene finishes, so a CSV bound by hash before then is a
partial packet. `_result_generation.json` beside the CSV says complete true or false. The figures refuse a packet that says
false, naming the packet and its missing genes, unless --allow-incomplete-packets; a CSV with no completeness record warns.
Each extra CSV's packet state goes into RUN_INFO.json. Figures and tables do not change when no packet is incomplete.
"""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


bif = _load("blastp_identity_figures_458_packets", ROOT / "tools/blastp_identity_figures.py")
fixture = _load("blastp_identity_fixture_458_packets", Path(__file__).with_name("test_451_blastp_identity_figures.py"))
world = fixture.world

PACKET = "lane/results/S2/p1"
CSV = f"{PACKET}/p1_blastp_top10_clustered.csv"
OUTPUTS = ("BLASTP_IDENTITY_BY_GENOME.png", "BLASTP_IDENTITY_BY_GENOME_numbers.tsv", "BLASTP_IDENTITY_BY_CLASS.png",
           "BLASTP_IDENTITY_BY_CLASS_numbers.tsv", "GENE_VALUES.tsv", "EXTRA_CSV_FILES.tsv")


def _receipt(w, **fields):
    path = w["root"] / PACKET / "_result_generation.json"
    path.write_text(json.dumps(dict(schema=1, generation="g458", files={}) | fields, sort_keys=True))


def _run(w, out, *extra):
    return bif.main(["--genomes", str(w["genomes"]), "--store", str(w["store"]), "--root", str(w["root"]), "--out", str(out),
                     "--binding", "locus_tag", *extra])


def _info(out):
    return json.loads((out / "RUN_INFO.json").read_text())


def test_incomplete_packet_is_refused_with_its_missing_genes(world, capsys):
    _receipt(world, genes_done=["ctg2_2"], genes_expected=["ctg2_2", "ctg2_9"], complete=False)
    out = world["tmp"] / "refused"
    with pytest.raises(SystemExit) as exc:
        _run(world, out, "--extra-csv", f"{PACKET}/*.csv", "--figure", "by-genome")
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "p1" in err and CSV in err and "ctg2_9" in err and "--allow-incomplete-packets" in err
    assert not out.exists()


def test_frozen_list_replay_is_refused_when_its_packet_is_incomplete(world, capsys):
    first = world["tmp"] / "first"
    assert _run(world, first, "--extra-csv", f"{PACKET}/*.csv", "--figure", "by-genome") == 0
    # The CSV's bytes are unchanged, so the list's sha256 check passes; only the receipt says the packet is unfinished.
    _receipt(world, genes_done=["ctg2_2"], genes_expected=["ctg2_2", "ctg2_9"], complete=False)
    with pytest.raises(SystemExit) as exc:
        _run(world, world["tmp"] / "replay", "--extra-csv-list", str(first / "EXTRA_CSV_FILES.tsv"), "--figure", "by-genome")
    assert exc.value.code == 2 and "ctg2_9" in capsys.readouterr().err


def test_opt_in_draws_warns_and_records_the_incomplete_packet(world, capsys):
    _receipt(world, genes_done=["ctg2_2"], genes_expected=["ctg2_2", "ctg2_9"], complete=False)
    out = world["tmp"] / "allowed"
    assert _run(world, out, "--extra-csv", f"{PACKET}/*.csv", "--figure", "by-genome", "--allow-incomplete-packets") == 0
    assert "ctg2_9" in capsys.readouterr().err
    info = _info(out)
    assert info["allow_incomplete_packets"] is True
    assert info["extra_csv_packets"] == [{"path": CSV, "state": "incomplete", "genes_missing": ["ctg2_9"], "generation": "g458"}]


def test_complete_and_unrecorded_packets_draw_the_same_figures(world, capsys):
    runs = {}
    for state, fields in (("no_generation_file", None), ("complete", dict(genes_done=["ctg2_2"], genes_expected=["ctg2_2"],
                                                                          complete=True)),
                          ("no_completeness_record", {})):
        if fields is not None:
            _receipt(world, **fields)
        out = world["tmp"] / state
        assert _run(world, out, "--extra-csv", f"{PACKET}/*.csv") == 0
        err = capsys.readouterr().err
        assert ("completeness unknown" in err) == (state != "complete")
        info = _info(out)
        assert info["allow_incomplete_packets"] is False
        assert [(p["path"], p["state"]) for p in info["extra_csv_packets"]] == [(CSV, state)]
        runs[state] = {name: (out / name).read_bytes() for name in OUTPUTS}
    assert runs["complete"] == runs["no_generation_file"] == runs["no_completeness_record"]
