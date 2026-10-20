"""Bound, descriptive bioassay figure preparation. No experimental inference.

Rosters and aliases are explicit inputs. Numeric screening values, qualitative
states, blank cells and missing rows remain distinguishable in exported data.

An assay cell has exactly four non-numeric states: + , − , n.t. and blank. A cell with no numeric
reading is labelled with its recorded state(s), never with a fifth state and never coerced
(a tested "−" is not "n.t."). Collection-specific display rules live in
mamey/data/bioassay_layouts.json (or a file passed with --layout-config), not in this code.
"""

from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import math
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CANDIDA = ('Candida albicans', 'Candida auris', 'Candida (species not named)')
LARVAE = ('Foulbrood 19118-1', 'Foulbrood 818')
MATERIALS = ('Crude extract', 'Fraction', 'HPLC fraction')
MATERIAL_STEM = {'Crude extract': 'crude', 'Fraction': 'fraction', 'HPLC fraction': 'hplc_fraction'}
LAYOUTS = ROOT / 'mamey/data/bioassay_layouts.json'
QUALITATIVE = ('+', '−')

def layout_profile(layout, path=None):
    """The display rules for one collection layout, from the bundled profile file or a user-supplied one."""
    profiles = json.loads(Path(path or LAYOUTS).read_text())
    if layout not in profiles or layout.startswith('_'):
        raise ValueError(f'Unknown layout {layout!r}; profiles: {sorted(k for k in profiles if not k.startswith("_"))}')
    return profiles[layout]

def _states(row):
    """The recorded non-numeric states behind one pooled row; '-' is written as '−' (same state)."""
    raw = json.loads(row['source_states']) if row['state'] == 'mixed_qualitative' else [row['state']]
    return ['−' if s == '-' else s for s in raw]

def empty_cell_label(missing):
    """Label for a cell with no numeric reading: its recorded state(s), from +, −, n.t. and blank only."""
    states = [s for r in missing for s in _states(r)]
    qual = [s for s in QUALITATIVE if s in states]
    if qual:
        return '/'.join(qual)
    if not states or set(states) == {'n.t.'}:
        return 'n.t.'
    return ''

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path, required=()):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        if not set(required) <= set(reader.fieldnames or []):
            raise ValueError(f'{path}: missing columns {required}')
        return list(reader)

def write(path, rows, fields=None):
    rows = list(rows)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with Path(path).open('w', encoding='utf-8', newline='') as f:
        w = _SafeDictWriter(f, fieldnames=fields, delimiter='\t', extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

def numeric(raw):
    if raw in ('', 'n.t.', '+', '-', '−'):
        return None
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f'Invalid inhibition percentage: {raw!r}')
    return value

def activity(value):
    if value is None:
        return ''
    return 'Strong (≥80%)' if value >= 80 else 'Moderate (50–79%)' if value >= 50 else 'Weak (25–49%)' if value >= 25 else 'Inactive (<25%)'

def target_map(kind, profile):
    if kind == 'A02':
        mapping = {x:x for x in ('Candida albicans','Candida auris','E. coli','MRSA')}
        mapping.update({x:(x if profile['split_larvae'] else 'P. larvae') for x in LARVAE})
        return mapping
    if kind in ('A01', 'A04') and profile.get('split_candida') and not (kind == 'A04' and profile.get('a04_pool_candida')):
        # per-species panels (owner, 12 Oct: split C. albicans and C. auris); screens that recorded only 'Candida' used C. albicans or C. auris (owner, 13 Oct) and keep their own panel
        mapping = {'Candida albicans':'C. albicans','Candida auris':'C. auris','Candida (species not named)':'C. albicans or C. auris (not recorded)'}
    else:
        mapping = {x:'Candida sp.' for x in CANDIDA}
    mapping.update({'MRSA':'MRSA'})
    if kind in ('A03','A06'):
        mapping.update({x:'P. larvae' for x in LARVAE})
    if kind == 'A06':
        mapping['E. coli'] = 'E. coli'
    return mapping

def prepare(table, roster_path, aliases_path, kind, layout, material='Crude extract', layouts=None):
    profile = layout_profile(layout, layouts)
    subset = profile['a06_subset_group'] if kind == 'A06' else None
    roster_rows = read(roster_path, ('strain','genus','group'))
    roster = {r['strain']:r for r in roster_rows}
    if len(roster) != len(roster_rows):
        raise ValueError('Duplicate roster strain')
    aliases = json.loads(Path(aliases_path).read_text())
    if any(k == v or v in aliases for k,v in aliases.items()):
        raise ValueError('Alias chains/cycles are not allowed')
    if any(k in roster for k in aliases):
        raise ValueError('Roster must use canonical isolate identifiers')
    mapping = target_map(kind, profile)
    # A02 draws crude extracts and fractions together; HPLC fractions get their own A02.
    materials = (('HPLC fraction',) if material == 'HPLC fraction' else ('Crude extract', 'Fraction')) if kind == 'A02' else (material,)
    buckets = defaultdict(list)
    seen = set()
    raw_rows = []
    for i,r in enumerate(read(table, ('strain','organism','material','best_pct')),2):
        key = (r['strain'],r['organism'],r['material'])
        if key in seen:
            raise ValueError(f'Duplicate canonical input key: {key}')
        seen.add(key)
        strain = aliases.get(r['strain'],r['strain'])
        if strain not in roster or r['organism'] not in mapping or r['material'] not in materials:
            continue
        if subset and roster[strain]['group'] != subset:
            continue
        value = numeric(r['best_pct'])
        # Keep explicit qualitative and missing states verbatim; no coercion.
        raw_rows.append(dict(source_row=i, source_strain=r['strain'], strain=strain,
                             organism=r['organism'], material=r['material'], best_pct=r['best_pct']))
        buckets[(strain,r['material'],mapping[r['organism']])].append((value,r['best_pct'],r['strain'],r['organism']))
    pooled=[]
    for strain,meta in roster.items():
        if subset and meta['group'] != subset: continue
        for mat in materials:
            for target in dict.fromkeys(mapping.values()):
                records=buckets.get((strain,mat,target),[])
                values=[x[0] for x in records if x[0] is not None]
                best=max(values) if values else None
                states=list(dict.fromkeys(x[1] for x in records if x[0] is None))
                state='numeric' if values else ('n.t.' if not records else states[0] if len(states)==1 else 'mixed_qualitative')
                pooled.append(dict(strain=strain,genus=meta['genus'],group=meta['group'],material=mat,target=target,
                                   best_pct='' if best is None else best,state=state,activity_class=activity(best),
                                   source_states=json.dumps(states),source_strains=';'.join(sorted({x[2] for x in records})),
                                   source_organisms=';'.join(sorted({x[3] for x in records}))))
    numeric_rows=[r for r in pooled if r['state']=='numeric']
    used = sorted({r['strain'] for r in raw_rows})
    used_rows=[dict(roster[s], source_strains=';'.join(sorted({r['source_strain'] for r in raw_rows if r['strain']==s}))) for s in used]
    plot=[]
    if kind in ('A03','A04'):
        x_target='P. larvae' if kind=='A03' else 'Candida sp.'
        by={ (r['strain'],r['target']):r for r in numeric_rows }
        split = kind == 'A04' and profile.get('split_candida') and not profile.get('a04_pool_candida')
        x_targets = [mapping[t] for t in CANDIDA] if split else [x_target]
        for s in roster:
            for target in x_targets:
                if (s,target) in by and (s,'MRSA') in by:
                    x,y=by[s,target],by[s,'MRSA']
                    row=dict(strain=s,genus=x['genus'],group=x['group'],material=material,x=x['best_pct'],y=y['best_pct'])
                    if split:
                        row['target']=target
                    plot.append(row)
    elif kind=='A01':
        drop=set(profile.get('a01_drop_targets') or [])
        for r in numeric_rows:
            if r['target'] in drop:
                continue
            focal=profile['focal_group']
            plot.append(dict(r, row=r['group'] if focal and r['group']!=focal else r['genus']))
    else:
        groups=list(dict.fromkeys(r['group'] for r in roster_rows)) if kind=='A02' else ['Streptomyces','Other genera','No 16S sequence']
        targets=list(dict.fromkeys(mapping.values())) if kind=='A02' else ['Candida sp.','E. coli','MRSA','P. larvae']
        for mat in materials:
            for group in groups:
                for target in targets:
                    def grp(r):
                        if kind=='A02': return r['group']
                        return r['genus'] if r['genus']=='Streptomyces' else 'No 16S sequence' if r['genus']=='Unassigned' else 'Other genera'
                    subset=[r for r in numeric_rows if r['material']==mat and r['target']==target and grp(r)==group]
                    n=len(subset); strong=sum(r['best_pct']>=80 for r in subset)
                    missing=[r for r in pooled if r['material']==mat and r['target']==target and grp(r)==group and r['state']!='numeric']
                    plot.append(dict(material=mat,group=group,target=target,n_tested=n,n_strong=strong,
                                     pct='' if not n else 100*strong/n,label=empty_cell_label(missing) if not n else f'{strong}/{n}',
                                     n_label=empty_cell_label(missing) if not n else f'n={n}',
                                     n_blank=sum(r['state']=='' for r in missing),n_untested=sum(r['state']=='n.t.' for r in missing),
                                     n_qualitative=sum(any(s in QUALITATIVE for s in _states(r)) for r in missing),
                                     n_qual_positive=sum('+' in _states(r) for r in missing),
                                     n_qual_negative=sum('−' in _states(r) for r in missing),
                                     block='Foulbrood' if target.startswith(('P. larvae','Foulbrood')) else 'Human pathogen panel'))
    if kind == 'A02' and materials == ('HPLC fraction',):
        # An HPLC-only grid leaves out groups with no HPLC fraction tested, instead of drawing an unlabeled row of n.t.
        tested = {r['group'] for r in plot if r['n_tested']}
        plot = [r for r in plot if r['group'] in tested]
    return dict(plot=plot, pooled=pooled, raw=raw_rows, used=used_rows)

def prepare_fractions(table, roster_path, aliases_path, layout, material='Fraction', layouts=None):
    """A07: one point per fraction (one fraction-plate well), best Candida (any species) against best MRSA.
    The table has one row per strain, fraction, organism and material: strain, fraction, organism, material, best_pct."""
    profile = layout_profile(layout, layouts)
    roster = {r['strain']: r for r in read(roster_path, ('strain', 'genus', 'group'))}
    aliases = json.loads(Path(aliases_path).read_text())
    vals, raw_rows = defaultdict(dict), []
    for i, r in enumerate(read(table, ('strain', 'fraction', 'organism', 'material', 'best_pct')), 2):
        strain = aliases.get(r['strain'], r['strain'])
        if strain not in roster or r['material'] != material:
            continue
        v = numeric(r['best_pct'])
        if v is None:
            continue
        target = 'Candida sp.' if r['organism'] in CANDIDA else r['organism'] if r['organism'] == 'MRSA' else None
        if target is None:
            continue
        raw_rows.append(dict(source_row=i, source_strain=r['strain'], strain=strain, fraction=r['fraction'], organism=r['organism'],
                             material=r['material'], best_pct=r['best_pct']))
        k = (strain, r['fraction'])
        vals[k][target] = max(v, vals[k].get(target, -1e9))
    plot = [dict(strain=s, fraction=f, genus=roster[s]['genus'], group=roster[s]['group'], material=material,
                 x=v['Candida sp.'], y=v['MRSA']) for (s, f), v in sorted(vals.items()) if 'Candida sp.' in v and 'MRSA' in v]
    used = sorted({r['strain'] for r in plot})
    return dict(plot=plot, pooled=[], raw=raw_rows, used=[dict(roster[s], source_strains=s) for s in used])

def cli(kind, r_script, argv=None):
    import argparse
    from mamey.figure_stamp import stamp_file
    p=argparse.ArgumentParser(description=f'{kind}: descriptive single-replicate screening figure candidate')
    for name in ('table','roster','aliases','lock','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--table-sha256',required=True); p.add_argument('--lock-sha256',required=True)
    p.add_argument('--layout',required=True,help='a profile name in the layout file (bundled: mamey/data/bioassay_layouts.json)')
    p.add_argument('--layout-config',type=Path,default=None,help='a layout profile JSON to use instead of the bundled one')
    p.add_argument('--material',choices=MATERIALS,default='Crude extract')
    p.add_argument('--prepare-only',action='store_true')
    p.add_argument('--palette-set',default='default')
    p.add_argument('--bar-labels',action='store_true',help='A06: also print strong/tested above each bar (default: n tested under each bar only)')
    p.add_argument('--point-labels',choices=('default','genus'),default='default',help='A03: genus = keep every genus and label every isolate that has a 16S genus')
    a=p.parse_args(argv)
    if sha(a.table)!=a.table_sha256 or sha(a.lock)!=a.lock_sha256:
        raise ValueError('Bound input hash mismatch')
    if a.out.exists(): raise FileExistsError(a.out)
    profile=layout_profile(a.layout,a.layout_config)
    result=(prepare_fractions(a.table,a.roster,a.aliases,a.layout,a.material,a.layout_config) if kind=='A07'
            else prepare(a.table,a.roster,a.aliases,kind,a.layout,a.material,a.layout_config))
    if not result['plot']: raise ValueError('No eligible plotted rows')
    a.out.mkdir(parents=True)
    for key,name in [('plot','plot_data.tsv'),('pooled','ASSAY_STATES.tsv'),('raw','SOURCE_ROWS.tsv'),('used','ISOLATES_USED.tsv')]:
        write(a.out/name,result[key])
    palette_path=ROOT/'mamey/data/genus_palette.json'
    palette=json.loads(palette_path.read_text())
    colors=dict(palette['default']); colors.update(palette.get('sets',{}).get(a.palette_set,{}))
    # Explicit spelling alias used by the printed figures, not a biological join.
    colors['Mycolicibacterium']=colors['Mycolicobacterium']
    for r in result['used']:
        colors.setdefault(r['genus'],palette['fallback'])
    config=dict(kind=kind,layout=a.layout,profile=profile,material=a.material,data=str((a.out/'plot_data.tsv').resolve()),
                stem=str((a.out/f'{kind}_{a.layout}_{MATERIAL_STEM[a.material]}').resolve()),
                palette=colors,fallback=palette['fallback'],theme=str(ROOT/'tools/sapote_pub_layout.R'),
                groups=list(dict.fromkeys(r['group'] for r in result['used'])),dpi=600,bar_labels=a.bar_labels,point_labels=a.point_labels)
    (a.out/'render_config.json').write_text(json.dumps(config,indent=2))
    inputs=[a.table,a.roster,a.aliases,a.lock,palette_path,Path(a.layout_config or LAYOUTS),Path(r_script),Path(__file__),ROOT/'tools/sapote_pub_layout.R',ROOT/'tools/bioassay_paper_theme.R',Path(__file__).parents[1]/'tools'/f'bioassay_{kind.lower()}.py']
    receipt=dict(kind=kind,layout=a.layout,material=a.material,status='PREPARED',inputs=[dict(path=str(x.resolve()),sha256=sha(x)) for x in inputs],
                 claim_scope='Single-replicate preliminary strain-level screening; no BGC attribution.',minimum_font_pt=8,
                 material_colors={'Crude extract':'#C0973F','Fraction':'#7E5AA2','HPLC fraction':'#7E5AA2'},source_rows=len(result['raw']),plotted_rows=len(result['plot']))
    (a.out/'RUN_INFO.json').write_text(json.dumps(receipt,indent=2))
    pooled_a04 = kind == 'A04' and profile.get('a04_pool_candida')
    candida = ('Candida targets are shown separately: C. albicans, C. auris, and screens recorded only as Candida '
               '(C. albicans or C. auris; species not recorded).' if kind in ('A01', 'A04') and profile.get('split_candida') and not pooled_a04
               else f"{profile.get('a04_candida_axis_label') or 'Candida sp.'} is the higher best inhibition of C. albicans, "
                    'C. auris or screens recorded only as Candida (species not recorded), per isolate.' if pooled_a04
               else 'Candida sp. pools C. albicans, C. auris and unnamed Candida where displayed.')
    labels = {'strong': ' Labelled points: isolates with at least 80% inhibition of both targets.',
              'none': ' Points are not labelled; per-isolate values are in plot_data.tsv.',
              'nonzero': ' Labelled points: every isolate not at 0% inhibition of both targets.'}.get(profile.get('a04_point_labels'), '') if kind == 'A04' else ''
    per = 'Each point is one fraction (one fraction-plate well); ' if kind == 'A07' else ''
    (a.out/'CAPTION.md').write_text('Single-replicate preliminary screening at 48 h. ' + per + 'Best numeric inhibition per isolate and material; 384-well data use only the bound 120 µg/mL selection. ' + candida + ' P. larvae pools strains 19118-1 and 818 where displayed as one target. Strong activity is ≥80%. Missing or qualitative entries are not numeric negatives. Activity is measured at strain level and is not attributed to a BGC.' + labels + '\n')
    if not a.prepare_only:
        render(a.out,r_script)
    return result

def render(out, r_script):
    from mamey.figure_stamp import stamp_file
    out=Path(out)
    config=json.loads((out/'render_config.json').read_text())
    env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',VECLIB_MAXIMUM_THREADS='4',
             BIOASSAY_CONFIG=str((out/'render_config.json').resolve()),BIOASSAY_THEME=str(ROOT/'tools/bioassay_paper_theme.R'))
    proc=subprocess.run(['Rscript',str(r_script),str(out/'render_config.json')],capture_output=True,text=True,timeout=1800,env=env)
    (out/'RENDER.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode: raise RuntimeError(proc.stdout+proc.stderr)
    for ext in ('.png','.pdf','.svg'): stamp_file(Path(config['stem']+ext),'bioassay_'+config['kind'].lower())
    receipt=json.loads((out/'RUN_INFO.json').read_text());receipt['status']='RENDERED'
    receipt['inputs']=[dict(path=x['path'],sha256=sha(x['path'])) for x in receipt['inputs']]
    theme_path=ROOT/'tools/bioassay_paper_theme.R'
    if str(theme_path) not in [x['path'] for x in receipt['inputs']]:receipt['inputs'].append(dict(path=str(theme_path),sha256=sha(theme_path)))
    receipt['outputs']=[dict(path=config['stem']+ext,sha256=sha(config['stem']+ext)) for ext in ('.png','.pdf','.svg')]
    (out/'RUN_INFO.json').write_text(json.dumps(receipt,indent=2))
