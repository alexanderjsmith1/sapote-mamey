import json, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import antismash_strictness_census as asc  # noqa: E402


def _zip(tmp, name, strictness, n_regions, macosx=False):
    p = tmp / f"{name}.zip"
    data = {"version": "8.0.4", "records": [{"id": "c1", "modules": {"antismash.detection.hmm_detection": {"strictness": strictness}}}]}
    with zipfile.ZipFile(p, "w") as z:
        z.writestr(f"{name}.json", json.dumps(data))
        for i in range(n_regions):
            z.writestr(f"{name}/c1.region{i+1:03d}.gbk", "LOCUS")
            if macosx:
                z.writestr(f"__MACOSX/{name}/._c1.region{i+1:03d}.gbk", "x")
    return p


def test_reads_setting_and_ignores_macosx_copies(tmp_path):
    r = asc.census(_zip(tmp_path, "A", "loose", 3, macosx=True))
    assert r["strictness"] == "loose" and r["regions"] == 3 and r["antismash_version"] == "8.0.4"


def test_mixed_settings_fail_uniform_gate(tmp_path, capsys):
    a, b = _zip(tmp_path, "A", "loose", 2), _zip(tmp_path, "B", "relaxed", 2)
    assert asc.main([str(a), str(b)]) == 0
    assert asc.main([str(a), str(b), "--require-uniform"]) == 3
    assert "STRICTNESS_MIXED" in capsys.readouterr().err


def test_uniform_passes(tmp_path):
    a, b = _zip(tmp_path, "A", "loose", 2), _zip(tmp_path, "B", "loose", 5)
    assert asc.main([str(a), str(b), "--require-uniform"]) == 0


def test_appledouble_outside_macosx_is_ignored(tmp_path):
    """A '._' AppleDouble copy outside __MACOSX/ (made by some zip tools) must not add a region."""
    import json, zipfile
    z = tmp_path / "AS-X.zip"
    rec = {"records": [{"modules": {"antismash.detection.hmm_detection": {"strictness": "loose"}}}], "version": "8.0.4"}
    with zipfile.ZipFile(z, "w") as w:
        w.writestr("AS-X/AS-X.json", json.dumps(rec))
        w.writestr("AS-X/c1.region001.gbk", "LOCUS")
        w.writestr("AS-X/._c1.region001.gbk", "junk")
    row = asc.census(z)
    assert row["regions"] == 1
