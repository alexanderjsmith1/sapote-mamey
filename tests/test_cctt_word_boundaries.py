"""Guard: CCTT short class-tokens must be word-bounded so they don't substring-match
amino-acid translation runs. Regression test for the LANM-in-translation false positive
(lichenysin / streptothricin spuriously firing T43-LAN)."""
import re
from mamey import source_scans as ss

# amino-acid run that contains LANM / LANC / HSAF / CRED / CREE as substrings
_TRANSLATION_DECOY = "MKQVAADKMIQVALANMYTELSNVHSAFCREDCREELANCGG"

def _lan_patterns():
    return ss.CCTT_PATTERNS["T43-LAN_lanthipeptide"]

def test_lan_does_not_fire_on_translation_substring():
    low = _TRANSLATION_DECOY.lower()
    assert not any(re.search(p, low) for p in _lan_patterns()), \
        "T43-LAN fired on an amino-acid translation substring (unbounded lanm/lanc?)"

def test_lan_still_fires_on_real_lanthipeptide_term():
    low = "lanthipeptide biosynthesis protein lanM".lower()
    assert any(re.search(p, low) for p in _lan_patterns()), \
        "T43-LAN failed to fire on a genuine lanthipeptide annotation"

def test_aa_spellable_cctt_tokens_are_bounded():
    # every short (<=4) purely-alpha token spellable in amino-acid letters must be \b-bounded
    AA = set("ACDEFGHIKLMNPQRSTVWY")
    for key, pats in ss.CCTT_PATTERNS.items():
        for p in pats:
            for tok in re.findall(r'(?<![\\\w])([a-z]{2,4})(?![\w])', p):
                if set(tok.upper()) <= AA and rf"\b{tok}\b" not in p and tok not in p.replace(tok, "", 1) + "x":
                    # token present unbounded and AA-spellable -> must be bounded
                    assert rf"\b{tok}\b" in p or f"|{tok}|" not in f"|{p}|", \
                        f"AA-spellable token '{tok}' in {key} is unbounded (substring-FP risk)"
