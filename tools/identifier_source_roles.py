"""One source-site role policy for repository tests and staged test artifacts.

Exact roles do not establish biological identity, registry absence or release
permission. A separate registry guard and all other export gates remain required.
The historically named tests/reviewed_public_reference_sites.json is the sole
source-site table; it now also records explicitly reviewed authored inputs.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tokenize
import unicodedata
from synthetic_id_registry_guard import identity_key

SCHEMA = 'sapote.reviewed-identifier-source-sites.v2'
POLICY = 'tests/reviewed_public_reference_sites.json'
ID = re.compile(r'\b(?:AS|AJS|as|ajs)[-_]?[0-9]{2,}|\bPENDING-[A-Z0-9]+')
PLACEHOLDERS = {'AS-XXX','AJS-XXX','PENDING-XXX'}
_IDENTITY_FIELDS = {'strain','strain_id','subject','subject_id','isolate','isolate_id','sid','sample_id'}
_PUBLIC_KINDS = {'public_natural_product_name':'public_product_reference',
                 'existing_public_reference_organism_spelling':'public_organism_reference'}
_FIXTURE_ROLE = 'authored_fixture_input_or_expected_value'
_MAX_BYTES = 16 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def normalise(token):
    return re.sub(r'^(AS|AJS)[-_]?([0-9])',r'\1-\2',token.upper())


def unique(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValueError('duplicate policy key')
        result[key] = value
    return result


def read_regular(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('noncanonical input')
    for component in [*reversed(path.parents),path]:
        if stat.S_ISLNK(component.lstat().st_mode):
            raise ValueError('linked input')
    selected = path.lstat()
    if not stat.S_ISREG(selected.st_mode) or selected.st_size > _MAX_BYTES:
        raise ValueError('input shape')
    fd = os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_CLOEXEC',0)|getattr(os,'O_NONBLOCK',0))
    try:
        before = os.fstat(fd)
        def generation(s):
            return (s.st_dev,s.st_ino,stat.S_IFMT(s.st_mode),s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if (not stat.S_ISREG(before.st_mode) or before.st_ino <= 0 or
                before.st_size > _MAX_BYTES or generation(before)!=generation(selected)):
            raise ValueError('input binding')
        blocks = [];count = 0
        while True:
            block = os.read(fd,1048576)
            if not block:break
            count += len(block)
            if count > _MAX_BYTES:raise ValueError('input grew')
            blocks.append(block)
        after = os.fstat(fd)
        if count!=before.st_size or generation(after)!=generation(before) or generation(path.lstat())!=generation(after):
            raise ValueError('input changed')
        return b''.join(blocks)
    finally:
        os.close(fd)


def reference_hashes(source_root):
    raw = read_regular(Path(source_root)/'tools/test_public_reference_tokens.json')
    catalog = json.loads(raw,object_pairs_hook=unique)
    if catalog.get('schema')!='sapote.test-public-reference-tokens.v1':raise ValueError('catalog schema')
    hashes = {};keys = set()
    for entry in catalog['tokens']:
        role = _PUBLIC_KINDS.get(entry['kind'])
        if role is None or role in hashes or not isinstance(entry['token'],str):raise ValueError('catalog entry')
        hashes[role] = digest(entry['token'].encode());keys.add(identity_key(entry['token']))
    if set(hashes)!=set(_PUBLIC_KINDS.values()):raise ValueError('catalog incomplete')
    return raw,hashes,keys


def declarations(source_root,public_keys):
    raw = read_regular(Path(source_root)/'tools/test_synthetic_ids.txt')
    values = [l.strip() for l in raw.decode().splitlines() if l.strip() and not l.lstrip().startswith('#')]
    seen = set()
    for value in values:
        key = identity_key(value)
        if (re.fullmatch(r'(?:AS|AJS)-[0-9]+|PENDING-[A-Z0-9]+',value) is None or
                key in seen or key in public_keys):raise ValueError('declaration contract')
        seen.add(key)
    return raw,set(values)


def semantics(raw,start,end):
    text = raw.decode('utf-8');lines = text.splitlines(keepends=True);starts = [0]
    for line in lines:starts.append(starts[-1]+len(line.encode()))
    tree = ast.parse(text);parents = {c:n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    def bounds(n):
        return (starts[n.lineno-1]+n.col_offset,starts[n.end_lineno-1]+n.end_col_offset)
    def contains(n):
        return hasattr(n,'end_lineno') and bounds(n)[0]<=start and end<=bounds(n)[1]
    line = next(n+1 for n in range(len(lines)) if starts[n]<=start<starts[n+1])
    funcs = [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and
             min([n.lineno]+[d.lineno for d in n.decorator_list])<=line<=n.end_lineno]
    owner = min(funcs,key=lambda n:n.end_lineno-n.lineno).name if funcs else '<module>'
    def at(p):return starts[p[0]-1]+len(lines[p[0]-1][:p[1]].encode())
    token = next((t for t in tokenize.generate_tokens(io.StringIO(text).readline)
                  if t.type in (tokenize.STRING,tokenize.COMMENT) and at(t.start)<=start and end<=at(t.end)),None)
    kind = 'comment' if token and token.type==tokenize.COMMENT else 'string' if token else 'code'
    def identity_target(target):
        if isinstance(target,ast.Name):return target.id.lower() in _IDENTITY_FIELDS
        if isinstance(target,ast.Attribute):return target.attr.lower() in _IDENTITY_FIELDS
        if isinstance(target,ast.Subscript):
            key=target.slice
            # A computed selector does not establish a non-identity destination.
            return not isinstance(key,ast.Constant) or not isinstance(key.value,str) or key.value.lower() in _IDENTITY_FIELDS
        if isinstance(target,ast.Starred):return identity_target(target.value)
        if isinstance(target,(ast.Tuple,ast.List)):return any(identity_target(t) for t in target.elts)
        return False
    def identity_assignment(target,value):
        if isinstance(target,(ast.Tuple,ast.List)) and isinstance(value,(ast.Tuple,ast.List)):
            if len(target.elts)==len(value.elts) and not any(isinstance(t,ast.Starred) for t in target.elts):
                return any(identity_assignment(t,v) for t,v in zip(target.elts,value.elts))
        # Unknown/starred unpacking cannot bind a product to a separate position.
        return identity_target(target) and contains(value)
    identity = False
    for n in ast.walk(tree):
        if isinstance(n,ast.Constant) and isinstance(n.value,str) and contains(n):
            expr = parents.get(n);container = parents.get(expr)
            if isinstance(expr,ast.Expr) and hasattr(container,'body') and container.body and container.body[0] is expr:kind='docstring'
        if isinstance(n,ast.Dict):
            for key,value in zip(n.keys,n.values):
                if isinstance(key,ast.Constant) and isinstance(key.value,str) and key.value.lower() in _IDENTITY_FIELDS and contains(value):identity=True
        if isinstance(n,(ast.Assign,ast.AnnAssign)):
            targets = n.targets if isinstance(n,ast.Assign) else [n.target]
            if n.value is not None and any(identity_assignment(t,n.value) for t in targets):identity=True
        if isinstance(n,(ast.AugAssign,ast.NamedExpr)) and identity_assignment(n.target,n.value):identity=True
        if isinstance(n,ast.keyword) and isinstance(n.arg,str) and n.arg.lower() in _IDENTITY_FIELDS and contains(n.value):identity=True
    return owner,kind,identity


def bound_sites(raw,entry,public,allowed):
    if digest(raw)!=entry['source_sha256']:raise ValueError('source hash')
    result = {};candidates = {(len(raw.decode()[:m.start()].encode()),len(raw.decode()[:m.end()].encode())) for m in ID.finditer(raw.decode())}
    for site in entry['sites']:
        if any(type(site[k]) is not int for k in ['start','end','context_start','context_end']):raise ValueError('offset type')
        a,b,ca,cb = (site[k] for k in ['start','end','context_start','context_end'])
        if (not 0<=ca<=a<b<=cb<=len(raw) or (a,b) in result or (a,b) not in candidates or
                digest(raw[a:b])!=site['token_sha256'] or digest(raw[ca:cb])!=site['context_sha256']):raise ValueError('site binding')
        role = site['role'];owner,kind,identity = semantics(raw,a,b)
        if owner!=site['owner'] or kind!=site['lexical_kind']:raise ValueError('owner or lexical role')
        provenance = site['provenance']
        if not isinstance(provenance,dict):raise ValueError('provenance shape')
        source_patch = (set(provenance) in ({'kind','reviewed_patch_sha256'}, {'kind','reviewed_patch_sha256','basis'}) and
                        ('basis' not in provenance or isinstance(provenance['basis'],str)) and
                        isinstance(provenance['reviewed_patch_sha256'],str) and
                        re.fullmatch(r'[0-9a-f]{64}',provenance['reviewed_patch_sha256']) is not None)
        site_review = (set(provenance)=={'kind','review_record_sha256'} and
                       provenance['kind']=='ADOPTED_AUTHORED_FIXTURE_SITE_REVIEW' and
                       isinstance(provenance['review_record_sha256'],str) and
                       re.fullmatch(r'[0-9a-f]{64}',provenance['review_record_sha256']) is not None)
        # A named record pin is not historical authorship or semantic proof by itself.
        # Root must adopt the actual independent review record, with exact source/site evidence.
        if role in public:
            after = raw[b:].decode()
            if (not source_patch or site['token_sha256']!=public[role] or identity or
                    provenance['kind']!='ADOPTED_PUBLIC_SOURCE_SITE' or
                    after and (after[0].isalnum() or after[0]=='_')):raise ValueError('public role context')
        elif role==_FIXTURE_ROLE:
            canonical = normalise(raw[a:b].decode())
            if (kind!='string' or canonical not in allowed or
                    digest(canonical.encode())!=site['canonical_declaration_sha256'] or
                    not ((source_patch and provenance['kind']=='ADOPTED_AUTHORED_FIXTURE_SOURCE') or site_review)):
                raise ValueError('authored fixture context')
        else:raise ValueError('unselected role')
        result[a,b] = role
    return result


def parse_entries(manifest):
    if manifest.get('schema')!=SCHEMA:raise ValueError('policy schema')
    entries = {}
    for entry in manifest['files']:
        rel = entry['path'];safe = PurePosixPath(rel)
        if (not isinstance(rel,str) or safe.is_absolute() or safe.as_posix()!=rel or
                '..' in safe.parts or '\\' in rel or ':' in rel or rel in entries):raise ValueError('policy path')
        entries[rel] = entry
    return entries


def reviewed_public_sites(root,path,raw,policy_path):
    """Compatibility API; only exact public sites, never authored identity values."""
    try:
        path = Path(path);root = Path(root)
        if any(root.joinpath(*path.relative_to(root).parts[:n]).is_symlink() for n in range(1,len(path.relative_to(root).parts)+1)):return set()
        manifest = json.loads(read_regular(policy_path),object_pairs_hook=unique);entry = parse_entries(manifest).get(path.relative_to(root).as_posix())
        if entry is None:return set()
        _,public,keys = reference_hashes(Path(__file__).resolve().parents[1]);_,allowed = declarations(Path(__file__).resolve().parents[1],keys)
        return {span for span,role in bound_sites(raw,entry,public,allowed).items() if role in public}
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,SyntaxError,tokenize.TokenError):
        return set()


def select_policy(source_root,expected=None):
    source_root = Path(source_root).absolute()
    raw = read_regular(source_root/POLICY)
    if expected is not None and digest(raw)!=expected:raise ValueError('policy changed after source selection')
    manifest = json.loads(raw,object_pairs_hook=unique);entries = parse_entries(manifest)
    catalog,public,keys = reference_hashes(source_root);listing,allowed = declarations(source_root,keys)
    normalizer=read_regular(source_root/'tools/synthetic_id_registry_guard.py')
    imported_normalizer=read_regular(Path(sys.modules[identity_key.__module__].__file__))
    if (digest(catalog)!=manifest['public_reference_catalog_sha256'] or
            digest(listing)!=manifest['canonical_declarations_sha256'] or
            digest(normalizer)!=manifest['identity_normalizer_sha256'] or
            digest(imported_normalizer)!=manifest['identity_normalizer_sha256']):raise ValueError('policy dependencies changed')
    bound = {}
    for rel,entry in entries.items():bound[rel]=bound_sites(read_regular(source_root/rel),entry,public,allowed)
    return raw,manifest,entries,bound,allowed



def test_source_snapshot(rows, *, final_inventory=False):
    """Bind the test subtree's bytes and namespace; final inventory must be cache-free."""
    selected = {};ignored = {'__pycache__','.pytest_cache','.DS_Store'}
    for row in rows:
        name,kind,size,sha = ((row['name'],row['kind'],row['size'],row['sha256']) if isinstance(row,dict)
                              else (row.name,row.kind,row.size,row.sha256))
        name = unicodedata.normalize('NFC',name.rstrip('/'))
        if name=='tests' or not name.startswith('tests/'):continue
        if any(part in ignored for part in PurePosixPath(name).parts):
            if final_inventory:raise ValueError('test cache reintroduced after cleanup')
            continue
        if name in selected or kind not in ['REGULAR_FILE','DIRECTORY_NO_CONTENT']:raise ValueError('test snapshot shape')
        if type(size) is not int or size<0:raise ValueError('test snapshot size')
        if kind=='REGULAR_FILE' and re.fullmatch(r'[0-9a-f]{64}',sha or '') is None:raise ValueError('test snapshot digest')
        if kind=='DIRECTORY_NO_CONTENT' and (size!=0 or sha!=''):raise ValueError('test directory snapshot')
        selected[name]=[name,kind,size,sha]
    payload=[selected[k] for k in sorted(selected,key=lambda value:value.encode('utf-8'))]
    return digest(json.dumps(payload,separators=(',',':'),ensure_ascii=True).encode())


def audit_test_identifiers(source_root,stage_root,expected_policy_sha256):
    result = {'schema':'sapote.source-test-role-audit.v1','state':'HOLD','artifact_export_permission':False,
              'scope':'readable tests source sites only; other privacy/archive/source-integrity gates remain required',
              'counts':{'public_reference_sites':0,'authored_fixture_sites':0,'existing_placeholder_sites':0,
                        'declared_unreviewed_sites':0,'unlisted_unreviewed_sites':0,'binary_outside_source_scope':0},'findings':[]}
    try:
        if re.fullmatch(r'[0-9a-f]{64}',expected_policy_sha256 or '') is None:raise ValueError('explicit policy digest required')
        source_root = Path(source_root).absolute();stage_root = Path(stage_root).absolute()
        raw,manifest,entries,bound,allowed = select_policy(source_root,expected_policy_sha256)
        result['policy_sha256'] = digest(raw)
        if not (stage_root/'tests').exists() and not (stage_root/'tests').is_symlink():
            result['state']='PASS_SOURCE_ROLE_SCOPE';result['test_source_sha256']=test_source_snapshot([])
            return result
        if not (stage_root/'tests').is_dir() or (stage_root/'tests').is_symlink():raise ValueError('tests source tree unavailable')
        if read_regular(stage_root/POLICY)!=raw:raise ValueError('staged role table changed or absent')
        snapshot=[]
        for path in sorted((stage_root/'tests').rglob('*')):
            if any(x in path.parts for x in ['__pycache__','.pytest_cache']):continue
            if path.is_symlink():raise ValueError('linked staged source')
            rel=path.relative_to(stage_root).as_posix()
            if path.is_dir():
                snapshot.append({'name':rel,'kind':'DIRECTORY_NO_CONTENT','size':0,'sha256':''});continue
            data = read_regular(path)
            snapshot.append({'name':rel,'kind':'REGULAR_FILE','size':len(data),'sha256':digest(data)})
            if rel in entries and digest(data)!=entries[rel]['source_sha256']:raise ValueError('staged source drift')
            try:text = data.decode('utf-8')
            except UnicodeError:
                result['counts']['binary_outside_source_scope']+=1;continue
            if '\0' in text:
                result['counts']['binary_outside_source_scope']+=1;continue
            roles = bound.get(rel,{})
            for match in ID.finditer(text):
                a,b = len(text[:match.start()].encode()),len(text[:match.end()].encode());token = match[0];after = text[match.end():]
                if token in PLACEHOLDERS and not(after and (after[0].isalnum() or after[0]=='_')):
                    result['counts']['existing_placeholder_sites']+=1;continue
                role = roles.get((a,b))
                if role in _PUBLIC_KINDS.values():result['counts']['public_reference_sites']+=1;continue
                if role==_FIXTURE_ROLE:result['counts']['authored_fixture_sites']+=1;continue
                declared = normalise(token) in allowed
                result['counts']['declared_unreviewed_sites' if declared else 'unlisted_unreviewed_sites']+=1
                display = re.sub(r'(?:AS|AJS)[-_]?[0-9]+|PENDING-[A-Z0-9]+','<identifier>',rel,flags=re.I)
                result['findings'].append({'path':display,'path_sha256':digest(rel.encode()),'line':text.count('\n',0,match.start())+1,
                                          'start':a,'end':b,'token_sha256':digest(token.encode()),
                                          'reason_code':'DECLARATION_WITHOUT_ARTIFACT_ROLE' if declared else 'UNREVIEWED_IDENTIFIER_SOURCE_SITE'})
        if read_regular(source_root/POLICY)!=raw or read_regular(stage_root/POLICY)!=raw:raise ValueError('policy changed during audit')
        result['test_source_sha256']=test_source_snapshot(snapshot)
        result['state'] = 'HOLD' if result['findings'] else 'PASS_SOURCE_ROLE_SCOPE'
    except (Exception,KeyboardInterrupt,SystemExit):
        result['state'] = 'HOLD';result['issues'] = ['SOURCE_ROLE_BINDING_OR_AUDIT_UNVERIFIED']
    return result



def validate_role_audit_receipt(record,expected_policy):
    keys={'schema','state','artifact_export_permission','scope','counts','findings','policy_sha256','test_source_sha256'}
    count_keys={'public_reference_sites','authored_fixture_sites','existing_placeholder_sites',
                'declared_unreviewed_sites','unlisted_unreviewed_sites','binary_outside_source_scope'}
    if (not isinstance(expected_policy,str) or re.fullmatch(r'[0-9a-f]{64}',expected_policy) is None or
            not isinstance(record,dict) or set(record)!=keys or
            record['schema']!='sapote.source-test-role-audit.v1' or record['state']!='PASS_SOURCE_ROLE_SCOPE' or
            record['artifact_export_permission'] is not False or
            record['scope']!='readable tests source sites only; other privacy/archive/source-integrity gates remain required' or
            record['policy_sha256']!=expected_policy or record['findings']!=[] or
            not isinstance(record['test_source_sha256'],str) or
            re.fullmatch(r'[0-9a-f]{64}',record['test_source_sha256']) is None or
            not isinstance(record['counts'],dict) or set(record['counts'])!=count_keys or
            any(type(v) is not int or v<0 for v in record['counts'].values()) or
            record['counts']['declared_unreviewed_sites']!=0 or record['counts']['unlisted_unreviewed_sites']!=0):
        raise ValueError('role receipt binding')
    return record['test_source_sha256']

def write_line(stream,text):
    offset = 0
    while offset<len(text):
        n = stream.write(text[offset:])
        if type(n) is not int or not 0<n<=len(text)-offset:raise OSError('unverified output progress')
        offset += n
    stream.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--stage-root',type=Path)
    parser.add_argument('--policy-sha256')
    parser.add_argument('--policy-digest',action='store_true')
    parser.add_argument('--receipt-stdout',action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.policy_digest:
            raw,*_ = select_policy(args.source_root,args.policy_sha256)
            write_line(sys.stdout,digest(raw)+'\n');return 0
        result = audit_test_identifiers(args.source_root,args.stage_root,args.policy_sha256)
        write_line(sys.stdout if args.receipt_stdout else sys.stderr,json.dumps(result,sort_keys=True)+'\n')
        return 0 if result['state']=='PASS_SOURCE_ROLE_SCOPE' else 2
    except (Exception,KeyboardInterrupt,SystemExit):
        return 2


if __name__=='__main__':raise SystemExit(main())
