"""Reference operands are reads; actual targets and redirects remain writes.
Only the static parser is called; shell payloads are never executed.
"""
import importlib.util
import os
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reference_guard', ROOT/'hooks/block_out_of_bounds_writes.py')
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

@pytest.mark.parametrize('verb', ['touch', 'truncate'])
@pytest.mark.parametrize('option', ['-r /outside/reference', '--reference /outside/reference',
    '--reference=/outside/reference', '-r/outside/reference', '-r "/outside/ref with spaces"'])
def test_reference_is_read_only(verb, option):
    paths=guard.bash_write_targets(f'{verb} {option} ./local', cwd='/allowed')
    assert [os.path.normpath(p) for p in paths]==['/allowed/local']

@pytest.mark.parametrize('command', ['touch -ar /outside/reference ./local',
    'touch -cmr /outside/reference ./local', 'truncate -cr /outside/reference ./local'])
def test_no_argument_flags_can_precede_reference(command):
    assert [os.path.normpath(p) for p in guard.bash_write_targets(command,cwd='/allowed')]==['/allowed/local']

@pytest.mark.parametrize('verb', ['touch', 'truncate'])
def test_read_operand_does_not_hide_an_outside_write_or_redirect(verb):
    paths=guard.bash_write_targets(f'{verb} -r ./reference /outside/target > /outside/log',cwd='/allowed')
    assert set(paths)=={'/outside/target','/outside/log'}

def test_attached_reference_does_not_eat_next_target():
    assert guard.bash_write_targets('touch -ra /outside/target',cwd='/allowed')==['/outside/target']

@pytest.mark.parametrize('verb', ['touch', 'truncate'])
def test_option_termination_keeps_reference_looking_targets(verb):
    assert [os.path.normpath(p) for p in guard.bash_write_targets(f'{verb} -- -r /outside/target',cwd='/allowed')]==['/allowed/-r','/outside/target']

@pytest.mark.parametrize('command', ['touch -r', 'truncate --reference', 'touch -ar'])
def test_missing_reference_operand_is_held(command):
    with pytest.raises(guard.UnresolvedShellPath,match='reference option has no operand'):
        guard.bash_write_targets(command,cwd='/allowed')

def test_other_command_options_do_not_acquire_reference_semantics():
    assert guard.bash_write_targets('rm -r /outside/target',cwd='/allowed')==['/outside/target']

@pytest.mark.parametrize('verb', ['touch', 'truncate'])
@pytest.mark.parametrize('option', ['-r {value}', '--reference {value}', '--reference={value}', '-r{value}'])
@pytest.mark.parametrize('value', ['"$(touch /outside/target)"', '"`touch /outside/target`"'])
def test_active_substitution_in_reference_is_held(verb,option,value):
    with pytest.raises(guard.UnresolvedShellPath):
        guard.bash_write_targets(verb+' '+option.format(value=value)+' ./local',cwd='/allowed')

def test_single_quoted_substitution_is_a_literal_read():
    command="touch -r '$(touch /outside/target)' ./local"
    assert [os.path.normpath(p) for p in guard.bash_write_targets(command,cwd='/allowed')]==['/allowed/local']

def test_bound_variable_reference_is_read_only():
    paths=guard.bash_write_targets('touch -r "$REFERENCE" ./local',cwd='/allowed',initial_variables={'REFERENCE':'/outside/ref'})
    assert [os.path.normpath(p) for p in paths]==['/allowed/local']
