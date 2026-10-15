"""An eligible sixth CDS survives filtering before reciprocal-best-hit selection."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace


def test_sixth_subject_survives_coverage_filter(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location('nt_cap', Path(__file__).resolve().parents[1] / 'deliverable_tools/clade_nt_core_bgc.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, '_p16'):
        monkeypatch.setattr(mod._p16, 'blastdb_sequence_count', lambda *a: 6)

    def fake(cmd, **kw):
        if cmd[0] == 'makeblastdb':
            return SimpleNamespace(stdout='')
        n = int(cmd[cmd.index('-max_target_seqs') + 1])
        text = ''.join(f'Q1\tR{i}\t99\t10\t100\t100\t9\t100\n' for i in range(5))
        if n >= 6:
            text += 'Q1\tR6\t99\t100\t100\t100\t99\t99\n'
        return SimpleNamespace(stdout=text)

    monkeypatch.setattr(mod.subprocess, 'run', fake)
    got = mod._blastn_dir('query', 'ref', 'blastn', 'makeblastdb', str(tmp_path))
    assert mod.best_hits(got) == {'Q1': 'R6'}
