from mamey.collection_figures import FigureSpec, _check_gate


def test_minimum_counts_only_rows_with_all_required_fields():
    spec = FigureSpec("generic", "Generic", "Generic fixture", ["genus", "source"], min_rows=2)
    rows = [{"genus": "Streptomyces", "source": "soil"},
            {"genus": "", "source": "water"}, {"genus": "Other", "source": None}]
    can, reason = _check_gate(spec, rows)
    assert not can and "only 1 rows" in reason and "minimum 2" in reason
    rows.append({"genus": "Other", "source": "water"})
    assert _check_gate(spec, rows) == (True, "")
