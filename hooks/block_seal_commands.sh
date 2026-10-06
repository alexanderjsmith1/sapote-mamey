#!/usr/bin/env bash
# GUARDRAIL (installed 2026-08-04, after Claude Code overstepped and made an actual cut; tightened 2026-08-06):
# Claude Code NEVER RUNS the actual Sapote-Mamey seal scripts. The designated Patch Chat owns the seal
# (CUT_PROTOCOL rule 2). This PreToolUse Bash hook DENIES *executing* the seal scripts — but NOT merely
# reading/greping/ls-ing/documenting them (the old version blocked any mention, which broke audit work).
# Claude Code builds a CANDIDATE under the patches folder and hands off — nothing more.
# FAIL-CLOSED (v9.7.367 candidate, Indigo2 JOB-B): an internal error in a BLOCKING guardrail must
# DENY, not silently allow. Deny is a stdout JSON decision (exit 0), so plain `set -e` alone would
# still fail OPEN (nonzero without deny JSON = non-blocking error). Strict mode + ERR trap that
# EMITS the deny decision.
set -euo pipefail
_fail_closed() {
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"GUARDRAIL INTERNAL ERROR in block_seal_commands.sh - failing CLOSED. The hook itself broke (python3 missing? grep error?), not your command. Fix the hook, then retry."}}'
  exit 0
}
trap _fail_closed ERR
# .402 jq-family port (ROSTER_402 seed #1): payload parse via python3 stdlib, not jq —
# with jq absent this fail-closed guard denied EVERY command with a misleading internal
# error. python3 is the bundle's own hard dependency; a malformed payload still exits
# nonzero -> ERR trap -> deny (unchanged fail direction).
input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("command") or "")')
[ -z "$cmd" ] && exit 0

# H04: decoded command positions, actual heredocs, bounded literal shell/eval recursion.
decision=$(printf '%s' "$cmd" | python3 -c 'import sys, json, os, re, shlex
def shell_tokens(command):
    """Lex shell words/operators and skip actual heredoc bodies, without executing text.

    Preserve raw quoting for path expansion; queue every << delimiter until the next
    unquoted newline. <<- removes tabs only. This is a bounded recognizer, not a shell.
    """
    tokens, pending = [], []
    i, n = 0, len(command)
    ops = ('"'"'&>>'"'"', '"'"'<<<'"'"', '"'"'<<-'"'"', '"'"'&&'"'"', '"'"'||'"'"', '"'"'>>'"'"', '"'"'>|'"'"', '"'"'<<'"'"', '"'"'&>'"'"', '"'"'>&'"'"', '"'"'<&'"'"', '"'"'<>'"'"', '"'"';;'"'"')
    while i < n:
        ch = command[i]
        if ch in '"'"' \t\r'"'"':
            i += 1
            continue
        if ch == '"'"'\n'"'"':
            tokens.append(('"'"'\n'"'"', '"'"'\n'"'"', '"'"'op'"'"'))
            i += 1
            for delimiter, dash in pending:
                while True:
                    end = command.find('"'"'\n'"'"', i)
                    if end < 0:
                        end = n
                    line = command[i:end]
                    i = end + (end < n)
                    if (line.lstrip('"'"'\t'"'"') if dash else line) == delimiter:
                        break
                    if end == n:
                        raise ValueError('"'"'unterminated heredoc: '"'"' + delimiter)
            pending = []
            continue
        if ch == '"'"'#'"'"':
            end = command.find('"'"'\n'"'"', i)
            i = n if end < 0 else end
            continue
        if ch in '"'"';|&()<>{}'"'"':
            op = next((op for op in ops if command.startswith(op, i)), ch)
            tokens.append((op, op, '"'"'op'"'"'))
            i += len(op)
            continue
        start, value = i, []
        while i < n:
            ch = command[i]
            if ch in '"'"' \t\r\n;|&()<>'"'"':
                break
            if ch == '"'"'\\'"'"':
                i += 1
                if i == n:
                    raise ValueError('"'"'incomplete shell escape'"'"')
                if command[i] != '"'"'\n'"'"':
                    value.append(command[i])
                i += 1
            elif ch in ('"'"'\x27'"'"', '"'"'\x22'"'"'):
                quote = ch
                i += 1
                while i < n and command[i] != quote:
                    if quote == '"'"'\x22'"'"' and command[i] == '"'"'\\'"'"' and i + 1 < n and command[i+1] in '"'"'$`\x22\\\n'"'"':
                        i += 1
                        if command[i] != '"'"'\n'"'"':
                            value.append(command[i])
                        i += 1
                    else:
                        value.append(command[i])
                        i += 1
                if i == n:
                    raise ValueError('"'"'unterminated shell quote'"'"')
                i += 1
            else:
                value.append(ch)
                i += 1
        raw, word = command[start:i], '"'"''"'"'.join(value)
        kind = '"'"'fd'"'"' if raw.isdigit() and i < n and command[i] in '"'"'<>'"'"' else '"'"'word'"'"'
        tokens.append((raw, word, kind))
        if len(tokens) >= 2 and tokens[-2][1] in ('"'"'<<'"'"', '"'"'<<-'"'"'):
            pending.append((word, tokens[-2][1] == '"'"'<<-'"'"'))
    if pending:
        raise ValueError('"'"'heredoc has no body'"'"')
    return tokens

import os, re, shlex

MAX_LITERAL_NESTING = 6
SHELLS = {'"'"'bash'"'"','"'"'sh'"'"','"'"'zsh'"'"','"'"'ksh'"'"','"'"'dash'"'"'}
WRAPPERS = {'"'"'command'"'"','"'"'builtin'"'"','"'"'exec'"'"','"'"'env'"'"','"'"'sudo'"'"','"'"'nice'"'"','"'"'nohup'"'"'}
REDIRECTS = {'"'"'>'"'"','"'"'>>'"'"','"'"'>|'"'"','"'"'&>'"'"','"'"'&>>'"'"','"'"'<>'"'"','"'"'>&'"'"','"'"'<&'"'"','"'"'<'"'"','"'"'<<'"'"','"'"'<<-'"'"','"'"'<<<'"'"'}
BOUNDARIES = {'"'"'\n'"'"','"'"';'"'"','"'"'&&'"'"','"'"'||'"'"','"'"'|'"'"','"'"'&'"'"','"'"'('"'"','"'"')'"'"','"'"'{'"'"','"'"'}'"'"','"'"';;'"'"'}


def literal_word(raw):
    quote, i = None, 0
    while i < len(raw):
        ch = raw[i]
        if ch == "'"'"'" and quote != '"'"'"'"'"': quote = None if quote == "'"'"'" else "'"'"'"
        elif ch == '"'"'"'"'"' and quote != "'"'"'": quote = None if quote == '"'"'"'"'"' else '"'"'"'"'"'
        elif ch == '"'"'\\'"'"' and quote != "'"'"'": i += 1
        elif ch in '"'"'$`'"'"' and quote != "'"'"'": return False
        i += 1
    return True


def command_argv(tokens):
    argv, i = [], 0
    while i < len(tokens):
        raw, value, kind = tokens[i]
        if kind == '"'"'op'"'"' and value in REDIRECTS:
            if i+1 >= len(tokens): raise ValueError('"'"'redirection has no operand'"'"')
            if argv and i > 0 and tokens[i-1][2] == '"'"'fd'"'"': argv.pop()
            i += 2; continue
        if kind != '"'"'op'"'"': argv.append((raw, value))
        i += 1
    while argv and argv[0][1] in ('"'"'if'"'"','"'"'then'"'"','"'"'elif'"'"','"'"'else'"'"','"'"'do'"'"','"'"'while'"'"','"'"'until'"'"','"'"'!'"'"'):
        argv.pop(0)
    while argv and re.match(r'"'"'^[A-Za-z_]\w*='"'"', argv[0][1]): argv.pop(0)
    while argv and os.path.basename(argv[0][1]) in WRAPPERS:
        wrapper = os.path.basename(argv.pop(0)[1])
        while argv:
            raw, flag = argv[0]
            if flag == '"'"'--'"'"': argv.pop(0); break
            if wrapper == '"'"'env'"'"' and re.match(r'"'"'^[A-Za-z_]\w*='"'"', flag): argv.pop(0); continue
            if wrapper == '"'"'env'"'"' and flag == '"'"'-'"'"': argv.pop(0); continue
            if not flag.startswith('"'"'-'"'"') or flag == '"'"'-'"'"': break
            argv.pop(0)
            if wrapper == '"'"'command'"'"' and not flag.startswith('"'"'--'"'"') and set(flag[1:]) <= set('"'"'pvV'"'"') and any(c in flag for c in '"'"'vV'"'"'):
                return []
            if wrapper in ('"'"'env'"'"','"'"'sudo'"'"','"'"'nice'"'"','"'"'nohup'"'"') and flag in ('"'"'--help'"'"','"'"'--version'"'"'):
                return []
            if wrapper == '"'"'sudo'"'"':
                takes = {'"'"'-u'"'"','"'"'-g'"'"','"'"'-p'"'"','"'"'-C'"'"','"'"'-D'"'"','"'"'-R'"'"','"'"'-T'"'"','"'"'-U'"'"','"'"'-r'"'"','"'"'-t'"'"',
                         '"'"'--user'"'"','"'"'--group'"'"','"'"'--prompt'"'"','"'"'--close-from'"'"','"'"'--chdir'"'"','"'"'--chroot'"'"',
                         '"'"'--command-timeout'"'"','"'"'--other-user'"'"','"'"'--role'"'"','"'"'--type'"'"'}
                noarg = {'"'"'-n'"'"','"'"'-E'"'"','"'"'-H'"'"','"'"'-b'"'"','"'"'-S'"'"','"'"'-k'"'"','"'"'-K'"'"','"'"'-N'"'"','"'"'--non-interactive'"'"','"'"'--preserve-env'"'"',
                         '"'"'--set-home'"'"','"'"'--background'"'"','"'"'--stdin'"'"','"'"'--reset-timestamp'"'"','"'"'--remove-timestamp'"'"','"'"'--no-update'"'"'}
                if flag in ('"'"'-s'"'"','"'"'-i'"'"','"'"'--shell'"'"','"'"'--login'"'"'):
                    raise ValueError('"'"'sudo shell/login execution is outside the literal wrapper recognizer'"'"')
            elif wrapper == '"'"'env'"'"':
                takes, noarg = {'"'"'-u'"'"','"'"'--unset'"'"','"'"'-C'"'"','"'"'--chdir'"'"'}, {'"'"'-i'"'"','"'"'--ignore-environment'"'"','"'"'-v'"'"','"'"'--debug'"'"'}
                if flag in ('"'"'-S'"'"','"'"'--split-string'"'"') or flag.startswith('"'"'--split-string='"'"'):
                    raise ValueError('"'"'env split-string execution is outside the literal wrapper recognizer'"'"')
            elif wrapper == '"'"'nice'"'"':
                takes, noarg = {'"'"'-n'"'"','"'"'--adjustment'"'"'}, set()
                if re.fullmatch(r'"'"'-\d+'"'"', flag): continue
            elif wrapper == '"'"'exec'"'"': takes, noarg = {'"'"'-a'"'"'}, {'"'"'-c'"'"','"'"'-l'"'"'}
            else: takes, noarg = set(), {'"'"'-p'"'"'} if wrapper == '"'"'command'"'"' else set()
            if flag in takes:
                if not argv: raise ValueError('"'"'wrapper option has no operand: '"'"' + flag)
                argv.pop(0)
            elif any(flag.startswith(opt+'"'"'='"'"') for opt in takes if opt.startswith('"'"'--'"'"')):
                pass
            elif any(flag.startswith(opt) and len(flag)>len(opt) for opt in takes if len(opt)==2):
                pass
            elif flag not in noarg and not (not flag.startswith('"'"'--'"'"') and all('"'"'-'"'"'+c in noarg for c in flag[1:])):
                raise ValueError('"'"'unsupported wrapper option: '"'"' + flag)
        if wrapper == '"'"'sudo'"'"':
            while argv and re.match(r'"'"'^[A-Za-z_]\w*='"'"', argv[0][1]): argv.pop(0)
    return argv


def actual_commands(command, depth=0):
    """Literal command positions, with queued heredocs consumed by the lexer.

    This does not evaluate substitutions, variables, aliases or script contents.
    Literal shell -c / eval strings recurse only to MAX_LITERAL_NESTING.
    """
    if depth > MAX_LITERAL_NESTING: raise ValueError('"'"'literal shell nesting exceeds inspection limit'"'"')
    stages, current = [], []
    for token in shell_tokens(command):
        if token[2] == '"'"'op'"'"' and token[1] in BOUNDARIES:
            if current: stages.append(current); current = []
        else: current.append(token)
    if current: stages.append(current)
    commands = []
    for stage in stages:
        argv = command_argv(stage)
        if not argv: continue
        verb = os.path.basename(argv[0][1])
        if verb == '"'"'eval'"'"':
            code = argv[1:]
            if code and code[0][1] == '"'"'--'"'"': code = code[1:]
            if not all(literal_word(raw) for raw, _ in code):
                raise ValueError('"'"'eval requires literal arguments for inspection'"'"')
            commands.extend(actual_commands('"'"' '"'"'.join(value for _, value in code), depth+1))
            continue
        if verb in SHELLS:
            i, script, nested = 1, None, False
            while i < len(argv):
                raw, value = argv[i]
                if value in ('"'"'--help'"'"', '"'"'--version'"'"'):
                    break
                if value == '"'"'--'"'"':
                    script = argv[i+1] if i+1 < len(argv) else None; break
                if value in ('"'"'-o'"'"','"'"'-O'"'"','"'"'--rcfile'"'"','"'"'--init-file'"'"'):
                    i += 2; continue
                if value.startswith('"'"'-'"'"') and not value.startswith('"'"'--'"'"') and '"'"'c'"'"' in value[1:]:
                    if i+1 >= len(argv): raise ValueError('"'"'shell -c has no code argument'"'"')
                    raw_code, code = argv[i+1]
                    if not literal_word(raw_code): raise ValueError('"'"'shell -c requires a literal code argument for inspection'"'"')
                    commands.extend(actual_commands(code, depth+1)); nested = True; break
                if value.startswith('"'"'-'"'"'): i += 1; continue
                script = argv[i]; break
            if not nested and script:
                if not literal_word(script[0]): raise ValueError('"'"'shell script path must be literal for inspection'"'"')
                commands.append([script])  # only the executed script, not arbitrary shell arguments
            continue
        commands.append(argv)
    return commands


def package_creation(argv):
    verb, args = os.path.basename(argv[0][1]), [value for _,value in argv[1:]]
    if verb not in ('"'"'zip'"'"','"'"'tar'"'"','"'"'ditto'"'"'): return False
    if any(value in ('"'"'--help'"'"','"'"'--version'"'"','"'"'-h'"'"','"'"'-h2'"'"') for value in args): return False
    if verb == '"'"'tar'"'"':
        create, extract, i = False, False, 0
        while i < len(args):
            value = args[i]
            if value == '"'"'--'"'"': break
            if value in ('"'"'--create'"'"','"'"'--append'"'"','"'"'--update'"'"','"'"'--concatenate'"'"'): create = True
            elif value in ('"'"'--extract'"'"','"'"'--get'"'"','"'"'--list'"'"','"'"'--compare'"'"','"'"'--diff'"'"'): extract = True
            elif value.startswith('"'"'--'"'"'):
                if value in ('"'"'--file'"'"','"'"'--directory'"'"','"'"'--files-from'"'"','"'"'--exclude'"'"'): i += 1
            elif value.startswith('"'"'-'"'"') or (i == 0 and re.fullmatch(r'"'"'[A-Za-z]+'"'"', value)):
                flags = value.lstrip('"'"'-'"'"')
                for j, flag in enumerate(flags):
                    if flag in '"'"'xdt'"'"': extract = True
                    if flag in '"'"'cruA'"'"': create = True
                    if flag in '"'"'fCT'"'"':
                        if j == len(flags)-1: i += 1
                        break
            i += 1
        return create and not extract
    if verb == '"'"'ditto'"'"' and '"'"'-x'"'"' in args: return False
    return True

try:
    commands = actual_commands(sys.stdin.read())
    blocked = any(os.path.basename(argv[0][1]) in {'"'"'release_cut.sh'"'"','"'"'make_public_tier.sh'"'"'}
                  or (os.path.basename(argv[0][1]) in {'"'"'source'"'"','"'"'.'"'"'} and len(argv)>1
                      and os.path.basename(argv[2][1] if argv[1][1] == '"'"'--'"'"' and len(argv)>2 else argv[1][1]) in {'"'"'release_cut.sh'"'"','"'"'make_public_tier.sh'"'"'})
                  for argv in commands)
    reason = '"'"'BLOCKED by guardrail: Claude Code never runs the actual Sapote-Mamey seal. Build a candidate and hand off; the owner retains sealing authority.'"'"' if blocked else None
except ValueError as exc:
    reason = '"'"'Cannot inspect seal command safely: '"'"' + str(exc)
if reason:
    sys.stdout.write(json.dumps({'"'"'hookSpecificOutput'"'"':{'"'"'hookEventName'"'"':'"'"'PreToolUse'"'"',
                     '"'"'permissionDecision'"'"':'"'"'deny'"'"','"'"'permissionDecisionReason'"'"':reason}}))
')
[ -z "$decision" ] || printf '%s' "$decision"
exit 0
