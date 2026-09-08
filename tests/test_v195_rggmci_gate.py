import json
import zipfile
from pathlib import Path

from mamey.models import BGCRecord
from mamey.rggmci import run_rggmci
from mamey.scoring import triage_bgcs


def _block(ref, loc, score, nprot, ident):
    return f'''
>>
Source: {ref} Streptomyces test chromosome, complete genome
Type: NRPS,T1PKS,halogenated
Cumulative BLAST score: {score}
Number of proteins with BLAST hits to this cluster: {nprot}
Reference location: {loc}
identity: {ident}%
'''


def _write_zip(path: Path):
    # v9.7.41: two overlapping shared references (CP000001, CP000002) so the pair carries
    # good_geometry_references == 2 -- the corrected HIGH threshold (a single good-geometry
    # reference now demotes HIGH->MODERATE per the 5-strain calibration).
    node1 = (_block("NZ_CP000001", "NZ_CP000001:10000-15000", 4000, 4, 70)
             + _block("NZ_CP000002", "NZ_CP000002:10000-15000", 3900, 4, 69))
    node2 = (_block("NZ_CP000001", "NZ_CP000001:14800-21000", 3800, 5, 68)
             + _block("NZ_CP000002", "NZ_CP000002:14800-21000", 3700, 5, 67))
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('knownclusterblast/NODE_1_c1.txt', node1)
        z.writestr('knownclusterblast/NODE_2_c1.txt', node2)


def test_rggmci_detects_overlapping_shared_reference(tmp_path):
    z = tmp_path / 'as.zip'
    _write_zip(z)
    bgcs = [
        BGCRecord('BGC001', 'NODE_1', 1, 1, 10000, 10000, products=['NRPS'], edge_status='Full-contig'),
        BGCRecord('BGC002', 'NODE_2', 1, 1, 10000, 10000, products=['T1PKS'], edge_status='Full-contig'),
    ]
    rg = run_rggmci(z, bgcs)
    assert rg['status'] == 'PASS'
    assert rg['pairs_total'] == 1
    top = rg['ranked_pairs'][0]
    assert top['pair'] == 'BGC001+BGC002'
    # gg==2 overlapping references + compatible NRPS/T1PKS hybrid -> HIGH survives both v9.7.41 gates.
    assert top['rggmci_confidence'] == 'HIGH_RG_GMCI_RESCUE'
    assert top['good_geometry_references'] == 2


def test_triage_uses_rggmci_rescue_without_claim_confidence_upgrade(tmp_path):
    z = tmp_path / 'as.zip'
    _write_zip(z)
    bgcs = [
        BGCRecord('BGC001', 'NODE_1', 1, 1, 10000, 10000, products=['NRPS'], edge_status='Full-contig', architecture_confidence='D'),
        BGCRecord('BGC002', 'NODE_2', 1, 1, 10000, 10000, products=['T1PKS'], edge_status='Full-contig', architecture_confidence='D'),
    ]
    rg = run_rggmci(z, bgcs)
    triage = {t.bgc_id: t for t in triage_bgcs(bgcs, rg)}
    assert 'RG-GMCI=HIGH_RG_GMCI_RESCUE' in triage['BGC001'].rationale
    assert triage['BGC001'].claim_confidence == 'Low-Moderate'
