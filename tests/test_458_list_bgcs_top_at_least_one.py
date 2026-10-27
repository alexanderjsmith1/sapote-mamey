"""list-bgcs --top refuses 0 and negative values.

--top 0 silently meant "no limit", and --top -3 sliced rows[:-3], dropping the last three BGCs.
"""
import pytest

from mamey.cli import build_parser


@pytest.mark.parametrize("bad", ["0", "-3"])
def test_top_below_one_is_refused(bad, capsys):
    with pytest.raises(SystemExit) as e:
        build_parser().parse_args(["list-bgcs", "pkg", "--top", bad])
    assert e.value.code == 2
    assert "at least 1" in capsys.readouterr().err


def test_top_one_and_omitted_still_parse():
    assert build_parser().parse_args(["list-bgcs", "pkg", "--top", "1"]).top_n == 1
    assert build_parser().parse_args(["list-bgcs", "pkg"]).top_n is None
