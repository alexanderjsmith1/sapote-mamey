from pathlib import Path
import os,sys,importlib.util
import pytest
from tests.test_named_contig_review import case,saved_run,parsed_run,LABEL,IDENTITY
import gap_directed_rescue as current
candidate=os.environ.get("LANE06_GDR_CANDIDATE")
if candidate:
    spec=importlib.util.spec_from_file_location("named_io_candidate",candidate);gdr=importlib.util.module_from_spec(spec);spec.loader.exec_module(gdr)
else:gdr=current

@pytest.mark.parametrize("when",["during_parse","before_redraw"])
def test_zip_disappears_is_typed_hold_before_render(parsed_run,tmp_path,monkeypatch,capsys,when):
    folder,refs,archive,prots,regions=parsed_run;out=tmp_path/"held_output"
    real=gdr.load_genome
    def load(*a):
        result=real(*a)
        if when=="during_parse":archive.unlink()
        return result
    monkeypatch.setattr(gdr,"load_genome",load)
    if when=="before_redraw":
        def names(*a,**k):archive.unlink();return {}
        monkeypatch.setattr(gdr,"load_gene_names",names)
    monkeypatch.setattr(gdr,"draw_locus_map",lambda *a,**k: pytest.fail("must refuse before render"))
    rc=gdr.main(["--zip",str(archive),"--label",LABEL,"--redraw",str(folder),"--mibig-dir",str(refs),"--out",str(out),"--named-contig",IDENTITY])
    captured=capsys.readouterr();assert rc==2 and "NAMED_CONTIG_" in captured.out and "HOLD" in captured.out
    assert "redrew" not in captured.out and not out.exists()

def test_default_io_exception_contract_unchanged(saved_run,tmp_path,monkeypatch):
    folder,refs,archive=saved_run
    def load(*a):raise FileNotFoundError("synthetic missing input")
    monkeypatch.setattr(gdr,"load_genome",load)
    with pytest.raises(FileNotFoundError):gdr.main(["--zip",str(archive),"--label",LABEL,"--redraw",str(folder),"--mibig-dir",str(refs),"--out",str(tmp_path/"default")])
