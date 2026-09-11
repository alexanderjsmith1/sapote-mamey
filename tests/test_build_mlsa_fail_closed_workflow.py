"""Real subprocess stubs exercise stop-on-failure and output isolation without companions."""
import importlib.util
import json
from pathlib import Path
import sys
import shlex
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mlsa_workflow", ROOT / "tools/build_mlsa.py")
mlsa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mlsa)

STUB = r"""
import json, os, pathlib, shutil, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
def value(flag): return args[args.index(flag)+1]
with open(os.environ['CALL_LOG'], 'a') as fh:
    fh.write(json.dumps({'tool': name, 'args': args, 'cwd': os.getcwd()})+'\n')
fail = os.environ.get('FAIL_TOOL') == name
empty = os.environ.get('EMPTY_TOOL') == name
if name == 'prodigal':
    pathlib.Path(value('-a')).write_text('' if empty else '>gene\nMPEP\n')
    pathlib.Path(value('-d')).write_text('' if empty else '>gene\nATGCCCGAACCC\n')
elif name == 'makeblastdb':
    assert not any(c.isspace() for c in value('-out'))
    assert not any(c.isspace() for c in value('-in'))
    assert pathlib.Path(value('-in')).is_file()
    pathlib.Path(value('-out')+'.pin').write_text('db')
elif name == 'blastp':
    assert not any(c.isspace() for c in value('-db'))
    assert pathlib.Path(value('-db')+'.pin').is_file()
    assert pathlib.Path(value('-query')).is_file()
    if os.environ.get('BAD_BLAST'):
        sys.stdout.write('unknown\t99\t4\t0\t20\n')
    elif not fail and not os.environ.get('NO_HIT'):
        sys.stdout.write('gene\t99\t4\t0\t20\n')
elif name == 'muscle':
    shutil.copyfile(value('-align'),value('-output'))
    if empty: pathlib.Path(value('-output')).write_text('')
elif name == 'iqtree':
    if not empty: pathlib.Path(value('-pre')+'.treefile').write_text('(a:1,b:1);\n')
if fail:
    sys.stderr.write('forced tool failure with partial output\n')
    sys.exit(9)
"""



def _write_python_stub(path, body):
    # A kernel shebang cannot quote an interpreter path containing spaces.
    # Use a shell/Python polyglot so argv[0] remains the actual tool pathname.
    prefix = "#!/bin/sh\n'''exec' " + shlex.quote(sys.executable) + ' "$0" "$@"\n' + "' '''\n"
    path.write_text(prefix + body)
    path.chmod(0o755)


def test_python_stub_preserves_interpreter_path_and_literal_arguments(tmp_path, monkeypatch):
    interpreter = tmp_path / "python with spaces and ' quote"
    interpreter.symlink_to(sys.executable)
    monkeypatch.setattr(sys, 'executable', str(interpreter))
    tool = tmp_path / 'tool with spaces'
    _write_python_stub(tool, 'import json, sys; print(json.dumps(sys.argv))\n')
    argument = 'literal $HOME; $(false) with spaces'
    result = subprocess.run([str(tool), argument], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [str(tool), argument]


@pytest.fixture
def run(tmp_path, monkeypatch):
    bins = tmp_path / 'binary directory'; bins.mkdir()
    for name in mlsa._BIN_ALIASES:
        f = bins / name
        _write_python_stub(f, STUB)
        f.chmod(0o755)
    genomes = tmp_path / 'genome inputs'; genomes.mkdir()
    for i in range(4): (genomes / f'genome {i}.fna').write_text('>contig\nACGT\n')
    seeds = tmp_path / 'seed inputs'; seeds.mkdir()
    for locus in mlsa.LOCI: (seeds / (locus+'.faa')).write_text('>seed\nMPEP\n')
    calls = tmp_path / 'calls.jsonl'
    monkeypatch.setenv('CALL_LOG', str(calls))
    out = tmp_path / 'run with spaces'
    def invoke():
        return mlsa.main([str(genomes), str(out), '--bin-dir', str(bins), '--seeds-dir', str(seeds)])
    return invoke, out, calls


@pytest.mark.parametrize('tool', ['prodigal','makeblastdb','blastp','muscle','iqtree'])
def test_first_tool_failure_stops_pipeline_with_diagnostics(run, monkeypatch, tool):
    invoke, out, calls = run
    monkeypatch.setenv('FAIL_TOOL',tool)
    assert invoke() != 0
    observed = [json.loads(line)['tool'] for line in calls.read_text().splitlines()]
    assert observed[-1] == tool and observed.count(tool) == 1
    status = json.loads((out/'run_status.json').read_text())
    assert status['status'] == 'FAILED' and 'TOOL_FAILURE' in status['detail']
    log = (out/'mlsa.log').read_text()
    assert 'forced tool failure' in log and 'TREE_OK' not in log
    if tool in {'prodigal','makeblastdb','blastp'}:
        assert not (out/'loci_report.tsv').exists()


def test_success_uses_space_safe_relative_blast_inputs(run):
    invoke, out, calls = run
    assert invoke() == 0
    assert json.loads((out/'run_status.json').read_text())['status'] == 'COMPLETE'
    blast = [json.loads(line) for line in calls.read_text().splitlines() if 'blast' in json.loads(line)['tool']]
    assert blast and all(Path(call['cwd']) == out/'blastdb' for call in blast)
    assert 'HIT' in (out/'loci_report.tsv').read_text()
    assert 'genome%200\tgenome 0.fna' in (out/'taxon_map.tsv').read_text()
    assert '>genome%200' in (out/'aln/supermatrix.fasta').read_text()


def test_stale_run_refused_without_reuse_or_overwrite(run):
    invoke, out, calls = run
    out.mkdir(); (out/'tree.treefile').write_text('stale')
    assert invoke() != 0
    assert (out/'tree.treefile').read_text() == 'stale' and not calls.exists()


def test_no_hit_is_successful_search_not_tool_failure(run, monkeypatch):
    invoke, out, calls = run; monkeypatch.setenv('NO_HIT','1')
    assert invoke() != 0  # no usable partitions is a data refusal
    assert 'NO_HIT' in (out/'loci_report.tsv').read_text()
    detail = json.loads((out/'run_status.json').read_text())['detail']
    assert 'NO_USABLE_DATA' in detail and 'TOOL_FAILURE' not in detail
    assert not any(json.loads(line)['tool'] in {'muscle','iqtree'} for line in calls.read_text().splitlines())


@pytest.mark.parametrize('tool', ['prodigal','muscle','iqtree'])
def test_exit_zero_with_empty_or_missing_output_fails(run, monkeypatch, tool):
    invoke, out, calls = run; monkeypatch.setenv('EMPTY_TOOL',tool)
    assert invoke() != 0
    assert 'OUTPUT_INVALID' in json.loads((out/'run_status.json').read_text())['detail']
    assert 'TREE_OK' not in (out/'mlsa.log').read_text()


def test_blast_subject_missing_from_cds_is_failure(run, monkeypatch):
    invoke, out, calls = run; monkeypatch.setenv('BAD_BLAST','1')
    assert invoke() != 0
    assert 'missing from CDS' in (out/'mlsa.log').read_text()


def test_invalid_fasta_header_fails_with_a_typed_error(tmp_path):
    path=tmp_path/'broken.faa';path.write_text('>\nMPEP\n')
    with pytest.raises(ValueError,match='OUTPUT_INVALID'):
        mlsa._checked_fasta(path)
