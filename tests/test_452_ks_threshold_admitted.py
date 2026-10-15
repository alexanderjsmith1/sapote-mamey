"""The KS containment threshold is admitted as a finite number in [0, 1] before any work (P300-130)."""
import io
import math
import zipfile

import pytest

from mamey import pks_ks_scan as P

# Two synthetic ~120-aa slices with no shared 5-mer, so containment between them is 0.0.
_KS_A = "M" + "ACDEFGHIKLMNPQRSTVWY" * 6
_KS_B = "M" + "YWVTSRQPNMLKIHGFEDCA" * 6


def _gbk(locus, seq):
    return (
        "LOCUS       synthetic 1000 bp DNA linear\n"
        "FEATURES             Location/Qualifiers\n"
        "     aSDomain        1..360\n"
        '                     /aSDomain="PKS_KS"\n'
        f'                     /locus_tag="{locus}"\n'
        f'                     /translation="{seq}"\n'
        "//\n"
    )


def _zip_two_unrelated():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("NODE_1.region1.gbk", _gbk("ctgA_1", _KS_A))
        zf.writestr("NODE_2.region1.gbk", _gbk("ctgB_1", _KS_B))
    buf.seek(0)
    return buf


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, -0.1, 1.5, True, False, "0.4", None])
def test_invalid_threshold_is_refused_before_work(bad):
    with pytest.raises(ValueError, match="KS containment threshold"):
        P.run_pks_ks_scan(_zip_two_unrelated(), threshold=bad)


def test_nan_cannot_emit_unrelated_unclassified_pairs():
    # Base behaviour: NaN skipped the `c < threshold` filter and emitted this 0.0-containment pair.
    with pytest.raises(ValueError):
        P.run_pks_ks_scan(_zip_two_unrelated(), threshold=math.nan)


@pytest.mark.parametrize("ok", [0, 0.0, 1, 1.0, P.DEFAULT_THRESHOLD])
def test_valid_thresholds_are_admitted_and_unchanged(ok):
    scan = P.run_pks_ks_scan(_zip_two_unrelated(), threshold=ok)
    assert scan["threshold"] == ok and scan["n_ks"] == 2
    # only a threshold of exactly 0 lets a 0.0-containment pair through, as before
    assert len(scan["cross_contig_clades"]) == (1 if ok == 0 else 0)
