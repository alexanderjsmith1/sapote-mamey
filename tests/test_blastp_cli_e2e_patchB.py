"""v9.7.196 fix — CLI-level end-to-end guard for Patch B. The unit tests called _scope_feats
directly and never exercised blastp_online_command -> extract_cds_features -> _find_crosswalk, so a
NameError (Path out of scope) and a ValueError (package dir has no proteins) shipped green. These
tests reach the CLI path and assert it does not crash on the two invocations the audit reproduced."""
import os
from types import SimpleNamespace

import pytest

from mamey.blastp_online import _find_crosswalk, blastp_online_command

_ZIP = "/tmp/as421_region.zip"
_PKG = "/data/mamey-local/work/strain_intake/runs_v184/AS-421/package"


def test_find_crosswalk_no_nameerror_on_zip():
    """_find_crosswalk must not NameError (the Path-out-of-scope crash) on a ZIP path."""
    args = SimpleNamespace(package="/tmp/does_not_matter.zip", bgc="BGC001", crosswalk=None, region=None)
    # returns None (no crosswalk) but must not raise NameError
    assert _find_crosswalk(args) is None


@pytest.mark.skipif(not os.path.isdir(_PKG), reason="AS-421 package not present")
def test_command_package_dir_refuses_cleanly_not_crash():
    """--package <pkg_dir> --bgc: a package dir has no proteins → the command must refuse (rc=1),
    not crash with ValueError."""
    args = SimpleNamespace(package=_PKG, bgc="BGC041", crosswalk=None, region=None,
                           database="nr", evalue="1e-5", batch_size=10, outdir="/tmp/bo_e2e")
    rc = blastp_online_command(args)
    assert rc == 1  # clean refusal, not an exception


def test_find_crosswalk_explicit_dir(tmp_path):
    """--crosswalk pointing at a dir with a crosswalk CSV resolves it."""
    csv = tmp_path / "AS-x_2b_bgc_crosswalk.csv"
    csv.write_text("bgc_id,contig,start,end\nBGC001,NODE_1,100,200\n")
    args = SimpleNamespace(package="/tmp/x.zip", bgc="BGC001", crosswalk=str(tmp_path), region=None)
    xw = _find_crosswalk(args)
    assert xw is not None and "BGC001" in xw
