#!/usr/bin/env python3
"""Relabel GToTree tip names from genome FASTA headers to a consistent
'Genus species Strain' scheme, then render with render_clean_tree.py.
Usage: relabel_and_render.py <treefile> <genomes_dir> <out.png> "Title1||Title2" [outgroup_substr]
AS-#### tips and *_OUTGROUP role suffixes are preserved.  An explicit outgroup
substring must resolve to exactly one relabeled tip.  With no substring, exactly
one *_OUTGROUP role-suffix tip is required."""
import sys, os, re, glob, subprocess, json

# AS query strain, dash OR underscore, prefixed OR embedded (e.g. 'AS-NNN', 'AS_NNN',
# 'Streptomyces_sp_AS_NNN'). The lookbehind stops a false hit inside another token (e.g. 'GAS_12').
_AS_QUERY_RE = re.compile(r'(?<![A-Za-z0-9])AS[-_](\d+)')


def _canonical_as_query(name):
    """Return the canonical 'AS-<n>' for an AS query tip, else None.

    Genome tips arrive named two ways — 'AS-NNN.fna' (dash) and 'Streptomyces_sp_AS_NNN.fna'
    (underscore, embedded). The old check `re.match(r'AS-\\d+', lf)` only recognized the dash form at
    the START, so the embedded/underscore tips fell through to the genus parser, which dropped the
    numeric strain token and collapsed them to a bare 'Streptomyces sp AS' — losing the strain's
    identity. This recognizes the AS id anywhere and normalizes it, preserving a trailing _OUTGROUP
    role suffix."""
    m = _AS_QUERY_RE.search(name or "")
    if not m:
        return None
    canon = f"AS-{m.group(1)}"
    if str(name).upper().endswith("_OUTGROUP"):
        canon += "_OUTGROUP"
    return canon


if __name__ == "__main__":
    treefile, gdir, outpng, title = sys.argv[1:5]
    og_selector = sys.argv[5] if len(sys.argv) > 5 else None
    RENDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_clean_tree.py")
    PY = sys.executable

    # genera reclassified into Micromonospora (Nouioui et al. 2018) — NCBI labels lag
    GENUS_SYN = {"Verrucosispora": "Micromonospora"}
    # tokens that mark the start of contig/assembly metadata (cut here)
    CRUFT = re.compile(r'^(NODE|length|cov|contig\w*|scaffold\w*|ctg[-_.]?\w*|chromosome|complete|whole|genome|shotgun|sequence|assembly|MFI|C\d+\.ctg.*|PRJ[EDN][ABJ]\d+|GC[AF]_\d+|[0-9]{4,})', re.I)
    # culture-collection acronyms whose following number belongs to the strain name
    COLL = re.compile(r'^(ATCC|DSMZ?|NBRC|JCM|CGMCC|NRRL|NBC|KCTC|CECT|LMG|CIP|IFO|'
                      r'NCIMB|NCTC|KACC|BCRC|VKM|CBS|MTCC|NPDC|WAC|SID|CCTCC|CCUG|'
                      r'IAM|IMET|RIA|MUCL|PCC|CNT|CNX|CNY|KM)[-_.]?\d*$', re.I)

    def clean_from_header(h):
        h = re.sub(r'^\S+\s+', '', h).strip()                 # drop accession token
        h = re.split(r',\s*(complete|whole|chromosome|draft|scaffold)', h)[0]
        h = re.sub(r'\b(chromosome|complete genome|complete sequence|genome assembly|isolate)\b.*$', '', h, flags=re.I)
        h = h.replace(' strain ', ' ').strip().strip(',')
        parts = h.split()
        if len(parts) < 2:
            return re.sub(r'\s+', '_', re.sub(r'[^A-Za-z0-9._ -]', '_', h.strip()))
        genus = GENUS_SYN.get(parts[0], parts[0])
        sp = parts[1]
        # strain designator: split embedded underscores (NPDC052566_374_D5.ctg-0001),
        # drop leading strain/isolate words, stop at cruft/genus-repeat/trailing digits
        rest = ' '.join(parts[2:]).replace('_', ' ')
        rest = re.sub(r'\b(strain|isolate|str\.?)\b', ' ', rest, flags=re.I)
        strain, seen = [], set()
        CRUFT_SUB = re.compile(r'(ctg|contig|scaffold|node|assembly|BV-?BRC)', re.I)
        for tok in rest.split():
            # A number right after a culture-collection acronym is PART of the strain
            # designation, not contig cruft: "antibioticus DSM 40234" must not
            # truncate to "DSM", which made the two S. antibioticus deposits render
            # as two identical tips. Merge it back onto the acronym.
            if strain and tok.isdigit() and COLL.match(strain[-1]) and not re.search(r'\d', strain[-1]):
                strain[-1] += tok
                continue
            if CRUFT.match(tok) or CRUFT_SUB.search(tok):    # cruft token or embedded cruft
                break
            if tok.lower() in (genus.lower(), sp.lower(), 'sp.', 'sp'):
                break                                        # genus/species repeat
            if tok.lower() in seen:                          # any duplicate
                continue
            if strain and tok.isdigit():                     # trailing bare digit run
                break
            seen.add(tok.lower())
            strain.append(tok)
            if len(strain) >= 2:                             # at most 2 strain tokens
                break
        lab = f"{genus} {sp}" + (" " + " ".join(strain) if strain else "")
        lab = re.sub(r'[^A-Za-z0-9._ -]', '_', lab)
        return re.sub(r'\s+', '_', lab.strip())

    # map genome filename stem -> clean label
    stem2lab = {}
    for f in glob.glob(os.path.join(gdir, "*.fna")):
        stem = os.path.basename(f)[:-4]
        with open(f) as fh:
            hdr = fh.readline().lstrip('>').rstrip()
        stem2lab[stem] = clean_from_header(hdr)

    with open(treefile) as fh:
        nwk = fh.read()

    leaves = re.findall(r'[(,]([^(),:]+):', nwk)
    relabel = {}
    for lf in sorted(set(leaves)):        # sorted: set order is randomised per process
        canon = _canonical_as_query(lf)
        if canon is not None:
            if lf != canon:
                relabel[lf] = canon        # normalise embedded/underscore AS id -> canonical AS-<n>
            continue                       # query strain — never send to the genus parser (keeps its ID)
        is_og = 'OUTGROUP' in lf.upper()
        base = lf.replace('_OUTGROUP', '')
        lab = stem2lab.get(lf) or stem2lab.get(base) or base
        if is_og and not lab.endswith('_OUTGROUP'):
            lab = lab + '_OUTGROUP'
        relabel[lf] = lab

    # longest-first to avoid partial clobber
    for old in sorted(relabel, key=len, reverse=True):
        new = relabel[old]
        if old != new:
            nwk = re.sub(r'(?<=[(,])' + re.escape(old) + r'(?=:)', new, nwk)

    # Resolve before writing the relabeled tree or invoking the renderer.  Count tip
    # occurrences rather than unique labels: two tips relabeled to the same text are still
    # ambiguous and must not collapse into an apparently unique set member.
    relabeled_tips = re.findall(r'[(,]([^(),:]+):', nwk)

    def _refuse(code, mode, match_count):
        payload = {
            "code": code,
            "event": "OUTPUT_REFUSED",
            "match_count": match_count,
            "path_disclosure": "REDACTED",
            "selector_mode": mode,
            "stage": "OUTGROUP_SELECTION",
        }
        print(json.dumps(payload, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        raise SystemExit(2)

    if og_selector is not None:
        mode = "EXPLICIT_SUBSTRING"
        if not og_selector.strip():
            _refuse("OUTGROUP_SELECTOR_EMPTY", mode, 0)
        matches = [tip for tip in relabeled_tips
                   if og_selector.upper() in tip.upper()]
        if not matches:
            _refuse("OUTGROUP_SELECTOR_NO_MATCH", mode, 0)
        if len(matches) != 1:
            _refuse("OUTGROUP_SELECTOR_AMBIGUOUS", mode, len(matches))
    else:
        matches = [tip for tip in relabeled_tips if tip.upper().endswith("_OUTGROUP")]
        mode = "ROLE_SUFFIX_FALLBACK"
        if not matches:
            _refuse("OUTGROUP_ROLE_SUFFIX_NO_MATCH", mode, 0)
        if len(matches) != 1:
            _refuse("OUTGROUP_ROLE_SUFFIX_AMBIGUOUS", mode, len(matches))
    og = matches[0]

    rel_tf = treefile.replace('.treefile', '_relabeled.treefile')
    with open(rel_tf, 'w') as fh:
        fh.write(nwk)

    cmd = [PY, RENDER, rel_tf, outpng, title, og]
    print("outgroup:", og)
    print("relabeled", sum(1 for k, v in relabel.items() if k != v), "of", len(relabel), "reference tips")
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-300:], r.stderr[-300:] if r.returncode else '', sep="\n")
    sys.exit(r.returncode)
