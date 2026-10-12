"""Direct governed-runner CPU admission; synthetic software transport only."""
import pytest
from tests.test_m5_gtotree_runtime_admission import synthetic, put, rt, runner


@pytest.mark.parametrize('iq_threads,budget,refused', [(9, 9, True), (8, 7, True), (8, 8, False)])
def test_direct_runner_iqtree_bound_by_budget_and_observed_cpu(synthetic, monkeypatch, capsys,
                                                               iq_threads, budget, refused):
    # The independently synthetic software probe reports eight available CPUs.
    # GToTree requests only two (one job, one MUSCLE thread); this cannot admit IQ9.
    proof = synthetic.prove()
    assert proof.contract('2.0.0', 1, 1, cpu_budget=budget)['cpu_count_observed'] == 8
    monkeypatch.setattr(rt, 'runtime_from_arguments', lambda args, binary: proof)
    iq = put(synthetic.root / 'iqtree', 'SYNTHETIC_IQTREE'); iq.chmod(0o755)
    genome = put(synthetic.root / 'SYNTHETIC_REFERENCE.fna', '>SYNTHETIC_REFERENCE\nACGT\n')
    genomes = put(synthetic.root / 'genomes.txt', str(genome) + '\n')
    work = synthetic.root / 'fresh_direct_output'
    reached_hmm = []
    class ReachedLaterHMMPreflight(Exception):
        pass
    def later_hmm(*args, **kwargs):
        reached_hmm.append(True)
        raise ReachedLaterHMMPreflight
    monkeypatch.setattr(runner, 'resolve_hmm', later_hmm)
    monkeypatch.setattr(runner, 'run', lambda *args, **kwargs: pytest.fail('unwatched native child'))
    monkeypatch.setattr(rt.WatchedLaunch, '__call__', lambda *args, **kwargs: pytest.fail('native child'))
    args = ['--approved', '--genome-list', str(genomes), '--workdir', str(work),
        '--outgroup', 'SYNTHETIC_REFERENCE', '--hmm', 'SYNTHETIC_MODEL',
        '--threads', '1', '--parallel', '1', '--iqtree-threads', str(iq_threads),
        '--gtotree-cpu-budget', str(budget), '--gtotree-bin', str(synthetic.e / 'bin/gtotree'),
        '--iqtree-bin', str(iq), '--gtotree-runtime-manifest', str(synthetic.manifest),
        '--gtotree-runtime-environment', str(synthetic.e), '--gtotree-runtime-source', str(synthetic.s)]
    if refused:
        assert runner.main(args) == 3
        assert 'GTOTREE_IQTREE_CPU_BUDGET' in capsys.readouterr().err
        assert reached_hmm == []
    else:
        # CPU8/IQ8/budget8 is admitted by the real runner, then deliberately stops
        # before HMM access/native computation. This is not a successful tree run.
        with pytest.raises(ReachedLaterHMMPreflight):
            runner.main(args)
        assert reached_hmm == [True]
    assert len(synthetic.calls) == 1  # software-only proof, no native watcher call
    assert not work.exists()
