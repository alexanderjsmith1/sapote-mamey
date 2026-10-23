"""Render a paper bioassay set using the installed A01-A07 bundle routes.

Spec TSV: name, layout, panel, material, table, roster, aliases, lock,
table_sha256, lock_sha256; optional point_labels, bar_labels, repel_seed, a07_xmax.
Paths resolve relative to the spec. No patching or copying of a sealed bundle.
"""
import argparse
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools._figure_route_common import bind, command, execute, output_dir, receipt, sha, table, unique
FIELDS = ['name','layout','panel','material','table','roster','aliases','lock','table_sha256','lock_sha256']

def plan(spec, out):
    spec = Path(spec).resolve()
    rows = table(spec, FIELDS); unique(rows, 'name')
    jobs = []; inputs = [spec]
    for r in rows:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', r['name']):
            raise ValueError('unsafe output name')
        if r['panel'] not in ('a01','a02','a03','a04','a06','a07'):
            raise ValueError('unsupported bioassay panel')
        if r['material'] not in ('Crude extract','Fraction','HPLC fraction'):
            raise ValueError('unsupported material; preserve source labels')
        paths = {k: (spec.parent/r[k]).resolve() for k in ('table','roster','aliases','lock')}
        for k in ('table','lock'):
            if sha(paths[k]) != r[k+'_sha256'].lower():
                raise ValueError(f'{k}: SHA-256 mismatch')
        bind(paths.values()); inputs.extend(paths.values())
        args = [x for k in ('table','roster','aliases','lock') for x in ('--'+k, paths[k])]
        args += ['--table-sha256',r['table_sha256'],'--lock-sha256',r['lock_sha256'],
                 '--layout',r['layout'],'--palette-set',r['layout'],'--material',r['material'],
                 '--out',Path(out)/r['name']]
        if r.get('point_labels'):
            if r['panel'] != 'a03' or r['point_labels'] not in ('default','genus'):
                raise ValueError('point_labels requires A03 and a supported label mode')
            args += ['--point-labels',r['point_labels']]
        if r.get('bar_labels'):
            if r['bar_labels'] not in ('yes','no'): raise ValueError('bar_labels must be yes/no')
            if r['bar_labels'] == 'yes':
                if r['panel'] != 'a06': raise ValueError('bar_labels requires A06')
                args += ['--bar-labels']
        env = {}
        if r.get('repel_seed'):
            env['BIOASSAY_REPEL_SEED'] = str(int(r['repel_seed']))
            env['BIOASSAY_A07_REPEL_SEED'] = str(int(r['repel_seed']))
        if r.get('a07_xmax'):
            from tools._figure_route_common import number
            if r['panel'] != 'a07': raise ValueError('a07_xmax requires A07')
            env['BIOASSAY_A07_XMAX'] = str(number(r['a07_xmax'], 0.001))
        tool = 'bioassay_'+r['panel']+'.py'
        inputs.extend([Path(__file__).parent/tool, Path(__file__).parent/Path(tool).with_suffix('.R')])
        jobs.append((r['name'],command(tool,args),env))
    inputs += [Path(__file__),Path(__file__).parent/'bioassay_route_records.py',Path(__file__).resolve().parents[1]/'mamey/bioassay_paper.py']
    return jobs, inputs

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--methods-context',type=Path,help='JSON object mapping job name or panel to approved methods metadata')
    p.add_argument('--dry-run',action='store_true'); a=p.parse_args(argv)
    jobs,inputs=plan(a.spec,a.out)
    import json
    context=json.loads(a.methods_context.read_text()) if a.methods_context else None
    if not a.dry_run and not isinstance(context,dict):
        raise ValueError('render mode requires --methods-context; approved prose is not inferred')
    if a.methods_context: inputs.append(a.methods_context); bind([a.methods_context])
    specs={r['name']:r for r in table(a.spec,FIELDS)}
    if not a.dry_run:
        from mamey.figure_policy import CAPTION_METHOD_FIELDS
        computed={'caption_schema_version','source_bindings','denominator','group_denominators','typed_missingness'}
        for name,_,_ in jobs:
            metadata=context.get(name,context.get(specs[name]['panel']))
            if not isinstance(metadata,dict) or any(not metadata.get(k) for k in set(CAPTION_METHOD_FIELDS)-computed):
                raise ValueError('missing approved methods fields for '+name)
    out=output_dir(a.out)
    if a.dry_run:
        import json
        (out/'PLAN.json').write_text(json.dumps([{'name':n,'argv':v,'env':e} for n,v,e in jobs],indent=2)+'\n')
        receipt(out,'bioassay_paper_set',inputs,{'runtime_state':'DRY_RUN_ONLY'},figures=False)
        return 0
    for name,cmd,env in jobs:
        execute(cmd,out/(name+'.log'),env)
        products=list((out/name).rglob('*'))
        if any(not any(f.suffix==ext for f in products) for ext in ('.png','.pdf','.svg')):
            raise ValueError(f'{name}: missing figure format')
        from tools.bioassay_route_records import record
        metadata=context.get(name,context.get(specs[name]['panel']))
        roster=(a.spec.resolve().parent/specs[name]['roster']).resolve()
        labels=[r['strain'] for r in table(roster,['strain'])]
        record(out/name,metadata,labels,scatter=specs[name]['panel'] in ('a03','a04','a07'))
    receipt(out,'bioassay_paper_set',inputs,{'figures':len(jobs),'assay_states':'preserved by installed bioassay_paper route'})
    return 0
if __name__=='__main__': raise SystemExit(main())
