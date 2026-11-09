"""outgroup_registry: an existing cache file is never removed or overwritten in place. A replacement
that fails admission leaves the old file byte-identical; a passing replacement keeps the old file
aside; an existing --out file and a changed fetch script are refused, not overwritten."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

HEADER = "tree_scope\tingroup_taxon\tfamily\toutgroup_genus\toutgroup_species_strain\tassembly_accession\tstatus\trationale\n"
ROW = "genus\tStreptomyces\tStreptomycetaceae\tGordonia\tGordonia bronchialis DSM 43247 NR_074529.1\tGCF_000024785.1\tLOCKED\truled\n"
SEQ = "ACGT" * 400
STALE = ">Gordonia_NR_074529_1_NR_119065.1  [outgroup for Streptomyces]\n" + SEQ + "\n"


def _load(tmp_path, monkeypatch):
    reg = tmp_path / "registry.tsv"
    reg.write_text(HEADER + ROW)
    monkeypatch.setenv("OUTGROUP_REGISTRY", str(reg))
    spec = importlib.util.spec_from_file_location("og_464r3", ROOT / "tools" / "outgroup_registry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.CACHE = str(tmp_path / "cache")
    monkeypatch.setattr(mod, "_blastdbcmd", lambda: "/fake/blastdbcmd")
    monkeypatch.setattr(mod, "_fetch_entry", lambda bdc, acc: ("NR_074529.1", "Gordonia bronchialis DSM 43247 16S ribosomal RNA", SEQ))
    return mod


def _stale_cache(tmp_path):
    d = tmp_path / "cache" / "16S"
    d.mkdir(parents=True)
    f = d / "Gordonia_Gordonia_bronchialis_DSM_43247.fasta"
    f.write_text(STALE)
    return f


def test_failed_replacement_leaves_old_cache_untouched(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    f = _stale_cache(tmp_path)
    monkeypatch.setattr(og, "header_admissible", lambda path: (False, "FORCED_FAIL"))
    with pytest.raises(og.RegistryAuthorityError, match="OUTGROUP_HEADER_INADMISSIBLE"):
        og.get_16s("Streptomyces", quiet=True)
    assert f.read_text() == STALE
    assert sorted(p.name for p in f.parent.iterdir()) == [f.name]  # the failed candidate was ours and is gone


def test_passing_replacement_keeps_the_old_file_aside(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    f = _stale_cache(tmp_path)
    fa = og.get_16s("Streptomyces", quiet=True)
    assert Path(fa) == f and f.read_text().startswith(">NR_074529.1 ")
    kept = [p for p in f.parent.iterdir() if ".replaced-" in p.name]
    assert len(kept) == 1 and kept[0].read_text() == STALE


def test_existing_out_is_refused(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    out = tmp_path / "mine.fasta"
    out.write_text("keep me\n")
    with pytest.raises(og.RegistryAuthorityError, match="OUTPUT_EXISTS"):
        og.get_16s("Streptomyces", quiet=True, out=str(out))
    assert out.read_text() == "keep me\n"


def test_changed_fetch_script_is_refused_and_identical_one_reused(tmp_path, monkeypatch):
    og = _load(tmp_path, monkeypatch)
    args = SimpleNamespace(genus="Streptomyces", scope="genus", fetch=True)
    assert og.cmd_genome(args) == 0
    sh = next((tmp_path / "cache" / "genomes").glob("fetch_*.sh"))
    first = sh.read_text()
    assert og.cmd_genome(args) == 0 and sh.read_text() == first
    sh.write_text("#!/bin/bash\necho edited by hand\n")
    with pytest.raises(og.RegistryAuthorityError, match="FETCH_SCRIPT_EXISTS"):
        og.cmd_genome(args)
    assert sh.read_text() == "#!/bin/bash\necho edited by hand\n"
