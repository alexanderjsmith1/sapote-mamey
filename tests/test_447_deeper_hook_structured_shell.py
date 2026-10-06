"""Bounded shell analysis only; command payloads are never executed."""
import json,os,subprocess
from pathlib import Path
import pytest
ROOT=Path(os.environ.get('SAPOTE_DEEP_TARGET',str(Path(__file__).resolve().parents[1])))
OUT='/etc/ssl'

def denied(command,project,variables=None):
 p=subprocess.run(['python3',str(ROOT/'hooks/block_out_of_bounds_writes.py')],input=json.dumps({'tool_name':'Bash','cwd':str(project),'tool_input':{'command':command}}),text=True,capture_output=True,env={**os.environ,'SAPOTE_WORKSPACE_ROOT':str(project),'CLAUDE_PROJECT_DIR':str(project),**(variables or {})})
 assert p.returncode==0,p.stderr
 return bool(p.stdout.strip()) and json.loads(p.stdout)['hookSpecificOutput']['permissionDecision']=='deny'

@pytest.mark.parametrize('command',[
 'if true; then cd {out}; fi; touch x',
 'if test -e flag; then cd {out}; else cd {project}; fi; touch x',
 'if false; then echo skipped; elif true; then cd {out}; fi; touch x',
 'if true; then if true; then cd {out}; fi; fi; touch x',
 'for DIR in {out}; do cd "$DIR"; done; touch x',
 'for DIR in sub {out}; do touch "$DIR/x"; done',
 'for DIR; do cd "$DIR"; done; touch x',
 'while test -e flag; do touch x; cd ..; done',
 'until test -e flag; do cd ..; touch x; done',
 'f() {{ cd {out}; }}; f; touch x',
 'function f {{ cd {out}; }}; f; touch x',
 'outer() {{ inner() {{ cd {out}; }}; inner; }}; outer; touch x',
 'if test -e flag; then f() {{ cd {out}; }}; else f() {{ cd {project}; }}; fi; f; touch x',
 'DEST={out}; if true; then DEST={project}; fi >"$DEST/log"',
 'DEST={out}; {{ DEST={project}; }} >"$DEST/log"',
 'f() {{ :; }} >{out}/log; f',
 'DEST={out}; f() {{ local DEST={project}; }}; f; touch "$DEST/x"',
 'DEST={out}; f() {{ declare DEST={project}; }}; f; touch "$DEST/x"',
 'f() {{ touch "$DEST/x"; }}; DEST={out} f',
 'f() {{ f; }}; f',
])
def test_structured_outside_or_unresolved_writes_are_held(command,tmp_path):
 (tmp_path/'sub').mkdir()
 assert denied(command.format(out=OUT,project=str(tmp_path)),tmp_path)

@pytest.mark.parametrize('command',[
 'if true; then touch local; else touch other; fi',
 'if false; then touch {out}/unreachable; else touch local; fi',
 'for DIR in sub .; do touch "$DIR/x"; done',
 'for DIR in; do touch {out}/unreachable; done',
 'while false; do touch {out}/unreachable; done; touch local',
 'until true; do touch {out}/unreachable; done; touch local',
 'f() {{ touch {out}/unused; }}; echo untouched',
 'f() {{ touch local; }}; f',
 'f() {{ cd {out}; }}; echo untouched',
 'f() {{ cd {out}; }}; (f); touch local',
 'f() (cd {out}); f; touch local',
 'DEST={project}; f() {{ local DEST={out}; }}; f; touch "$DEST/x"',
 'DEST={project}; f() {{ declare DEST={out}; }}; f; touch "$DEST/x"',
 'f() {{ :; }} >{out}/unused; echo unused',
 'f() {{ cd {out}; }}; f() {{ cd {project}; }}; f; touch local',
 'if test -e flag; then touch one; else touch two; fi | cat; touch local',
 '{{ cd {out}; }} | cat; touch local',
 'if true; then cd {out}; fi & touch local',
 'if true; then echo "then fi do done"; fi; touch local',
 'echo "if true; then touch {out}/literal; fi" >local',
])
def test_local_unreachable_unused_and_scoped_controls(command,tmp_path):
 (tmp_path/'sub').mkdir()
 assert not denied(command.format(out=OUT,project=str(tmp_path)),tmp_path)

@pytest.mark.parametrize('command',[
 'DEST={project}; for X; do touch "$DEST/x"; DEST={out}; done',
 'DEST={project}; while test -e flag; do touch "$DEST/x"; DEST={out}; done',
 'eval "cd {out}"; touch x',
 'source local.sh; touch x',
 'trap "cd {out}" DEBUG; touch x',
 'shopt -s lastpipe; echo x | cd {out}; touch x',
])
def test_later_iterations_and_opaque_state_changes_are_held(command,tmp_path):
 assert denied(command.format(project=str(tmp_path),out=OUT),tmp_path)

@pytest.mark.parametrize('command',[
 'eval "echo harmless"',
 'source local.sh; ls',
 'shopt -s lastpipe; echo x | cat; touch local',
 'shopt -u lastpipe; echo x | cd {out}; touch local',
 'f() {{ touch {out}/unused; }}; unset -f f; f',
 'DEST={project}; f() {{ local -a DEST; }}; f; touch "$DEST/x"',
])
def test_state_mutation_read_only_and_scope_controls(command,tmp_path):
 assert not denied(command.format(project=str(tmp_path),out=OUT),tmp_path)

@pytest.mark.parametrize('command',[
 'f() {{ cd {out}; }}; f | cat; touch local',
 'f() {{ cd {out}; }}; echo x | f; touch local',
 'f() {{ cd {out}; }}; f & touch local',
 'shopt -s lastpipe; f() {{ cd {out}; }}; f | cat; touch local',
 'shopt -u lastpipe; echo x | {{ cd {out}; }}; touch local',
])
def test_function_and_compound_pipeline_scope_controls(command,tmp_path):
 assert not denied(command.format(out=OUT),tmp_path)

@pytest.mark.parametrize('command',[
 'shopt -s lastpipe; f() {{ cd {out}; }}; echo x | f; touch local',
 'shopt -s lastpipe; echo x | {{ cd {out}; }}; touch local',
])
def test_lastpipe_function_and_compound_writes_are_held(command,tmp_path):
 assert denied(command.format(out=OUT),tmp_path)

def test_nested_analysis_work_is_bounded(tmp_path):
 values=' '.join(str(i) for i in range(64))
 body='for A in '+values+'; do for B in '+values+'; do echo safe; done; done'
 assert denied(body,tmp_path)

@pytest.mark.parametrize('declaration',['local DEST','declare DEST','typeset DEST'])
def test_new_bare_function_local_does_not_keep_caller_value(tmp_path,declaration):
 assert denied(f'DEST="{tmp_path}"; f() {{ {declaration}; touch "$DEST/x"; }}; f',tmp_path)

@pytest.mark.parametrize('declaration',['local -I DEST','declare -I DEST','shopt -s localvar_inherit; local DEST'])
def test_unbound_runtime_local_inheritance_is_held(tmp_path,declaration):
 assert denied(f'DEST="{tmp_path}"; f() {{ {declaration}; touch "$DEST/x"; }}; f',tmp_path)

def test_bound_startup_local_inheritance_control(tmp_path):
 assert not denied(f'DEST="{tmp_path}"; f() {{ local DEST; touch "$DEST/x"; }}; f',tmp_path,{'BASHOPTS':'localvar_inherit'})

@pytest.mark.parametrize('command',[
 'DEST={out}; f() {{ local DEST={project}; local DEST; touch "$DEST/x"; }}; f',
 'DEST={project}; f() {{ declare -p DEST; touch "$DEST/x"; }}; f',
 'DEST={project}; f() {{ local DEST={project}; DEST+=/sub; }}; f; touch "$DEST/x"',
])
def test_repeated_local_listing_and_local_append_restore_controls(tmp_path,command):
 assert not denied(command.format(project=str(tmp_path),out=OUT),tmp_path)

def test_disabled_local_inheritance_and_combined_global_flags(tmp_path):
 assert denied(f'DEST="{tmp_path}"; shopt -s localvar_inherit; shopt -u localvar_inherit; f() {{ local DEST; touch "$DEST/x"; }}; f',tmp_path)
 assert denied(f'DEST="{tmp_path}"; f() {{ declare -gx DEST={OUT}; }}; f; touch "$DEST/x"',tmp_path)

def test_declaration_initializers_expand_before_local_binding(tmp_path):
 assert not denied(f'DEST="{tmp_path}"; f() {{ local DEST="$DEST"; touch "$DEST/x"; }}; f',tmp_path)

def test_declaration_arguments_share_the_pre_command_expansion_state(tmp_path):
 assert denied(f'DEST={OUT}; declare DEST="{tmp_path}" OTHER="$DEST"; touch "$OTHER/x"',tmp_path)
 assert not denied(f'DEST="{tmp_path}"; declare DEST={OUT} OTHER="$DEST"; touch "$OTHER/x"',tmp_path)
