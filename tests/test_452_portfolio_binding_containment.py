from types import SimpleNamespace
import pytest
from mamey.portfolio_config import write_portfolio_binding, PortfolioConfigError

@pytest.mark.parametrize("kind", ["directory", "temporary"])
def test_binding_publication_cannot_follow_output_symlink_outside_project(tmp_path, kind):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    evidence = outside / "unique.json"
    evidence.write_text("original")
    if kind == "directory":(root / "project_outputs").symlink_to(outside)
    else:
        (root / "project_outputs").mkdir()
        (root / "project_outputs/portfolio_binding.tmp").symlink_to(evidence)
    with pytest.raises(PortfolioConfigError):
        write_portfolio_binding(root, SimpleNamespace(as_dict=lambda: {"schema": "synthetic"}))
    assert evidence.read_text() == "original"
    assert not (outside / "portfolio_binding.json").exists()
