"""Frozen CSV lists reproduce numerical outputs and reject input drift."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
fixture=load("extra_fixture",Path(__file__).with_name("test_451_blastp_identity_figures.py"))
world=fixture.world

@pytest.fixture(params=["renderer","query_index"])
def runner(world,request):
    if request.param=="renderer":
        mod=load("extra_renderer",ROOT/"tools/blastp_identity_figures.py")
        args=["--root",str(world["root"]),"--store",str(world["store"]),"--genomes",str(world["genomes"]),"--binding","locus_tag","--figure","by-genome"]
        receipt=lambda out:out
        outputs=lambda out:[out/"GENE_VALUES.tsv",out/"BLASTP_IDENTITY_BY_GENOME_numbers.tsv"]
    else:
        (world["root"]/"Blastp RESULTS").mkdir()
        mod=load("extra_index",ROOT/"tools/blastp_query_index.py")
        args=["--root",str(world["root"])]
        receipt=lambda out:out.with_name(out.name+".provenance")
        outputs=lambda out:[out]
    return mod,args,receipt,outputs


def first(world,runner):
    mod,args,receipt,outputs=runner;out=world["tmp"]/"first"
    assert mod.main(args+["--out",str(out),"--extra-csv","lane/results/*/*/*.csv"])==0
    manifest=receipt(out)/"EXTRA_CSV_FILES.tsv"
    rows=list(csv.DictReader(manifest.open(),delimiter="\t"));assert len(rows)==1
    assert set(rows[0])=={"path","sha256","bytes"}
    assert not Path(rows[0]["path"]).is_absolute()
    return out,manifest,rows


def test_glob_list_replay_is_exact(world,runner):
    mod,args,receipt,outputs=runner;out,manifest,rows=first(world,runner)
    # A later matching lane file must not silently enter the frozen replay.
    extra=world["root"]/"lane/results/later/run/new.csv";extra.parent.mkdir(parents=True)
    extra.write_text("strain,gene,hit_rank,pct_identity\n")
    replay=world["tmp"]/"replay"
    assert mod.main(args+["--out",str(replay),"--extra-csv-list",str(manifest)])==0
    for a,b in zip(outputs(out),outputs(replay)):assert a.read_bytes()==b.read_bytes()
    info=json.loads((receipt(replay)/"RUN_INFO.json").read_text())
    assert info["extra_csv_list_sha256"]==hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert info["extra_csv_manifest_sha256"]==hashlib.sha256((receipt(replay)/"EXTRA_CSV_FILES.tsv").read_bytes()).hexdigest()


@pytest.mark.parametrize("drift",["changed","missing"])
def test_drift_names_file_and_exits_two(world,runner,drift,capsys):
    mod,args,receipt,outputs=runner;out,manifest,rows=first(world,runner)
    source=world["root"]/rows[0]["path"]
    if drift=="changed":source.write_text(source.read_text()+"\n")
    else:source.unlink()
    with pytest.raises(SystemExit) as exc:
        mod.main(args+["--out",str(world["tmp"]/"refused"),"--extra-csv-list",str(manifest)])
    assert exc.value.code==2
    assert rows[0]["path"] in capsys.readouterr().err
    assert not (world["tmp"]/"refused").exists()
