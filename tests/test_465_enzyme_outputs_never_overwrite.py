"""Enzyme catalog, context and page tools never overwrite an input or an existing output, and a failed run leaves no
output. Synthetic fixtures only."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cohort_enzyme_catalog as cec  # noqa: E402
import cohort_enzyme_catalog_page as ecp  # noqa: E402
import enzyme_family_context as efc  # noqa: E402
from test_465_enzyme_family_context import KS, cds, make  # noqa: E402


def one_genome(root, strain="V-1"):
    g = make(root, strain, {"BGC001": [cds("v1", KS, ["PKS_KS"])]}, {"BGC001": "T1PKS"})
    (root / strain / "package" / f"{strain}_proteins.faa").write_text(">v1\nMPEPTIDE\n")
    return g


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    g = one_genome(root)
    gt = root / "genomes.tsv"
    gt.write_text(f"strain\tgene_context\nV-1\t{g}\n")
    return root, gt, root / "V-1" / "package" / "V-1_proteins.faa"


def no_partials(folder):
    return not [p for p in Path(folder).rglob(".*.partial-*")]


@pytest.mark.parametrize("mode", ["direct", "symlink", "hardlink", "existing", "manifest"])
def test_emit_fasta_refuses_an_existing_path_and_changes_nothing(ws, mode):
    root, gt, faa = ws
    out = root / "out.faa"
    if mode == "direct":
        out = faa
    elif mode == "symlink":
        out.symlink_to(faa)
    elif mode == "hardlink":
        os.link(faa, out)
    elif mode == "existing":
        out.write_text("USER DATA\n")
    elif mode == "manifest":
        out = gt
    before = {p: p.read_bytes() for p in (faa, gt, out)}
    with pytest.raises(cec.CatalogError, match="already exists"):
        cec.emit_fasta(cec.read_genomes(gt, root), out)
    assert {p: p.read_bytes() for p in before} == before
    assert no_partials(root)


def test_emit_fasta_checks_every_input_first_and_leaves_no_partial_file(ws):
    root, gt, _ = ws
    g2 = one_genome(root, "V-2")
    (root / "V-2" / "package" / "V-2_proteins.faa").unlink()
    gt.write_text(gt.read_text() + f"V-2\t{g2}\n")
    with pytest.raises(cec.CatalogError, match="V-2: protein FASTA not found"):
        cec.emit_fasta(cec.read_genomes(gt, root), root / "pool.faa")
    assert not (root / "pool.faa").exists() and no_partials(root)


def test_emit_fasta_dangling_symlink_is_refused_and_its_target_not_created(ws):
    root, gt, _ = ws
    (root / "link.faa").symlink_to(root / "elsewhere.faa")
    with pytest.raises(cec.CatalogError, match="already exists"):
        cec.emit_fasta(cec.read_genomes(gt, root), root / "link.faa")
    assert not (root / "elsewhere.faa").exists()


def test_emit_fasta_success_publishes_only_the_output(ws):
    root, gt, _ = ws
    assert cec.emit_fasta(cec.read_genomes(gt, root), root / "pool.faa") == 1
    assert (root / "pool.faa").read_text() == ">V-1|v1\nMPEPTIDE\n" and no_partials(root)


def test_catalog_build_refuses_a_manifest_link_to_an_input(ws):
    root, gt, _ = ws
    out = root / "cat"
    out.mkdir()
    (out / "RUN_INFO.json").symlink_to(gt)
    before = gt.read_bytes()
    with pytest.raises(cec.CatalogError, match="already exists"):
        cec.build(gt, root, out)
    assert gt.read_bytes() == before and sorted(p.name for p in out.iterdir()) == ["RUN_INFO.json"]


def test_catalog_build_that_fails_late_publishes_nothing(ws):
    root, gt, _ = ws
    (root / "bad.tsv").write_text("centroid\tmember\nV-1|v1\tV-1|zz\n")  # centroid not its own member: refused late
    with pytest.raises(cec.CatalogError, match="not listed as their own member"):
        cec.build(gt, root, root / "cat", clusters=root / "bad.tsv")
    assert list((root / "cat").iterdir()) == []


@pytest.mark.parametrize("mode", ["existing", "symlink", "hardlink"])
def test_context_refuses_an_existing_or_linked_manifest(ws, mode):
    root, gt, _ = ws
    cec.build(gt, root, root / "cat")
    out = root / "ctx"
    out.mkdir()
    m = out / "CONTEXT_RUN_INFO.json"
    if mode == "existing":
        m.write_text("KEEP\n")
    elif mode == "symlink":
        m.symlink_to(gt)
    else:
        os.link(gt, m)
    before = (gt.read_bytes(), m.read_bytes())
    with pytest.raises(cec.CatalogError, match="already exists"):
        efc.build(root / "cat", gt, root, out=out)
    assert (gt.read_bytes(), m.read_bytes()) == before
    assert sorted(p.name for p in out.iterdir()) == ["CONTEXT_RUN_INFO.json"]
    with pytest.raises(SystemExit) as e:
        efc.main(["--catalog", str(root / "cat"), "--genomes", str(gt), "--root", str(root), "--out", str(out)])
    assert e.value.code == 2 and (gt.read_bytes(), m.read_bytes()) == before


def test_page_refuses_a_dangling_symlink(ws):
    root, gt, _ = ws
    (root / "cl.tsv").write_text("centroid\tmember\nV-1|v1\tV-1|v1\n")
    cec.build(gt, root, root / "cat", clusters=root / "cl.tsv")
    efc.build(root / "cat", gt, root)
    (root / "page.html").symlink_to(root / "target.html")
    with pytest.raises(cec.CatalogError, match="already exists"):
        ecp.build(root / "cat", root / "page.html", min_strains=1)
    assert not (root / "target.html").exists()
    ecp.build(root / "cat", root / "ok.html", min_strains=1)
    assert (root / "ok.html").stat().st_size > 0 and no_partials(root)
