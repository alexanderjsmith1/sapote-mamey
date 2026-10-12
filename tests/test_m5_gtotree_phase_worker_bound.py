"""Independent known-answer requested-worker bounds; no native computation.

The inherited fabricated runtime is explicitly test-only software authority.
Positive/negative expectations below are fixed examples derived from independent
source review, not calculated by duplicating the production formula.
"""
import json
from pathlib import Path
import pytest
from tests.test_m5_gtotree_runtime_admission import (
    synthetic, make_plan, rt, versions, watch_owner,
)


def with_observed_cpus(synthetic, monkeypatch, count):
    original = synthetic.watched
    def watched(command, **kwargs):
        result = original(command, **kwargs)
        path = Path(command[-1]) / 'IMPORT_ORIGINS.json'
        record = json.loads(path.read_text())
        record['available_cpu_count_observed'] = count
        path.write_text(json.dumps(record))
        return result
    monkeypatch.setattr(watch_owner, 'run_watched', watched)
    return synthetic.prove()


@pytest.mark.parametrize('threads,jobs,budget,cpus,hmm,muscle,phase', [
    (1, 1, 2, 8, 2, 1, 2),
    (3, 2, 6, 8, 4, 6, 6),
    (2, 3, 6, 8, 6, 6, 6),
    (4, 3, 12, 16, 6, 12, 12),
    (8, 1, 8, 8, 2, 8, 8),
])
def test_independent_known_answer_positive_phase_workers(
        synthetic, monkeypatch, threads, jobs, budget, cpus, hmm, muscle, phase):
    proof = with_observed_cpus(synthetic, monkeypatch, cpus)
    contract = versions.resource_contract('2.0.0', threads, jobs,
                                         verified_runtime=proof, cpu_budget=budget)
    assert contract['status'] == 'PASS_SOURCE_BOUND_RESOURCE_PROFILE'
    assert contract['maximum_parallel_search_threads'] == hmm
    assert contract['maximum_parallel_muscle_threads'] == muscle
    assert contract['phase_requested_threads'] == phase
    assert contract['muscle_threads'] == threads
    assert contract['cpu_count_observed'] == cpus
    assert contract['native_execution_validated'] is False


@pytest.mark.parametrize('threads,jobs,budget,cpus', [
    (3, 2, 4, 8),    # six concurrent MUSCLE workers do not fit budget four
    (4, 3, 10, 16),  # twelve workers exceed caller budget ten
    (4, 3, 12, 10),  # budget twelve cannot exceed ten observed CPUs for this phase
    (1, 6, 10, 16),  # HMM phase still independently requires twelve workers
    (4, 4, 16, 10),  # larger explicit budget cannot authorize sixteen on ten CPUs
])
def test_independent_known_answer_budget_and_available_cpu_refusals(
        synthetic, monkeypatch, threads, jobs, budget, cpus):
    proof = with_observed_cpus(synthetic, monkeypatch, cpus)
    with pytest.raises(ValueError, match='CPU_BUDGET'):
        versions.resource_contract('2.0.0', threads, jobs,
                                   verified_runtime=proof, cpu_budget=budget)
    assert len(synthetic.calls) == 1  # software-only fake probe, no native launch


def test_actual_planner_uses_shared_phase_bound_for_concurrent_trees(synthetic, monkeypatch):
    root, proof, iqtree = make_plan(synthetic, monkeypatch, threads=3, cpu_budget=4)
    manifest = json.loads((root / 'RUN_MANIFEST.json').read_text())
    policy = manifest['resource_policy']
    assert policy['gtotree_jobs'] == 1
    assert policy['muscle_threads'] == 3
    assert policy['phase_requested_threads'] == 3
    assert policy['max_concurrent_trees'] == 1
    assert policy['gtotree_resource_contract']['maximum_parallel_muscle_threads'] == 3
