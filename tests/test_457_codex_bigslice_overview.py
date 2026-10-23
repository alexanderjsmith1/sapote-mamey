import pytest
from tools.bigslice_overview_figure import validate,CATS

def make(tmp_path,bad=False):
    a=['collection\tcategory\tregions\ttotal_regions']
    b=['collection\tstrain\tcontig\tregion\tdistance']
    for coll in ('bee_wasp','moss','attine'):
        for cat in sorted(CATS):a.append(f'{coll}\t{cat}\t{1 if cat=="reference_family" else 0}\t{2 if bad else 1}')
        b.append(f'{coll}\tSYN_{coll}\tSYN_contig\tregion001\t0.5')
    (tmp_path/'panelA_data.tsv').write_text('\n'.join(a)+'\n')
    (tmp_path/'panelB_isolate.tsv').write_text('\n'.join(b)+'\n')
    (tmp_path/'panelB_background.tsv').write_text('source\tdistance\nisolate\t0.5\nisolate\t0.5\nisolate\t0.5\nreference\t0.9\n')

def test_mutually_exclusive_categories_and_distance_parity(tmp_path):
    make(tmp_path);assert len(validate(tmp_path))==3

def test_denominator_conflict_refuses(tmp_path):
    make(tmp_path,True)
    with pytest.raises(ValueError):validate(tmp_path)
