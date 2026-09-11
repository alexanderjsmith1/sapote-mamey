
"""phylo 16s panel. External inputs remain outside the software bundle."""
from contextlib import closing
import argparse
import os
import re
import shutil
# Use the bundle's spreadsheet-safe writers for all tabular exports.
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

import sqlite3
import sys
import tempfile

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging
_LOG = logging.getLogger(__name__)
import _phylo16s as _p16
from _tip_label import binomial, outgroup_label, query_label, ref_label


DB = _p16.rrna16s_db(os.environ.get("SAPOTE_16S_SQLITE"), must_exist=False)


def q(con, sql, args=()):
    return con.execute(sql, args).fetchall()


def pick_queries(con, args):
    """Queries: a named set, an explicit strain list, or a genus."""
    if args.strains:
        want = [s.strip() for s in args.strains.split(",") if s.strip()]
        marks = ",".join("?" * len(want))
        return q(con, f"SELECT r.acc_base, r.definition, r.seq, r.designation FROM record r "
                      f"WHERE r.source='as_governed' AND r.designation IN ({marks})", want)
    if args.set:
        return q(con, "SELECT r.acc_base, r.definition, r.seq, r.designation FROM record r "
                      "JOIN record_strain rs USING(acc_base) JOIN strain_set ss "
                      "ON ss.strain_uid = rs.strain_uid WHERE ss.set_name = ?",
                 (args.set,))
    if args.genus:
        return q(con, "SELECT acc_base, definition, seq, designation FROM record "
                      "WHERE source='as_governed' AND genus = ?", (args.genus,))
    sys.exit("one of --set / --strains / --genus is required")


def apply_query_identity_review(con, queries):
    """Exclude query records only through an explicit, auditable review rule.

    Rules can bind one deposited accession or a designation/genus pair.  The
    latter is deliberately narrower than a designation-only rename: a real
    strain with the same designation in another genus remains untouched.
    Stored records are preserved; this gate changes panel admission only.
    """
    present = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='query_identity_review'"
    ).fetchone()
    if not present:
        return queries
    columns = {row[1] for row in con.execute("PRAGMA table_info(query_identity_review)")}
    required = {
        "review_id", "match_accession", "match_designation", "match_genus",
        "reviewed_action", "reason_code",
    }
    if not required.issubset(columns):
        raise ValueError("QUERY_IDENTITY_REVIEW_SCHEMA_INVALID")
    rules = con.execute(
        "SELECT review_id,match_accession,match_designation,match_genus,"
        "reviewed_action,reason_code FROM query_identity_review ORDER BY review_id"
    ).fetchall()
    accepted = []
    for row in queries:
        acc, _definition, _seq, designation = row
        rec = _record(con, acc)
        genus = (rec.get("genus") or "").strip()
        matched = []
        for review_id, match_acc, match_designation, match_genus, action, reason in rules:
            accession_match = bool(match_acc) and acc == match_acc
            pair_match = (bool(match_designation) and bool(match_genus)
                          and designation == match_designation and genus == match_genus)
            if accession_match or pair_match:
                if action != "exclude_query":
                    raise ValueError(f"QUERY_IDENTITY_REVIEW_ACTION_INVALID: {review_id}")
                matched.append((review_id, reason))
        if matched:
            _LOG.warning(
                "QUERY_IDENTITY_REVIEW_EXCLUDED: accession=%s designation=%s genus=%s rules=%s",
                acc, designation, genus,
                ",".join(f"{review_id}:{reason}" for review_id, reason in matched),
            )
            continue
        accepted.append(row)
    return accepted


UNCULTURED_BY_DEFINITION = (
    "LOWER(definition) NOT LIKE 'uncultured%' "
    "AND LOWER(definition) NOT LIKE '%unidentified%' "
    "AND LOWER(definition) NOT LIKE '% clone %' "
    "AND LOWER(definition) NOT LIKE '% clone,%' "
    "AND LOWER(definition) NOT LIKE '%bacterium enrichment%'"
)
if UNCULTURED_BY_DEFINITION != _p16.UNCULTURED_DEFINITION_SQL:
    raise RuntimeError("16S reference-admission SQL drifted from tools/_phylo16s.py")


# v9.7.421 (SEXTANT_421b): a 16S reference panel must contain 16S genes. Measured on the store,
# 19 non-type candidates exceed 2,000 nt (one is a 9.4 Mb complete genome) and 16.6% fall under
# 1,200 nt. Type strains never exposed this because RefSeq 16S records are uniform in length.
REFERENCE_LEN_MIN = int(os.environ.get("PHYLO16S_REF_LEN_MIN", "1200"))
REFERENCE_LEN_MAX = int(os.environ.get("PHYLO16S_REF_LEN_MAX", "1700"))


NULLISH_METADATA = ("", "missing", "not applicable", "not determined", "unknown", "n/a", "na", "none",
                    "not collected", "not provided", "not available", "-")


def metadata_predicate(con):
    """SQL requiring a deposited isolation source or host, over whichever columns this store has.

    SEXTANT_421i (Alex's rule: "if you cannot find an isolation source, don't add it to the tree").
    Measured on the attines_rare panel 2026-09-09: 32 of 87 references carried no deposited habitat or
    country and rendered as blank strips. Schema-tolerant because the base `record` schema has neither
    column; stores gain them by extension. Refuses when the store cannot record metadata at all,
    rather than silently admitting everything.
    """
    cols = {r[1] for r in con.execute("PRAGMA table_info(record)")}
    have = [c for c in ("isolation_source", "host") if c in cols]
    if not have:
        raise ValueError("METADATA_UNRECORDABLE: --require-metadata was requested but this store "
                         "has neither isolation_source nor host on record")
    marks = ",".join("?" * len(NULLISH_METADATA))
    return (" AND (" + " OR ".join(f"LOWER(TRIM(COALESCE({c},''))) NOT IN ({marks})" for c in have) + ")",
            list(NULLISH_METADATA) * len(have))


def rank_references(con, queries, sources, exclude, scope_genus, habitat_tags=None, exclude_type=False,
                    require_type=False, require_metadata=False):
    """One blastn of the panel's queries against a temporary DB of every candidate reference."""
    if len({row[0] for row in queries}) != len(queries):
        raise ValueError('duplicate query record identity')
    for acc, _, seq, _ in queries:
        if not acc or re.search(r'\s|[>\x00-\x1f]',acc):
            raise ValueError('unsafe query record key')
        _p16.sequence(seq)
    marks = ",".join("?" * len(sources))


    sql = (f"SELECT acc_base, definition, seq, binomial, source FROM record "
           f"WHERE source IN ({marks}) AND seq IS NOT NULL AND uncultured = 0 "
           f"AND LENGTH(seq) BETWEEN {REFERENCE_LEN_MIN} AND {REFERENCE_LEN_MAX}"
           f" AND {UNCULTURED_BY_DEFINITION}")
    params = list(sources)
    # Exclude exact governed identities, never a naming pattern.
    sql += (" AND source != 'as_governed'"
           " AND NOT EXISTS (SELECT 1 FROM record AS governed WHERE governed.source = 'as_governed'"
           " AND (governed.acc_base = record.acc_base OR (NULLIF(record.designation, '') IS NOT NULL"
           " AND governed.designation = record.designation)))")
    has_type_review = bool(con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='record_type_review'"
    ).fetchone())
    if require_type and exclude_type:
        raise ValueError("REFERENCE_TYPE_FILTER_CONFLICT")
    # A reviewed role overrides the imported source flag without rewriting it. This matters for
    # source-wide RefSeq type-material imports that later prove to contain a non-type record.
    if has_type_review and require_type:
        sql += (" AND (EXISTS (SELECT 1 FROM record_type_review tr WHERE tr.acc_base=record.acc_base"
                " AND tr.reviewed_role='type_reference') OR (NOT EXISTS (SELECT 1 FROM record_type_review tr"
                " WHERE tr.acc_base=record.acc_base) AND is_type=1))")
    elif require_type:
        sql += " AND is_type=1"
    if has_type_review and exclude_type:
        sql += (" AND (EXISTS (SELECT 1 FROM record_type_review tr WHERE tr.acc_base=record.acc_base"
                " AND tr.reviewed_role='cultured_non_type_reference') OR (NOT EXISTS (SELECT 1 FROM record_type_review tr"
                " WHERE tr.acc_base=record.acc_base) AND (is_type IS NULL OR is_type != 1)))")
    elif exclude_type:
        # Unknown stays admissible as an unknown-status candidate; it is not relabeled as non-type.
        sql += " AND (is_type IS NULL OR is_type != 1)"
    meta_args = []
    if require_metadata:
        clause, meta_args = metadata_predicate(con)
        sql += clause
        params += meta_args
    if scope_genus:
        sql += " AND genus = ?"
        params.append(scope_genus)


    if habitat_tags:
        tmarks = ",".join("?" * len(habitat_tags))
        sql += (f" AND acc_base IN (SELECT acc_base FROM record_tag WHERE tag IN ({tmarks}))")
        params += list(habitat_tags)
    cands = {a: (d, s, b, src) for a, d, s, b, src in q(con, sql, tuple(params))
             if a not in exclude}
    for acc, (_, seq, _, _) in cands.items():
        _p16.accession(acc)
        _p16.sequence(seq)
    if not cands:
        return []


    tmp = _p16.space_free_workdir("phylo16s_panel_")
    try:
        ref_fa, qry_fa = f"{tmp}/ref.fa", f"{tmp}/qry.fa"
        with open(ref_fa, "w") as fh:
            for a, (d, s, b, src) in sorted(cands.items()):
                fh.write(f">{a}\n{s}\n")
        with open(qry_fa, "w") as fh:
            for a, d, s, desig in queries:
                fh.write(f">{a}\n{s}\n")


        _p16.run_checked([_p16.blast_bin("makeblastdb"), "-in", ref_fa, "-dbtype", "nucl",
                          "-out", f"{tmp}/refdb"], "makeblastdb (panel reference pool)")
        p = _p16.run_checked(
            [_p16.blast_bin("blastn"), "-task", "blastn", "-db", f"{tmp}/refdb",
             "-query", qry_fa, "-outfmt", "6 qseqid sseqid pident length",
             "-max_target_seqs", "2000", "-num_threads", "4", "-evalue", "1e-20"],
            "blastn (panel reference ranking)")
        best = {}
        for line in p.stdout.splitlines():
            f = line.split("\t")
            if len(f) != 4 or f[0] not in {row[0] for row in queries} or f[1] not in cands:
                raise ValueError("malformed or unbound BLAST ranking row")
            sid, pid, ln = f[1], float(f[2]), int(f[3])
            if not __import__('math').isfinite(pid) or not 0 <= pid <= 100 or ln <= 0:
                raise ValueError("invalid BLAST identity or alignment length")
            if ln < 500:
                continue
            if sid not in best or (pid, ln) > best[sid]:
                best[sid] = (pid, ln)


        uid_of, chosen_for_uid = {}, {}
        for acc in best:
            row = con.execute("SELECT strain_uid FROM record_strain WHERE acc_base=?", (acc,)).fetchone()
            uid_of[acc] = row[0] if row else acc
        for acc, (pid, ln) in sorted(best.items()):
            u = uid_of[acc]
            cur = chosen_for_uid.get(u)
            seqlen = len(cands[acc][1])
            if cur is None or seqlen > cur[1]:
                chosen_for_uid[u] = (acc, seqlen)

        out = []
        for acc, _ in sorted(chosen_for_uid.values(), key=lambda t: (-best[t[0]][0], -best[t[0]][1], t[0])):
            pid, ln = best[acc]
            d, sq, b, src = cands[acc]
            out.append((acc, d, sq, b, src, pid, ln))
        return out
    finally:
        shutil.rmtree(tmp)


def _one_value(con, uid, key):
    values = {str(row[0]).strip() for row in con.execute(
        "SELECT value FROM strain_meta WHERE strain_uid=? AND key=?", (uid, key)) if row[0] and str(row[0]).strip()}
    if len(values) > 1:
        raise ValueError(f"conflicting {key} metadata for {uid}")
    return next(iter(values), "")


def _record(con, acc):
    cols = [r[1] for r in con.execute("PRAGMA table_info(record)")]
    row = con.execute("SELECT * FROM record WHERE acc_base=?", (acc,)).fetchone()
    if row is None:
        raise ValueError(f"record absent: {acc}")
    return dict(zip(cols, row))


def _versioned(rec):
    if rec['acc_base'].startswith(('LOCAL:', 'AS_LOCAL_')):
        if rec.get('acc_version'):
            raise ValueError('local record key cannot be a deposited accession')
        return ''
    value = _p16.accession(rec.get('acc_version') or rec['acc_base'])
    if value.split('.')[0] != rec['acc_base']:
        raise ValueError('record accession/version conflict')
    return value


def _select_query_records(con, queries):
    """Choose one record per designation with governed source precedence before sequence length."""
    by_strain = {}
    sources = {}
    for row in queries:
        acc, _definition, seq, designation = row
        if not designation or not seq:
            raise ValueError('query has missing strain identity or sequence')
        if re.search(r'\s|[\x00-\x1f]', designation):
            raise ValueError('query tip key contains whitespace')
        source = (_record(con, acc).get('source') or '').strip()
        sources.setdefault(designation, set()).add(source)
        candidate_key = (source != 'as_governed', -len(seq), acc)
        current = by_strain.get(designation)
        if current is None or candidate_key < current[0]:
            by_strain[designation] = (candidate_key, row)
    for designation, seen in sorted(sources.items()):
        if len(seen) > 1:
            chosen = _record(con, by_strain[designation][1][0]).get('source') or ''
            _LOG.warning(
                "DESIGNATION_ORIGIN_COLLISION: %s occurs in sources %s; selected source=%s "
                "by governed-source precedence before length",
                designation, ",".join(sorted(seen)), chosen)
    return {designation: value[1] for designation, value in by_strain.items()}


# --- SEXTANT_421d: strand orientation of deposited reference sequences --------
# Deposited 16S records are not uniformly on the plus strand. A 2026-09-09 scan
# of the governed store (59,677 rows carrying sequence) found 95 stored
# reverse-complemented; every one sits in the non-type pool that SEXTANT_421
# makes reachable, and none is a RefSeq type record. That is why the defect is
# invisible until the non-type pool is opened.
#
# A reverse-complemented reference aligns to nothing, so the backbone gives it a
# terminal branch near 1.0 substitutions/site and tree_sanity_check refuses the
# figure with LONG_TERMINAL/DOMINATING_BRANCH. The gate is right, but it names a
# tip rather than the cause, and the operator has no way to reach the reason.
#
# Orientation is decided from two universal 16S landmarks, not by alignment, so
# the test is deterministic and needs neither BLAST nor the network. The stored
# record is never rewritten -- only the working panel copy is oriented -- and
# every panel record carries an explicit `orientation` value so the change is
# visible in the panel metadata and in the receipt.
# The 515F anchor is taken downstream of its degenerate position (GTGCCAGC*M*GCCGCGGTAA)
# and kept long. An 8-mer such as GCTGGCAC is NOT specific: measured 2026-09-09 it fires on
# the plus strand of 191 records -- 58 of them RefSeq type, e.g. Bacillus cereus NR_114582.1 --
# which would have raised ORIENTATION_AMBIGUOUS and aborted those panels.
ORIENTATION_PLUS_LANDMARKS = ('GCCGCGGTAA', 'GTACACACCGCCCGTCA')
ORIENTATION_MINUS_LANDMARKS = ('TTACCGCGGC', 'TGACGGGCGGTGTGTAC')
_ORIENTATION_COMPLEMENT = str.maketrans(
    'ACGTRYSWKMBDHVNacgtryswkmbdhvn',
    'TGCAYRSWMKVHDBNtgcayrswmkvhdbn')


def reverse_complement(seq):
    """Reverse-complement over the IUPAC alphabet the panel already accepts."""
    return (seq or '').translate(_ORIENTATION_COMPLEMENT)[::-1]


def orient_sequence(seq):
    """Return (sequence, orientation) with the panel copy on the plus strand.

    A record carrying both plus- and minus-strand landmarks is not an
    orientation question: it is a suspect record, and flipping it would be a
    guess. Refuse it by name instead.
    """
    upper = (seq or '').upper()
    plus = any(mark in upper for mark in ORIENTATION_PLUS_LANDMARKS)
    minus = any(mark in upper for mark in ORIENTATION_MINUS_LANDMARKS)
    if plus and minus:
        raise ValueError('ORIENTATION_AMBIGUOUS')
    if minus:
        return reverse_complement(seq), 'reverse_complemented'
    # No minus landmark: leave short fragments and divergent records untouched
    # rather than assert an orientation the sequence does not evidence.
    return seq, 'as_deposited'


def prepare_panel(con, a):
    import math
    queries = apply_query_identity_review(con, pick_queries(con, a))
    # A designation can also occur on an unrelated public record. Source precedence
    # is therefore decided before sequence length; length alone can select the wrong organism.
    by_strain = _select_query_records(con, queries)
    queries = [by_strain[k] for k in sorted(by_strain)]
    if not queries:
        raise ValueError('no sequence-bearing queries matched')
    if a.strains:
        wanted = {x.strip() for x in a.strains.split(',') if x.strip()}
        if wanted != set(by_strain):
            raise ValueError('explicit query strain list is incomplete')
    qaccs = {x[0] for x in queries}
    qids = {x[3] for x in queries}
    # Exclude all alternate accessions of the selected query strains, not just chosen records.
    for acc, designation in con.execute("SELECT acc_base,designation FROM record"):
        if designation in qids:
            qaccs.add(acc)
    # v9.7.421: 'nontype' named only the directed-fetch source, so a composition asking for
    # non-type references could not reach a store's harvested candidate pools at all. Those pools
    # were reachable only through 'all', which also pulls type strains, so there was no way to
    # request a non-type panel and get one. Widening the map is not by itself an admission rule:
    # 'nontype' also excludes recorded type material via rank_references(exclude_type=True).
    sources = {'type': ('refseq_type',),
               'nontype': ('nontype_fetch', 'pdf_candidate', 'attribute_candidate'),
               'external': ('external',),
               'all': ('refseq_type','nontype_fetch','pdf_candidate','attribute_candidate','external')}
    composition=[]
    for text in a.refs.split(','):
        kind, sep, value=text.strip().partition(':')
        if not sep or kind not in {*sources,'habitat'}:
            raise ValueError('reference composition requires known kind:Nx entries')
        mult=float(value.rstrip('xX'))
        if not math.isfinite(mult) or mult < 0:
            raise ValueError('reference multiplier must be finite and nonnegative')
        tags=[x.strip() for x in (a.habitat_tags or '').split(',') if x.strip()] if kind=='habitat' else None
        if kind=='habitat' and not tags:
            raise ValueError('habitat references require explicit habitat tags')
        composition.append((kind,int(mult*len(queries)),tags))
    records=[];counts=[];chosen_ids=set()
    for acc,definition,seq,designation in queries:
        rec=_record(con,acc)
        link=con.execute('SELECT strain_uid FROM record_strain WHERE acc_base=?',(acc,)).fetchone()
        uid=link[0] if link else ('AS:'+designation if rec['source']=='as_governed' else 'REC:'+acc)
        host=_one_value(con,uid,'host') or rec.get('host') or ''
        iso=_one_value(con,uid,'isolation_source') or rec.get('isolation_source') or ''
        country=rec.get('country') or ''
        version = _versioned(rec)
        genus = (rec.get('genus') or '').strip()
        if not re.fullmatch(r'[A-Z][a-z-]+', genus) or genus.endswith('aceae'):
            genus = ''
        label_head = f'{genus} sp. {designation}' if genus else designation
        label = query_label(label_head, host, version)
        if not version:
            label += ' (local 16S; no GenBank accession)'
        records.append(dict(tip=designation,label=label,kind='query',
                            category=iso,source=country,accession=_versioned(rec),host=host,isolation_source=iso,
                            seq=seq,pct_identity='',aligned_nt='',source_role=rec['source'],record_key=acc))
    for kind,wanted,tags in composition:
        selected=0
        if wanted:
            pool=rank_references(con,queries,sources['all' if kind=='habitat' else kind],qaccs,a.scope_genus,tags,
                                 exclude_type=(kind=='nontype'),
                                 require_type=(kind=='type'),
                                 **({'require_metadata': True} if getattr(a,'require_metadata',False) else {}))
            skipped_duplicate_strain=0
            for acc,definition,seq,binom,src,pid,ln in pool:
                link=con.execute('SELECT strain_uid FROM record_strain WHERE acc_base=?',(acc,)).fetchone()
                uid=link[0] if link else 'REC:'+acc
                if uid in chosen_ids:
                    skipped_duplicate_strain+=1
                    continue
                rec=_record(con,acc);host=rec.get('host') or _one_value(con,uid,'host')
                iso=rec.get('isolation_source') or _one_value(con,uid,'isolation_source')
                version=_versioned(rec)
                tip='REF_'+version
                records.append(dict(tip=tip,label=ref_label(binom or binomial(definition) or definition,
                    acc=version,strain=rec.get('designation') or '',is_type=bool(rec.get('is_type')),
                    source=iso or host),kind=kind,category=iso,source=rec.get('country') or '',
                    accession=version,host=host,isolation_source=iso,seq=seq,pct_identity=pid,
                    aligned_nt=ln,source_role=src,record_key=acc))
                chosen_ids.add(uid);selected+=1
                if selected==wanted:break
            # v9.7.421: report what was actually selected, after de-duplication -- not what was
            # predicted before the loop. A composition that silently returns far fewer references
            # than were ranked is otherwise indistinguishable from a genus that genuinely has few.
            sys.stderr.write(f"[phylo-16s-panel] refs '{kind}': ranked={len(pool)} requested={wanted} "
                             f"selected={selected} skipped_duplicate_strain={skipped_duplicate_strain}\n")
        counts.append(dict(kind=kind,requested=wanted,selected=selected))
    if a.outgroup:
        if '.' in a.outgroup:
            rows=con.execute('SELECT acc_base FROM record WHERE acc_version=?',(a.outgroup,)).fetchall()
        else:
            rows=con.execute('SELECT acc_base FROM record WHERE acc_base=?',(a.outgroup,)).fetchall()
        if len(rows)!=1:raise ValueError('outgroup accession must resolve to exactly one stored record/version')
        rec=_record(con,rows[0][0]);acc=_versioned(rec)
        if not rec.get('seq'):raise ValueError('outgroup sequence is missing')
        if any(x['accession']==acc for x in records):raise ValueError('outgroup is already selected as query or reference')
        records.append(dict(tip='OUTGROUP_'+acc,label=outgroup_label(rec.get('binomial') or binomial(rec['definition']),acc),
            kind='outgroup',category=rec.get('isolation_source') or '',source=rec.get('country') or '',accession=acc,
            host=rec.get('host') or '',isolation_source=rec.get('isolation_source') or '',seq=rec['seq'],
            pct_identity='',aligned_nt='',source_role=rec['source'],record_key=rec['acc_base']))
    keys=[x['tip'] for x in records]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate panel tip keys')
    for rec in records:
        rec['role'] = rec['kind'] if rec['kind'] in ('query', 'outgroup') else 'reference'
        stored = _record(con, rec['record_key'])
        rec['taxon'] = stored.get('binomial') or ''
        rec['taxon_source'] = 'record.binomial' if rec['taxon'] else ''
        target, evidence = _p16.explicit_type_strain_target(stored.get('definition') or '')
        rec['type_strain_of'] = target
        rec['type_evidence'] = evidence
        rec['seq']=_p16.sequence(rec['seq'])
        try:
            rec['seq'], rec['orientation'] = orient_sequence(rec['seq'])
        except ValueError:
            raise ValueError(
                'ORIENTATION_AMBIGUOUS: %s carries both plus- and minus-strand 16S '
                'landmarks; exclude it or resolve the deposit' % rec['accession'])
        if not rec['seq'] or re.search(r'[^ACGTRYSWKMBDHVNacgtryswkmbdhvn]',rec['seq']):
            raise ValueError('panel sequence contains unsupported symbols')
    flipped=[x['accession'] for x in records if x.get('orientation')=='reverse_complemented']
    if flipped:
        _LOG.warning(
            'ORIENTATION_NORMALISED: %d of %d panel records were stored '
            'reverse-complemented and were oriented to the plus strand for this '
            'panel only (stored records unchanged): %s',
            len(flipped), len(records), ', '.join(sorted(flipped)))
    return records,counts


def main():
    import csv, hashlib, io, json
    from pathlib import Path
    ap=argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--name',required=True)
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--set');group.add_argument('--strains');group.add_argument('--genus')
    ap.add_argument('--scope-genus');ap.add_argument('--habitat-tags')
    ap.add_argument('--refs',default='type:1x');ap.add_argument('--outgroup')
    ap.add_argument('--db',default='');ap.add_argument('--outdir',required=True)
    ap.add_argument('--require-metadata',action='store_true',help='admit only references whose deposit records an isolation source or host')
    ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',a.name):ap.error('name must be a simple filename component')
    root=Path(a.outdir);paths=[root/(a.name+x) for x in ['.fasta','_meta.tsv','_panel_receipt.json']]
    if any(x.exists() for x in paths):ap.error('output already exists; choose a new panel name')
    db=Path(_p16.rrna16s_db(a.db or None)).resolve()
    database_sha256=_p16.sha256_file(db)
    with closing(_p16.read_database(str(db))) as con:
        con.execute('BEGIN')
        if a.dry_run:
            reviewed = apply_query_identity_review(con, pick_queries(con, a))
            _LOG.info(f'DRY_RUN: {len(reviewed)} admitted query records after identity review; ranking NOT_MEASURED; no outputs')
            return 0
        records,counts=prepare_panel(con,a)
    fasta=''.join('>'+x['tip']+'\n'+x['seq']+'\n' for x in records)
    fields=['tip','label','role','taxon','taxon_source','type_strain_of','type_evidence','category','source','kind','record_key','accession','host','isolation_source','pct_identity','aligned_nt','source_role','orientation']
    buf=io.StringIO();writer=_SafeDictWriter(buf,fieldnames=fields,delimiter='\t',extrasaction='ignore');writer.writeheader();writer.writerows(records)
    selected=[dict(**{k:v for k,v in x.items() if k!='seq'},sequence_sha256=hashlib.sha256(x['seq'].upper().encode()).hexdigest()) for x in records]
    if _p16.sha256_file(db)!=database_sha256:raise ValueError('input database changed during panel selection')
    receipt=dict(status='PANEL_SELECTED_NOT_TREE_VALIDATED',database_sha256=database_sha256,database=db.name,composition=counts,records=selected,
                 fasta_sha256=hashlib.sha256(fasta.encode()).hexdigest(),metadata_sha256=hashlib.sha256(buf.getvalue().encode()).hexdigest())
    root.mkdir(parents=True,exist_ok=True)
    # Each destination is exclusive; receipt is the completion marker and is written last.
    for dest,text in zip(paths,[fasta,buf.getvalue(),json.dumps(receipt,indent=2)+'\n']):
        with dest.open('x') as handle:handle.write(text)
    _LOG.info(f'Panel written: {len(records)} tips; receipt {paths[-1]}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    sys.exit(main())
