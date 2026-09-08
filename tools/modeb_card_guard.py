#!/usr/bin/env python3
"""Mode-B CARD GUARD — the check that would have caught 2026-08-17.

WHAT FAILED: 1,559 W4 cards hardcoded "Micromonospora, honeybee-associated (Apis
mellifera, Ontario)" into §1/§12 regardless of the real strain — moss/lichen/mushroom
strains all mislabeled honeybee, a Streptomyces called Micromonospora. No gate compared
a card's STATED strain identity to the strain's authoritative record.

THE AUTHORITATIVE SOURCE is each strain's own `strain_data/AS-XXX/STRAIN_CARD.md`
(rows: **Genus**, **Host / location**). Every Mode-B card MUST agree with it.

USAGE:
  modeb_card_guard.py <card.md> [<card.md> ...]      # validate specific cards
  modeb_card_guard.py --strain AS-XXX                 # validate all of a strain's cards
Exit 0 = all pass; exit 2 = at least one FAIL (identity mismatch or unresolved).

This is deliberately NARROW: it checks the one class of defect that is both catastrophic
(false scientific facts) and mechanically checkable (stated identity vs authoritative
identity). It does not grade prose. Pair with audit_cards_content.py for presentation.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os, re, sys, glob


def _default_asm():
    """Portable default (v9.7.370 fold fix — the portability guard caught the literal
    default at fold time, same class it caught in find_asset/register_compute_output):
    AS_STRAIN_MASTER env wins; else derive from the workspace-root contract; else fail
    visibly rather than silently scan a nonexistent personal path."""
    v = os.environ.get("AS_STRAIN_MASTER")
    if v:
        return v
    for env in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"):
        r = os.environ.get(env)
        if r:
            return os.path.join(r, "strain_data")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        from mamey.workspace_root import workspace_root as _wr
        return os.path.join(str(_wr()), "strain_data")
    except Exception:
        raise SystemExit(
            "modeb_card_guard: no strain-master root configured. Set AS_STRAIN_MASTER "
            "(or SAPOTE_WORKSPACE_ROOT/SAPOTE_ROOT), or run from a bundle where the "
            "mamey package is importable.")


ASM = _default_asm()
GENUS_ROW = re.compile(r"\*\*Genus\*\*\s*\|\s*\*?([A-Z][a-z]+)", re.I)
HOST_ROW  = re.compile(r"\*\*Host\s*/?\s*location\*\*\s*\|\s*([^\|\n]+)", re.I)
# ecology token families that must not be swapped for one another
ECO = {
    "bee": {"bee", "honeybee", "bumblebee", "bombus", "apis", "pollinator", "hymenoptera"},
    "wasp": {"wasp"},
    "moss": {"moss"},
    "liverwort": {"liverwort"},
    "lichen": {"lichen", "usnea"},
    "mushroom": {"mushroom", "fungus", "fungal"},
    "ant": {"ant", "attine", "fungus-growing"},
}


def eco_class(text):
    # v9.7.371 fix: was a bare substring test (`tok in t`) -- "ant" is a substring of "plant"
    # (a genuinely common actinomycete habitat descriptor: "plant rhizosphere isolate") and "bee"
    # is a substring of "beetle" (also a real habitat category). Reproduced live: a genuinely
    # plant-associated strain and a fabricated "attine ant"-associated claim both resolved to the
    # identical eco_class {"ant"}; a beetle-associated strain resolved to {"bee"}. Since check()'s
    # whole ECOLOGY check is `ceco & aeco` (non-empty intersection = PASS), this collision let a
    # real ecology-fabrication case (STRAIN_CARD says plant, fabricated card claims ant-associated)
    # silently pass the exact gate this tool exists to catch (per its own header comment, "the
    # check that would have caught" a prior real fabrication incident). Word-boundary matching
    # closes both collisions (and any other short-token/substring case in this table) at once.
    t = (text or "").lower()
    hits = {k for k, toks in ECO.items()
            if any(re.search(r"(?<![a-z])" + re.escape(tok) + r"(?![a-z])", t) for tok in toks)}
    return hits


def authoritative(strain):
    """(genus, host_text, host_eco_classes) from the strain's STRAIN_CARD.md."""
    p = os.path.join(ASM, strain, "STRAIN_CARD.md")
    if not os.path.exists(p):
        return None
    t = open(p, errors="replace").read()
    g = GENUS_ROW.search(t)
    h = HOST_ROW.search(t)
    genus = g.group(1) if g else None
    host = (h.group(1).strip() if h else "")
    return genus, host, eco_class(host)


def strain_of(path):
    m = re.search(r"(AS-\d+)", os.path.basename(path)) or re.search(r"/(AS-\d+)/", path)
    return m.group(1) if m else None


def card_identity(text):
    """(stated_genus, stated_eco_classes) as the CARD asserts them ABOUT THE STRAIN in §1/§12.

    BUGFIX 2026-08-18: the strain genus must come ONLY from a sentence that ASSERTS the strain's
    identity ("AS-XXX is a Streptomyces...", "sits in AS-XXX (Streptomyces ...)", "in Streptomyces
    sp. (bee-associated)"). The earlier version fell through to a bare genus-name regex, which
    matched a BLASTp SUBJECT organism from an inline gene table (e.g. "...[Actinomadura ...]") and
    reported it as the strain genus — a false FAIL on clean Codex cards. We NEVER scan gene-hit
    rows: identity patterns must bind AS-<id> or an explicit "<Genus> sp. (…-associated)" strain
    phrase. If no identity assertion is found, genus is None (WARN, not a wrong FAIL)."""
    GEN = (r"Streptomyces|Micromonospora|Pseudonocardia|Nocardia|Kribbella|Kitasatospora|"
           r"Amycolatopsis|Actinomadura|Saccharopolyspora|Saccharothrix|Peterkaempfera|"
           r"Streptosporangium|Actinophytocola|Verrucosispora|Nocardiopsis")
    gen = None
    # ONLY strain-identity assertions — each pattern anchors to AS-<id> or a "<Genus> sp. (…-assoc)"
    # strain phrase, so a bracketed BLASTp subject organism can never match.
    for pat in (rf"sits in AS-\d+ \(({GEN})\b",
                rf"lies on .*? in ({GEN}) sp\.",
                rf"\bAS-\d+ is an? ({GEN})\b",
                rf"\bAS-\d+ is a[n]? [a-z\- ]*?({GEN})\b",
                rf"\bin ({GEN}) sp\.? \([a-z\- ]*?associated",
                rf"\*\*Genus\*\*[^\n|]*\|\s*\*?({GEN})\b"):
        m = re.search(pat, text)
        if m:
            gen = m.group(1)
            break
    # ecology as the card states it ABOUT THE STRAIN (bound to AS-<id> or a strain phrase),
    # never a gene-hit organism's habitat.
    eco = set()
    # v9.7.395: {GEN} must be wrapped — as a bare interpolation the alternation bound at top
    # level, so ` sp\.? \(...-associated` attached ONLY to the last genus (Nocardiopsis) and the
    # eco capture group lived in that branch alone. For every other genus, a card stating its
    # ecology solely as "<Genus> sp. (bee-associated)" extracted NO ecology, ceco stayed empty,
    # and check() skipped the ecology comparison — a fabricated ecology passed the exact gate
    # this tool exists to enforce. (?:...) keeps the eco text as group(1).
    for pat in (r"AS-\d+ is ([a-z\- ]+?)-associated",
                rf"(?:{GEN}) sp\.? \(([a-z\- ]+?)[-\s]associated",
                r"\*\*Host\s*/?\s*location\*\*[^\n|]*\|\s*([^\|\n]+)"):
        for m in re.finditer(pat, text):
            eco |= eco_class(m.group(1))
    return gen, eco


def check(path):
    strain = strain_of(path)
    if not strain:
        return ("SKIP", path, "no strain id in path/name")
    auth = authoritative(strain)
    if not auth:
        return ("FAIL", path, f"{strain}: no STRAIN_CARD.md — cannot verify identity")
    agen, ahost, aeco = auth
    text = open(path, errors="replace").read()
    cgen, ceco = card_identity(text)
    problems = []
    if agen and cgen and cgen != agen:
        problems.append(f"GENUS: card says '{cgen}', STRAIN_CARD says '{agen}'")
    if aeco and ceco and not (ceco & aeco):
        problems.append(f"ECOLOGY: card says {sorted(ceco)}, STRAIN_CARD says {sorted(aeco)} ({ahost})")
    if problems:
        return ("FAIL", path, f"{strain}: " + " | ".join(problems))
    if not cgen:
        return ("WARN", path, f"{strain}: card states no genus (cannot confirm; expected {agen})")
    return ("PASS", path, f"{strain}: genus {cgen} ✓" + (f", eco {sorted(ceco)} ✓" if ceco else ""))


def main(argv):
    cards = []
    if argv and argv[0] == "--strain" and len(argv) > 1:
        s = argv[1]
        for base in (os.path.join(ASM, s, "**", "*ModeB*card*.md"),
                     os.path.join(ASM, s, "**", "*mode_b*card*.md"),
                     os.path.join(ASM, s, "**", "COMPLETE_SUCCESSOR_MODEB_CARD.md")):
            cards += glob.glob(base, recursive=True)
    else:
        cards = argv
    cards = sorted(set(cards))
    if not cards:
        emit("modeb_card_guard: no cards to check"); return 0
    fails = warns = 0
    for c in cards:
        status, path, msg = check(c)
        if status == "FAIL": fails += 1
        if status == "WARN": warns += 1
        if status != "PASS" or len(cards) <= 5:
            emit(f"[{status}] {msg}")
    emit(f"\n{len(cards)} cards | FAIL {fails} | WARN {warns} | PASS {len(cards)-fails-warns}")
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
