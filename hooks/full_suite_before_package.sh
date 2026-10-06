#!/usr/bin/env bash
# GUARDRAIL (2026-08-06, after F04/F05): a candidate handoff zip must be gated on a FRESH FULL-suite
# green run — not just a card's focused tests. F04/F05 passed its 18 focused tests but regressed 13
# seal/package tests that only the full suite caught. This PreToolUse(Bash) hook DENIES zipping a
# `candidate_cut_*` handoff unless its source-bound configured-suite receipt matches
# the candidate's current bytes and completed successful canonical profile run
# (-q -p no:cacheprovider --run-slow --run-network). Legacy mtime markers
# do not establish suite scope. Candidate lookup remains a separate bounded policy.
# .402 jq-family port (ROSTER_402 seed #1): payload parse via python3 stdlib, not jq —
# jq is absent in clean/container shells and the silent-empty form disarmed this hook
# there. Same repair shape as bgc_node_name_guard (.401 seal-gate repair).
set -euo pipefail
_fail_closed() {
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Cannot inspect packaging command safely: malformed or unsupported shell input."}}'
  exit 0
}
trap _fail_closed ERR
input=$(cat 2>/dev/null) || input=""
cmd=$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("command") or "")' 2>/dev/null || true)
[ -z "$cmd" ] && exit 0

# H06: share the scoped shell-state evaluator installed beside this hook.
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
inspected=$(printf '%s' "$input" | python3 -c '
import json, os, sys, re
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import block_out_of_bounds_writes as model

MAX_SCAN = 10000
found, steps, writes, concurrent = set(), [0], [], [False]


def note_concurrency(command):
    concurrent[0] |= any(kind == '"'"'op'"'"' and value in ('"'"'|'"'"','"'"'|&'"'"','"'"'&'"'"')
                         for _,value,kind in model.shell_tokens(command))


def expanded(raw, variables):
    value = model._expand_shell_word(raw, variables)
    quote, escaped = None, False
    for char in raw:
        if escaped: escaped = False; continue
        if char == '"'"'\\'"'"' and quote != "'"'"'": escaped = True; continue
        if char in ("'"'"'", '"'"'"'"'"'):
            if quote == char: quote = None
            elif quote is None: quote = char
        elif quote is None and char in '"'"'*?['"'"':
            raise model.UnresolvedShellPath('"'"'package source globbing requires explicit literal sources'"'"')
    return value


def register_candidate(canonical):
    ancestor = next((p for p in (canonical, *canonical.parents)
                     if p.is_dir() and p.name.startswith('"'"'candidate_cut_'"'"')), None)
    if ancestor is None: return False
    for written in writes:
        target = Path(written).resolve()
        if target == ancestor or target in ancestor.parents or ancestor in target.parents:
            raise model.UnresolvedShellPath('"'"'candidate receipt inputs may change earlier in this request: '"'"' + str(written))
    found.add(str(ancestor))
    return ancestor


def resolve_source(raw, bases, variables):
    value = expanded(raw, variables)
    if not value: raise model.UnresolvedShellPath('"'"'empty package source'"'"')
    if os.path.isabs(value): paths = [Path(value)]
    else:
        if not bases: raise model.UnresolvedShellPath('"'"'package source cwd is unresolved'"'"')
        paths = [Path(base) / value for base in bases]
    checked = []
    for path in paths:
        lexical = Path(os.path.abspath(path))
        canonical = path.resolve(strict=True)
        checked.append(canonical)
        for written in writes:
            raw_write = Path(os.path.abspath(written))
            real_write = raw_write.resolve()
            if any(a == b or a in b.parents or b in a.parents
                   for a in (lexical, canonical) for b in (raw_write, real_write)):
                raise model.UnresolvedShellPath('"'"'packaging source may change earlier in this request: '"'"' + str(written))
        ancestor = register_candidate(canonical)
        if ancestor:
            checked.append(ancestor); continue
        if not canonical.is_dir(): continue
        # Archive selection can include candidate trees beneath an ordinary parent.
        queue, seen = [canonical], set()
        while queue:
            directory = queue.pop()
            real = directory.resolve(strict=True)
            if real in seen: continue
            seen.add(real)
            steps[0] += 1
            if steps[0] > MAX_SCAN: raise model.UnresolvedShellPath('"'"'package source scan limit; use explicit candidate paths'"'"')
            ancestor = register_candidate(real)
            if ancestor:
                checked.append(ancestor); continue
            for child in real.iterdir():
                steps[0] += 1
                if steps[0] > MAX_SCAN: raise model.UnresolvedShellPath('"'"'package source scan limit; use explicit candidate paths'"'"')
                if child.is_dir(): queue.append(child)
                elif child.is_symlink():
                    ancestor = register_candidate(child.resolve(strict=True))
                    if ancestor: checked.append(ancestor)
    return checked


def archive_output(raw, bases, variables, checked, verb):
    value = expanded(raw, variables)
    if not value: raise model.UnresolvedShellPath('"'"'empty archive output'"'"')
    if value == '"'"'-'"'"' and verb == '"'"'tar'"'"': return  # standard output; redirects modeled separately
    if os.path.isabs(value): paths = [Path(value)]
    else:
        if not bases: raise model.UnresolvedShellPath('"'"'archive output cwd is unresolved'"'"')
        paths = [Path(base) / value for base in bases]
    # ZIP may append its default suffix. Retain both admitted spellings because
    # overwrite/extension behavior also depends on pre-existing archive names.
    if verb == '"'"'zip'"'"':
        paths += [Path(str(path) + '"'"'.zip'"'"') for path in list(paths) if not str(path).lower().endswith('"'"'.zip'"'"')]
    planned = []
    for path in paths:
        lexical = Path(os.path.abspath(path)); canonical = path.resolve()
        for source in checked:
            if any(output == source or source in output.parents or output in source.parents
                   for output in (lexical, canonical)):
                raise model.UnresolvedShellPath('"'"'archive output intersects packaged source or its bound candidate receipt tree: '"'"' + str(path))
        planned.extend((str(lexical), str(canonical)))
    # Append only after all current sources/output relationships have been checked:
    # these writes can invalidate later creation commands, not earlier commands.
    writes.extend(planned)


def observe(argv, bases, variables, depth=0):
    if depth > 6: raise model.UnresolvedShellPath('"'"'nested package inspection limit'"'"')
    verb = os.path.basename(argv[0][1])
    if verb in ('"'"'bash'"'"','"'"'sh'"'"','"'"'zsh'"'"','"'"'ksh'"'"','"'"'dash'"'"','"'"'eval'"'"'):
        if verb == '"'"'eval'"'"': code = argv[1:]
        else:
            code = []
            for index, (raw, value) in enumerate(argv[1:], 1):
                if value.startswith('"'"'-'"'"') and not value.startswith('"'"'--'"'"') and '"'"'c'"'"' in value[1:]:
                    if index+1 >= len(argv): raise model.UnresolvedShellPath('"'"'shell -c has no command'"'"')
                    code = [argv[index+1]]; break
        if code:
            text = '"'"' '"'"'.join(expanded(raw, variables) for raw, _ in code)
            note_concurrency(text)
            nested_variables = variables
            if verb != '"'"'eval'"'"':
                # The evaluator tracks scalar bindings, not export attributes. A new shell
                # cannot safely inherit every parent scalar as though it were exported.
                nested_variables = {} if variables.get('"'"'__command_environment_cleared__'"'"') else {k:v for k,v in os.environ.items() if variables.get(k) == v}
                for raw in variables.get('"'"'__command_environment_unsets__'"'"', []): nested_variables.pop(expanded(raw, variables), None)
                for raw,value in variables.get('"'"'__command_environment_assignments__'"'"', []):
                    name = value.split('"'"'='"'"',1)[0]
                    rhs = raw.split('"'"'='"'"',1)[1]
                    if raw[:1] in ("'"'"'", '"'"'"'"'"') and raw.find(raw[0],1) > raw.find('"'"'='"'"'): rhs = raw[0] + rhs
                    nested_variables[name] = model._expand_shell_word(rhs, variables, assignment=True)
                nested_variables['"'"'__unbound_shell_names__'"'"'] = set(variables) - set(nested_variables)
            for base in bases or [None]:
                model.bash_write_targets(text, base, collect_writes=False, initial_variables=nested_variables,
                    command_observer=lambda a,b,v: observe(a,b,v,depth+1), write_observer=writes.append)
        return
    if verb not in ('"'"'zip'"'"','"'"'tar'"'"','"'"'ditto'"'"'): return
    args = argv[1:]
    values = [value for _,value in args]
    if any(v in ('"'"'--help'"'"','"'"'--version'"'"') for v in values) or (verb == '"'"'zip'"'"' and any(v in ('"'"'-h'"'"','"'"'-h2'"'"') for v in values)): return
    env_option = '"'"'TAR_OPTIONS'"'"' if verb == '"'"'tar'"'"' else '"'"'ZIPOPT'"'"' if verb == '"'"'zip'"'"' else None
    def check_archive_environment():
        option_value = None if variables.get('"'"'__command_environment_cleared__'"'"') else variables.get(env_option)
        unbound_option = env_option in variables.get('"'"'__unbound_shell_names__'"'"', set())
        for raw in variables.get('"'"'__command_environment_unsets__'"'"', []):
            if expanded(raw, variables) == env_option: option_value = None; unbound_option = False
        for raw, value in variables.get('"'"'__command_environment_assignments__'"'"', []):
            if value.split('"'"'='"'"',1)[0] == env_option:
                rhs = raw.split('"'"'='"'"',1)[1]
                if raw[:1] in ("'"'"'", '"'"'"'"'"') and raw.find(raw[0],1) > raw.find('"'"'='"'"'): rhs = raw[0] + rhs
                option_value = model._expand_shell_word(rhs, variables, assignment=True)
                unbound_option = False
        if option_value or unbound_option:
            raise model.UnresolvedShellPath(env_option + '"'"' modifies archive semantics; unset it for inspection'"'"')
    if verb == '"'"'zip'"'"':
        if any(v in ('"'"'-sf'"'"','"'"'--show-files'"'"') for v in values): return
        operands, ended = [], False
        for raw, value in args:
            if value == '"'"'--'"'"' and not ended: ended = True; continue
            if not ended and value.startswith('"'"'-'"'"'):
                if value == '"'"'--test'"'"': continue
                if value == '"'"'-'"'"' or value.startswith('"'"'--'"'"') or not set(value[1:]) <= set('"'"'rqjXyT0123456789'"'"'):
                    raise model.UnresolvedShellPath('"'"'unsupported zip creation option: '"'"' + value)
                continue
            operands.append(raw)
        check_archive_environment()
        checked = []
        for raw in operands[1:]: checked.extend(resolve_source(raw,bases,variables))
        if len(operands) > 1: archive_output(operands[0],bases,variables,checked,verb)
        return
    if verb == '"'"'ditto'"'"':
        if '"'"'-x'"'"' in values: return
        if not any(v == '"'"'-c'"'"' or (v.startswith('"'"'-'"'"') and not v.startswith('"'"'--'"'"') and '"'"'c'"'"' in v[1:]) for v in values): return
        operands = []
        for raw,value in args:
            if value.startswith('"'"'-'"'"'):
                if value in ('"'"'--keepParent'"'"','"'"'--sequesterRsrc'"'"','"'"'--norsrc'"'"','"'"'--noextattr'"'"','"'"'--noacl'"'"') or (not value.startswith('"'"'--'"'"') and set(value[1:]) <= set('"'"'ck'"'"')): continue
                raise model.UnresolvedShellPath('"'"'unsupported ditto creation option: '"'"' + value)
            operands.append(raw)
        if len(operands) != 2: raise model.UnresolvedShellPath('"'"'ditto creation requires one source and one destination'"'"')
        checked = resolve_source(operands[0],bases,variables)
        archive_output(operands[1],bases,variables,checked,verb); return
    # tar: extraction/listing controls take precedence over contradictory creation flags.
    modes, index, ended = set(), 0, False
    while index < len(args):
        value = args[index][1]
        if value == '"'"'--'"'"': ended = True; index += 1; continue
        if ended: index += 1; continue
        if value in ('"'"'--extract'"'"','"'"'--get'"'"','"'"'--list'"'"','"'"'--compare'"'"','"'"'--diff'"'"'): return
        if value in ('"'"'--create'"'"','"'"'--append'"'"','"'"'--update'"'"','"'"'--concatenate'"'"'): modes.add('"'"'c'"'"')
        elif value.startswith('"'"'--'"'"'):
            if '"'"'='"'"' not in value and value in ('"'"'--file'"'"','"'"'--directory'"'"','"'"'--files-from'"'"','"'"'--exclude-from'"'"','"'"'--use-compress-program'"'"'):
                index += 1
        elif value.startswith('"'"'-'"'"') or (index == 0 and re.fullmatch('"'"'[A-Za-z]+'"'"',value)):
            flags = value.lstrip('"'"'-'"'"')
            for pos, flag in enumerate(flags):
                if flag in '"'"'cruAxdt'"'"': modes.add(flag)
                if flag in '"'"'fCTXI'"'"':
                    if pos == len(flags)-1: index += 1
                    break
        index += 1
    if modes & set('"'"'xdt'"'"') or not modes & set('"'"'cruA'"'"'): return
    check_archive_environment()
    current, index, ended = bases, 0, False
    checked, outputs = [], []
    while index < len(args):
        raw,value = args[index]
        if value == '"'"'--'"'"' and not ended: ended=True;index+=1;continue
        if not ended and value.startswith('"'"'--'"'"'):
            if value in ('"'"'--create'"'"','"'"'--append'"'"','"'"'--update'"'"','"'"'--concatenate'"'"','"'"'--gzip'"'"','"'"'--bzip2'"'"','"'"'--xz'"'"','"'"'--verbose'"'"','"'"'--dereference'"'"'):
                index+=1;continue
            option, sep, attached = value.partition('"'"'='"'"')
            if option not in ('"'"'--file'"'"','"'"'--directory'"'"'):
                raise model.UnresolvedShellPath('"'"'unsupported tar creation option or file list: '"'"' + value)
            if sep: operand = raw.split('"'"'='"'"',1)[1]
            else:
                index+=1
                if index >= len(args): raise model.UnresolvedShellPath('"'"'missing tar option operand'"'"')
                operand=args[index][0]
            if option == '"'"'--directory'"'"': current=change_tar_directory(operand,current,variables)
            else: outputs.append(operand)
            index+=1;continue
        short = not ended and (value.startswith('"'"'-'"'"') or (index==0 and re.fullmatch('"'"'[A-Za-z]+'"'"',value)))
        if short:
            flags = value.lstrip('"'"'-'"'"'); offset=1 if value.startswith('"'"'-'"'"') else 0
            for position,flag in enumerate(flags):
                if flag in '"'"'cruAzjJvph'"'"': continue
                if flag not in '"'"'fC'"'"': raise model.UnresolvedShellPath('"'"'unsupported tar creation option or file list: '"'"' + value)
                if position+1<len(flags): operand=raw[offset+position+1:]
                else:
                    index+=1
                    if index>=len(args): raise model.UnresolvedShellPath('"'"'missing tar option operand'"'"')
                    operand=args[index][0]
                if flag=='"'"'C'"'"': current=change_tar_directory(operand,current,variables)
                else: outputs.append(operand)
                break
            index+=1;continue
        checked.extend(resolve_source(raw,current,variables)); index+=1
    if len(outputs) != 1:
        raise model.UnresolvedShellPath('"'"'tar creation requires one explicit -f/--file output; default archive destination is unresolved'"'"')
    archive_output(outputs[0],bases,variables,checked,verb)


def change_tar_directory(raw,bases,variables):
    value=expanded(raw,variables)
    if os.path.isabs(value): return frozenset([value])
    if not bases: raise model.UnresolvedShellPath('"'"'tar -C relative to unresolved cwd'"'"')
    return frozenset(str(Path(base)/value) for base in bases)



def might_archive(command, depth=0):
    """Only a no-archive fallback for unsupported shell grammar; never resolves cwd.

    Unknown wrappers/nested code are held. Quoted prose in ordinary command arguments
    is not an execution position, and cannot manufacture a packaging decision.
    """
    if depth > 6: return True
    stage = []
    stages = []
    for raw,value,kind in model.shell_tokens(command):
        if kind == '"'"'op'"'"' and value in ('"'"'\n'"'"','"'"';'"'"','"'"'&&'"'"','"'"'||'"'"','"'"'|'"'"','"'"'&'"'"','"'"'('"'"','"'"')'"'"','"'"'{'"'"','"'"'}'"'"','"'"';;'"'"'):
            if stage: stages.append(stage); stage=[]
        else: stage.append((raw,value,kind))
    if stage: stages.append(stage)
    for stage in stages:
        argv = [(raw,value) for raw,value,kind in stage if kind in ('"'"'word'"'"','"'"'fd'"'"')]
        while argv and (argv[0][1] in ('"'"'if'"'"','"'"'then'"'"','"'"'elif'"'"','"'"'else'"'"','"'"'do'"'"','"'"'while'"'"','"'"'until'"'"','"'"'!'"'"') or re.match(r'"'"'^[A-Za-z_]\w*='"'"',argv[0][1])): argv.pop(0)
        if not argv: continue
        verb = os.path.basename(argv[0][1])
        if verb in ('"'"'zip'"'"','"'"'tar'"'"','"'"'ditto'"'"'): return True
        if verb in ('"'"'env'"'"','"'"'sudo'"'"','"'"'nice'"'"','"'"'nohup'"'"','"'"'command'"'"','"'"'builtin'"'"','"'"'exec'"'"'):
            if any(os.path.basename(value) in ('"'"'zip'"'"','"'"'tar'"'"','"'"'ditto'"'"','"'"'bash'"'"','"'"'sh'"'"','"'"'eval'"'"') for _,value in argv[1:]): return True
        if verb in ('"'"'bash'"'"','"'"'sh'"'"','"'"'zsh'"'"','"'"'ksh'"'"','"'"'dash'"'"','"'"'eval'"'"'):
            code = argv[1:] if verb == '"'"'eval'"'"' else []
            if verb != '"'"'eval'"'"':
                for index,(_,value) in enumerate(argv[1:],1):
                    if value.startswith('"'"'-'"'"') and not value.startswith('"'"'--'"'"') and '"'"'c'"'"' in value[1:]:
                        code=argv[index+1:index+2];break
            if code:
                try: text='"'"' '"'"'.join(expanded(raw,dict(os.environ)) for raw,_ in code)
                except (ValueError,TypeError): return True
                if might_archive(text, depth+1): return True
    return False


try:
    data=json.load(sys.stdin)
    command=(data.get('"'"'tool_input'"'"') or {}).get('"'"'command'"'"') or '"'"''"'"'
    cwd=data.get('"'"'cwd'"'"') or os.getcwd()
    note_concurrency(command)
    try:
        model.bash_write_targets(command,cwd,collect_writes=False,command_observer=observe,write_observer=writes.append)
    except model.UnresolvedShellPath:
        if found or might_archive(command): raise
    if concurrent[0]:
        for candidate in found:
            root = Path(candidate)
            for written in writes:
                target = Path(written).resolve()
                if target == root or root in target.parents or target in root.parents:
                    raise model.UnresolvedShellPath('"'"'concurrent pipeline/background write intersects bound candidate receipt tree: '"'"' + str(written))
    result={'"'"'candidates'"'"':sorted(found)}
except (ValueError,OSError,TypeError) as exc:
    result={'"'"'error'"'"':'"'"'Cannot bind packaging sources safely: '"'"'+str(exc)}
sys.stdout.write(json.dumps(result))
' "$script_dir")
error=$(printf '%s' "$inspected" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("error", ""), end="")')
if [ -n "$error" ]; then
  printf '%s' "$error" | python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":sys.stdin.read()}}))'
  exit 0
fi
names=$(printf '%s' "$inspected" | python3 -c 'import json,sys; print("\n".join(json.load(sys.stdin).get("candidates", [])), end="")')
[ -z "$names" ] && exit 0
while IFS= read -r cand; do
  [ -z "$cand" ] && continue
  name="${cand##*/}"

# --- guardrail-hook integrity gate (an audit lane .371) -------------------------------------------------------
# Before a candidate bundle is zipped, verify its OWN hook set is complete + portable: every
# bundle-scoped hook in its HOOKS_MANIFEST.tsv ships in hooks/, none hardcode the workspace root without
# an env-var fallback, no cruft. Self-contained (`verify --tree`), so no dependency on the live .claude.
# Fail-open if the tool/manifest isn't in the candidate (older candidates predate the hook system).
htool="$cand/sapote_hooks/sapote_hooks.py"
if [ -f "$htool" ] && [ -f "$cand/sapote_hooks/HOOKS_MANIFEST.tsv" ]; then
  if ! hg=$(python3 "$htool" verify --tree "$cand" --gate 2>&1); then
    hreason="BLOCKED before packaging: guardrail-hook integrity gate FAILED for $name.

$hg

Every bundle-scoped hook in HOOKS_MANIFEST.tsv must ship in hooks/ and be portable. Resolve each finding
(ship the missing hook into hooks/, or re-scope it to 'workspace' in the manifest; fix any NON-PORTABLE
hardcoded root), then re-zip. (Workspace cruft is advisory and does not fail this gate.)"
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}' "$(printf '%s' "$hreason" | python3 -c 'import json,sys; sys.stdout.write(json.dumps(sys.stdin.read()))')"
    exit 0
  fi
fi
# --------------------------------------------------------------------------------------------------

receipt_tool="$cand/tools/full_suite_receipt.py"
if [ ! -f "$receipt_tool" ]; then
  detail="Source-bound suite recorder/checker is missing from this candidate."
elif ! detail=$(python3 -c '
import json,sys
from pathlib import Path
try:
    receipt=json.loads((Path(sys.argv[1]) / "_CANDIDATE_NOTES/.fullsuite_green").read_text())
    command=receipt.get("command") if isinstance(receipt,dict) else None
    tail=["-m","pytest","-q","-p","no:cacheprovider","--run-slow","--run-network"]
    if (not isinstance(receipt,dict) or receipt.get("schema") != "sapote.full-suite-receipt.v2" or
        not isinstance(command,list) or len(command) != len(tail)+1 or
        not isinstance(command[0],str) or not command[0] or command[1:] != tail or
        receipt.get("python_dont_write_bytecode") != "1" or receipt.get("pythonpath") != "."):
        raise ValueError("minimum receipt protocol requires v2 plus exact canonical complete pytest profile and child environment")
except (OSError,ValueError,TypeError) as exc:
    print("Canonical FULL-suite receipt refused: " + str(exc))
    sys.exit(1)
' "$cand" 2>&1); then
  : # Hold older checker/receipt protocols before invoking candidate-owned code.
elif detail=$(python3 "$receipt_tool" check --candidate "$cand" 2>&1); then
  continue
fi
reason="BLOCKED by guardrail: packaging requires a successful configured FULL-suite receipt bound to this candidate's current bytes. $detail "
reason+="Run the candidate recorder with your configured Python: python3 '$receipt_tool' run --candidate '$cand'. Legacy touched markers and selected tests are insufficient."

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}' "$(printf '%s' "$reason" | python3 -c 'import json,sys; sys.stdout.write(json.dumps(sys.stdin.read()))')"
exit 0  # One complete denial object; never concatenate responses for later candidates.
done <<< "$names"
exit 0
