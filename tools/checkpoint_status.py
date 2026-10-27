#!/usr/bin/env python3
"""Read-only Checkpoint facts; preserve pending states and the ongoing goal.

Input is an explicit pinned roster. It does not scan or modify sources, ingest
Inbox items, manage goals, update memories, dispatch runners or accept science.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,math,os,re,shutil,socket
from pathlib import Path

SCHEMA='sapote.checkpoint.v1'
KINDS={'goal','inbox','allocation','deliverable','patch','receipt','ledger','memory'}
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def parse_time(value):
    try:
        t=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return t if t.tzinfo is not None else None
    except (ValueError,TypeError):return None
def age_state(value,now,max_age):
    if type(max_age) not in (int,float) or max_age<0 or (type(max_age) is float and not math.isfinite(max_age)):
        raise ValueError('FINITE_NONNEGATIVE_AGE_BOUND_REQUIRED')
    stamp=parse_time(value)
    if stamp is None:return 'TIME_UNAVAILABLE'
    age=(now-stamp).total_seconds()/60
    return 'FUTURE_TIME_HOLD' if age<0 else 'STALE' if age>max_age else 'WITHIN_DECLARED_AGE'
def load_source(item,base,max_bytes):
    p=Path(item['path']);p=p if p.is_absolute() else Path(base)/p
    row={'id':item['id'],'kind':item['kind'],'path':str(p.resolve()),'sha256':None,'byte_state':'UNVERIFIED'}
    row['declared_surface']=item.get('surface','UNSPECIFIED')
    if not p.is_file():row['byte_state']='MISSING';return row,None
    if p.stat().st_size>max_bytes:row['byte_state']='UNVERIFIED_BYTE_BUDGET';return row,None
    with p.open('rb') as f:raw=f.read(max_bytes+1)
    if len(raw)>max_bytes:row['byte_state']='UNVERIFIED_BYTE_BUDGET';return row,None
    row['sha256']=hashlib.sha256(raw).hexdigest()
    if not re.fullmatch('[a-fA-F0-9]{64}',item.get('sha256','')):row['byte_state']='BASELINE_UNPINNED';return row,None
    if row['sha256']!=item['sha256'].lower():row['byte_state']='CHANGED';return row,None
    row['byte_state']='HASH_MATCH'
    if item['kind'] in {'deliverable','patch','ledger','memory'}:return row,None
    try:
        obj=json.loads(raw)
        if not isinstance(obj,dict):raise ValueError('JSON object required')
        return row,obj
    except (ValueError,UnicodeError):row['byte_state']='INVALID_JSON';return row,None
def build(manifest,base,now,resource_root):
    if manifest.get('schema')!=SCHEMA:raise ValueError('SCHEMA_HOLD')
    if now.tzinfo is None:raise ValueError('OFFSET_AWARE_CLOCK_REQUIRED')
    cap=manifest.get('max_source_bytes',20000000)
    if type(cap) is not int or cap<1:raise ValueError('POSITIVE_BYTE_BUDGET_REQUIRED')
    items=manifest.get('sources');ids=set();kinds={};facts=[];payload={};actions=[]
    if not isinstance(items,list) or not items:raise ValueError('EXPLICIT_SOURCE_ROSTER_REQUIRED')
    for item in items:
        if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id'].strip() or item['id'] in ids:raise ValueError('SOURCE_ID_HOLD')
        if item.get('kind') not in KINDS or not isinstance(item.get('path'),str) or not item['path'].strip():raise ValueError('SOURCE_KIND_OR_PATH_HOLD')
        ids.add(item['id']);kinds[item['id']]=item['kind']
        row,obj=load_source(item,base,manifest.get('max_source_bytes',20000000));facts.append(row);payload[item['id']]=obj
        if row['byte_state']!='HASH_MATCH':actions.append({'source':row['id'],'action':'Resolve '+row['byte_state']+' before using this source as current evidence.'})
    def one(kind):
        keys=[k for k,v in kinds.items() if v==kind]
        if len(keys)>1:raise ValueError('AMBIGUOUS_SINGLETON:'+kind)
        return payload[keys[0]] if keys else None
    g=one('goal');goal={'reported_status':g.get('status','UNAVAILABLE') if g else 'UNAVAILABLE',
       'objective':g.get('objective') if g else None,'lifecycle':'Ongoing goal; milestone completion does not complete the overall goal.',
       'authority':'Read-only supplied policy assertion; this tool does not call a goal management API.'}
    inbox=one('inbox');inbox_fact={'state':'UNAVAILABLE','current_open_count':None}
    if inbox:
        source=inbox.get('source') or {};p=Path(source.get('path',''));timing=age_state(inbox.get('observed_at'),now,manifest.get('max_inbox_age_minutes',45))
        if not source.get('path') or not p.is_absolute() or not p.is_file():binding='LIVE_LEDGER_UNAVAILABLE'
        elif not re.fullmatch('[a-fA-F0-9]{64}',source.get('sha256','')):binding='LIVE_LEDGER_UNPINNED'
        elif p.stat().st_size>manifest.get('max_source_bytes',20000000):binding='LIVE_LEDGER_UNVERIFIED_BUDGET'
        else:binding='LIVE_LEDGER_MATCH' if digest(p)==source['sha256'].lower() else 'LIVE_LEDGER_CHANGED'
        count=inbox.get('open_unique_id_count');valid_count=type(count) is int and count>=0
        current=binding=='LIVE_LEDGER_MATCH' and timing=='WITHIN_DECLARED_AGE' and valid_count
        inbox_fact={'state':'CURRENT_SNAPSHOT' if current else 'REFRESH_REQUIRED','ledger_binding':binding,'age_state':timing,
           'reported_open_count':count,'current_open_count':count if current else None,
           'count_state':'VALID_REPORTED_COUNT' if valid_count else 'INVALID_OR_MISSING_REPORTED_COUNT',
           'reported_unledgered_directories':inbox.get('unledgered_directories',[]),
           'native_check':inbox.get('native_inbox_bookkeeping_check'),'scope':'Inbox bookkeeping only, not full master or scientific acceptance.'}
        if not current:actions.append({'source':'inbox','action':'Refresh the read-only Inbox receipt; do not present stale counts as current.'})
        if current and inbox_fact['current_open_count']:actions.append({'source':'inbox','action':'Route pending submissions for independent native verification; do not auto-apply.'})
        if inbox_fact['reported_unledgered_directories']:actions.append({'source':'inbox','action':'Review unledgered directory ownership and content before any ledger repair.'})
    usage=shutil.disk_usage(resource_root);allocation=one('allocation');resource={'disk_free_bytes':usage.free,'disk_floor_bytes':15000000000,
       'disk_state':'BELOW_FLOOR' if usage.free<15000000000 else 'ABOVE_FLOOR','logical_CPUs':os.cpu_count(),
       'host_id':socket.gethostname(),'allocated_cores':None,'queue':'UNAVAILABLE','allocation_state':'NO_BOUND_ALLOCATION_RECEIPT'}
    if allocation:
        state=age_state(allocation.get('observed_at'),now,manifest.get('max_allocation_age_minutes',15))
        cores=allocation.get('allocated_cores')
        if allocation.get('schema')!='sapote.scheduler-allocation.v1':state='ALLOCATION_SCHEMA_HOLD'
        elif allocation.get('host_id')!=resource['host_id']:state='DIFFERENT_HOST'
        elif isinstance(cores,bool) or not isinstance(cores,(int,float)) or not math.isfinite(cores) or cores<=0:state='INVALID_ALLOCATION'
        resource['allocation_state']=state
        if state=='WITHIN_DECLARED_AGE':resource['allocated_cores']=cores;resource['queue']=allocation.get('queue','UNAVAILABLE')
    if resource['disk_state']=='BELOW_FLOOR':actions.append({'source':'disk','action':'Hold new output writes and compute; report the measured resource condition.'})
    receipts=[]
    for key,kind in kinds.items():
        if kind=='receipt' and payload[key] is not None:
            obj=payload[key];receipt={'source':key,'reported_status':obj.get('status',obj.get('result','NOT_REPORTED')),
               'scope':'Bound receipt bytes only; check target identity and producer scope before deriving deliverable readiness.',
               'scientific_acceptance':'NOT_ESTABLISHED','release':'NOT_AUTHORIZED','reported_checks':[],
               'target_state':'NO_ADMITTED_TARGET_BINDING'}
            if obj.get('schema')=='sapote.delivery_capability_card.result.v1':
                artifact=obj.get('artifact') or {};target=artifact.get('actual_sha256','');target_path=artifact.get('path','')
                receipt['reported_checks']=[{'kind':r.get('kind','UNSPECIFIED'),'state':r.get('state','UNSPECIFIED')} for r in obj.get('checks',[]) if isinstance(r,dict)]
                listed=[r for r in facts if target_path and r['path']==str(Path(target_path).resolve()) and r['kind']=='deliverable']
                receipt['target_state']='TARGET_NOT_LISTED' if not listed else 'TARGET_CHANGED_OR_UNVERIFIED'
                if re.fullmatch('[a-fA-F0-9]{64}',target) and any(r['byte_state']=='HASH_MATCH' and r['sha256']==target.lower() for r in listed):receipt['target_state']='TARGET_BYTES_RECHECKED'
            receipts.append(receipt)
    return {'schema':SCHEMA,'status':'CHECKPOINT_FACTS_WITH_EXPLICIT_HOLDS','observed_at':now.isoformat(),'goal':goal,
       'sources':facts,'QC_receipts':receipts,'inbox':inbox_fact,'resources':resource,
       'deliverables':[r for r in facts if r['kind']=='deliverable'],'patch_candidates':[r for r in facts if r['kind']=='patch'],
       'ledger_review':'Native owner routes required; checkpoint does not mutate ledgers.',
       'memory_review':'No update performed. Memory additions/corrections require the user-authorized route.',
       'next_actions':actions,'limits':'No runtime process/scheduler inspection, scientific admission, source mutation, generated bootstrap rewrite or overall-goal completion.'}
def markdown(r):
    def cell(value):return str(value).replace('|','\\|').replace('\n',' ').replace('\r',' ')
    resource=r['resources'];inbox=r['inbox'];cores=resource['allocated_cores']
    lines=['# Checkpoint', '', 'Observed: '+r['observed_at'], '', 'Overall goal reported by the supplied snapshot: **'+cell(r['goal']['reported_status'])+'**. Completed milestones do not end it.','',
      '## Resources','',
      '- Free disk: '+format(resource['disk_free_bytes']/1e9,'.2f')+' GB; floor '+format(resource['disk_floor_bytes']/1e9,'.0f')+' GB ('+cell(resource['disk_state'])+').',
      '- Logical CPUs: '+cell(resource['logical_CPUs'])+'. Allocated cores: '+('unknown' if cores is None else cell(cores))+'.',
      '- Queue: '+('unknown' if resource['queue']=='UNAVAILABLE' else cell(resource['queue']))+'. Allocation receipt: '+cell(resource['allocation_state'])+'.','',
      '## Inbox','']
    if inbox.get('current_open_count') is not None:lines.append('- Pending unique submissions reported by the current byte-bound receipt: **'+cell(inbox['current_open_count'])+'**.')
    else:lines.append('- Current pending count: **unknown**. Snapshot state: '+cell(inbox['state'])+'. Reported historical count: '+cell(inbox.get('reported_open_count','unavailable'))+'.')
    for name in inbox.get('reported_unledgered_directories',[]):lines.append('- Reported unledgered directory: '+cell(name)+'.')
    if inbox.get('native_check'):lines.append('- Native Inbox bookkeeping: '+cell(inbox['native_check'].get('status','UNAVAILABLE'))+'; this is not a full master audit.')
    lines+=['','## Deliverables and patches','','| Item | Surface declared by manifest | Byte check |','|---|---|---|']
    for row in r['deliverables']+r['patch_candidates']:lines.append('| '+cell(row['id'])+' | '+cell(row['declared_surface'])+' | '+cell(row['byte_state'])+' |')
    lines+=['','Byte agreement does not establish readiness, scientific acceptance or adoption.','', '## QC receipts','']
    for row in r['QC_receipts']:
        lines.append('- '+cell(row['source'])+': '+cell(row['reported_status'])+'; target '+cell(row['target_state'])+'.')
        for check in row['reported_checks']:lines.append('  - '+cell(check['kind'])+': '+cell(check['state'])+' (reported by the pinned card).')
    if not r['QC_receipts']:lines.append('No pinned QC receipt is available.')
    lines+=['','## Next actions','']
    for row in r['next_actions']:lines.append('- '+row['action'])
    lines+=['','## Ledger and memory review','',r['ledger_review'],r['memory_review'],'',r['limits'],'']
    return '\n'.join(lines)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--now');a=p.parse_args()
    if a.out.exists():p.error('fresh output folder required')
    if not a.out.parent.is_dir():p.error('output parent must already exist')
    if a.out.resolve().is_relative_to(Path(__file__).resolve().parents[1]):p.error('output must remain outside the tool source tree')
    raw=a.manifest.read_bytes();manifest=json.loads(raw)
    now=dt.datetime.fromisoformat(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    r=build(manifest,a.manifest.resolve().parent,now,a.out.parent);r['manifest_sha256']=hashlib.sha256(raw).hexdigest()
    r['producer']={'path':str(Path(__file__).resolve()),'sha256':digest(Path(__file__)),'scope':'Read-only presenter code bytes; not proof of external execution or acceptance.'}
    if r['resources']['disk_state']=='BELOW_FLOOR':print(json.dumps(r,indent=2));raise SystemExit(2)
    a.out.mkdir();(a.out/'CHECKPOINT.json').write_text(json.dumps(r,indent=2)+'\n');(a.out/'CHECKPOINT.md').write_text(markdown(r));print(json.dumps({'status':r['status'],'goal':r['goal']['reported_status'],'inbox':r['inbox'],'resources':r['resources']},indent=2))
if __name__=='__main__':main()
