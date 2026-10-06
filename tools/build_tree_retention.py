#!/usr/bin/env python3
"""Mandatory byte-bound input and retained-tip gate for build_tree.sh.

Pure admission/QC: no engine, networking, threshold or scientific interpretation.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def load_gate(path):
    if not Path(path).is_file():raise ValueError('MANDATORY_RETENTION_GATE_UNAVAILABLE')
    spec=importlib.util.spec_from_file_location('_build_tree_retention_gate',path)
    if spec is None or spec.loader is None:raise ValueError('MANDATORY_RETENTION_GATE_UNLOADABLE')
    module=importlib.util.module_from_spec(spec)
    try:spec.loader.exec_module(module)
    except Exception as exc:raise ValueError('MANDATORY_RETENTION_GATE_UNLOADABLE: '+str(exc)) from exc
    return module


def input_binding(genome_list,tree_spec,gate):
    listing=Path(genome_list).resolve();spec=Path(tree_spec).resolve()
    payload=json.loads(spec.read_text())
    if not isinstance(payload,dict):raise ValueError('TREE_SPEC_NOT_OBJECT')
    inputs=[]
    for name in gate.read_genome_list(listing):
        path=Path(name).expanduser()
        if not path.is_absolute():path=listing.parent/path
        path=path.resolve()
        if not path.is_file():raise ValueError('TREE_INPUT_UNAVAILABLE: '+str(path))
        inputs.append({'tip':gate.tip_from_genome_path(path),'path':str(path),'sha256':digest(path)})
    tips=[row['tip'] for row in inputs]
    if not tips or len(set(tips))!=len(tips):raise ValueError('TREE_INPUT_TIP_IDENTITY_AMBIGUOUS')
    queries=gate.declared_query_tips(tips,payload)
    if not queries or not set(queries).issubset(tips):raise ValueError('TREE_QUERY_DECLARATION_UNBOUND')
    return {'schema':'sapote.build-tree-inputs.v1','genome_list':str(listing),'genome_list_sha256':digest(listing),
            'tree_spec':str(spec),'tree_spec_sha256':digest(spec),'queries':sorted(queries),'inputs':inputs,
            'allow_reference_drop':payload.get('allow_reference_drop') is True}


def check(binding_path,genome_list,tree_spec,out_dir,gate,final_tree=None):
    recorded=json.loads(Path(binding_path).read_text())
    actual=input_binding(genome_list,tree_spec,gate)
    if actual!=recorded:return {'status':'TREE_INPUT_BINDING_CHANGED','dropped':[],'unexpected':[]}
    retained = gate.gtotree_retained_tips(out_dir)
    if final_tree:
        from Bio import Phylo
        parsed = Phylo.read(final_tree, 'newick')
        tips = [tip.name for tip in parsed.get_terminals()]
        if any(not isinstance(name, str) or not name for name in tips) or len(tips) != len(set(tips)):
            raise ValueError('FINAL_TREE_TIP_IDENTITY_AMBIGUOUS')
        retained = set(tips)
    result=gate.tip_retention([row['tip'] for row in actual['inputs']],retained,
                             set(actual['queries']),str(out_dir),allow_reference_drop=actual['allow_reference_drop'])
    if final_tree:
        result['final_tree']={'path':str(Path(final_tree).resolve()),'sha256':digest(final_tree)}
    if result['unexpected']:
        result['status']='TREE_TIP_UNEXPECTED'
    result['source_binding']=actual
    if result['dropped']:gate.write_dropped_by_qc(str(Path(out_dir).parent/'DROPPED_BY_QC.tsv'),result)
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--genome-list',required=True);ap.add_argument('--tree-spec',required=True)
    ap.add_argument('--binding',required=True);ap.add_argument('--out-dir');ap.add_argument('--final-tree');ap.add_argument('--bind',action='store_true')
    ap.add_argument('--gate',default=str(Path(__file__).with_name('gtotree_execution_gate.py')))
    a=ap.parse_args(argv);rc=0
    try:
        gate=load_gate(a.gate)
        if a.bind:
            binding=input_binding(a.genome_list,a.tree_spec,gate)
            Path(a.binding).write_text(json.dumps(binding,indent=2)+'\n')
            result={'status':'TREE_INPUTS_BOUND','source_binding':binding}
        else:
            if not a.out_dir:ap.error('--out-dir is required for retention check')
            result=check(a.binding,a.genome_list,a.tree_spec,a.out_dir,gate,a.final_tree)
            if result['status'] not in ('TIPS_RETAINED','REFERENCE_TIP_DROPPED_ALLOWED'):rc=5
    except Exception as exc:
        result={'status':'TREE_RETENTION_GATE_REFUSED','error':str(exc)};rc=3
    receipt=Path(a.binding).with_name('tree_retention_status.json')
    receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return rc

if __name__=='__main__':raise SystemExit(main())
