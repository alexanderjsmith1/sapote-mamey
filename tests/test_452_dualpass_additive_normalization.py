from pathlib import Path
import pytest
from mamey.dualpass_ledger import normalize_ledger

@pytest.mark.parametrize("name", ["claims.TSV", "claims.tab", "claims", "claims.tsv"])
def test_normalization_never_replaces_source_or_prior_output(tmp_path, name):
    source = tmp_path / name
    content = "assertion_type\tvalue\nlead_flag\tlead\n"
    source.write_text(content)
    output = Path(normalize_ledger(source, {"lead_flag": {}}))
    assert output != source
    assert source.read_text() == content
    output.write_text("prior evidence")
    with pytest.raises(FileExistsError):
        normalize_ledger(source, {"lead_flag": {}})
    assert output.read_text() == "prior evidence"
    assert source.read_text() == content
