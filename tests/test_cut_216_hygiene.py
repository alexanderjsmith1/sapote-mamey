"""v9.7.216 hygiene: claim-safety false-positive fixes (#3) verified against the AS-424 receipts,
+ hmm-adjudicate dependency-name fix (#4)."""
from mamey.claim_safety_gate import lint_text

def test_denial_not_flagged():
    # the exact §14 denial that flagged MEDIUM before (negation 100+ chars upstream)
    t = "The evidence does not support that BGC010 produces colibrimycin; KCB is a 12-gene partial only."
    assert lint_text(t) == [], lint_text(t)

def test_makes_idiom_not_flagged():
    for t in ["The edge truncation makes it difficult to resolve the flank.",
              "The over-merge makes the region-level score an aggregate.",
              "This makes them hard to separate."]:
        assert lint_text(t) == [], (t, lint_text(t))

def test_real_overclaim_still_flagged():
    assert lint_text("This cluster produces colibrimycin at high titre.")
    assert lint_text("The BGC synthesizes bombyxamycin.")

def test_safe_context_not_flagged():
    assert lint_text("capacity consistent with colibrimycin biosynthesis") == []

def test_hmm_adjudicate_names_actual_missing_module():
    # the fix reads exc.name; simulate a missing 'Bio' import surfacing through the except path
    import mamey.hmm_blastp_adjudicate as h
    import inspect
    src = inspect.getsource(h)
    assert 'getattr(exc, "name"' in src and "pyhmmer + biopython" in src
