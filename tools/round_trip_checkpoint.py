#!/usr/bin/env python3
"""Read-only inbox visibility and byte-bound exchange reconciliation.

Does not verify science, update ledgers, accept findings, apply submissions or
discover a scheduler's allocated CPU budget. Outputs are observations only.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,importlib,io,json,os,re,shutil,sys
from collections import Counter,defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

ZONE=ZoneInfo('America/Los_Angeles')
STATES={'SUBMITTED','ACCEPTED','APPLIED','RETURNED','WITHDRAWN'}
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def rows(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f,delimiter='\t'))
def table_snapshot(path):
    p=Path(path).resolve();payload=p.read_bytes()
    data=list(csv.DictReader(io.StringIO(payload.decode('utf-8-sig'),newline=''),delimiter='\t'))
    return data,{'path':str(p),'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload)}
def bound(path):return {'path':str(Path(path).resolve()),'sha256':sha(path),'bytes':Path(path).stat().st_size}
def inbox(master,now,native_bundle=None):
    master=Path(master).resolve();folder=master/'00 Inbox';ledger=folder/'INBOX_LEDGER.tsv'
    result={'scope':'Read-only ledger and immediate folder snapshot; no content/scientific acceptance or mutation.',
       'observed_at':now.isoformat(),'timezone':str(ZONE),'master':str(master)}
    if not ledger.is_file():return {**result,'status':'LEDGER_UNAVAILABLE','open_count':None,'source':None}
    data,source=table_snapshot(ledger);result['source']=source;groups=defaultdict(list);issues=[];waiting=[]
    for r in data:
        sid=r.get('id','');groups[sid].append(r);status=r.get('status','')
        if not sid or Path(sid).name!=sid or sid in {'.','..'}:issues.append({'id':sid,'issue':'INVALID_SUBMISSION_ID'});continue
        if status not in STATES:issues.append({'id':sid,'issue':'UNKNOWN_STATE','state':status})
        if r.get('verifier') and r['verifier'].casefold()==r.get('submitter','').casefold():issues.append({'id':sid,'issue':'SELF_VERIFIED_ASSERTION'})
        if status not in {'SUBMITTED','ACCEPTED'}:continue
        stamp=r.get('verified') if status=='ACCEPTED' else r.get('submitted');age=None
        try:
            when=dt.datetime.strptime(stamp or '', '%Y-%m-%d %H:%M').replace(tzinfo=ZONE)
            age=(now-when).total_seconds()/3600
            if age<0:issues.append({'id':sid,'issue':'FUTURE_TIMESTAMP'});age=None
        except ValueError:issues.append({'id':sid,'issue':'AGE_UNAVAILABLE'})
        if not (folder/sid).is_dir():issues.append({'id':sid,'issue':'OPEN_FOLDER_MISSING'})
        waiting.append({'id':sid,'state':status,'age_hours':round(age,2) if age is not None else None,
            'age_time_basis':'submitted' if status=='SUBMITTED' else 'verified',
            'accepted_over_24h':status=='ACCEPTED' and age is not None and age>=24,
            'topic':r.get('topic',''),'next_action':'Independent verification required' if status=='SUBMITTED' else 'Await authorized apply; acceptance is a ledger assertion'})
    # A withdrawn historical row may coexist with one live row, per owner contract.
    duplicate_live=[sid for sid,rs in groups.items() if sum(r.get('status')!='WITHDRAWN' for r in rs)>1]
    ids=set(groups);orphans=sorted(p.name for p in folder.iterdir() if p.is_dir() and p.name not in ids|{'Done','Returned'} and not p.name.startswith('.'))
    result.update(status='SNAPSHOT_WITH_HOLDS' if issues or duplicate_live or orphans else 'SNAPSHOT',
        ledger_rows=len(data),state_counts=dict(Counter(r.get('status','') for r in data)),
        open_row_count=len(waiting),open_unique_id_count=len({r['id'] for r in waiting}),
        waiting=sorted(waiting,key=lambda r:-(r['age_hours'] if r['age_hours'] is not None else -1)),
        duplicate_live_ids=duplicate_live,unledgered_directories=orphans,issues=issues)
    if native_bundle:
        native=Path(native_bundle).resolve();owner=native/'mamey/strain_master.py'
        sys.path.insert(0,str(native))
        module=importlib.import_module('mamey.strain_master')
        if Path(module.__file__).resolve()!=owner:raise ValueError('Loaded unexpected native owner')
        result['native_owner']=bound(owner)
        result['native_inbox_bookkeeping_check']=module._check_inbox(str(master),now=now.replace(tzinfo=None))
    return result

def reconcile(sent_manifest,returned,root):
    sent,sent_source=table_snapshot(sent_manifest);back,return_source=table_snapshot(returned);base=Path(root).resolve();byid=defaultdict(list)
    if not sent:raise ValueError('EMPTY_SENT_MANIFEST')
    for r in sent:
        if not r.get('member') or not re.fullmatch('[0-9a-fA-F]{64}',r.get('sha256','')):raise ValueError('SENT_MANIFEST_PIN_REQUIRED')
        byid[r['member']].append(r)
    seen=Counter(r.get('item_id','') for r in back);out=[]
    for r in back:
        item=r.get('item_id','');checks=[];original=byid.get(item,[]);actual=None
        if len(original)!=1:checks.append('SENT_ID_MISSING_OR_AMBIGUOUS')
        elif (r.get('sent_sha256') or '').lower()!=original[0]['sha256'].lower():checks.append('BASELINE_MISMATCH')
        if seen[item]>1:checks.append('DUPLICATE_RETURN_ID')
        name=r.get('returned_path','');p=(base/name).resolve()
        if not name:checks.append('RETURN_PATH_UNAVAILABLE')
        elif not p.is_relative_to(base):checks.append('RETURN_PATH_ESCAPES_ROOT')
        elif not p.is_file():checks.append('RETURN_FILE_UNAVAILABLE')
        else:
            actual=sha(p)
            if (r.get('returned_sha256') or '').lower()!=actual:checks.append('RETURN_BYTES_MISMATCH')
        if r.get('decision','PENDING') not in {'PENDING','REVIEWED','HOLD','SUPERSEDED'}:checks.append('UNSUPPORTED_DECISION')
        out.append({**r,'actual_return_sha256':actual,'state':'HOLD' if checks else 'BYTE_BOUND_PENDING_REVIEW',
             'issues':checks,'acceptance':'NOT_ESTABLISHED'})
    return {'status':'NO_RETURNS_PENDING' if not out else 'HOLDS' if any(r['issues'] for r in out) else 'BYTE_BINDINGS_CHECKED',
       'sources':[sent_source,return_source],'returned_rows':len(out),
       'not_returned_ids':sorted(set(byid)-set(seen)),'rows':out,
       'limits':'A matching hash binds bytes only. REVIEWED is an external assertion, not acceptance. No ledger, source or result is edited.'}

def resources(path):
    usage=shutil.disk_usage(path)
    return {'disk_free_bytes':usage.free,'disk_floor_bytes':15000000000,'below_disk_floor':usage.free<15000000000,
       'logical_CPUs':os.cpu_count(),'allocated_core_budget':None,'CPU_queue':'UNAVAILABLE_WITHOUT_BOUND_SCHEDULER_RECEIPT',
       'limits':'Logical CPU count is not an allocation. No scheduler or runner is started/stopped.'}
def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    a=sub.add_parser('inbox');a.add_argument('--master',required=True);a.add_argument('--now');a.add_argument('--bundle-root');a.add_argument('--out',required=True)
    a=sub.add_parser('reconcile');a.add_argument('--sent-manifest',required=True);a.add_argument('--returned',required=True);a.add_argument('--root',required=True);a.add_argument('--out',required=True)
    a=ap.parse_args()
    if a.command=='inbox':
        now=dt.datetime.fromisoformat(a.now) if a.now else dt.datetime.now(ZONE)
        now=now.replace(tzinfo=ZONE) if now.tzinfo is None else now.astimezone(ZONE)
        result=inbox(a.master,now,a.bundle_root);result['resources']=resources(Path(a.out).resolve().parent)
    else:result=reconcile(a.sent_manifest,a.returned,a.root)
    requested=Path(a.out)
    if requested.is_symlink():
        sys.stderr.write('OUTPUT_SYMLINK_REFUSED: choose a new observation receipt path\n')
        raise SystemExit(2)
    out=requested.resolve()
    if resources(out.parent)['below_disk_floor']:raise SystemExit('DISK_FLOOR_HOLD: receipt not written; read stdout only')
    if out.exists():raise SystemExit('Refusing overwrite: choose an unused observation receipt path')
    # This command never writes beside input ledgers or returned evidence.
    inputs=[Path(a.master).resolve()] if a.command=='inbox' else [Path(a.root).resolve()]
    if any(out.is_relative_to(p) for p in inputs):raise SystemExit('Output must be outside inspected source root')
    try:
        with requested.open('x',encoding='utf-8') as receipt:receipt.write(json.dumps(result,indent=2)+'\n')
    except FileExistsError:
        sys.stderr.write('RECEIPT_COLLISION_REFUSED: existing evidence was preserved\n')
        raise SystemExit(2)
    print(json.dumps({k:v for k,v in result.items() if k not in {'waiting','rows','sources','issues'}},indent=2))
if __name__=='__main__':main()
