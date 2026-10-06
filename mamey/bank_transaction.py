"""Cooperating-process bank locks, durable journal publication and explicit recovery.

Root stores remain compatible. A pending journal makes readers refuse the bank.
The last coherent before image and each after image remain in versioned recovery
folders. No atomic multi-file or hostile-concurrent-writer claim is made.
"""
from __future__ import annotations
import atexit
import contextlib
import csv
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

STORES = ('bgc_data.json','gene_data.json','rggmci_full.json','tigrfam.json','tfbs_coupling.json','resistance_coupling.json','strains.json','modeb_verdicts.csv','SCHEMA_VERSION')
PENDING='.ingest_pending.json'
STATE='.ingest_state.json'

class BankError(RuntimeError):
    pass

def _hash(data):return hashlib.sha256(data).hexdigest()

def _sync_dir(path):
    if os.name=='nt':return  # Windows file flushes used; directory fsync unavailable.
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def _regular(path):
    path=Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise BankError('BANK_DESTINATION_NOT_REGULAR: '+str(path))

def _write(path,data):
    path=Path(path);_regular(path)
    fd, temp=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        os.replace(temp,path);_sync_dir(path.parent)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def _json(path,obj):_write(path,(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode())

def _empty_bundle_source(bank):
    """Recognize an empty Sapote source checkout, never an existing cohort bank.

    Stable owned source markers plus no cohort-store/journal state distinguish
    read-only default inspection. Cooperating writers refuse this empty source
    destination, so bypassing lock creation cannot race a first bank generation.
    Marker-bearing roots with actual bank state retain ordinary shared locking.
    """
    state_names=STORES+('deep_data.json',PENDING,STATE,'.ingest_transactions')
    if any((bank/name).exists() or (bank/name).is_symlink() for name in state_names):
        return False
    markers=('pyproject.toml','mamey/__init__.py','mamey/bank_transaction.py','tools/ingest_package.py')
    if not all((bank/name).is_file() and not (bank/name).is_symlink()
               and (bank/name).resolve().is_relative_to(bank) for name in markers):
        return False
    import tomllib
    try:
        metadata=tomllib.loads((bank/'pyproject.toml').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise BankError('BANK_SOURCE_MARKERS_UNVERIFIED: cannot classify source destination') from exc
    if metadata.get('project',{}).get('name')!='mamey' or not isinstance(metadata.get('tool',{}).get('sapote'),dict):
        return False
    return True

@contextlib.contextmanager
def lock(bank,writer=False):
    bank=Path(bank).resolve()
    if writer and (bank/'manifest.json').exists():raise BankError('BANK_PACKAGE_DESTINATION_REFUSED: use a separate cohort bank')
    if _empty_bundle_source(bank):
        if writer:raise BankError('BANK_SOURCE_DESTINATION_REFUSED: use a separate cohort bank')
        yield bank
        return
    if writer:bank.mkdir(parents=True,exist_ok=True)
    path=bank/'.ingest.lock'
    _regular(path)
    try:
        import fcntl
        backend='fcntl'
    except ImportError:
        try:import msvcrt
        except ImportError as exc:raise BankError('BANK_LOCK_BACKEND_UNAVAILABLE: refuse unlocked access') from exc
        backend='msvcrt'
    if not bank.exists() and not writer:
        yield bank
        return
    if not writer and not path.exists() and (bank/'manifest.json').exists():
        if (bank/PENDING).exists() or (bank/STATE).exists():raise BankError('BANK_LOCK_MISSING_FOR_TRANSACTIONAL_BANK')
        yield bank
        return
    create = writer or not path.exists()
    with path.open('a+b' if create else 'r+b' if backend=='msvcrt' else 'rb') as handle:
        if backend=='fcntl':fcntl.flock(handle.fileno(),fcntl.LOCK_EX if writer else fcntl.LOCK_SH)
        else:
            if create and path.stat().st_size==0:handle.write(b'0');handle.flush()
            handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_LOCK,1)
        try:yield bank
        finally:
            if backend=='fcntl':fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
            else:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)

def coherent(bank):
    bank=Path(bank).resolve()
    _regular(bank/PENDING);_regular(bank/STATE)
    if (bank/PENDING).exists():raise BankError('BANK_RECOVERY_REQUIRED: use ingest_package.py --recover rollback|finish; no complete bank can be advertised')
    if not (bank/STATE).exists():return {'state':'LEGACY_UNRECEIPTED'}
    _regular(bank/STATE)
    try:state=json.loads((bank/STATE).read_text())
    except (ValueError,OSError) as exc:raise BankError('BANK_COMMIT_STATE_INVALID') from exc
    if state.get('schema')!='sapote.bank-commit.v1' or not isinstance(state.get('files_sha256'),dict) or not set(STORES) <= set(state['files_sha256']):raise BankError('BANK_COMMIT_STATE_INVALID')
    for name,expected in state['files_sha256'].items():
        if name not in STORES and name!='deep_data.json':raise BankError('BANK_COMMIT_PATH_INVALID')
        path=bank/name;_regular(path)
        actual=_hash(path.read_bytes()) if path.exists() else None
        if actual!=expected:raise BankError('BANK_COMMIT_BYTES_MISMATCH: '+name)
    return state

@contextlib.contextmanager
def reader(bank):
    with lock(bank) as root:
        coherent(root)
        yield root

import threading
_READER_LOCAL=threading.local()
def _reader_locks():
    if not hasattr(_READER_LOCAL, 'held'):_READER_LOCAL.held=[]
    return _READER_LOCAL.held

def hold_reader(bank):
    """CLI reader lock held to process exit; release_reader_locks for embeddings."""
    context=reader(bank);context.__enter__();_reader_locks().append(context)

def release_reader_locks():
    held=_reader_locks()
    while held:held.pop().__exit__(None,None,None)
atexit.register(release_reader_locks)

def _boundary(name):
    """Fault-injection boundary; no operational action."""
    return None

def validate_stores(bank):
    root=Path(bank)
    values={}
    for name in STORES:
        p=root/name;_regular(p)
        if not p.exists():continue
        raw=p.read_bytes()
        if name.endswith('.json'):
            try:obj=json.loads(raw)
            except ValueError as exc:raise BankError('BANK_STORE_JSON_INVALID: '+name) from exc
            if name=='strains.json':
                if not isinstance(obj,(dict,list)) or isinstance(obj,list) and any(not isinstance(x,dict) or not x.get('sid') for x in obj):raise BankError('BANK_STORE_SCHEMA_INVALID: '+name)
            elif not isinstance(obj,dict):raise BankError('BANK_STORE_SCHEMA_INVALID: '+name)
            if name=='bgc_data.json' and (not isinstance(obj.get('strains'),dict) or not isinstance(obj.get('bgcs'),list) or any(not isinstance(x,dict) or not x.get('sid') for x in obj['bgcs'])):raise BankError('BANK_STORE_SCHEMA_INVALID: '+name)
            if name=='gene_data.json' and any(not isinstance(obj.get(k),dict) for k in ('scan_agg','tfbs')):raise BankError('BANK_STORE_SCHEMA_INVALID: '+name)
            values[name]=obj
        elif name.endswith('.csv'):
            with p.open(newline='',encoding='utf-8') as h:
                rows=csv.DictReader(h)
                if not rows.fieldnames or 'strain' not in rows.fieldnames or len(set(rows.fieldnames))!=len(rows.fieldnames):raise BankError('BANK_STORE_CSV_INVALID')
                if any(None in r or any(v is None for v in r.values()) for r in rows):raise BankError('BANK_STORE_CSV_INVALID')
        elif not raw.strip():raise BankError('BANK_SCHEMA_MARKER_EMPTY')
    extra=root/'deep_data.json';_regular(extra)
    if extra.exists():
        try: obj=json.loads(extra.read_text())
        except ValueError as exc: raise BankError('BANK_STORE_JSON_INVALID: deep_data.json') from exc
        if not isinstance(obj,dict):raise BankError('BANK_STORE_SCHEMA_INVALID: deep_data.json')
    return values

def _stage(bank):
    parent=bank/'.ingest_transactions'
    if parent.is_symlink() or (parent.exists() and not parent.is_dir()):raise BankError('BANK_JOURNAL_DIRECTORY_INVALID')
    parent.mkdir(exist_ok=True);_sync_dir(bank)
    tx=parent/uuid.uuid4().hex;tx.mkdir();(tx/'before').mkdir();(tx/'after').mkdir()
    return tx

def prepare(bank,stage_builder,names=STORES):
    """Caller holds writer lock. All stores validated before any canonical write."""
    bank=Path(bank);coherent(bank);validate_stores(bank)
    tx=_stage(bank);before={}
    for name in names:
        p=bank/name;_regular(p);before[name]=_hash(p.read_bytes()) if p.exists() else None
        if p.exists():
            _write(tx/'before'/name,p.read_bytes());_write(tx/'after'/name,p.read_bytes())
            # Compatibility convenience only; durable before image is canonical recovery.
            _write(bank/(name+'.bak'),p.read_bytes())
    if (bank/STATE).exists():_write(tx/'before'/STATE,(bank/STATE).read_bytes())
    stage_builder(tx/'after')
    validate_stores(tx/'after')
    for name in names:
        if (tx/'after'/name).exists():_write(tx/'after'/name,(tx/'after'/name).read_bytes())
    after={name:_hash((tx/'after'/name).read_bytes()) if (tx/'after'/name).exists() else None for name in names}
    state={'schema':'sapote.bank-commit.v1','transaction':tx.name,'files_sha256':after}
    if (tx/'after'/'schema_admission.json').exists():
        state['schema_admission']=json.loads((tx/'after'/'schema_admission.json').read_text())
    journal={'schema':'sapote.bank-journal.v1','transaction':tx.name,'before_sha256':before,'after_sha256':after,'prior_state_exists':(bank/STATE).exists(),'prior_state_sha256':_hash((bank/STATE).read_bytes()) if (bank/STATE).exists() else None,'schema_admission':state.get('schema_admission')}
    _json(tx/'journal.json',journal);_sync_dir(tx/'before');_sync_dir(tx/'after');_sync_dir(tx);_sync_dir(tx.parent)
    _boundary('prepared')
    _json(bank/PENDING,journal);_boundary('pending')
    for name in names:
        p=tx/'after'/name
        if p.exists():_write(bank/name,p.read_bytes())
        elif (bank/name).exists():(bank/name).unlink();_sync_dir(bank)
        _boundary('published:'+name)
    _json(bank/STATE,state);_boundary('committed')
    (bank/PENDING).unlink();_sync_dir(bank);_boundary('cleared')
    return state

def recover(bank,mode):
    if mode not in ('rollback','finish'):raise BankError('BANK_RECOVERY_MODE_INVALID')
    with lock(bank,writer=True) as root:
        _regular(root/PENDING)
        if not (root/PENDING).exists():raise BankError('BANK_NO_PENDING_RECOVERY')
        journal=json.loads((root/PENDING).read_text())
        tid=journal.get('transaction','')
        if journal.get('schema')!='sapote.bank-journal.v1' or len(tid)!=32 or any(x not in '0123456789abcdef' for x in tid):raise BankError('BANK_JOURNAL_INVALID')
        tx=root/'.ingest_transactions'/tid
        if tx.resolve()!=tx or not tx.is_dir():raise BankError('BANK_RECOVERY_PATH_INVALID')
        if journal.get('prior_state_exists'):
            old=tx/'before'/STATE;_regular(old)
            if not old.exists() or _hash(old.read_bytes())!=journal.get('prior_state_sha256'):raise BankError('BANK_PRIOR_STATE_IMAGE_MISMATCH')
        phase='before' if mode=='rollback' else 'after'
        hashes=journal.get(phase+'_sha256',{})
        if not isinstance(hashes,dict) or not set(STORES)<=set(hashes) or set(hashes)-set(STORES)-{'deep_data.json'}:raise BankError('BANK_RECOVERY_MANIFEST_INVALID')
        for name,expected in hashes.items():
            p=tx/phase/name;_regular(p)
            actual=_hash(p.read_bytes()) if p.exists() else None
            if expected!=actual:raise BankError('BANK_RECOVERY_IMAGE_MISMATCH: '+name)
            _regular(root/name)
        for name in hashes:
            p=tx/phase/name
            if p.exists():_write(root/name,p.read_bytes())
            elif (root/name).exists():(root/name).unlink();_sync_dir(root)
        if mode=='rollback':
            old=tx/'before'/STATE
            if journal.get('prior_state_exists'):
                _regular(old);_write(root/STATE,old.read_bytes())
            elif (root/STATE).exists():(root/STATE).unlink();_sync_dir(root)
        else:_json(root/STATE,{'schema':'sapote.bank-commit.v1','transaction':tid,'files_sha256':hashes,'schema_admission':journal.get('schema_admission')})
        (root/PENDING).unlink();_sync_dir(root)
        coherent(root)
        return {'state':'ROLLED_BACK' if mode=='rollback' else 'FINISHED','transaction':tid}

def reader_scope(func):
    """Release only locks acquired by this invocation, including exceptional exits."""
    import functools
    @functools.wraps(func)
    def wrapped(*args,**kwargs):
        held=_reader_locks()
        prior=len(held)
        try:return func(*args,**kwargs)
        finally:
            while len(held)>prior:held.pop().__exit__(None,None,None)
    return wrapped
