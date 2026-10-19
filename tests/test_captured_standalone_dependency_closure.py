"""Generated standalone must carry shared captured-reader dependencies without the engine."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import zipfile
import pytest
from .test_444_rggmci_package_parity import package

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "packaging/rggmci/build_rggmci_package.py"


def test_generated_capture_readers_import_and_use_archive_without_engine(package, tmp_path):
    gbk = ("LOCUS       SYNTHETIC_CLOSURE          12 bp    DNA     linear   BCT 01-JAN-2000\n"
           "ACCESSION   SYNTHETIC_CLOSURE\nVERSION     SYNTHETIC_CLOSURE.1\n"
           "FEATURES             Location/Qualifiers\n     region          1..12\n"
           '                     /product="NRPS"\n     CDS             1..12\n'
           '                     /locus_tag="SYNTHETIC_GENE"\n                     /translation="MRTK"\n'
           "ORIGIN\n        1 atgcgtactaaa\n//\n")
    source = tmp_path / "fixture.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("full.gbk", gbk)
        archive.writestr("fixture.region001.gbk", gbk)
    program = '''
import sys,json,hashlib
from pathlib import Path
import rggmci
from rggmci import source_context,archive_snapshot,ref_completion,residue_tiling
from rggmci.reader import read_regions
p=Path(sys.argv[1]);records=read_regions(p)
assert len(records)==1 and ref_completion.has_whole_genome_gbk(p)
result=rggmci.run(p,reference_completion='off',threads=1)
assert result['input']['antismash_zip_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
assert result['reference_completion']['completion_tier']=='OFF'
assert result['invocation']['sequence_context']['available'] is True
assert not any(n=='mamey' or n.startswith(('mamey.','Bio')) for n in sys.modules)
assert not hasattr(archive_snapshot,'parse_captured'), 'engine-only intake adapter must not leak into standalone'
print(json.dumps({'records':len(records),'source_bound':True,'stdlib_only':True}))
'''
    env = {key: value for key, value in os.environ.items()
           if key not in {"PYTHONPATH", "PYTHONSTARTUP"} and not key.startswith("RGGMCI_")}
    env.update(PYTHONPATH=str(package / "src"), PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-S", "-B", "-c", program, str(source)],
                            cwd=tmp_path, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["source_bound"] is True
    root = package / "src/rggmci"
    provenance = json.loads((root / "PROVENANCE.json").read_text())["source_sha256"]
    assert "mamey/source_context.py" in provenance and "mamey/archive_snapshot.py" in provenance
    assert hashlib.sha256((root / "source_context.py").read_bytes()).hexdigest() == provenance["mamey/source_context.py"]


def test_missing_declared_capture_helper_refuses_before_package_creation(tmp_path):
    spec = importlib.util.spec_from_file_location("dependency_builder", BUILD)
    builder = importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
    source = tmp_path / "incomplete/mamey";source.mkdir(parents=True)
    names = set(builder.VERBATIM) | {name for specs in builder.LIFT.values() for name, _ in specs}
    for name in names:
        (source / name).write_text("pass\n")
    (source / "rggmci.py").write_text("from .source_context import source_zipfile\n")
    out = tmp_path / "refused-package"
    with pytest.raises(SystemExit, match="CAPTURE_READER_DEPENDENCY_MISSING"):
        builder.main(["--bundle", str(source.parent), "--out", str(out)])
    assert not out.exists()
