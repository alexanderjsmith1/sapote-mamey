"""BOMs must not hide comment banners or disable provenance column checks."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools' / 'check_provenance_columns.py'

@pytest.mark.parametrize('bom', ['', '\ufeff'])
@pytest.mark.parametrize('banner', ['', '# provenance,software fixture\n', '  # provenance,software fixture\n# second banner\n'])
@pytest.mark.parametrize('delimiter,suffix', [(',', '.csv'), ('\t', '.tsv'), (',', '.tsv'), ('\t', '.csv')])
@pytest.mark.parametrize('valid', [False, True])
def test_bom_comment_banner_preserves_region_check(tmp_path, bom, banner, delimiter, suffix, valid):
    header = ['strain', 'contig', 'bgc'] + (['region'] if valid else [])
    row = ['engineering_fixture', 'software_contig', 'BGC001'] + (['region001'] if valid else [])
    path = tmp_path / ('fixture' + suffix)
    path.write_text(bom + banner + delimiter.join(header) + '\n' + delimiter.join(row) + '\n', encoding='utf-8')
    result = subprocess.run([sys.executable, '-B', str(SCRIPT), str(path)], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    assert result.returncode == (0 if valid else 1), result.stdout + result.stderr
    if not valid:
        assert 'missing region' in result.stderr
