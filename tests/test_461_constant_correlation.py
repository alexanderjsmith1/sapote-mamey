"""Synthetic software fixtures only; no rendering or cohort inference."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import numpy as np
import pytest

TARGET=Path(__file__).resolve().parents[1]/'tools/build_normalization_matrix.py'
spec=importlib.util.spec_from_file_location('normalization_under_test',TARGET)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def rows(counts,contigs=None):
    contigs=contigs or [2**i for i in range(len(counts))]
    out=[]
    for i,(count,contig) in enumerate(zip(counts,contigs)):
        r={'sid':f'SYN-{i}','organism':'software fixture','contigs':contig,'raw_BGC':20+i,'corrected_BGC':20+i,'genome_Mbp':8+i,'den_ecto+napaa':1,'den_terpene':1,'den_halogenase':1}
        r.update({f'cls_{c}':0 for c in mod.CLASSES});r['cls_NRPS']=count;out.append(r)
    return out


@pytest.mark.parametrize('counts,contigs',[([1]*12,None),([2]*12,None),([1]*12,[10]*12),([5],[10])])
def test_constant_class_correlation_unmeasurable(counts,contigs):
    data=rows(counts,contigs);before=copy.deepcopy(data)
    ranking,matrix,_=mod.derive(data)
    assert ranking[0]['corr_fragmentation']==''
    assert ranking[0]['regime']==mod.NOT_MEASURABLE
    assert matrix[0]['raw']==''
    assert data==before


def test_constant_class_normalization_cells_unchanged_blank():
    ranking,matrix,_=mod.derive(rows([1]*12))
    assert all(value=='' for key,value in matrix[0].items() if key!='class')


@pytest.mark.parametrize('counts',[list(range(1,13)),list(range(12,0,-1)),[1,3,2,5,4,3,1,2,4,5,2,3]])
def test_nonconstant_correlation_formula_unchanged(counts):
    data=rows(counts);ranking,matrix,_=mod.derive(data)
    expected=float(np.corrcoef(np.array(counts,float),np.log10([r['contigs'] for r in data]))[0,1])
    assert ranking[0]['corr_fragmentation']==round(expected,3)
    assert ranking[0]['regime']==mod.regime_of(expected)
    assert matrix[0]['raw']==round(expected,3)


def test_low_total_class_still_excluded():
    assert mod.derive(rows([0,1,0,1]))[0:2]==([],[])


def test_undefined_rows_sort_last_and_serialize_as_blank(tmp_path):
    import csv
    data=rows([1]*12)
    for i,row in enumerate(data):
        row['cls_T1PKS']=i+1
    ranking,matrix,dens=mod.derive(data)
    assert ranking[-1]['class']==matrix[-1]['class']=='NRPS'
    path=tmp_path/'synthetic_ranking.csv'
    mod.write_csv(str(path),ranking,['class','n_total','corr_fragmentation','regime'])
    with path.open() as handle:
        serialized=list(csv.DictReader(handle))
    assert serialized[-1]['corr_fragmentation']==''
    assert serialized[-1]['regime']=='not measurable'
