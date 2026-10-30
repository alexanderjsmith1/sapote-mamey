"""Synthetic ZIP member locators; no sequence inputs or rendering."""
from zipfile import ZipFile
import pytest
from mamey.kcb_locusmap import _match_member, read_kcb_from_zip


def test_region_only_refuses_ambiguous_contigs():
    with pytest.raises(ValueError,match='multiple'):
        _match_member(['knownclusterblast/ctgA_c1.txt','knownclusterblast/ctgB_c1.txt'],'','region001')


def test_missing_region_does_not_fall_back_to_only_member(tmp_path):
    archive=tmp_path/'synthetic.zip'
    with ZipFile(archive,'w') as zf:
        zf.writestr('knownclusterblast/ctgA_c1.txt','synthetic unused text')
    with pytest.raises(KeyError,match='matching'):
        read_kcb_from_zip(archive,region='region002')


def test_short_contig_and_region_refuse_multiple_full_contigs():
    with pytest.raises(ValueError,match='multiple'):
        _match_member(['knownclusterblast/NODE_1_length_100_cov_1_c1.txt',
                       'knownclusterblast/NODE_1_length_200_cov_2_c1.txt'],'NODE_1','region001')


def test_unique_region_selection_still_succeeds():
    members=['knownclusterblast/ctgA_c1.txt','knownclusterblast/ctgB_c2.txt']
    assert _match_member(members,'','region002')==members[1]
    assert _match_member(members,'ctgA','region001')==members[0]
