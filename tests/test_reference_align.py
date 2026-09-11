"""Smoke tests for bgc_reference_align.py (classify + score/pid math; no network)."""
import os, importlib.util
HERE=os.path.dirname(__file__)
spec=importlib.util.spec_from_file_location("ra",os.path.join(HERE,"..","tools","bgc_reference_align.py"))
ra=importlib.util.module_from_spec(spec); spec.loader.exec_module(ra)
def test_classify():
    assert ra.classify("Radical_SAM","B12-binding radical SAM")=="core"
    assert ra.classify("MFS_1","MFS transporter")=="transport"
    assert ra.classify("2OG-FeII_Oxy_3","2OG-Fe(II) oxygenase")=="tailoring"
    print("PASS test_classify")
def test_score_pid_identical():
    import pytest; pytest.importorskip("Bio")  # optional dep: skip (not fail) when absent, per policy
    al=ra._aligner()
    s="MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ"
    sc,pid,L=ra._score_pid(al,s,s)
    assert pid==100.0 and L==len(s), (pid,L)
    print("PASS test_score_pid_identical")
if __name__=="__main__":
    test_classify(); test_score_pid_identical(); print("ALL PASS")
