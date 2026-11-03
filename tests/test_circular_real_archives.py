"""External-evidence regressions for two verified antiSMASH circular regions.

Set SAPOTE_CIRCULAR_FIXTURE_ROOT to the Oct 30 demonstration folder. These
source archives are not redistributed with the bundle. Missing evidence skips;
a hash mismatch fails before parsing.
"""
import hashlib
import json
import os
from pathlib import Path
import pytest
from mamey.parsers import parse_bgcs_from_zip

CASES = [
    ('GRAECA_ORIGINAL_SOURCE_RECHECK.json','archive_path','archive_sha256','full_identity','region_length_bp'),
    ('PARVOSATA_SOURCE_RECHECK.json','original_archive','original_archive_sha256','identity','region_sequence_length'),
]

@pytest.mark.parametrize('name,path_key,hash_key,identity_key,length_key',CASES)
def test_real_circular_region_length(name,path_key,hash_key,identity_key,length_key):
    root=os.environ.get('SAPOTE_CIRCULAR_FIXTURE_ROOT')
    if not root: pytest.skip('External source evidence root was not supplied')
    receipt=Path(root)/'10 Resolve the circularcoordinate issue for paper use'/name
    if not receipt.is_file(): pytest.skip('Source receipt unavailable')
    item=json.loads(receipt.read_text()); archive=Path(item[path_key])
    if not archive.is_file(): pytest.skip('Source archive unavailable')
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==item[hash_key]
    strain,contig,region,bgc=item[identity_key].split(' / ')
    records=parse_bgcs_from_zip(archive,json_mode='off')
    found=[r for r in records if (r.contig,r.antismash_region,r.bgc_id)==(contig,region,bgc)]
    assert len(found)==1
    record=found[0];assert record.start>record.end
    assert record.contig_length-record.start+record.end==item[length_key]
    assert record.length_kb==round(item[length_key]/1000,2)
