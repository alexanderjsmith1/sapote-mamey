#!/usr/bin/env bash
# GUARDRAIL (2026-08-06, after the .351 overstep): Claude Code must NEVER create a top-level folder
# that looks like a real Sapote-Mamey cut. The real release folder form is `Sapote Mamey vX.Y.Z/`
# (with a space) directly under the workspace root — that is what confused the Developer or User's team when Claude
# made one. Candidates ALWAYS live under `Patches for next cut Sapote Mamey (vX.Y.Z)/candidate_cut_*`.
#
# PreToolUse(Bash): DENY a create/copy/package op that WRITES a `Sapote Mamey v<digit>` folder anywhere
# NOT inside a "Patches for next cut ..." queue or a `candidate_cut_*` dir. Reading a sealed
# `sapote-mamey-*-CODE-*` tree as a SOURCE is unaffected.
#
# v9.7.355 (the review lane) — fixes two residual false-positives that survived the 2026-08-07 the patch lane narrowing,
# and closes one hole, by checking PER-ARGUMENT instead of on a space-broken token:
#   (E) a legit candidate path whose LAST segment is `Sapote Mamey vX` was DENIED, because the old
#       space-based token extraction (`[^"' ]*Sapote Mamey v...`) could not see the "Patches for next cut"
#       prefix (these folder names contain spaces). Now: the whole quoted arg is tested for a queue marker.
#   (F) `shasum ... "Sapote Mamey v9.7.354.zip"` was DENIED, because the verb regex matched `zip` as a  version-sync-ok
#       substring of the `.zip` extension. Now: the negative class excludes a leading `.` (`[^a-z.]`), so a
#       `.zip`/`.tar` FILENAME no longer counts as a packaging verb; a real `zip`/`tar` COMMAND still does.
#   (HOLE) `cp -R "<queue>/candidate_cut_x" "Sapote Mamey v9.7.355"` (create a top-level release folder in a  version-sync-ok
#       command that also names a candidate) was ALLOWED under a whole-command marker test. Per-argument, the
#       bare destination arg carries no marker → still DENIED.
# FAIL-CLOSED (v9.7.367 candidate, Indigo2 JOB-B): an internal error in a BLOCKING guardrail must
# DENY, not silently allow. Deny is a stdout JSON decision (exit 0), so plain `set -e` alone would
# still fail OPEN (nonzero without deny JSON = non-blocking error). Strict mode + ERR trap that
# EMITS the deny decision.
set -euo pipefail
_fail_closed() {
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"GUARDRAIL INTERNAL ERROR in block_top_level_release_folder.sh - failing CLOSED. The hook itself broke (python3 missing? grep error?), not your command. Fix the hook, then retry."}}'
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

# H04: select actual creation commands; quoted printf/grep mentions stay data.
inspected=$(printf '%s' "$cmd" | python3 -c 'import sys, json, os, re, shlex
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
    selected = [argv for argv in commands if os.path.basename(argv[0][1]) in
                {'"'"'mkdir'"'"','"'"'cp'"'"','"'"'mv'"'"','"'"'rsync'"'"','"'"'ditto'"'"','"'"'install'"'"','"'"'zip'"'"','"'"'tar'"'"'}]
    result = {'"'"'commands'"'"':'"'"'\n'"'"'.join(shlex.join([os.path.basename(argv[0][1])]+[value for _,value in argv[1:]]) for argv in selected)}
except ValueError as exc:
    result = {'"'"'error'"'"':'"'"'Cannot inspect release-folder command safely: '"'"' + str(exc)}
sys.stdout.write(json.dumps(result))
')
error=$(printf '%s' "$inspected" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("error", ""), end="")')
if [ -n "$error" ]; then
  printf '%s' "$error" | python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":sys.stdin.read()}}))'
  exit 0
fi
cmd=$(printf '%s' "$inspected" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("commands", ""), end="")')
[ -z "$cmd" ] && exit 0

# Require a real create/copy/package verb as a COMMAND TOKEN — NOT a `.zip`/`.tar` file extension.
# The `.` in the negative class stops "backup.zip"/"x.tar" from matching the verbs zip/tar.
printf '%s' "$cmd" | grep -qE '(^|[^a-z.])(mkdir|cp|mv|rsync|ditto|install|zip|tar)([^a-z]|$)' || exit 0

# No space-form release-folder name at all → nothing to guard. (Note: the queue folder "Sapote Mamey (vX)"
# has a paren after the space, so it does NOT match `Sapote Mamey v[0-9]`; only the release form does.)
printf '%s' "$cmd" | grep -qE 'Sapote Mamey v[0-9]' || exit 0

deny=0
# Prefer PER-ARGUMENT checks. Release folders contain spaces, so in any real command they are quoted.
# For each quoted arg that names a `Sapote Mamey v<digit>` folder, allow it ONLY when that same arg also
# sits inside a queue ("Patches for next cut") or a candidate_cut_* dir. (Portable: no bash-4 `mapfile`.)
qcount=0
while IFS= read -r a; do
  [ -z "$a" ] && continue
  printf '%s' "$a" | grep -qE 'Sapote Mamey v[0-9]' || continue
  qcount=$((qcount+1))
  # v9.7.370 (the patch lane, hooks lane, the Developer or User-assigned 2026-08-18): an arg naming an EXISTING release
  # path is a REFERENCE to the real sealed folder (a read source / var assignment), not a creation —
  # a creation target does not exist yet. Writes INTO sealed trees are a different hook's job
  # (block_sealed_tree_edits.sh). Fixes the false-positive where reading FROM the sealed tree
  # (cp "<sealed>/file" "<queue>/file", or S="<sealed>" in a compound command) was denied twice
  # on 2026-08-18. The .355 HOLE case (cp <queue>/x "Sapote Mamey vX" — new top-level dest) still
  # denies: that destination does not exist.
  ap=${a#\"}; ap=${ap%\"}; ap=${ap#\'}; ap=${ap%\'}
  ap=${ap#*=}   # a quoted VAR="path" assignment: test the path part
  [ -e "$ap" ] && continue
  case "$a" in
    *"Patches for next cut"*|*candidate_cut*) : ;;   # inside a queue/candidate → allowed
    *) deny=1 ;;                                       # a bare/top-level release folder → deny
  esac
done < <(printf '%s' "$cmd" | grep -oE '"[^"]*"|'"'"'[^'"'"']*'"'"'')

# No quoted arg named a release folder (e.g. an unquoted path): fall back to a whole-command marker test.
if [ "$qcount" = 0 ]; then
  case "$cmd" in
    *"Patches for next cut"*|*candidate_cut*) : ;;
    *) deny=1 ;;
  esac
fi

if [ "$deny" = 1 ]; then
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED by guardrail: do not create a top-level \"Sapote Mamey vX.Y.Z/\" folder — that mimics a real cut and confuses the team (the .351 overstep). Build a CANDIDATE under \"Patches for next cut Sapote Mamey (vX.Y.Z)/candidate_cut_*_AQUARIUS/\" and hand off a zip. The actual cut/seal is the Patch Chat + the Developer or User, never Claude Code. See memory: never-make-the-actual-cut, check-before-create."}}'
fi
exit 0
