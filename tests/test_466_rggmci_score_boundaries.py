"""Exercise score classification at the published RG-GMCI boundaries."""
import pytest
from mamey.models import BGCRecord
from mamey.rggmci import ClusterBlastReference, _pair_score


def ref(start, end, rank, nprot):
    return ClusterBlastReference(bgc_id='BGC1', contig='ctg', region_number=1,
        region_key=None, ref='ref', source='fixture', reference_type='', rank=rank,
        nprot=nprot, cumulative_score=0.0, mean_identity=None,
        interval_start=start, interval_end=end, source_file='fixture')


def bgc():
    return BGCRecord(bgc_id='BGC1', contig='ctg', region_number=1, start=1,
                     end=100, contig_length=1000, edge_status='Interior')


@pytest.mark.parametrize('second_start,rank,nprot,expected_score,expected_tier', [
    (20, 1, 3, 14, 'HIGH_RG_GMCI_RESCUE'),
    (100, 1, 3, 13, 'MODERATE_RG_GMCI_CANDIDATE'),
    (20, 8, 0, 9, 'MODERATE_RG_GMCI_CANDIDATE'),
    (20, 11, 0, 8, 'LOW_SHARED_REFERENCE_SIGNAL'),
])
def test_pair_score_boundary(second_start, rank, nprot, expected_score, expected_tier):
    a = ref(0, 100, rank, nprot)
    b = ref(second_start, second_start + 100, rank, nprot)
    score, tier, _ = _pair_score(a, b, bgc(), bgc())
    assert score == expected_score
    assert tier == expected_tier
