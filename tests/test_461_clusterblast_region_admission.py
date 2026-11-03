"""Invalid inventory region tokens must not bind another exact region key."""
import importlib.util
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('clusterblast_region_control', ROOT / 'tools' / 'rank_clusterblast_phylo_candidates.py')
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def inventory(path, region):
    path.write_text('BGC_ID,Contig,Region\nSYNTHETIC_BGC,SYNTHETIC_CONTIG,' + region + '\n')


@pytest.mark.parametrize('region', ['1.5', '1.0000000000000001', 'nan', 'inf', '-inf', 'bad', '1e100000000'])
def test_invalid_region_refused(tmp_path, region):
    path = tmp_path / 'inventory.csv'
    inventory(path, region)
    with pytest.raises(mod.CandidateError, match='region'):
        mod.inventory_region_map(path)


@pytest.mark.parametrize('region', ['1', '001', '1.0', '1e0'])
def test_exact_integer_forms_preserve_key(tmp_path, region):
    path = tmp_path / 'inventory.csv'
    inventory(path, region)
    mapping, count = mod.inventory_region_map(path)
    assert count == 1
    assert mapping == {'SYNTHETIC_CONTIG_c1': 'SYNTHETIC_BGC'}


def test_invalid_region_refused_before_output_directory(tmp_path):
    path = tmp_path / 'inventory.csv'
    inventory(path, '1.5')
    archive = tmp_path / 'input.zip'
    with zipfile.ZipFile(archive, 'w') as out:
        out.writestr('input.fna', '>synthetic\nAAAA\n')
    manifest = tmp_path / 'manifest.tsv'
    manifest.write_text('strain_id\tcohort\tantismash_zip\tassembly_member\tbgc_inventory_csv\n'
                        f'SYNTHETIC_STRAIN\tfixture\t{archive}\tinput.fna\t{path}\n')
    output = tmp_path / 'result'
    assert mod.main([str(manifest), str(output)]) == 2
    assert not output.exists()
