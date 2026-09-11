"""Figure-label compatibility API backed by the bundled source-aware parser.

Parsed tokens are syntax candidates only, never sequence identity or record verification.
"""
from pathlib import Path
import re
import sys
if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.tip_label import accession_candidates, binomial, host_taxon, _text, _word_shorten


def accession(text):
    """Return one supported syntax candidate; ambiguous strings are not guessed."""
    result = accession_candidates(text or "")
    return result["candidates"][0] if len(result["candidates"]) == 1 else ""


def species_from_tip(tip):
    """Strip the exact accession occurrence before interpreting an encoded organism label."""
    result = accession_candidates(tip)
    if result["state"] == "AMBIGUOUS":
        return "", ""
    acc = accession(tip)
    rest = tip
    if acc:
        occurrence = result["occurrences"][0]
        start, end = occurrence["span"]
        # Leading accessions precede an organism; trailing accessions follow it.
        rest = tip[end:] if not tip[:start].strip("_ -") else tip[:start]
    return binomial(rest.replace("_", " ").strip()), acc


def source_text(text, width=30):
    """Display shortening only; the raw deposited value remains in the metadata."""
    if type(width) is not int or width < 1:
        raise ValueError("width must be a positive integer")
    value = re.sub(r"\s+", " ", _text(text or "").strip())
    value = {"rhizosphere soil": "rhizosphere"}.get(value.lower(), value)
    return _word_shorten(value, width)


def _label(head, source, acc, marker, width):
    if type(width) is not int or width < 1:
        raise ValueError("width must be a positive integer")
    head, source, acc = (_text(x) for x in (head, source, acc))
    # Accession and source are protected complete fields. Overflow is preferable to silent loss.
    tail = " ".join(x for x in ("[" + source + "]" if source else "", marker, "(" + acc + ")" if acc else "") if x)
    room = width - len(tail) - 1
    short = _word_shorten(head, room) if room > 0 else head
    return " ".join(x for x in (short or head, tail) if x)


def ref_label(species, acc="", strain="", is_type=False, type_marker="paren", width=72, source=""):
    if type_marker not in ("paren", "none"):
        raise ValueError("type_marker must be paren or none")
    normalized = re.sub(r"\s+", " ", _text(source).strip())
    normalized = {"rhizosphere soil": "rhizosphere"}.get(normalized.lower(), normalized)
    return _label(" ".join(x for x in (species, strain) if x) or "unnamed", normalized, acc,
                  "(T)" if is_type and type_marker == "paren" else "", width)


def query_label(strain_id, host="", acc="", width=58):
    return _label(strain_id, _text(host) if host else "host not recorded", acc, "", width)


def outgroup_label(species, acc="", width=58):
    """Role belongs in metadata/caption; retain the normal organism label."""
    return _label(species or "unnamed", "", acc, "", width)
