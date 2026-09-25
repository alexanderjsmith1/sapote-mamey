import shutil, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import sixteen_s_similarity_check as c  # noqa: E402


def test_species_name_expansion():
    assert c.full_species("Streptomyces sp.", "S. griseus") == "Streptomyces griseus"
    assert c.full_species("Nocardia sp.", "N. alba") == "Nocardia alba"
    assert c.full_species("Devosia sp.", "D. honganensis") == "Devosia honganensis"
    assert c.full_species("Streptomyces sp.", "Kitasatospora herbaricolor") == "Kitasatospora herbaricolor"


def test_flag_threshold_and_blanks():
    assert c.flag("100", "96.27", 1.0) and c.flag("95.0", "100.00", 1.0)
    assert not c.flag("98.6", "98.52", 1.0)
    assert not c.flag("", "98.5", 1.0) and not c.flag("99", "", 1.0)


@pytest.mark.skipif(shutil.which("blastn") is None, reason="BLAST+ not on PATH")
def test_end_to_end_needs_blast():
    pytest.skip("end-to-end run needs a local 16S database; see CARD.md for the recorded real run")
