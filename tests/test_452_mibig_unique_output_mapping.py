import pytest
from tools.fetch_mibig_reference import _extract_from_tarball

@pytest.mark.parametrize("specs", [["BGC0000001:one", "BGC0000001:two"], ["BGC0000001:same", "BGC0000002:same"], ["BGC0000001:one", "invalid"]])
def test_ambiguous_request_is_refused_before_opening_archive_or_writing(tmp_path, specs):
    out = tmp_path / "output"
    if "invalid" in specs:
        written, missing = _extract_from_tarball(str(tmp_path / "missing.tar.gz"), specs, outdir=str(out))
        assert written == [] and missing == ["invalid"]
    else:
        with pytest.raises(ValueError):
            _extract_from_tarball(str(tmp_path / "missing.tar.gz"), specs, outdir=str(out))
    assert not out.exists()
