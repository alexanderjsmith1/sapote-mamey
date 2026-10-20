"""Hosted full-profile admission configuration; no hosted run or platform proof."""
from copy import deepcopy
from pathlib import Path
import shlex

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]


def workflow():
    return yaml.load((ROOT/'.github/workflows/ci.yml').read_text(),Loader=yaml.BaseLoader)


def full_profile_contract(data):
    selected=data['on']['workflow_dispatch']['inputs']['run_configured_suite']
    assert selected['type']=='boolean' and selected['default']=='false'
    steps=[s for s in data['jobs']['test']['steps'] if '--run-slow' in s.get('run','')]
    assert len(steps)==1
    step=steps[0]
    assert "github.event_name == 'workflow_dispatch'" in step['if']
    assert 'inputs.run_configured_suite' in step['if']
    assert '&&' in step['if']
    args=shlex.split(step['run'])
    assert args==['python','-B','-m','pytest','-q','-p','no:cacheprovider','--run-slow','--run-network']
    return step


def test_full_profile_requires_explicit_manual_scope():
    full_profile_contract(workflow())


def test_default_ci_retains_fast_partition_and_declared_linux_python():
    data=workflow();job=data['jobs']['test']
    assert job['runs-on']=='ubuntu-latest'
    assert job['strategy']['matrix']['python-version']==['3.12']
    # v9.7.454: the default step runs without bytecode writes (python -B, no cache provider), as the cut does.
    assert any(s.get('run')=='python -B -m pytest -q -p no:cacheprovider' for s in job['steps'])


@pytest.mark.parametrize('mutation',['missing_input','missing_network','automatic_run'])
def test_incomplete_or_unscoped_full_profile_refuses(mutation):
    data=deepcopy(workflow());step=full_profile_contract(data)
    if mutation=='missing_input':del data['on']['workflow_dispatch']['inputs']['run_configured_suite']
    elif mutation=='missing_network':step['run']=step['run'].replace(' --run-network','')
    else:step['if']='true'
    with pytest.raises((AssertionError,KeyError)):
        full_profile_contract(data)


def dependency_contract(project, data):
    """Test tools stay opt-in and the CI test job admits them before collection."""
    import ast
    from packaging.requirements import Requirement
    required = {'pytest', 'build', 'pdfplumber', 'psutil'}
    names = lambda requirements: {Requirement(value).name.lower() for value in requirements}
    extras = project['project']['optional-dependencies']
    assert required <= names(extras['test'])
    assert required.isdisjoint(names(project['project']['dependencies']))
    assert required.isdisjoint(names(extras['all']))
    steps = data['jobs']['test']['steps']
    installs = [step for step in steps if step.get('name') == 'Install']
    assert len(installs) == 1 and 'if' not in installs[0]
    commands = [shlex.split(line, comments=True) for line in installs[0]['run'].splitlines()]
    editables = [args[args.index('-e') + 1] for args in commands if args[:2] == ['pip', 'install'] and '-e' in args]
    assert len(editables) == 1
    assert editables[0].startswith('.[') and editables[0].endswith(']')
    assert {'figures', 'bio', 'documents', 'test'} <= set(editables[0][2:-1].split(','))
    imports = []
    for args in commands:
        if args[:2] == ['python', '-c']:
            imports.append({alias.name for node in ast.walk(ast.parse(args[2])) if isinstance(node, ast.Import) for alias in node.names})
    assert any(required <= imported for imported in imports)


def test_test_tools_are_opt_in_and_ci_imports_them():
    import tomllib
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    dependency_contract(project, workflow())


@pytest.mark.parametrize('mutation', ['missing_pdf', 'missing_psutil', 'core_leak', 'all_leak', 'missing_ci_extra', 'missing_import_probe', 'disabled_install'])
def test_incomplete_test_dependency_admission_refuses(mutation):
    import tomllib
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    data = workflow()
    install = next(step for step in data['jobs']['test']['steps'] if step.get('name') == 'Install')
    if mutation == 'missing_pdf': project['project']['optional-dependencies']['test'].remove('pdfplumber')
    elif mutation == 'missing_psutil': project['project']['optional-dependencies']['test'].remove('psutil')
    elif mutation == 'core_leak': project['project']['dependencies'].append('pdfplumber')
    elif mutation == 'all_leak': project['project']['optional-dependencies']['all'].append('psutil')
    elif mutation == 'missing_ci_extra': install['run'] = install['run'].replace('documents,test]', 'documents]')
    elif mutation == 'missing_import_probe': install['run'] = '\n'.join(line for line in install['run'].splitlines() if 'python -c' not in line)
    else: install['if'] = 'false'
    with pytest.raises(AssertionError):
        dependency_contract(project, data)
