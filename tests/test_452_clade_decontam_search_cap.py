"""A sixth reference contig contributes to the documented summed-bitscore decision."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace


def test_sixth_subject_changes_sum(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location('decontam_cap', Path(__file__).resolve().parents[1] / 'deliverable_tools/clade_decontam.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, '_p16'):
        monkeypatch.setattr(mod._p16, 'blastdb_sequence_count', lambda *a: 6)

    def fake(cmd, **kw):
        if cmd[0] == 'makeblastdb':
            return SimpleNamespace(returncode=0, stdout='', stderr='')
        n = int(cmd[cmd.index('-max_target_seqs') + 1])
        return SimpleNamespace(stdout=''.join(f'Q1\tR{i}\t99\t100\t100\n' for i in range(min(n, 6))))

    monkeypatch.setattr(mod.subprocess, 'run', fake)
    got = mod.summed_bitscores_vs_ref('query', 'ref', 'blastn', 'makeblastdb', str(tmp_path))
    assert got == {'Q1': 600}
