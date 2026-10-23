"""Portable placement page entry point; uses placement_display, never refits trees.

--display-args is a JSON array of placement_display arguments, without --out.
Relative path-valued arguments resolve from the invocation directory. Bind every
external source using --inputs TSV(path). Supply --caption-note in the array for
captioned re-rendering. Display grouping uses the existing --max-nt/--min-cols
contract, and PDFs/SVGs are produced by the admitted display renderer.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools._figure_route_common import bind,command,execute,output_dir,receipt,table

def plan(args_path, inputs_path, out):
    args=json.loads(Path(args_path).read_text())
    if not isinstance(args,list) or not args or not all(isinstance(x,str) for x in args):
        raise ValueError('display arguments must be a nonempty JSON string array')
    if any(x=='--out' or x.startswith('--out=') or x=='--python' or x.startswith('--python=') or x=='--rscript' or x.startswith('--rscript=') for x in args):
        raise ValueError('output and executable overrides are reserved')
    inp=Path(inputs_path).resolve()
    paths=[(inp.parent/r['path']).resolve() for r in table(inp,['path'])]
    bind(paths)
    # Every existing file-valued argument must be in the declared inventory.
    declared=set(paths)
    for arg in args:
        candidate=Path(arg)
        if candidate.is_file() and candidate.resolve() not in declared:
            raise ValueError(f'undeclared input: {arg}')
    if '--plot-only' not in args: args+=['--plot-only']
    return command('placement_display.py',args+['--out',str(Path(out)/'pages')]),paths+[Path(args_path),inp]

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--display-args',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--dry-run',action='store_true')
    a=p.parse_args(argv);cmd,inputs=plan(a.display_args,a.inputs,a.out)
    from tools._figure_route_common import ROOT
    inputs += [Path(__file__),ROOT/'tools/placement_display.py',ROOT/'tools/collapse_near_identical.py',ROOT/'tools/ggtree_rect_heatmap.R']
    out=output_dir(a.out)
    if a.dry_run:
        (out/'PLAN.json').write_text(json.dumps(cmd,indent=2)+'\n')
        receipt(out,'placement_tree_pages',inputs,{'runtime_state':'DRY_RUN_ONLY'},figures=False);return 0
    execute(cmd,out/'render.log',{'GG_SVG':'1'})
    receipt(out,'placement_tree_pages',inputs,{'tree_fit':'NOT_EXECUTED','assay_states':'delegated unchanged'})
    return 0
if __name__=='__main__': raise SystemExit(main())
