"""BC2 .399 audit: tools/strain_bigscape_report.py's "BGC class distribution" section shows a
class line unconditionally when its count is 1 IF the class name is PKS/NRPS/RiPP-family --
the code's own comment documents this as "always surface scientifically important classes even
as singletons." That check compared the raw antismash_class TSV value against these three
literals case-sensitively. Real antiSMASH classes are lowercase for several of them
("nrps", "t1pks", ...), confirmed against mamey/class_architecture.py::_REAL_CLASSES -- so a
real singleton NRPS/PKS/RiPP class was silently dropped from the report, contradicting the
code's own stated intent.

Reuses tests/test_strain_report_and_labels_v9_7_293.py's own harness (argv patching, per-BGC
TSV fixture, read the output markdown) with realistic lowercase class values instead of that
test's uppercase ones.
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(__file__)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "..", "tools", name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


report = _load("strain_bigscape_report")


def test_singleton_lowercase_nrps_class_is_not_silently_dropped():
    d = tempfile.mkdtemp()
    per = os.path.join(d, "per_bgc.tsv")
    with open(per, "w") as fh:
        fh.write("strain\tlocator\tantismash_class\tfamily_status\tMIBiG_family_anchors\tnearest_MIBiG\tnearest_distance\n")
        # exactly ONE occurrence of a real, realistic lowercase NRPS class -- the code's own
        # comment intent is "always show this, regardless of count".
        fh.write("AS-X\tNODE_1_length_50000_cov_10.region001\tnrps\tKNOWN\tBGC1 (x)\tBGC1 (x)\t0.42\n")
        # bulk out the count so 'terpene' (k>=2) shows for comparison, unaffected either way
        fh.write("AS-X\tNODE_2_length_50000_cov_10.region001\tterpene\tnovel\t\t\t1.000\n")
        fh.write("AS-X\tNODE_3_length_50000_cov_10.region001\tterpene\tnovel\t\t\t1.000\n")

    out = os.path.join(d, "out.md")
    argv = sys.argv[:]
    sys.argv = ["x", "--strain", "AS-X", "--per-bgc", per, "--out", out]
    try:
        report.main()
    finally:
        sys.argv = argv

    txt = open(out).read()
    section = txt.split("## BGC class distribution")[1].split("##")[0]
    assert "nrps: 1" in section, f"singleton real NRPS class dropped from report:\n{section}"
