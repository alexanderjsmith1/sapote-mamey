"""v9.7.438: a caller-supplied label must never name a file outside the tool's --outdir.

The defect, reproduced on pristine v9.7.437: `tools/fetch_mibig_reference.py` built its output as
`os.path.join(outdir, f"{label}.gbk")` straight from the `ACCESSION:label` spec. Running

    --acc BGC0000001:../project_data/precious --outdir refs/

wrote the MIBiG member over `project_data/precious.gbk` -- an existing reference file outside the
declared output root -- and reported it as a normal write, with the escaped path printed as if it
were a result. `tools/fetch_reference_cluster.py:genes_to_gbk` had the identical construction.

Severity is bounded by provenance: in the shipped bundle the label reaches these tools only from an
operator's `--acc` / `--mibig` argument (`tools/cluster_brief.py:157` forwards the operator's spec
verbatim), not from parsed antiSMASH or ClusterBlast data. So this is a fail-closed/containment gap
and a real footgun -- a mistyped label silently destroys a reference GBK -- rather than a
data-driven injection path. The guard is cheap either way, and `--outdir` is the whole safety
contract these tools offer.

These tests pin the invariant (nothing lands outside outdir) rather than the individual bad strings.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mamey.path_safety import (  # noqa: E402
    UnsafeOutputLabel, contained_output_path, safe_label,
)

ESCAPING_LABELS = [
    "../project_data/precious",     # the reproduced case
    "../../etc/hosts",
    "/etc/passwd",                  # absolute
    "refs/../../outside",
    "sub/dir",                      # any separator at all
    "back\\slash",                  # Windows separator, rejected on every platform
    "..",
    ".",
    ".hidden",
    "",
    "   ",
    "nul\x00byte",
    "new\nline",
    "a" * 101,                      # over the length ceiling
]

ACCEPTED_LABELS = ["nystatin_ref", "BGC0000116", "polyoxin", "ref-2", "anti.fungal", "x+y", "A1"]


@pytest.mark.parametrize("label", ESCAPING_LABELS)
def test_safe_label_refuses_anything_that_is_not_a_plain_filename(label):
    with pytest.raises(UnsafeOutputLabel):
        safe_label(label)


@pytest.mark.parametrize("label", ACCEPTED_LABELS)
def test_safe_label_admits_ordinary_reference_labels(label):
    assert safe_label(label) == label


@pytest.mark.parametrize("label", ESCAPING_LABELS)
def test_contained_output_path_refuses_escapes(tmp_path, label):
    with pytest.raises(UnsafeOutputLabel):
        contained_output_path(tmp_path, label, ".gbk")


def test_contained_output_path_returns_a_direct_child(tmp_path):
    target = contained_output_path(tmp_path, "nystatin_ref", ".gbk")
    assert target.parent == tmp_path.resolve()
    assert target.name == "nystatin_ref.gbk"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mibig_tarball(path: Path, accession: str = "BGC0000001") -> None:
    with tarfile.open(path, "w:gz") as tar:
        data = b"LOCUS       " + accession.encode() + b"\n//\n"
        info = tarfile.TarInfo(f"mibig_gbk_4.0/{accession}.gbk")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


def test_mibig_fetch_does_not_write_outside_outdir(tmp_path):
    """The end-to-end reproduction: the neighbouring file must survive untouched."""
    module = _load("fetch_mibig_reference")
    tarball = tmp_path / "mibig_gbk_4.0.tar.gz"
    _mibig_tarball(tarball)
    outdir = tmp_path / "refs"
    outdir.mkdir()
    victim_dir = tmp_path / "project_data"
    victim_dir.mkdir()
    victim = victim_dir / "precious.gbk"
    victim.write_text("REAL REFERENCE DATA", encoding="utf-8")

    with pytest.raises(UnsafeOutputLabel):
        module._extract_from_tarball(
            str(tarball), ["BGC0000001:../project_data/precious"],
            version="4.0", outdir=str(outdir))

    assert victim.read_text(encoding="utf-8") == "REAL REFERENCE DATA"
    assert list(outdir.iterdir()) == []


def test_mibig_fetch_still_writes_an_ordinary_label(tmp_path):
    """The guard must not break the documented happy path."""
    module = _load("fetch_mibig_reference")
    tarball = tmp_path / "mibig_gbk_4.0.tar.gz"
    _mibig_tarball(tarball)
    outdir = tmp_path / "refs"

    written, missing = module._extract_from_tarball(
        str(tarball), ["BGC0000001:nystatin_ref"], version="4.0", outdir=str(outdir))

    assert missing == []
    assert len(written) == 1
    landed = Path(written[0][2])
    assert landed == (outdir.resolve() / "nystatin_ref.gbk")
    assert landed.read_bytes().startswith(b"LOCUS")


def test_reference_cluster_gbk_writer_refuses_an_escaping_label(tmp_path):
    """The sibling construction in fetch_reference_cluster.genes_to_gbk is guarded too."""
    module = _load("fetch_reference_cluster")
    genes = [{"tag": "ctg1_1", "start": 0, "end": 30, "strand": 1,
              "aa": "MKV", "gene": "abcA", "domains": ""}]
    outdir = tmp_path / "refs"
    outdir.mkdir()
    victim = tmp_path / "precious.gbk"
    victim.write_text("REAL REFERENCE DATA", encoding="utf-8")

    with pytest.raises(UnsafeOutputLabel):
        module.genes_to_gbk(genes, "../precious", str(outdir))

    assert victim.read_text(encoding="utf-8") == "REAL REFERENCE DATA"


def test_no_unguarded_interpolated_output_names_remain():
    """Ratchet: an output filename INTERPOLATED from a variable must go through the guard.

    Only interpolated names are flagged. `Path(outdir) / "dendrogram.png"` is a constant and
    cannot escape, so it stays out of the ratchet -- an over-broad version of this check fired on
    six such literals in cluster_gene_compare / cluster_relate and would have trained the next
    reader to ignore it.

    Widening this check past the two sites the hostile-audit pass named is what surfaced
    `tools/scope_cluster.py` and the seven `{grp}`-named outputs in `tools/phylo_place.py`;
    the ratchet exists so a fourth site has to be a reviewed decision rather than a silent one.
    """
    import re
    interpolated = re.compile(
        r"""(Path\(\s*outdir\s*\)\s*/\s*f["'][^"']*\{"""
        r"""|os\.path\.join\(\s*outdir\s*,\s*f["'][^"']*\{)""")
    guarded = ("contained_output_path", "safe_label(")
    allow = {
        # every {grp} here is validated once at the top of cmd_report by safe_label(); adding the
        # call to each of the seven f-strings would be noise, so the file is listed with its reason.
        "tools/phylo_place.py",
    }
    offenders = []
    for py in sorted((ROOT / "tools").rglob("*.py")):
        rel = py.relative_to(ROOT).as_posix()
        if rel in allow:
            continue
        for lineno, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if interpolated.search(line) and not any(g in line for g in guarded):
                offenders.append(f"{rel}:{lineno}")
    assert not offenders, (
        "an output filename is interpolated from a variable with no containment guard — route it "
        f"through mamey.path_safety.contained_output_path / safe_label: {offenders}")


def test_phylo_place_validates_its_provenance_group(tmp_path, monkeypatch):
    """`grp` is read from _provenance.json, not typed by an operator — the data-derived case."""
    module = _load("phylo_place")
    pj = tmp_path / "_provenance.json"
    pj.write_text('{"group": "../../escaped"}', encoding="utf-8")
    with pytest.raises(UnsafeOutputLabel):
        module.safe_label(json.loads(pj.read_text())["group"], field="group")
    # the ordinary case still passes through untouched
    assert module.safe_label("streptomyces_cohort", field="group") == "streptomyces_cohort"


def test_scope_cluster_refuses_an_escaping_label(tmp_path):
    """--label and --category both name the scoped GBK; either can escape."""
    module = _load("scope_cluster")
    outdir = tmp_path / "scope_out"
    outdir.mkdir()
    with pytest.raises(UnsafeOutputLabel):
        module.contained_output_path(str(outdir), "../evil_nucleoside", "_scoped.gbk")
    assert module.contained_output_path(str(outdir), "AS168_nucleoside", "_scoped.gbk") == (
        outdir.resolve() / "AS168_nucleoside_scoped.gbk")
