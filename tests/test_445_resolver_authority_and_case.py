import json,zipfile
from pathlib import Path
import pytest
from mamey import strain_data_home as s

@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.delenv("MAMEY_PACKAGE_HOMES",raising=False)
    monkeypatch.delenv("SAPOTE_ASSEMBLY_AUTHORITY",raising=False)
    s.clear_strain_data_cache()

def pkg(root,home="MAMEY COMPLETE",version="999",contigs=9,engine="1.9.171"):
    p=root/home/f"TST-1_SapoteMamey_v9.7.{version}_engine{engine}_loose_Complete_Package.zip"
    p.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(p,"w") as z:
        z.writestr("package/manifest.json",json.dumps({"strain":"TST-1","assembly":{"contigs":contigs,"genome_bp":900},"antismash_profile":"loose"}))
        z.writestr("result.json",'{"records":[]}')
    return p

def authority(root,path="",anti="",extra=""):
    p=root/"OFFICIAL_DATA/ASSEMBLY_AUTHORITY.tsv";p.parent.mkdir(exist_ok=True)
    p.write_text("strain\tauthoritative_contigs\tauthoritative_genome_bp\tclean_package\tclean_antismash_zip\tantismash_flavor\n"+f"TST-1\t2\t900\t{path}\t{anti}\tloose\n"+extra)
    return p

def test_uppercase_home_found_without_env(tmp_path):
    p=pkg(tmp_path);assert s.resolve_mamey_package("TST-1",str(tmp_path))==str(p)

def test_archive_cannot_outrank_active(tmp_path):
    p=pkg(tmp_path,"Mamey Complete",version="1");pkg(tmp_path,"Mamey Complete_ARCHIVE",version="999")
    assert s.resolve_mamey_package("TST-1",str(tmp_path))==str(p)

def test_empty_descriptor_explains_homes(tmp_path):
    assert "Mamey Complete*" in s.strain_data_home("TST-1",str(tmp_path))["searched_homes"]

def test_clean_directory_wins_over_newer_raw(tmp_path):
    pkg(tmp_path);p=tmp_path/"clean/package";p.mkdir(parents=True)
    (p/"manifest.json").write_text(json.dumps({"strain":"TST-1","assembly":{"contigs":2,"genome_bp":900},"antismash_profile":"loose"}))
    authority(tmp_path,"clean/package")
    assert s.resolve_mamey_package("TST-1",str(tmp_path),"loose")==str(p)
    assert s.resolve_antismash_zip("TST-1",str(tmp_path)) is None

def test_raw_only_fails_closed(tmp_path):
    pkg(tmp_path,"mamey_packages");authority(tmp_path)
    assert s.resolve_mamey_package("TST-1",str(tmp_path)) is None
    assert s.strain_data_home("TST-1",str(tmp_path))["assembly_authority"]["status"]=="SUPERSEDED_ASSEMBLY_OR_MISSING"

def test_nominated_missing_does_not_fall_back(tmp_path):
    pkg(tmp_path,"mamey_packages",contigs=2);authority(tmp_path,"missing/package")
    assert s.resolve_mamey_package("TST-1",str(tmp_path)) is None

def test_clean_antismash_flavor_binding(tmp_path):
    p=pkg(tmp_path);authority(tmp_path,anti=str(p))
    assert s.resolve_antismash_zip("TST-1",str(tmp_path),"loose")==str(p)
    assert s.resolve_antismash_zip("TST-1",str(tmp_path),"strict") is None

def test_invalid_table_and_changed_row_are_not_cached(tmp_path):
    pkg(tmp_path,"mamey_packages",contigs=2);p=authority(tmp_path)
    assert s.resolve_mamey_package("TST-1",str(tmp_path)) is not None
    p.write_text("bad header\n")
    assert s.resolve_mamey_package("TST-1",str(tmp_path)) is None

def test_explicit_missing_authority_refuses(tmp_path,monkeypatch):
    pkg(tmp_path,"mamey_packages");monkeypatch.setenv("SAPOTE_ASSEMBLY_AUTHORITY","missing.tsv")
    assert s.resolve_mamey_package("TST-1",str(tmp_path)) is None

def test_nested_excluded_cannot_outrank_active(tmp_path):
    p=pkg(tmp_path,"Mamey Complete",version="1")
    pkg(tmp_path,"Mamey Complete/variants_EXCLUDED",version="999")
    assert s.resolve_mamey_package("TST-1",str(tmp_path))==str(p)

def test_owner_matched_assembly_prefers_engine_and_lists_other(tmp_path):
    older=pkg(tmp_path,"mamey_packages",version="999",contigs=2,engine="1.9.100")
    newer=pkg(tmp_path,"mamey_packages",version="1",contigs=2,engine="1.9.172")
    authority(tmp_path)
    d=s.strain_data_home("TST-1",str(tmp_path))
    assert d["mamey_package"]==str(newer)
    assert d["superseded_packages"]==[str(older)]

@pytest.mark.parametrize("manifest",[[],{"strain":"TST-1","assembly":[]}])
def test_malformed_nominated_manifest_refuses(tmp_path,manifest):
    p=pkg(tmp_path,"mamey_packages",contigs=2)
    with zipfile.ZipFile(p,"w") as z:z.writestr("package/manifest.json",json.dumps(manifest))
    authority(tmp_path,str(p))
    assert s.resolve_mamey_package("TST-1",str(tmp_path)) is None
