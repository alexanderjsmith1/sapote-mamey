"""epa-ng gets fitted model parameters or the placement refuses.

epa-ng does not optimize a model given by name only (src/main.cpp), and its IQ-TREE
report reader handles +I and +G only (src/util/parse_model.hpp).
"""
from __future__ import annotations

import inspect

import pytest
from tools import phylo_place as place

IQ_REPORT = "IQ-TREE 3.1.2 built May 17 2026\n\nModel of substitution: {model}\n\nRate parameter R:\n"


def _refpkg(tmp_path, **files):
    ref = tmp_path / "refpkg"
    ref.mkdir()
    for name, content in files.items():
        (ref / name.replace("__", ".")).write_text(content)
    return ref


def test_raxml_bestmodel_is_preferred(tmp_path):
    ref = _refpkg(tmp_path, ref__bestModel="GTR{1/1/1/1/1/1}+FU{0.25/0.25/0.25/0.25}+G4m{1}\n",
                  ref__iq__iqtree=IQ_REPORT.format(model="GTR+F+I+G4"), MODEL="GTR+I+G\n")
    assert place._epa_model_arg(str(ref), False) == str(ref / "ref.bestModel")


def test_iqtree_report_with_gamma_is_passed_as_model_file(tmp_path):
    ref = _refpkg(tmp_path, ref__iq__iqtree=IQ_REPORT.format(model="GTR+F+I+G4"), MODEL="GTR+I+G\n")
    assert place._epa_model_arg(str(ref), False) == str(ref / "ref.iq.iqtree")


@pytest.mark.parametrize("model", ("GTR+F+I+R2", "GTR+F+R4"))
def test_iqtree_freerate_refuses(tmp_path, model):
    ref = _refpkg(tmp_path, ref__iq__iqtree=IQ_REPORT.format(model=model), MODEL="GTR+I+G\n")
    with pytest.raises(SystemExit, match="EPA_MODEL_NOT_REPRESENTABLE"):
        place._epa_model_arg(str(ref), False)


@pytest.mark.parametrize("model", ("GTR+I+G\n", "GTR+G\n", None))
def test_nucleotide_name_only_refuses(tmp_path, model):
    ref = _refpkg(tmp_path, **({"MODEL": model} if model else {}))
    with pytest.raises(SystemExit, match="EPA_MODEL_UNFITTED"):
        place._epa_model_arg(str(ref), False)


def test_explicit_fitted_model_string_is_accepted(tmp_path):
    fitted = "GTR{0.41/1.16/0.55/0.45/2.61/1.0}+FU{0.21/0.25/0.35/0.19}+IU{0.72}+G4m{0.39}"
    ref = _refpkg(tmp_path, MODEL=fitted + "\n")
    assert place._epa_model_arg(str(ref), False) == fitted


def test_protein_empirical_matrix_name_still_accepted(tmp_path):
    ref = _refpkg(tmp_path, MODEL="LG+I+G\n")
    assert place._epa_model_arg(str(ref), True) == "LG+I+G"


def test_iqtree_fallback_limits_modelfinder_to_epa_readable_rates():
    src = inspect.getsource(place)
    assert '["-mrate", "E,I,G,I+G"]' in src
