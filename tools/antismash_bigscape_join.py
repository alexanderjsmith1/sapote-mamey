#!/usr/bin/env python3
"""antismash_bigscape_join.py -- reconcile antiSMASH per-BGC output with BiG-SCAPE GCF families.

antiSMASH and BiG-SCAPE both compare a BGC to MIBiG, by DIFFERENT methods:
  * antiSMASH KnownClusterBlast (KCB): gene-level BLAST of the BGC against MIBiG -> a % similarity hit.
  * BiG-SCAPE GCF: Pfam-domain-architecture clustering; a family that contains a MIBiG ref = KNOWN.
This tool joins them per BGC on the `node.region` locator and flags where they agree/disagree -- a
disagreement (antiSMASH finds a KCB hit but BiG-SCAPE calls the family novel, or vice-versa) is
exactly the BGC worth a human look.

It is deliberately DB-free and portable: it reads antiSMASH region GBKs (which you already have) plus
the small BiG-SCAPE derived TSV (cross_strain_GCFs.tsv or known_vs_novel with a members_locators
column) -- no 400 MB SQLite DB required. Optionally also reads antiSMASH `knownclusterblast/` text
files for the actual KCB MIBiG accessions + similarity.

Outputs one row per strain BGC: antiSMASH class + domain architecture, antiSMASH KCB top hit (if
given), BiG-SCAPE family + KNOWN/NOVEL + MIBiG anchors, and a reconciliation verdict.

Usage:
  python antismash_bigscape_join.py \
      --gbk-dir bigscape_input/ \
      --bigscape-tsv cross_strain_GCFs.tsv \
      [--kcb-dir antismash_out/*/knownclusterblast/] \
      --out antismash_bigscape_integrated.tsv

Stdlib only.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, re, glob, csv, collections, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bigscape_namespace import NamespaceError, load_membership_tsv, public_error

LOCATOR = re.compile(r'_(NODE_.+)\.(region\d+)\.gbk$', re.I)
ASDOM = re.compile(r'/aSDomain="([^"]+)"')
PRODUCT = re.compile(r'/product="([^"]+)"')


def parse_gbk(path):
    with open(path, encoding='utf-8', errors='ignore') as _f:
        txt = _f.read()
    doms = ASDOM.findall(txt)
    prods = list(dict.fromkeys(PRODUCT.findall(txt)))
    return prods, doms


def locator_of(fname):
    b = os.path.basename(fname)
    if b.upper().startswith('BGC'):
        return None, None
    m = LOCATOR.search(b)
    return b.split('_')[0], (f"{m.group(1)}.{m.group(2)}" if m else None)


def read_bigscape_tsv(path):
    """cross_strain_GCFs.tsv or known_vs_novel: needs a members_locators col (strain:loc;...) +
    family_id + a contains_MIBiG / status + optional mibig accessions. Returns {strain:loc -> ctx}."""
    out = {}
    with open(path, newline='') as fh:
        header = next(csv.reader(fh, delimiter='\t'), [])
    cols = {c.lower(): c for c in header}
    rows = load_membership_tsv(path, key_fields=('qualified_family_id',))
    if rows:
        def col(*n):
            for x in n:
                if x in cols:
                    return cols[x]
            return None
        cut = col('cutoff'); fam = col('family_id'); mem = col('members_locators')
        km = col('contains_mibig', 'status', 'n_mibig'); anc = col('mibig_matches', 'mibig')
        for row in rows:
            members = (row.get(mem) or '').split(';') if mem else []
            status_raw = (row.get(km) or '').strip() if km else ''
            known = status_raw.lower() in ('1', 'true', 'yes', 'known') or (status_raw.isdigit() and int(status_raw) > 0)
            anchors = (row.get(anc) or '').strip() if anc else ''
            for m in members:
                m = m.strip()
                if ':' in m:
                    prior = out.get(m)
                    if prior is not None and prior['qualified_family'] != row['qualified_family_id']:
                        raise NamespaceError('DUPLICATE_CONFLICT', 'one portable locator has conflicting family assignments')
                    out[m] = {'family': row.get(fam, '') if fam else '',
                              'qualified_family': row['qualified_family_id'],
                              'status': 'KNOWN' if known else 'NOVEL',
                              'anchors': anchors}
    return out


def read_kcb(kcb_dirs):
    """Parse antiSMASH knownclusterblast *.txt -> {(strain, locator) -> (mibig_acc, pct)}. Best-effort.

    Keyed by strain as well as region number. Every antiSMASH run restarts region numbering at
    region1, region2, ... -- so a region-number-only key silently collided across strains whenever
    --kcb-dir was given more than one directory, exactly the documented usage
    (`--kcb-dir antismash_out/*/knownclusterblast/`, one dir per strain): a later strain's regionN
    hit overwrote an earlier strain's, and every GBK sharing that region number then read back
    whichever strain's hit happened to be processed last. The antiSMASH convention this tool's own
    usage line assumes is `antismash_out/<strain>/knownclusterblast/`, so the strain id is the
    PARENT directory of the given kcb_dir.
    """
    out = {}
    for d in kcb_dirs:
        strain = os.path.basename(os.path.normpath(os.path.join(d, os.pardir)))
        for f in glob.glob(os.path.join(d, '*.txt')):
            base = os.path.basename(f)
            m = re.search(r'(region\d+)', base, re.I)
            if not m:
                continue
            with open(f, encoding='utf-8', errors='ignore') as _fh:
                txt = _fh.read()
            # first "Significant hits" line with a BGC accession
            hit = re.search(r'(BGC\d{7})', txt)
            pct = re.search(r'(\d+)\s*%', txt)
            if hit:
                out[(strain, m.group(1).lower())] = (hit.group(1), pct.group(1) + '%' if pct else '')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gbk-dir', required=True)
    ap.add_argument('--bigscape-tsv', required=True)
    ap.add_argument('--kcb-dir', nargs='*', default=[])
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    bs = read_bigscape_tsv(a.bigscape_tsv)
    kcb = read_kcb(a.kcb_dir) if a.kcb_dir else {}
    rows = []
    agree = disagree = only_as = only_bs = 0
    for f in glob.glob(os.path.join(a.gbk_dir, '*.gbk')):
        strain, loc = locator_of(f)
        if not strain or not loc:
            continue
        key = f"{strain}:{loc}"
        prods, doms = parse_gbk(f)
        dc = collections.Counter(doms)
        dstr = ', '.join(f"{d}\u00d7{c}" if c > 1 else d for d, c in dc.most_common(10))
        ctx = bs.get(key, {})
        region = loc.split('.')[-1].lower()
        kcbhit = kcb.get((strain, region))
        # reconcile: antiSMASH KCB hit vs BiG-SCAPE KNOWN
        as_known = bool(kcbhit)
        bs_known = ctx.get('status') == 'KNOWN'
        if kcbhit and ctx:
            if as_known == bs_known:
                verdict = 'agree'; agree += 1
            else:
                verdict = 'DISAGREE (inspect)'; disagree += 1
        elif kcbhit and not ctx:
            verdict = 'antiSMASH-only'; only_as += 1
        elif ctx:
            verdict = 'bigscape-only'; only_bs += 1
        else:
            verdict = 'no-call'
        rows.append([strain, loc, ';'.join(prods), dstr,
                     f"{kcbhit[0]} ({kcbhit[1]})" if kcbhit else '',
                     ctx.get('family', ''), ctx.get('qualified_family', ''),
                     ctx.get('status', ''), ctx.get('anchors', ''),
                     verdict])
    rows.sort(key=lambda r: (r[0], r[1]))
    with open(a.out, 'w', newline='') as fh:
        w = _SafeWriter(fh, delimiter='\t')
        w.writerow(['strain', 'locator', 'antismash_class', 'antismash_domains',
                    'antismash_KCB_MIBiG', 'bigscape_family', 'bigscape_qualified_family', 'bigscape_status',
                    'bigscape_MIBiG_anchors', 'reconciliation'])
        w.writerows(rows)
    emit(f"wrote {a.out}: {len(rows)} BGCs")
    if kcb:
        emit(f"reconciliation: {agree} agree, {disagree} DISAGREE, {only_as} antiSMASH-only, {only_bs} bigscape-only")
    else:
        emit("(no --kcb-dir: antiSMASH domains joined to BiG-SCAPE families; upload knownclusterblast/ for KCB reconciliation)")


if __name__ == '__main__':
    try:
        main()
    except NamespaceError as error:
        # v9.7.405: sys.stderr.write, not print() — a typed-refusal diagnostic, and the
        # print ratchet is at ceiling. Registering these front doors as EXCLUDED files
        # would have dropped their PRE-EXISTING prints from the count too: a lower
        # measure without paying anything.
        sys.stderr.write(public_error(error) + "\n")
        sys.exit(2)
