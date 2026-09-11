"""Candidate session extension of tool_database_reader; no new registry.

FrozenDatabaseSession admits one explicit manifest and retains one read-only
transaction. Public rows/iter_rows are bounded SELECT projections for existing
source adapters. inspect/hit_evidence reuse the existing BLAST owner unchanged.
Input bytes are checked at admission and close; stamps/sidecars before every
query. This detects ordinary drift, not hostile replacement-and-restoration.
"""
from __future__ import annotations
import json
import sqlite3
import time
from pathlib import Path
from . import tool_database_reader as owner

def decode_retained_json(blob,sha256=None):
    """Owner's bounded, hash-checked compressed JSON decoding for source adapters."""
    return owner._unpack(blob,sha256)

class FrozenDatabaseSession:
    def __init__(self,root,manifest,*,expected_manifest_sha256,expected_schema=owner.SCHEMA,adapter='manifest',dependencies=()):
        self.root=Path(root).resolve();self.manifest_locator=manifest
        self.expected_manifest_sha256=expected_manifest_sha256
        if expected_schema not in (owner.SCHEMA,'antismash_reference_comparisons_candidate/1'):raise ValueError('UNSUPPORTED_SESSION_SCHEMA')
        if adapter not in owner.ADAPTERS:raise ValueError('UNSUPPORTED_SESSION_ADAPTER')
        self.expected_schema=expected_schema;self.adapter=adapter;self.dependencies=tuple(dependencies);self._c=None;self._pins=[]

    def __enter__(self):
        if self._c is not None:raise ValueError('SESSION_ALREADY_OPEN')
        try:
            mp=owner._relative_file(self.root,self.root,self.manifest_locator)
            if owner._digest(mp)!=self.expected_manifest_sha256:raise ValueError('MANIFEST_HASH_MISMATCH')
            self.manifest=json.loads(mp.read_text(),object_pairs_hook=owner._unique_object)
            m=self.manifest
            if m.get('schema')!=self.expected_schema:raise ValueError('SESSION_SCHEMA_MISMATCH')
            dp=owner._relative_file(self.root,mp.parent,m['database']);owner._no_sidecars(dp)
            if type(m.get('bytes')) is not int or dp.stat().st_size!=m['bytes']:raise ValueError('DATABASE_SIZE_MISMATCH')
            if 'files' in m:
                matches=[f for f in m['files'] if f.get('path')==m['database']]
                if len(matches)!=1 or matches[0].get('sha256')!=m['database_sha256'] or matches[0].get('bytes')!=m['bytes']:raise ValueError('MANIFEST_DATABASE_ENTRY_CONFLICT')
            with dp.open('rb') as f:
                h=f.read(100)
                if h[:16]!=b'SQLite format 3\x00' or h[18:20]!=b'\x01\x01':raise ValueError('WAL_OR_NON_SQLITE_INPUT')
            self._pins=[(mp,self.expected_manifest_sha256,owner._stamp(mp)),(dp,m['database_sha256'],owner._stamp(dp))]
            for d in self.dependencies:
                root=Path(d['root']).resolve();p=owner._relative_file(root,root,d['path'])
                self._pins.append((p,d['sha256'],owner._stamp(p)))
            self._c=sqlite3.connect(dp.as_uri()+'?mode=ro',uri=True,timeout=1);self._c.row_factory=sqlite3.Row
            self._c.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,owner.PACK_LIMIT+65536)
            self._c.execute('PRAGMA query_only=ON');self._c.execute('PRAGMA trusted_schema=OFF');self._c.execute('BEGIN');self._c.execute('SELECT name FROM sqlite_master LIMIT 1').fetchall()
            self.check(hashes=True)
            self._deadline()
            if self._c.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('SQLITE_INTEGRITY_HOLD')
            if self._c.execute('PRAGMA foreign_key_check').fetchone() is not None:raise ValueError('SQLITE_FOREIGN_KEY_HOLD')
            if self.adapter!='manifest':owner._adapter_report(self._c,m,self.adapter,None,1,0)
            self.receipt={'file':str(dp),'sha256':m['database_sha256'],'bytes':m['bytes'],'manifest':str(mp),'manifest_sha256':self.expected_manifest_sha256,'status':m.get('status'),'source_verification':'Hash/size/quick-check/foreign-key verified frozen database; external original artifacts not reopened','dependencies':[{'path':str(p),'sha256':h} for p,h,_ in self._pins[2:]]}
            return self
        except Exception:
            if self._c is not None:self._c.close();self._c=None
            raise

    def _deadline(self):
        deadline=time.monotonic()+10
        self._c.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)

    def check(self,*,hashes=False):
        if self._c is None:raise ValueError('SESSION_NOT_OPEN')
        owner._no_sidecars(self._pins[1][0])
        for p,h,stamp in self._pins:
            if owner._stamp(p)!=stamp:raise ValueError('INPUT_CHANGED_DURING_SESSION')
            if hashes and owner._digest(p)!=h:raise ValueError('INPUT_HASH_MISMATCH')

    def rows(self,sql,parameters=(),*,limit=1000):
        """One SELECT, <=1000 rows and <=8 MiB materialized source values.

        SQL is authored by the calling adapter, never browser/user query text.
        Reject overflow rather than turn truncation into zero/missing evidence.
        """
        self.check()
        if type(limit) is not int or not 1<=limit<=1000:raise ValueError('ROW_BUDGET_HOLD')
        if not sql.lstrip().upper().startswith('SELECT ') or ';' in sql:raise ValueError('READ_ONLY_SELECT_REQUIRED')
        self._deadline()
        result=[];size=0
        for r in self._c.execute('SELECT * FROM ('+sql+') LIMIT ?',(*parameters,limit+1)):
            result.append(dict(r));size+=sum(len(v) if isinstance(v,(str,bytes)) else 16 for v in r)
            if len(result)>limit or size>owner.PACK_LIMIT:raise ValueError('RESULT_BUDGET_HOLD')
        self.check();return result

    def iter_rows(self,sql,parameters=(),*,max_rows=100000):
        """Deterministic caller-ordered partitions, fixed 500-row pages.

        Requires ORDER BY. A hard total ceiling stops accidental bulk reads.
        No source database is copied and no rows are silently discarded.
        """
        if 'ORDER BY' not in sql.upper() or type(max_rows) is not int or not 1<=max_rows<=100000:raise ValueError('ORDERED_PARTITION_BUDGET_REQUIRED')
        n=0
        while True:
            rows=self.rows(sql+' LIMIT ? OFFSET ?',(*parameters,500,n),limit=500)
            if n+len(rows)>max_rows:raise ValueError('TOTAL_ROW_BUDGET_HOLD')
            yield from rows;n+=len(rows)
            if len(rows)<500:return

    def inspect(self,identity,*,gene_order=None,view='genes',search_id=None,hit_rank=None,limit=1000,offset=0):
        self.check();self._deadline()
        if type(limit) is not int or not 1<=limit<=1000 or type(offset) is not int or offset<0:raise ValueError('QUERY_PAGE_HOLD')
        if view not in owner.BLASTP_VIEWS:raise ValueError('QUERY_VIEW_HOLD')
        if not isinstance(identity,(list,tuple)) or len(identity)!=4:raise ValueError('FULL_IDENTITY_REQUIRED')
        if view!='genes' and (type(gene_order) is not int or gene_order<0):raise ValueError('EXACT_GENE_REQUIRED')
        result=owner._adapter_report(self._c,self.manifest,self.adapter,identity,limit,offset,gene_order,view,search_id,hit_rank)
        if len(json.dumps(result,allow_nan=False).encode())>2*1024*1024:raise ValueError('RESULT_BUDGET_HOLD')
        self.check();return result

    def hit_evidence(self,identity,gene_order,search_id,*,limit=25,offset=0):
        """Raw hits including HSPs after full-locus/gene search-owner binding."""
        if self.adapter not in owner.BLASTP_ADAPTERS:raise ValueError('BLASTP_ADAPTER_REQUIRED')
        if type(search_id) is not int or search_id<1:raise ValueError('SEARCH_SELECTOR_HOLD')
        binding=self.inspect(identity,gene_order=gene_order,limit=1)
        if len(binding.get('records',[]))!=1:raise ValueError('EXACT_GENE_NOT_FOUND')
        if type(limit) is not int or not 1<=limit<=1000 or type(offset) is not int or offset<0:raise ValueError('QUERY_PAGE_HOLD')
        g=binding['records'][0]
        if g['availability_state']=='MISSING_OR_UNBOUND_PROTEIN_HOLD':raise ValueError('PROTEIN_BINDING_HOLD')
        raw,total=owner._blastp_hit_evidence(self._c,g['query_sha256'],self.adapter=='blastp-swissprot-v2',search_id,limit,offset)
        if len(json.dumps(raw,allow_nan=False).encode())>2*1024*1024:raise ValueError('RESULT_BUDGET_HOLD')
        self.check();return raw,total

    def close(self):
        if self._c is not None:
            try:self.check(hashes=True)
            finally:self._c.close();self._c=None

    def __exit__(self,*args):self.close()
