"""P3 lineage-genus regression (v9.7.187): _genus must read the genus from a delimited
lineage string (terminal rank), not just a binomial's first token. v9.7.185 P3 returned
REVIEW for every lineage-form --taxonomy because _genus took the first whitespace token
("bacteria") of a ";"-delimited lineage."""
import pytest
from mamey.cohort_resolver import _genus, actino_status
from mamey.master_workbook import _scope_from_taxonomy

LINEAGE_STREP = "Bacteria;Actinomycetota;Actinomycetes;Streptomycetales;Streptomycetaceae;Streptomyces"
LINEAGE_PAENI = "Bacteria, Firmicutes, Bacilli, Bacillales, Paenibacillaceae, Paenibacillus"
LINEAGE_OSCIL = "Bacteria;Cyanobacteria;Oscillatoriophycideae;Oscillatoria"


@pytest.mark.parametrize("tax,genus", [
    (LINEAGE_STREP, "streptomyces"),
    (LINEAGE_PAENI, "paenibacillus"),
    (LINEAGE_OSCIL, "oscillatoria"),
    ("Streptomyces", "streptomyces"),          # binomial path unchanged
    ("Streptomyces sp. AS-162", "streptomyces"),
    ("Candidatus Streptomyces", "streptomyces"),
])
def test_genus_from_lineage_or_binomial(tax, genus):
    assert _genus(tax) == genus


@pytest.mark.parametrize("tax,scope", [
    (LINEAGE_STREP, "IN_SCOPE"),
    (LINEAGE_PAENI, "OUT_OF_SCOPE"),
    (LINEAGE_OSCIL, "REVIEW"),
    ("Streptomyces", "IN_SCOPE"),
])
def test_scope_from_lineage(tax, scope):
    # regression: v9.7.185 P3 returned REVIEW for every lineage-form taxonomy
    assert _scope_from_taxonomy(tax) == scope
