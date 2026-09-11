"""Source-aware display labels; machine tip keys and trees are never changed.

Syntax checks reuse strain_identity for its declared namespaces, adding NR/XR
RefSeq transcript-shaped tokens. Candidates parsed from text are not accession
identity, record-existence evidence, or a sequence-to-record binding.
"""
from __future__ import annotations
import re
from .strain_identity import looks_like_accession

# Candidate discovery only. Full supported-token validation follows; no prefix salvage.
_CANDIDATE = re.compile(r"(?<![A-Za-z0-9.])(?:NZ_)?[A-Z]{1,6}_?\d+(?:[._]\d+)?(?![A-Za-z0-9.]|_\d)", re.I)
SUPPORTED_NAMESPACES = "strain_identity namespaces plus NR_/XR_ transcript-shaped tokens; syntax only"

def supported_syntax(value):
    if not isinstance(value,str) or not value or any(c.isspace() for c in value):return False
    # Structured input retains its exact spelling and dotted version. Underscore versions
    # may be normalized only by candidate discovery, where raw text is also retained.
    if re.search(r"\d_\d",value):return False
    return bool(looks_like_accession(value) or re.fullmatch(r"(?:NR|XR)_\d{6,}(?:\.\d+)?",value,re.I))

def accession_candidates(text):
    if not isinstance(text,str):raise ValueError("LABEL_TEXT_REQUIRED")
    found=[]
    for match in _CANDIDATE.finditer(text):
        raw=match.group();value=re.sub(r"(?<=\d)_(\d+)$",r".\1",raw)
        if supported_syntax(value):found.append(dict(raw=raw,candidate=value,span=list(match.span())))
    unique=sorted({x['candidate'] for x in found})
    return dict(state='AMBIGUOUS' if len(unique)>1 else 'HEURISTIC_CANDIDATE' if unique else 'NO_SUPPORTED_CANDIDATE',candidates=unique,occurrences=found,authority='UNBOUND',namespaces=SUPPORTED_NAMESPACES)

def _balanced(value):
    stack=[]
    for char in value:
        if char in '([{':stack.append(char)
        elif char in ')]}':
            if not stack or '([{'.index(stack.pop())!=')]}'.index(char):return False
    return not stack

def _text(value):
    if not isinstance(value,str) or any(ord(c)<32 for c in value):raise ValueError('INVALID_LABEL_TEXT')
    if not _balanced(value):raise ValueError('BRACKET_BALANCE_HOLD')
    return value

def _source(source):
    return isinstance(source,dict) and all(isinstance(source.get(k),str) and source[k].strip() for k in ('source_file','record_locator')) and bool(re.fullmatch('[0-9a-f]{64}',source.get('source_sha256','')))

def _shorten(text,room):
    if len(text)<=room:return text
    words=text.split()
    while words:
        candidate=' '.join(words)+'…'
        if len(candidate)<=room and _balanced(candidate):return candidate
        words.pop()
    return ''

def make_label(tip_key,raw_label,*,query=False,outgroup=False,fields=None,width=58):
    """Return label + holds + provenance. Protected fields overflow rather than truncate.

    `fields` is an optional source-record projection with `source`, `accession`,
    `species`, and `host`. Provenance presence is not independent verification.
    Unknown authority retains the entire raw label, with a visible UNBOUND marker.
    """
    if type(width) is not int or width<1:raise ValueError('WIDTH_POSITIVE_INTEGER_REQUIRED')
    tip_key=_text(tip_key);raw_label=_text(raw_label)
    if not tip_key:raise ValueError('TIP_KEY_REQUIRED')
    fields=fields or {};holds=[];candidate=accession_candidates(raw_label)
    source=fields.get('source');bound=_source(source)
    acc=fields.get('accession','')
    if acc and not supported_syntax(acc):raise ValueError('UNSUPPORTED_ACCESSION_TOKEN')
    if acc and not bound:holds.append('ACCESSION_AUTHORITY_UNBOUND')
    if candidate['state']=='AMBIGUOUS':holds.append('AMBIGUOUS_LABEL_CANDIDATES')
    # Without a source record, do not promote or discard a parsed token.
    if not bound:
        holds.append('SOURCE_FIELDS_UNBOUND')
        # v9.7.416 (Sextant): the unbound provenance is recorded in `holds` and the returned
        # `authority` field; do NOT stamp a visible '| UNBOUND' on every tree tip — it is clutter,
        # and the figure caption already carries the claim-safety statement. (Alex 2026-09-08.)
        label=('OUTGROUP ' if outgroup else '')+(tip_key+' | ' if query and tip_key!=raw_label else '')+raw_label
    else:
        for k in ('species','host'):_text(fields.get(k,''))
        protected=('OUTGROUP ' if outgroup else '')+(tip_key if query else '')
        tail=('('+acc+')') if acc else ''
        if not acc:holds.append('ACCESSION_FIELD_MISSING')
        else:holds.append('ACCESSION_TO_TIP_SEQUENCE_UNVERIFIED')
        if candidate['candidates'] and acc and any(x!=acc for x in candidate['candidates']):holds.append('LABEL_SOURCE_ACCESSION_CONFLICT')
        description=fields.get('species','')
        host=fields.get('host','')
        if host:description+=' ['+host+']'
        room=width-len(protected)-len(tail)-2
        short=_shorten(description.strip(),max(0,room))
        label=' '.join(x for x in (protected.strip(),short,tail) if x)
        if not label:label=tip_key;holds.append('DISPLAY_FIELDS_MISSING')
    if len(label)>width:holds.append('WIDTH_OVERFLOW_HOLD')
    assert _balanced(label)
    return dict(tip_key=tip_key,label=label,raw_label=raw_label,query=bool(query),outgroup=bool(outgroup),source_fields=fields,candidate_inspection=candidate,holds=holds,width=width,authority='SOURCE_FIELD_ONLY_NOT_SEQUENCE_IDENTITY' if bound else 'UNBOUND',tip_key_unchanged=True)

def unique_labels(records):
    """Preserve every tip; duplicate display strings receive an untruncated machine key."""
    if len({r['tip_key'] for r in records})!=len(records):raise ValueError('DUPLICATE_MACHINE_TIP_KEY')
    counts={}
    for r in records:counts[r['label']]=counts.get(r['label'],0)+1
    for r in records:
        if counts[r['label']]>1:
            r['label']+=' | tip='+r['tip_key'];r['holds'].append('DISPLAY_COLLISION_DISAMBIGUATED')
            if len(r['label'])>r['width'] and 'WIDTH_OVERFLOW_HOLD' not in r['holds']:r['holds'].append('WIDTH_OVERFLOW_HOLD')
    if len({r['label'] for r in records})!=len(records):raise ValueError('DISPLAY_COLLISION_HOLD')
    return {r['tip_key']:r for r in records}


_STOP = {"colony", "collected", "isolated", "fungal", "garden", "strain", "from", "in", "on"}
ABBREV = ("sp", "spp", "cf", "aff", "nr", "subsp", "var", "str", "gen")


def binomial(text):
    """`Genus species` (with `subsp.`/`var.` when present), dropping the nomenclatural authority.

    Replaces flat character cuts. `Nocardioides flavus (ex Ruan and Zhang 1979) Yoon et al. 2005`
    becomes `Nocardioides flavus`, not the 40-character fragment that reached a published figure.
    """
    t = re.sub(r"\s+", " ", (text or "").strip())
    t = re.sub(r"^(?:[A-Z]{2}_?\d+(?:[._]\d+)?)\s+", "", t)
    t = t.replace("_", " ")
    m = re.match(r"([A-Z][a-z]+)\s+(sp\.|spp\.|[a-z]+)(?:\s+(subsp\.|var\.)\s+([a-z]+))?", t)
    if not m:
        return ""
    out = f"{m.group(1)} {m.group(2)}"
    if m.group(3):
        out += f" {m.group(3)} {m.group(4)}"
    return out


def _word_shorten(text, width):
    """Shorten at a word boundary, marked with an ellipsis -- never a mid-word character cut.

    v9.7.414 addendum: the original fallback here was `text[:width]`, a flat slice -- exactly the
    defect class this whole function exists to eliminate, just reachable through a narrower gate
    (fires only when NO token survives the walk in `host_taxon`, e.g. a /host sentence that opens
    directly with collection detail rather than an organism name). Confirmed reachable: input
    `"colony sample from unlabeled site"` returned `"colony sample from unlabeled sit"` under the
    flat slice -- the exact mid-word severing pattern named in this card's own motivating incidents.
    """
    text = text.strip()
    if len(text) <= width:
        return text
    words, out = text.split(), ""
    for w in words:
        candidate = (out + " " + w).strip()
        if len(candidate) + 1 > width:          # +1 reserves room for the "…" marker
            break
        out = candidate
    return (out + "…") if out else ("…" if width > 0 else "")


def host_taxon(text, width=32):
    """The organism/substrate from a deposited /host sentence, without the collection detail.

    Walks TOKENS and stops at collection detail, a token containing a DIGIT (colony and accession
    codes always do; organism names never), or an opening quote. Splitting on punctuation instead
    produced `Atta sp` (period eaten by the split) and, when the period was protected,
    `Atta sp. CF180404-02 ''Joan Call` (colony code leaking in).
    """
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise ValueError("width must be a positive integer")
    out = []
    for tok in (text or "").strip().split():
        t = tok.rstrip(",")
        if t.lower().rstrip(".") in _STOP or re.search(r"\d", t) or t.startswith("'"):
            break
        out.append(t)
        if tok.endswith(","):
            break
    h = re.sub(r"\s+(?:and|or|from|in)$", "", " ".join(out).strip()).strip()
    if h.endswith(".") and h[:-1].split() and h[:-1].split()[-1].lower() not in ABBREV:
        h = h[:-1]
    h = h or (text or "").strip()
    h = _word_shorten(h, width)      # word-safe for BOTH the walked result and the raw-text fallback --
                                      # a verbose /host sentence can walk past `width` before any stop
                                      # token appears, so this is not fallback-only
    if h.count("(") > h.count(")"):                                   # never emit an unbalanced paren
        h = h[:h.rfind("(")].strip() if h.rfind("(") > 0 else h.replace("(", "")
    return h
