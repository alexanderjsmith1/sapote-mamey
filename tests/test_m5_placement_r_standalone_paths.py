"""Current R bootstrap/relative both route; graphics gate is explicitly opt-in."""
import hashlib
import itertools
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
Phylo = pytest.importorskip("Bio.Phylo")
from tools import phylo_place as native
from .test_m5_placement_metadata_children import fake_renderer, execute_strips
from .test_trees_432_color_strips_report_deliverable import _fixture, _build, _tsv

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "tools/render_placement_COLOR_STRIPS.R"
SIX_KEYS = ("OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


def selected_r():
    selected = os.environ.get("SAPOTE_TEST_RSCRIPT")
    if not selected:
        pytest.skip("coordinator-selected SAPOTE_TEST_RSCRIPT required; no real-R proof from skip")
    executable = Path(selected).resolve(strict=True)
    assert executable.is_file()
    return executable


def test_both_current_child_environment_pins_exact_six_controls(tmp_path, monkeypatch):
    _fixture(tmp_path)
    calls = fake_renderer(tmp_path, monkeypatch)
    result = execute_strips(tmp_path)
    assert result["state"] == "RENDERED_WITH_OMISSIONS" and len(calls) == 2
    for _argv, kwargs in calls:
        assert {key:kwargs["env"].get(key) for key in SIX_KEYS} == {key:"2" for key in SIX_KEYS}
    for child in result["variants"]:
        assert child["resource_environment"] == {key:"2" for key in SIX_KEYS}


def test_actual_r_bootstrap_constructs_absolute_children_from_relative_parent_path(tmp_path):
    """Evaluate actual source bootstrap with base R and intercepted system2, no graphics needed."""
    executable = selected_r()
    relative = Path("relative parent") / "Genus" / RENDERER.name
    target = tmp_path / relative
    target.parent.mkdir(parents=True)
    shutil.copyfile(RENDERER, target)
    text = RENDERER.read_text()
    bootstrap = text[text.index("a<-commandArgs("):text.index("\nctx<-")]
    recorded = tmp_path / "child_calls.txt"
    harness = tmp_path / "actual_bootstrap.R"
    harness.write_text("\n".join([
        "target<-normalizePath("+json.dumps(str(target))+",mustWork=TRUE)",
        "recorded<-"+json.dumps(str(recorded)),
        "commandArgs<-function(trailingOnly=FALSE)if(trailingOnly)'both' else "+json.dumps("--file="+str(relative)),
        "counter<-0L",
        "system2<-function(command,args){counter<<-counter+1L;stopifnot(counter<=2L,identical(command,file.path(R.home('bin'),'Rscript')),identical(args,c(shQuote(target),c('concise','experiment_id')[counter])));cat(args[2],file=recorded,append=TRUE,sep='\\n');0L}",
        "quit<-function(status=0){stopifnot(counter==2L,status==0);base::quit(status=status)}",
        "eval(parse(text="+json.dumps(bootstrap)+"))",
    ])+"\n")
    completed = subprocess.run([str(executable),str(harness)],cwd=tmp_path,env=os.environ.copy(),
                               stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
    assert completed.returncode == 0, completed.stdout
    assert recorded.read_text().splitlines() == ["concise","experiment_id"]


def test_real_r_both_from_relative_parent_preserves_saved_metric_and_denominators(tmp_path):
    """Actual full source both recursion, chosen R/packages, and independently read output."""
    executable = selected_r()
    _fixture(tmp_path)
    tree_path = tmp_path / "tree.newick"
    tree_path.write_text(tree_path.read_text().replace(":0.01",":0.012345678901234567",1))
    original = tree_path.read_bytes()
    built = _build(tmp_path)
    panel = Path(built["dir"])
    assert (panel/"tree_input.newick").read_bytes() == original
    child = tmp_path / "relative parent" / "Genus"
    child.mkdir(parents=True)
    for name in built["input_files"]:
        shutil.copyfile(panel/name,child/name)
    shutil.copyfile(RENDERER,child/RENDERER.name)
    input_before = hashlib.sha256((child/"tree_input.newick").read_bytes()).hexdigest()
    env = dict(os.environ);env.update({key:"1" for key in SIX_KEYS})
    with (child/"render.log").open("x") as log:
        completed = subprocess.run([str(executable),str((child/RENDERER.name).relative_to(tmp_path)),"both"],
            cwd=tmp_path,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert completed.returncode == 0, (child/"render.log").read_text()
    assert hashlib.sha256((child/"tree_input.newick").read_bytes()).hexdigest() == input_before
    metadata = {row["tip"]:row for row in _tsv(child/"metadata.tsv")}
    for variant in ("concise","experiment_id"):
        artifacts = native._strip_artifacts_checked(child,"Genus",variant,metadata)
        assert len(artifacts) == 8
        caption = (child/f"EPAng_Genus_R04_{variant}_caption.txt").read_text()
        assert "Displayed 4 of 8 source tips and 1 of 2 query tips" in caption
        assert "1 query tips omitted" in caption
    source = Phylo.read(child/"tree_input.newick","newick")
    saved = Phylo.read(child/"tree_display.newick","newick")
    for a,b in itertools.combinations(metadata,2):
        assert saved.distance(a,b) == pytest.approx(source.distance(a,b),rel=1e-13,abs=1e-15)
    assert tree_path.read_bytes() == original
