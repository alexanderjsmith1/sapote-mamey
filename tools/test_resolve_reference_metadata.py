"""Offline tests for resolve_reference_metadata — parse, strain-gate, absence, deposit heuristic.
No network: efetch is monkeypatched with a real-shaped GenBank SOURCE fixture. Run: pytest -q."""
import resolve_reference_metadata as m

FIX = (
    "LOCUS       CP129614   1 bp    DNA     linear   BCT\n"
    "FEATURES             Location/Qualifiers\n"
    "     source          1..6500000\n"
    '                     /organism="Nocardia sp. PE-7"\n'
    '                     /strain="PE-7"\n'
    '                     /isolation_source="an LDPE film in soil"\n'
    '                     /country="South Korea: Jeonju"\n'
    "     gene            1..1000\n"
)

def test_parse_source():
    q = m.parse_source(FIX)
    assert q["isolation_source"] == "an LDPE film in soil"
    assert q["country"] == "South Korea: Jeonju"
    assert q["strain"] == "PE-7"

def test_strain_match_resolves(monkeypatch):
    monkeypatch.setattr(m, "efetch_source", lambda acc, **k: FIX)
    r = m.resolve("CP129614.1", expected_strain="PE-7")
    assert r["status"] == "STRAIN_CONFIRMED"
    assert r["isolation_source"] == "an LDPE film in soil"

def test_strain_gate_refuses_mismatch(monkeypatch):
    monkeypatch.setattr(m, "efetch_source", lambda acc, **k: FIX)
    r = m.resolve("CP129614.1", expected_strain="OTHER-99")
    assert r["status"] == "REFUSED_STRAIN_MISMATCH"
    assert r["isolation_source"] == ""  # never assigns on mismatch

def test_absence_preserved(monkeypatch):
    fix2 = FIX.replace('                     /isolation_source="an LDPE film in soil"\n', "")
    fix2 = fix2.replace('                     /country="South Korea: Jeonju"\n', "")
    monkeypatch.setattr(m, "efetch_source", lambda acc, **k: fix2)
    r = m.resolve("X", expected_strain="PE-7")
    assert r["isolation_source"] == "Not recorded"
    assert r["status"] == "STRAIN_CONFIRMED_NO_METADATA"

def test_deposit_city_heuristic():
    assert "SUSPECT_DEPOSIT" in m.deposit_city_flag("Germany: Braunschweig")
    assert m.deposit_city_flag("China: Yunnan") == ""

def test_no_strain_in_record_refuses_without_trust(monkeypatch):
    fix3 = FIX.replace('                     /strain="PE-7"\n', "")
    monkeypatch.setattr(m, "efetch_source", lambda acc, **k: fix3)
    r = m.resolve("X", expected_strain="PE-7")
    assert r["status"] == "REFUSED_NO_STRAIN_IN_RECORD"
    r2 = m.resolve("X", expected_strain="PE-7", trust_title=True)
    assert r2["status"] in ("STRAIN_CONFIRMED", "STRAIN_CONFIRMED_NO_METADATA")
