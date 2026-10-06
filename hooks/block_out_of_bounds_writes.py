#!/usr/bin/env python3
"""PreToolUse GUARDRAIL — inspect recognized writes against allowed roots.

WHY (2026-08-18, the roster lane): Claude wrote deliverable files into a sibling agent's
workspace (the Codex workspace) — OUTSIDE this project root. That is an instruction/house-rule
boundary (shared-corpus boundary; the Codex workspace is read-only to
this chat) that had NO enforced hook. This hook checks every Write/Edit/MultiEdit/
NotebookEdit whose target resolves outside the allowlist is DENIED, and Bash write-ops whose TARGET is
an out-of-bounds path are DENIED as defense-in-depth.

ALLOWED write roots (everything else is denied):
  * the workspace root ($SAPOTE_WORKSPACE_ROOT / $CLAUDE_PROJECT_DIR, defaulting to this project)
  * ~/.claude                                (Claude config + this session's memory files)
  * /private/tmp, /tmp, /var/folders         (scratch / OS temp)

Known reads use no write target. Unsupported Bash syntax is held for clarification,
including read-only forms that this bounded recognizer cannot classify. For supported
Bash, the WRITE TARGET is inspected (redirect target; cp/mv/rsync/ln/
install destination; mkdir/touch/rmdir/truncate/sed -i/dd targets). A command that merely *mentions* an
out-of-bounds path — e.g. writing a log line that quotes it, or `cp <codex-file> ./local` (read source)
— is ALLOWED, because the write target is in-bounds. Heredoc bodies are ignored (never a target).

BASH SCOPE: direct operations plus bounded if/elif/else, for/while/until, groups,
subshells and declared functions are inspected statically. Unresolved paths and
unsupported compound syntax are held. This is not a general Bash sandbox: dynamic
scripts, writes inside uninspected eval/source text, expanding heredoc substitutions,
pre-opened descriptor destinations and filesystem races remain separate holds.

FAIL-CLOSED: any internal error DENIES (a broken hard-boundary guard must not fail open).
Deny = stdout JSON permissionDecision:deny, exit 0 (same contract as block_sealed_tree_edits.sh).
"""
import sys, json, os, re, shlex

ALLOWED_ROOTS_RAW = [
    (os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()),
    os.path.expanduser("~/.claude"),
    "/private/tmp",
    "/tmp",
    "/var/folders",
    "/dev",  # shell plumbing: >/dev/null, 2>/dev/null, /dev/stdout, etc. (not a workspace)
]

def _deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)

def _fail_closed(detail):
    _deny("GUARDRAIL INTERNAL ERROR in block_out_of_bounds_writes.py — failing CLOSED "
          f"({detail}). The hook broke, not your command. Fix the hook, then retry.")

def _real(p):
    try:
        return os.path.realpath(p)
    except Exception:
        return p

def _allowed_roots():
    return [_real(r) for r in ALLOWED_ROOTS_RAW]

def _under_allowed(abspath, roots):
    rp = _real(abspath)
    return any(rp == root or rp.startswith(root + os.sep) for root in roots)

def _resolve(path, cwd):
    if not os.path.isabs(path):
        path = os.path.join(cwd, path)
    return path

def _looks_like_path(tok):
    # a token worth checking as a filesystem target
    return tok != ""

# commands whose DESTINATION is the last path argument (or the -t / --target-directory argument)
DEST_LAST = {"cp", "rsync", "install", "ln"}
# commands where every non-flag path arg is a write target. mv mutates its sources as well as its destination,
# and deletion is a write (audit F04).
ALL_ARGS = {"mkdir", "touch", "rmdir", "truncate", "rm", "unlink", "shred", "mv"}


def shell_tokens(command):
    """Lex shell words/operators and skip actual heredoc bodies, without executing text.

    Preserve raw quoting for path expansion; queue every << delimiter until the next
    unquoted newline. <<- removes tabs only. This is a bounded recognizer, not a shell.
    """
    tokens, pending = [], []
    i, n = 0, len(command)
    ops = ('&>>', '<<<', '<<-', '&&', '||', '>>', '>|', '<<', '&>', '>&', '<&', '<>', ';;')
    while i < n:
        ch = command[i]
        if ch in ' \t\r':
            i += 1
            continue
        if ch == '\n':
            tokens.append(('\n', '\n', 'op'))
            i += 1
            for delimiter, dash in pending:
                while True:
                    end = command.find('\n', i)
                    if end < 0:
                        end = n
                    line = command[i:end]
                    i = end + (end < n)
                    if (line.lstrip('\t') if dash else line) == delimiter:
                        break
                    if end == n:
                        raise ValueError('unterminated heredoc: ' + delimiter)
            pending = []
            continue
        if ch == '#':
            end = command.find('\n', i)
            i = n if end < 0 else end
            continue
        if ch in ';|&()<>{}':
            op = next((op for op in ops if command.startswith(op, i)), ch)
            tokens.append((op, op, 'op'))
            i += len(op)
            continue
        start, value = i, []
        while i < n:
            ch = command[i]
            if ch in ' \t\r\n;|&()<>':
                break
            if ch == '\\':
                i += 1
                if i == n:
                    raise ValueError('incomplete shell escape')
                if command[i] != '\n':
                    value.append(command[i])
                i += 1
            elif ch in ('\x27', '\x22'):
                quote = ch
                i += 1
                while i < n and command[i] != quote:
                    if quote == '\x22' and command[i] == '\\' and i + 1 < n and command[i+1] in '$`\x22\\\n':
                        i += 1
                        if command[i] != '\n':
                            value.append(command[i])
                        i += 1
                    else:
                        value.append(command[i])
                        i += 1
                if i == n:
                    raise ValueError('unterminated shell quote')
                i += 1
            else:
                value.append(ch)
                i += 1
        raw, word = command[start:i], ''.join(value)
        kind = 'fd' if raw.isdigit() and i < n and command[i] in '<>' else 'word'
        tokens.append((raw, word, kind))
        if len(tokens) >= 2 and tokens[-2][1] in ('<<', '<<-'):
            pending.append((word, tokens[-2][1] == '<<-'))
    if pending:
        raise ValueError('heredoc has no body')
    return tokens


def strip_heredoc_bodies(command):
    tokens = shell_tokens(command)
    kept, skip = [], False
    for raw, value, kind in tokens:
        if skip:
            skip = False
            continue
        if kind == 'op' and value in ('<<', '<<-'):
            skip = True
            continue
        kept.append(raw if raw != '\n' else '\n')
    return ' '.join(kept)


def shell_segments(command):
    """Keep pipeline stages separate and preserve quoted operators as word content."""
    segments, current = [], []
    for raw, value, kind in shell_tokens(command):
        if kind == 'op' and value in ('\n', ';', '&&', '||', '|', '&', '(', ')', '{', '}'):
            if current:
                segments.append(' '.join(current))
                current = []
        else:
            current.append(raw)
    if current:
        segments.append(' '.join(current))
    return segments

class UnresolvedShellPath(ValueError):
    """A recognized write has a path or effective directory we cannot bind."""


def _expand_shell_word(raw, variables, *, assignment=False):
    """Expand simple $NAME/${NAME} only where shell quoting permits it.

    Command substitution and complex parameter expansion are deliberately held for
    write paths; they are never evaluated by the hook. Read-only commands still pass.
    """
    out, i, quote = [], 0, None
    # Tilde expands only in an unquoted literal prefix, before parameter expansion.
    tilde = re.match(r'^~([A-Za-z0-9_.+-]*)(?=/|:|$)' if assignment else r'^~([A-Za-z0-9_.+-]*)(?=/|$)', raw)
    if tilde:
        user = tilde.group(1)
        if user in ('+', '-'):
            key = 'PWD' if user == '+' else 'OLDPWD'
            if key not in variables: raise UnresolvedShellPath('unbound tilde directory: ' + raw)
            home = variables[key]
        elif not user:
            if 'HOME' in variables:
                home = variables['HOME']
            elif 'HOME' in variables.get('__unbound_shell_names__', set()):
                raise UnresolvedShellPath('unbound HOME for tilde path')
            else:
                import pwd
                home = pwd.getpwuid(os.getuid()).pw_dir
        else:
            home = os.path.expanduser('~' + user)
        out.append(home); i = len(tilde.group(0))
    while i < len(raw):
        ch = raw[i]
        if ch == "'" and quote != '"':
            quote = None if quote == "'" else "'"
            i += 1
        elif ch == '"' and quote != "'":
            quote = None if quote == '"' else '"'
            i += 1
        elif ch == '\\' and quote != "'":
            if i+1 < len(raw) and (quote is None or raw[i+1] in '$`"\\\n'):
                i += 1
                if raw[i] != '\n': out.append(raw[i])
                i += 1
            else:
                out.append(ch); i += 1
        elif assignment and quote is None and ch == '~' and i > 0 and raw[i-1] == ':':
            prefix = re.match(r'~[A-Za-z0-9_.+-]*(?=/|:|$)', raw[i:])
            if prefix:
                out.append(_expand_shell_word(prefix.group(0), variables)); i += len(prefix.group(0))
            else:
                out.append(ch); i += 1
        elif ch == '$' and quote != "'":
            match = re.match(r'\$(?:\{([A-Za-z_]\w*)\}|([A-Za-z_]\w*))', raw[i:])
            if not match:
                raise UnresolvedShellPath('unsupported expansion in path: ' + raw)
            name = match.group(1) or match.group(2)
            if name not in variables:
                raise UnresolvedShellPath('unbound variable in path: ' + name)
            value = variables[name]
            if quote is None and not assignment and (re.search(r'\s', value) or any(ch in value for ch in '*?[')):
                raise UnresolvedShellPath('unquoted variable needs shell splitting/globbing: ' + raw)
            out.append(value); i += len(match.group(0))
        elif ch == '`' and quote != "'":
            raise UnresolvedShellPath('command substitution in path: ' + raw)
        else:
            out.append(ch); i += 1
    return ''.join(out)



class ShellProgram:
    """Parse a bounded shell grammar without evaluating any shell expression.

    Reserved words count only at command boundaries and when unquoted. Unsupported
    compound syntax is held visibly instead of being flattened into guessed cwd.
    """
    def __init__(self, tokens):
        self.tokens, self.i = tokens, 0

    def value(self):
        return self.tokens[self.i][1] if self.i < len(self.tokens) else None

    def keyword(self, value):
        return self.i < len(self.tokens) and self.tokens[self.i] == (value, value, 'word')

    def take(self, value):
        if self.value() != value: raise UnresolvedShellPath('expected shell delimiter: ' + value)
        self.i += 1

    def suffix(self):
        result = []
        redirects = {'>','>>','>|','&>','&>>','<>','>&','<&','<','<<','<<-','<<<'}
        while self.i < len(self.tokens):
            if self.tokens[self.i][2] == 'fd' and self.i+1 < len(self.tokens) and self.tokens[self.i+1][1] in redirects:
                result.append(self.tokens[self.i]); self.i += 1
            if self.i >= len(self.tokens) or self.tokens[self.i][2]!='op' or self.value() not in redirects:
                break
            result.append(self.tokens[self.i]); self.i += 1
            if self.i >= len(self.tokens) or self.tokens[self.i][2] not in ('word','fd'):
                raise UnresolvedShellPath('compound redirect has no word target')
            result.append(self.tokens[self.i]); self.i += 1
        return result

    def append(self, nodes, node):
        redirects = self.suffix()
        nodes.append(('redirected',node,redirects) if redirects else node)

    def sequence(self, stops=()):
        nodes = []
        while self.i < len(self.tokens):
            if any(self.keyword(x) for x in stops) or self.value() in (')', '}'):
                return nodes
            token = self.tokens[self.i]
            if token[2] == 'op' and token[1] in (';', '\n', '&&', '||', '|', '&'):
                nodes.append(('flat', [token])); self.i += 1; continue
            if self.keyword('if'):
                self.i += 1; branches = []
                while True:
                    condition = self.sequence(('then',)); self.take('then')
                    body = self.sequence(('elif', 'else', 'fi')); branches.append((condition, body))
                    if not self.keyword('elif'): break
                    self.i += 1
                other = []
                if self.keyword('else'):
                    self.i += 1; other = self.sequence(('fi',))
                if not self.keyword('fi'): raise UnresolvedShellPath('unterminated if')
                self.i += 1; self.append(nodes,('if',branches,other)); continue
            if self.keyword('for'):
                self.i += 1
                if self.i >= len(self.tokens) or not re.fullmatch(r'[A-Za-z_]\w*', self.value() or ''):
                    raise UnresolvedShellPath('unsupported for-loop variable')
                name = self.value(); self.i += 1; values = None
                if self.keyword('in'):
                    self.i += 1; values = []
                    while self.i < len(self.tokens) and self.tokens[self.i][2] != 'op':
                        values.append(self.tokens[self.i]); self.i += 1
                while self.value() in (';', '\n'): self.i += 1
                if not self.keyword('do'): raise UnresolvedShellPath('unsupported for-loop header')
                self.i += 1; body = self.sequence(('done',)); self.take('done')
                self.append(nodes,('for',name,values,body)); continue
            if self.keyword('while') or self.keyword('until'):
                self.i += 1; condition = self.sequence(('do',)); self.take('do')
                body = self.sequence(('done',)); self.take('done')
                self.append(nodes,('loop',condition,body,token[1] == 'until')); continue
            name = None
            if self.keyword('function'):
                self.i += 1
                if self.i >= len(self.tokens): raise UnresolvedShellPath('missing function name')
                name = self.value(); self.i += 1
                if self.value() == '(':
                    self.take('('); self.take(')')
            elif (self.i + 2 < len(self.tokens) and token[2] == 'word'
                  and re.fullmatch(r'[A-Za-z_]\w*', token[1])
                  and self.tokens[self.i+1][1] == '(' and self.tokens[self.i+2][1] == ')'):
                name = token[1]; self.i += 3
            if name is not None:
                if not re.fullmatch(r'[A-Za-z_]\w*', name): raise UnresolvedShellPath('unsupported function name')
                while self.value() == '\n': self.i += 1
                opening = self.value()
                if opening not in ('{', '('): raise UnresolvedShellPath('unsupported function body')
                self.i += 1; body = self.sequence(); self.take('}' if opening == '{' else ')')
                redirects = self.suffix()
                if redirects: body = [('redirected',('group',body,opening == '('),redirects)]; opening = '{'
                nodes.append(('function',name,body,opening == '(')); continue
            if token[2] == 'op' and token[1] in ('(', '{'):
                self.i += 1; body = self.sequence(); self.take(')' if token[1] == '(' else '}')
                self.append(nodes,('group',body,token[1] == '(')); continue
            if any(self.keyword(x) for x in ('case','select','coproc','then','else','elif','fi','do','done','esac')):
                raise UnresolvedShellPath('unsupported shell compound: ' + self.value())
            words = []
            while self.i < len(self.tokens):
                item = self.tokens[self.i]
                if item[2] == 'op' and item[1] in (';', '\n', '&&','||','|','&','(',')','{','}'):
                    break
                words.append(item); self.i += 1
            if not words: raise UnresolvedShellPath('unsupported shell token: ' + str(self.value()))
            nodes.append(('flat', words))
        if stops: raise UnresolvedShellPath('missing shell compound terminator')
        return nodes

def bash_write_targets(cmd, cwd=None, *, command_observer=None, write_observer=None, collect_writes=True, initial_variables=None):
    """Inspect common direct writes with scoped cwd, directory stacks and literal variables.

    Conditional directory changes retain both possible states after a branch. Unknown
    relative-write directories produce an explicit hold, never a guessed local path.
    Script-internal writes remain outside this bounded recognizer's scope.
    Optional observers receive actual command argv, feasible execution directories and
    the expansion view. Packaging observers may disable write collection without changing
    the default write-guard semantics.
    """
    tokens = shell_tokens(cmd)
    targets = []
    environment = os.environ if initial_variables is None else initial_variables
    oldpwd = environment.get('OLDPWD')
    state = {'here': frozenset([cwd]) if cwd else None,
             'old': frozenset([oldpwd]) if oldpwd else None,
             'stack': [], 'vars': dict(environment), 'readonly': set(), 'unbound_vars': set(), 'uncertain_attrs': set(),
             'namerefs': {}, 'physical': 'physical' in environment.get('SHELLOPTS', '').split(':'),
             'lastpipe': 'lastpipe' in environment.get('BASHOPTS','').split(':'),
             'localvar_inherit': 'localvar_inherit' in environment.get('BASHOPTS','').split(':')}
    if initial_variables is not None:
        state['unbound_vars'] = set(state['vars'].pop('__unbound_shell_names__', set()))
    if cwd: state['vars']['PWD'] = cwd
    else: state['vars'].pop('PWD', None)
    scopes, segment = [], []
    prior_cd = None
    pipeline = None
    alternative = None

    def clone(s):
        return {**s, 'stack': list(s['stack']) if s['stack'] is not None else None, 'vars': dict(s['vars']),
                'readonly': set(s['readonly']), 'unbound_vars': set(s['unbound_vars']),
                'uncertain_attrs': set(s['uncertain_attrs']), 'namerefs': dict(s['namerefs'])}

    def merge(left, right):
        merged = clone(left)
        for key in ('here', 'old'):
            merged[key] = (left[key] | right[key]) if left[key] is not None and right[key] is not None else None
        if left['stack'] != right['stack']: merged['stack'] = None
        merged['vars'] = {k: v for k,v in left['vars'].items() if right['vars'].get(k) == v}
        merged['unbound_vars'] = left['unbound_vars'] | right['unbound_vars'] | ((set(left['vars']) | set(right['vars'])) - set(merged['vars']))
        merged['readonly'] = left['readonly'] | right['readonly']
        merged['uncertain_attrs'] = left['uncertain_attrs'] | right['uncertain_attrs']
        merged['physical'] = left['physical'] if left['physical'] == right['physical'] else None
        merged['lastpipe'] = left['lastpipe'] if left['lastpipe'] == right['lastpipe'] else None
        merged['localvar_inherit'] = left['localvar_inherit'] if left['localvar_inherit'] == right['localvar_inherit'] else None
        merged['namerefs'] = {}
        for name in set(left['namerefs']) | set(right['namerefs']):
            a, b = left['namerefs'].get(name, frozenset()), right['namerefs'].get(name, frozenset())
            merged['namerefs'][name] = a | b if a is not None and b is not None else None
        sync_directories(merged)
        return merged

    def sync_directories(s):
        for name, key in (('PWD', 'here'), ('OLDPWD', 'old')):
            dirs = s[key]
            if dirs is not None and len(dirs) == 1:
                s['vars'][name] = next(iter(dirs))
            else:
                s['vars'].pop(name, None)

    assignment_name = re.compile(r'^([A-Za-z_]\w*)(?:\[[^\]]*\])?(?:\+)?=')

    def invalidate(name=None, *, seen=None):
        # Invalidating a mutation target preserves reads while holding later path use.
        # Unknown/indirect variable names may address any currently bound scalar.
        if name is None or not re.fullmatch(r'[A-Za-z_]\w*(?:\[[^\]]*\])?', name):
            for key in list(state['vars']):
                if key not in state['readonly']:
                    state['vars'].pop(key, None); state['unbound_vars'].add(key)
            state['old'] = None
            return
        name = name.split('[', 1)[0]
        seen = set() if seen is None else seen
        if name in seen:
            invalidate(); return
        seen.add(name)
        if name in state['namerefs']:
            referents = state['namerefs'][name]
            if referents is None:
                invalidate()
            else:
                for referent in referents: invalidate(referent, seen=set(seen))
        if name not in state['readonly']:
            state['vars'].pop(name, None); state['unbound_vars'].add(name)
            if name == 'OLDPWD': state['old'] = None

    def mutation_name(raw):
        try:
            return _expand_shell_word(raw, {**state['vars'], '__unbound_shell_names__': state['unbound_vars']})
        except UnresolvedShellPath:
            return None

    def assign(raw, val, *, uncertain=False, variable_view=None):
        match = assignment_name.match(val)
        if not match: invalidate(); return
        name = match.group(1)
        if name in state['namerefs']:
            invalidate(name); return
        if name in state['readonly']: return
        if uncertain or name in state['uncertain_attrs'] or '[' in val.split('=',1)[0] or '+=' in val:
            invalidate(name); return
        value = raw.split('=', 1)[1]
        # export/declare accept a whole quoted assignment; preserve RHS quote state.
        if raw[:1] in ("'", '"') and raw.find(raw[0], 1) > raw.find('='):
            value = raw[0] + value
        try:
            bindings = variable_view if variable_view is not None else {**state['vars'], '__unbound_shell_names__': state['unbound_vars']}
            state['vars'][name] = _expand_shell_word(value, bindings, assignment=True)
            state['unbound_vars'].discard(name)
            if name == 'OLDPWD':
                value = state['vars'][name]
                state['old'] = frozenset([value]) if os.path.isabs(value) else (
                    frozenset(_resolve(value, base) for base in state['here']) if state['here'] else None)
        except UnresolvedShellPath:
            invalidate(name)

    def builtin_mutation(verb, argv):
        if verb == 'printf':
            # -- ends printf option parsing; a literal format '-v' is not mutation.
            if len(argv) > 1 and argv[1][1] == '--': return
            if len(argv) > 1 and argv[1][1] == '-v':
                invalidate(mutation_name(argv[2][0]) if len(argv) > 2 else None)
            elif len(argv) > 1 and argv[1][1].startswith('-v'):
                invalidate(mutation_name(argv[1][0][2:]))
            return
        read = verb == 'read'
        takes = set('adinNptu') if read else set('dnOsuCc')
        noarg = set('ers') if read else set('t')
        names, array, callback, i = [], None, False, 1
        while i < len(argv):
            raw, val = argv[i]
            if val == '--':
                names.extend(raw for raw, _ in argv[i+1:]); break
            if not val.startswith('-') or val == '-':
                names.extend(raw for raw, _ in argv[i:]); break
            flags, j = val[1:], 0
            while j < len(flags):
                flag = flags[j]
                if flag in takes:
                    operand = raw[2+j:] if j+1 < len(flags) else (argv[i+1][0] if i+1 < len(argv) else None)
                    if j+1 >= len(flags): i += 1
                    if operand is None: invalidate(); return
                    if read and flag == 'a': array = operand
                    if not read and flag == 'C': callback = True
                    break
                if flag not in noarg:
                    invalidate(); return
                j += 1
            i += 1
        if callback:
            invalidate()
            state['here'], state['stack'], state['physical'] = None, None, None
            return  # callbacks can mutate bindings and cwd beyond the array
        if array is not None:
            invalidate(mutation_name(array)); return
        if not names: names = ['REPLY' if read else 'MAPFILE']
        for raw in names: invalidate(mutation_name(raw))

    def cd_destinations(value, variables, *, physical=None):
        mode = state['physical'] if physical is None else physical
        def admitted(paths):
            logical = frozenset(os.path.normpath(path) for path in paths)
            measured = frozenset(os.path.realpath(path) for path in paths)
            return measured if mode is True else logical if mode is False else logical | measured
        if os.path.isabs(value): return admitted([value])
        if state['here'] is None: raise UnresolvedShellPath('relative cd from unknown directory')
        paths = [_resolve(value, base) for base in state['here']]
        # Bash consults CDPATH except for a leading dot or dot-dot component.
        if value.split('/', 1)[0] not in ('.', '..'):
            cdpath = variables.get('CDPATH')
            if cdpath is None and 'CDPATH' in variables.get('__unbound_shell_names__', set()):
                raise UnresolvedShellPath('unbound CDPATH for relative cd')
            if cdpath:
                for entry in cdpath.split(':'):
                    for base in state['here']:
                        paths.append(_resolve(value, _resolve(entry, base)))
        # Retain all candidate directories. Filesystem observations are not a proof
        # that a preceding command did not create/change a directory.
        return admitted(paths)

    def add(raw, *, bases=None, override=False):
        if not collect_writes and write_observer is None: return
        value = _expand_shell_word(raw, {**state['vars'], '__unbound_shell_names__': state['unbound_vars']})
        if not _looks_like_path(value):
            return
        here = bases if override else state['here']
        if not os.path.isabs(value) and here is None:
            raise UnresolvedShellPath('relative write after an unresolved directory change: ' + raw)
        paths = [value] if os.path.isabs(value) or not here else [_resolve(value, base) for base in here]
        if collect_writes: targets.extend(paths)
        if write_observer is not None:
            for path in paths: write_observer(path)

    def process(words):
        nonlocal prior_cd, functions
        if not words:
            return
        prior_cd = None
        # File redirections are inspected and removed from argv, including glued forms.
        argv = []
        i = 0
        while i < len(words):
            raw, val, kind = words[i]
            if kind == 'op' and val in ('>', '>>', '>|', '&>', '&>>', '<>', '>&', '<&', '<', '<<', '<<-', '<<<'):
                if i+1 >= len(words):
                    raise UnresolvedShellPath('redirection has no target')
                target = words[i+1][0]
                if val in ('>', '>>', '>|', '&>', '&>>', '<>'):
                    add(target)
                elif val in ('>&', '<&'):
                    value = _expand_shell_word(target, state['vars'])
                    if not re.fullmatch(r'(?:\d+-?|-)', value):
                        if val == '>&': add(target)
                        else: raise UnresolvedShellPath('unbound input descriptor: ' + target)
                # A preceding numeric fd is syntax rather than a command argument.
                if argv and i > 0 and words[i-1][2] == 'fd': argv.pop()
                i += 2
                continue
            argv.append((raw, val)); i += 1
        k = 0
        while k < len(argv) and assignment_name.match(argv[k][1]):
            k += 1
        if k == len(argv):
            for raw, val in argv: assign(raw, val)
            return
        prefix_assignments = argv[:k]
        argv = argv[k:]
        # Wrapper options have different arities. Their cwd applies only to the
        # wrapped command; shell redirections above still use the caller's cwd.
        execution_dirs = state['here']
        external_wrapper = False
        function_bypass = False
        builtin_only = False
        environment_assignments = list(prefix_assignments)
        environment_cleared = False
        environment_unsets = []
        while argv and os.path.basename(argv[0][1]) in ('sudo','nice','nohup','command','env','builtin','exec'):
            wrapper = os.path.basename(argv.pop(0)[1])
            function_bypass |= wrapper in ('command', 'env', 'sudo', 'nohup', 'nice')
            builtin_only |= wrapper == 'builtin'
            external_wrapper |= wrapper in ('sudo', 'nice', 'nohup', 'env')
            while argv:
                raw, flag = argv[0]
                if flag == '--': argv.pop(0); break
                if wrapper == 'env' and flag == '-':
                    environment_cleared = True
                    argv.pop(0); continue
                if wrapper == 'env' and re.match(r'^[A-Za-z_]\w*=', flag):
                    environment_assignments.append(argv.pop(0)); continue
                if not flag.startswith('-') or flag == '-': break
                argv.pop(0)
                if wrapper == 'command' and flag.startswith('-') and not flag.startswith('--') and set(flag[1:]) <= set('pvV') and any(ch in flag for ch in 'vV'):
                    return  # command lookup, with redirects already inspected
                if flag in ('--help', '--version') and wrapper in ('env','nice','nohup','sudo'):
                    return
                value = None
                cwd_option = False
                if wrapper == 'sudo':
                    takes = {'-u','-g','-p','-C','-R','-T','-U','-r','-t','-D',
                             '--user','--group','--prompt','--close-from','--chroot',
                             '--command-timeout','--other-user','--role','--type','--chdir'}
                    noarg = {'-n','-E','-H','-b','-S','-k','-K','-N',
                             '--non-interactive','--preserve-env','--set-home','--background',
                             '--stdin','--reset-timestamp','--remove-timestamp','--no-update'}
                    cwd_option = flag in ('-D','--chdir') or flag.startswith('--chdir=') or (flag.startswith('-D') and len(flag)>2)
                    if flag in ('-s','-i','--shell','--login') or flag == '-R' or flag.startswith('--chroot'):
                        raise UnresolvedShellPath('unsupported sudo shell/root wrapper')
                elif wrapper == 'env':
                    takes = {'-u','--unset','-C','--chdir'}
                    noarg = {'-i','--ignore-environment','-','-v','--debug'}
                    cwd_option = flag in ('-C','--chdir') or flag.startswith('--chdir=') or (flag.startswith('-C') and len(flag)>2)
                    if flag in ('-S','--split-string') or flag.startswith('--split-string='):
                        raise UnresolvedShellPath('unsupported env split-string wrapper')
                elif wrapper == 'nice':
                    takes, noarg = {'-n','--adjustment'}, set()
                    if re.fullmatch(r'-\d+', flag): continue
                elif wrapper == 'exec':
                    takes, noarg = {'-a'}, {'-c','-l'}
                else:
                    takes, noarg = set(), {'-p'} if wrapper == 'command' else set()
                if flag in takes:
                    if not argv: raise UnresolvedShellPath('wrapper option has no operand: ' + flag)
                    value = argv.pop(0)[0]
                elif any(flag.startswith(opt+'=') for opt in takes if opt.startswith('--')):
                    value = raw.split('=',1)[1]
                elif any(flag.startswith(opt) and len(flag)>len(opt) for opt in takes if len(opt)==2):
                    value = raw[2:]
                elif flag not in noarg and not (flag.startswith('-') and not flag.startswith('--') and all('-'+ch in noarg for ch in flag[1:])):
                    raise UnresolvedShellPath('unsupported wrapper option: ' + flag)
                if wrapper == 'env' and flag in ('-i','--ignore-environment'):
                    environment_cleared = True
                if wrapper == 'env' and (flag in ('-u','--unset') or flag.startswith('--unset=') or flag.startswith('-u')) and value is not None:
                    environment_unsets.append(value)
                if cwd_option:
                    value = _expand_shell_word(value, state['vars'])
                    if os.path.isabs(value): execution_dirs = frozenset([value])
                    elif execution_dirs is None: raise UnresolvedShellPath('wrapper cwd is unresolved')
                    else: execution_dirs = frozenset(_resolve(value, base) for base in execution_dirs)
            if wrapper == 'sudo':
                while argv and re.match(r'^[A-Za-z_]\w*=', argv[0][1]): argv.pop(0)
        if not argv: return
        verb = os.path.basename(argv[0][1])
        if command_observer is not None and not builtin_only and (function_bypass or argv[0][1] not in functions):
            command_observer(argv, execution_dirs,
                             {**state['vars'], '__unbound_shell_names__': set(state['unbound_vars']),
                              '__command_environment_assignments__': environment_assignments,
                              '__command_environment_cleared__': environment_cleared,
                              '__command_environment_unsets__': environment_unsets})
        def add_operand(raw):
            add(raw, bases=execution_dirs, override=True)
        if not external_wrapper and verb in ('source','.','eval','trap'):
            # These builtins can change directory or install callbacks without a
            # directly visible cd. Inspecting their arbitrary scripts is out of
            # scope; a later recognized relative/variable write must be held.
            invalidate(); state['here']=state['stack']=None
            for name in functions:
                if None not in functions[name]: functions[name].append(None)
            sync_directories(state)
            return
        if not external_wrapper and verb == 'shopt' and any(val in ('lastpipe','localvar_inherit') for _,val in argv[1:]):
            flags = ''.join(val[1:] for _,val in argv[1:] if val.startswith('-') and not val.startswith('--'))
            for option in ('lastpipe','localvar_inherit'):
                if any(val == option for _,val in argv[1:]):
                    if 's' in flags: state[option]=None if option == 'localvar_inherit' else True
                    elif 'u' in flags: state[option]=False
            return
        if not external_wrapper and verb == 'unset' and any(val=='-f' for _,val in argv[1:]):
            for _,val in argv[1:]:
                if not val.startswith('-'): functions.pop(val,None)
            return
        if verb == 'set' and not external_wrapper:
            for _, value in argv[1:]:
                if value == '--': break
                if value in ('physical',): continue
                if value.startswith('-') and 'P' in value[1:]: state['physical'] = True
                elif value.startswith('+') and 'P' in value[1:]: state['physical'] = False
            option_end = next((i for i, (_,value) in enumerate(argv) if value == '--'), len(argv))
            for i, (_, value) in enumerate(argv[1:option_end], 1):
                if value in ('-o', '+o') and i+1 < option_end and argv[i+1][1] == 'physical':
                    state['physical'] = value == '-o'
            return
        if verb in ('read', 'printf', 'mapfile', 'readarray'):
            if not external_wrapper: builtin_mutation(verb, argv)
            return
        if verb in ('export', 'readonly', 'declare', 'typeset', 'local'):
            if external_wrapper: return
            if verb == 'local' and not frames: return
            flags = [val for _, val in argv[1:] if val.startswith('-')]
            # Listing declarations does not create or mutate local variables.
            if any(any(ch in flag for ch in 'fFp') for flag in flags): return
            if any('I' in flag for flag in flags):
                raise UnresolvedShellPath('local inheritance option requires a bound Bash capability')
            # Declaration arguments expand before the builtin binds any names,
            # including `local DEST="$DEST"` and multiple assignment operands.
            declaration_bindings = {**state['vars'], '__unbound_shell_names__': set(state['unbound_vars'])}
            local_scope = frames and (verb == 'local' or (verb in ('declare','typeset') and not any('g' in flag for flag in flags)))
            if local_scope:
                for _, val in argv[1:]:
                    match = assignment_name.match(val)
                    name = match.group(1) if match else val
                    if re.fullmatch(r'[A-Za-z_]\w*', name) and localize(name):
                        inherit = state['localvar_inherit'] is True
                        # A newly declared bare scalar must not retain its caller's
                        # value. An inherited startup option is supported;
                        # unbound runtime/branch-selected inheritance is held
                        # because an older Bash may reject that shopt option.
                        if not inherit:
                            state['vars'].pop(name,None); state['unbound_vars'].add(name)
                        state['namerefs'].pop(name,None)  # never inherited
            # Function listings do not assign scalar variables. Arrays, integer
            # evaluation and namerefs cannot be represented as literal paths.
            if any('f' in flag or 'F' in flag for flag in flags): return
            uncertain = any(any(ch in flag for ch in 'aAin') for flag in flags) if verb != 'export' else False
            make_readonly = verb == 'readonly' or any('r' in flag for flag in flags)
            nameref = verb in ('declare', 'typeset', 'local') and any('n' in flag for flag in flags)
            for raw, val in argv[1:]:
                if val.startswith('-'): continue
                if assignment_name.match(val):
                    name = assignment_name.match(val).group(1)
                    if nameref:
                        try:
                            referent = _expand_shell_word(raw.split('=',1)[1], declaration_bindings, assignment=True)
                        except UnresolvedShellPath:
                            referent = None
                        state['namerefs'][name] = (frozenset([referent]) if referent and re.fullmatch(r'[A-Za-z_]\w*', referent) else None)
                    if uncertain: state['uncertain_attrs'].add(name)
                    if nameref:
                        state['vars'].pop(name, None); state['unbound_vars'].add(name)
                    else:
                        assign(raw, val, uncertain=uncertain, variable_view=declaration_bindings)
                elif re.fullmatch(r'[A-Za-z_]\w*', val):
                    name = val
                    if uncertain:
                        state['uncertain_attrs'].add(name)
                        if nameref:
                            state['namerefs'][name] = None
                            state['vars'].pop(name, None); state['unbound_vars'].add(name)
                        else:
                            invalidate(name)
                else:
                    continue
                if make_readonly: state['readonly'].add(name)
            return
        if verb == 'unset':
            if external_wrapper: return
            if any(val == '-f' for _, val in argv[1:]): return
            for _, name in argv[1:]:
                if re.fullmatch(r'[A-Za-z_]\w*', name) and name not in state['readonly']:
                    if name in state['namerefs']:
                        invalidate(name)
                        if any(val == '-n' for _,val in argv[1:]): state['namerefs'].pop(name, None)
                        continue
                    state['uncertain_attrs'].discard(name)
                    state['vars'].pop(name, None); state['unbound_vars'].discard(name)
                    if name == 'OLDPWD': state['old'] = None
            return
        if verb in ('cd','pushd','popd'):
            if external_wrapper:
                raise UnresolvedShellPath('directory builtin under external wrapper is not modeled')
            prior_cd = clone(state)
            mode, args, ended = state['physical'], [], False
            for raw, val in argv[1:]:
                if val == '--' and not ended:
                    ended = True; continue
                if not ended and verb == 'cd' and re.fullmatch(r'-[LPe@]+', val):
                    for option in val[1:]:
                        if option == 'L': mode = False
                        elif option == 'P': mode = True
                    continue
                args.append(raw)
            if verb in ('pushd', 'popd') and any(val == '-n' or re.fullmatch(r'[+-]\d+', val) for _,val in argv[1:]):
                # Stack rotations/options are not interpreted as filesystem paths.
                state['stack'] = None
                if not any(val == '-n' for _,val in argv[1:]): state['here'] = None
                sync_directories(state)
                return
            try:
                directory_vars = {**state['vars'], '__unbound_shell_names__': set(state['unbound_vars'])}
                for prefix_raw, prefix_val in prefix_assignments:
                    name = prefix_val.split('=', 1)[0]
                    try:
                        directory_vars[name] = _expand_shell_word(prefix_raw.split('=', 1)[1], state['vars'], assignment=True)
                        directory_vars['__unbound_shell_names__'].discard(name)
                    except UnresolvedShellPath:
                        directory_vars.pop(name, None)
                        directory_vars['__unbound_shell_names__'].add(name)
                if verb == 'popd':
                    if args or not state['stack']: raise UnresolvedShellPath('unbound popd stack')
                    dest = state['stack'].pop()
                elif verb == 'pushd' and not args:
                    if not state['stack']: raise UnresolvedShellPath('unbound pushd stack')
                    dest, state['stack'][-1] = state['stack'][-1], state['here']
                else:
                    value = _expand_shell_word(args[0], {**state['vars'], '__unbound_shell_names__': state['unbound_vars']}) if args else _expand_shell_word('~', directory_vars)
                    if value == '-':
                        if any(val.startswith('OLDPWD=') for _, val in prefix_assignments):
                            if 'OLDPWD' not in directory_vars: raise UnresolvedShellPath('unbound prefix OLDPWD')
                            dest = cd_destinations(directory_vars['OLDPWD'], directory_vars, physical=mode)
                        else:
                            dest = state['old']
                        if not dest: raise UnresolvedShellPath('cd - has no bound OLDPWD')
                    else:
                        dest = cd_destinations(value, directory_vars, physical=mode)
                    if verb == 'pushd' and state['stack'] is not None:
                        state['stack'].append(state['here'])
                state['old'], state['here'] = state['here'], dest
                sync_directories(state)
            except UnresolvedShellPath:
                state['here'] = None
                sync_directories(state)
            return
        prior_cd = None
        rest, options_ended = [], False
        arguments = iter(argv[1:])
        for raw, val in arguments:
            if val == '--' and not options_ended:
                options_ended = True
            elif not options_ended and verb in ('touch', 'truncate'):
                # -r reads its operand; it is not a write target. Recognize
                # supported no-argument flag bundles ending in r as well.
                flags = 'acfhm' if verb == 'touch' else 'co'
                separated_reference = val in ('-r', '--reference') or bool(
                    re.fullmatch(r'-[' + flags + r']+r', val))
                if separated_reference:
                    reference = next(arguments, None)
                    if reference is None:
                        raise UnresolvedShellPath('reference option has no operand: ' + val)
                    _expand_shell_word(reference[0], state['vars'])
                elif val.startswith('--reference=') or re.fullmatch(r'-[' + flags + r']*r.+', val):
                    _expand_shell_word(raw, state['vars'])
                elif not val.startswith('-'):
                    rest.append((raw,val))
            elif options_ended or not val.startswith('-'):
                rest.append((raw,val))
        if verb in DEST_LAST:
            target = None
            for i,(raw,val) in enumerate(argv[1:],1):
                if val in ('-t','--target-directory') and i+1 < len(argv): target = argv[i+1][0]
                elif val.startswith('--target-directory='): target = raw.split('=',1)[1]
                elif val.startswith('-t') and len(val)>2: target = raw[2:]
            if target is not None: add_operand(target)
            elif rest: add_operand(rest[-1][0])
        elif verb in ALL_ARGS or verb == 'tee':
            for raw,_ in rest: add_operand(raw)
        elif verb == 'sed' and any(val.startswith('-i') for _,val in argv[1:]):
            # sed's expression is text, not a target; remaining operands are files.
            for raw,_ in rest[1:]: add_operand(raw)
        elif verb == 'dd':
            for raw,val in argv[1:]:
                if val.startswith('of='): add_operand(raw[3:])

    def run_flat(sequence):
        nonlocal state, segment, prior_cd, pipeline, alternative, scopes
        for token in sequence:
            raw,val,kind = token
            if kind != 'op' or val not in ('\n',';','&&','||','|','&','(',')','{','}'):
                segment.append(token)
                continue
            before = clone(state)
            process(segment); segment = []
            if val == '(':
                scopes.append(clone(state))
            elif val == ')':
                if scopes: state = scopes.pop()
            elif val == '|':
                if pipeline is None: pipeline = before
                state = clone(pipeline)  # every pipeline stage executes in its own shell scope
            elif val == '&':
                state = before
            elif val == '&&' and prior_cd is not None:
                # After a failed cd, && skips its RHS; a later ; resumes in the old cwd.
                if state['here'] is None or not all(os.path.isdir(p) and os.access(p, os.X_OK) for p in state['here']):
                    alternative = merge(alternative, prior_cd) if alternative is not None else prior_cd
            elif val == '||' and prior_cd is not None:
                alternative = merge(alternative, state) if alternative is not None else clone(state)
                # The right-hand command is the failed-cd branch, in the original cwd.
                state = prior_cd
                prior_cd = None
            if val in (';','\n','&&','||') and pipeline is not None:
                state = merge(pipeline,state) if state['lastpipe'] is not False else pipeline
                pipeline = None
            if val in (';','\n'):
                if prior_cd is not None and (state['here'] is None or not all(
                        os.path.isdir(p) and os.access(p, os.X_OK) for p in state['here'])):
                    state = merge(state, prior_cd)
                if alternative is not None:
                    state = merge(state, alternative)
                    alternative = None
                prior_cd = None
        process(segment); segment = []
    parser = ShellProgram(tokens)
    program = parser.sequence()
    if parser.i != len(tokens): raise UnresolvedShellPath('unmatched shell compound terminator')
    functions, frames, analysis_steps = {}, [], 0

    def clone_functions():
        return {name:list(values) for name,values in functions.items()}

    def merge_functions(variants):
        result = {}
        for name in set().union(*(set(v) for v in variants)):
            values = []
            for variant in variants:
                for value in variant.get(name,[None]):
                    if value not in values: values.append(value)
            result[name] = values
        return result

    def literal_truth(nodes):
        meaningful = [n for n in nodes if not (n[0]=='flat' and all(t[2]=='op' and t[1] in (';','\n') for t in n[1]))]
        if len(meaningful)!=1 or meaningful[0][0]!='flat': return None
        words = meaningful[0][1]
        if not words or words[0][2] != 'word' or words[0][1] in functions: return None
        return True if words[0][1] in ('true',':') else False if words[0][1]=='false' else None

    def localize(name):
        if not frames: return False
        frame = frames[-1]
        if name not in frame:
            frame[name] = (name in state['vars'], state['vars'].get(name),
                           name in state['unbound_vars'], name in state['readonly'],
                           name in state['uncertain_attrs'], state['namerefs'].get(name), name in state['namerefs'])
            return True
        return False

    def evaluate(nodes, depth=0):
        nonlocal state, pipeline, prior_cd, alternative, segment, functions, analysis_steps
        if depth > 24: raise UnresolvedShellPath('shell analysis nesting/recursion limit')
        chunk = []
        def flush():
            nonlocal chunk
            if chunk: run_flat(chunk); chunk = []
        for index, node in enumerate(nodes):
            analysis_steps += 1
            if analysis_steps > 4096: raise UnresolvedShellPath('shell analysis work limit')
            kind = node[0]
            if kind == 'flat':
                words = node[1]
                argv = [t for t in words if t[2] in ('word','fd')]
                k = 0
                while k < len(argv) and re.match(r'^[A-Za-z_]\w*(?:\[.*\])?\+?=',argv[k][1]): k += 1
                verb = argv[k][1] if k < len(argv) else None
                if verb in functions:
                    flush()
                    if verb not in functions:
                        chunk.extend(words); continue
                    # Inspect call-site redirections in the caller's environment.
                    process(words)
                    call_state, call_functions = clone(state), clone_functions()
                    following = nodes[index+1][1][0][1] if index+1 < len(nodes) and nodes[index+1][0]=='flat' and nodes[index+1][1] else None
                    call_isolated = following in ('|','&') or (pipeline is not None and state['lastpipe'] is False)
                    call_outcomes, call_function_outcomes = [], []
                    for variant in call_functions[verb]:
                        state, functions = clone(call_state), {name:list(values) for name,values in call_functions.items()}
                        if variant is None:
                            call_outcomes.append(clone(state));call_function_outcomes.append(clone_functions());continue
                        saved = {}
                        for raw, val, _ in argv[:k]:
                            name = val.split('=',1)[0]
                            saved[name] = (name in state['vars'],state['vars'].get(name),name in state['unbound_vars'])
                            assign(raw,val)
                        frames.append({})
                        before = clone(state)
                        body, subshell = variant
                        evaluate(body, depth+1)
                        for name,(present,value,unbound,readonly,uncertain,referents,has_ref) in frames.pop().items():
                            if present: state['vars'][name] = value
                            else: state['vars'].pop(name,None)
                            if unbound: state['unbound_vars'].add(name)
                            else: state['unbound_vars'].discard(name)
                            if readonly: state['readonly'].add(name)
                            else: state['readonly'].discard(name)
                            if uncertain: state['uncertain_attrs'].add(name)
                            else: state['uncertain_attrs'].discard(name)
                            if has_ref: state['namerefs'][name]=referents
                            else: state['namerefs'].pop(name,None)
                        for name,(present,value,unbound) in saved.items():
                            if present: state['vars'][name] = value
                            else: state['vars'].pop(name,None)
                            if unbound: state['unbound_vars'].add(name)
                            else: state['unbound_vars'].discard(name)
                        if subshell: state = before
                        call_outcomes.append(clone(state)); call_function_outcomes.append(clone_functions())
                    state = call_outcomes[0]
                    for outcome in call_outcomes[1:]: state = merge(state,outcome)
                    functions = merge_functions(call_function_outcomes)
                    if call_isolated: state, functions = call_state, call_functions
                    elif pipeline is not None:
                        state = merge(call_state,state)
                        functions = merge_functions([call_functions,functions])
                    prior_cd = None
                else:
                    chunk.extend(words)
                continue
            flush()
            if kind == 'function':
                functions[node[1]] = [(node[2],node[3])]; continue
            before, before_functions = clone(state), clone_functions()
            outer_pipeline, outer_alternative = pipeline, alternative
            pipeline = alternative = None
            next_operator = nodes[index+1][1][0][1] if index+1 < len(nodes) and nodes[index+1][0]=='flat' and nodes[index+1][1] else None
            isolated = next_operator in ('|','&') or (outer_pipeline is not None and state['lastpipe'] is False)
            if kind == 'redirected':
                process(node[2])
                evaluate([node[1]],depth+1)
            elif kind == 'group':
                evaluate(node[1],depth+1)
                if node[2]: state, functions = before, before_functions
            elif kind == 'if':
                outcomes, function_outcomes = [], []
                remaining, remaining_functions = clone(state), clone_functions()
                exhausted = False
                for condition, body in node[1]:
                    state, functions = clone(remaining), {name:list(values) for name,values in remaining_functions.items()}
                    truth = literal_truth(condition)
                    evaluate(condition,depth+1)
                    remaining, remaining_functions = clone(state), clone_functions()
                    if truth is not False:
                        evaluate(body,depth+1); outcomes.append(clone(state)); function_outcomes.append(clone_functions())
                    if truth is True:
                        exhausted = True; break
                if not exhausted:
                    state, functions = clone(remaining), remaining_functions
                    evaluate(node[2],depth+1);outcomes.append(clone(state));function_outcomes.append(clone_functions())
                state = outcomes[0]
                for outcome in outcomes[1:]: state = merge(state,outcome)
                functions = merge_functions(function_outcomes)
            elif kind == 'for':
                name, values, body = node[1:]
                expanded = None
                if values is not None:
                    try:
                        expanded = [_expand_shell_word(raw,{**state['vars'],'__unbound_shell_names__':state['unbound_vars']}) for raw,_,_ in values]
                    except UnresolvedShellPath: expanded = None
                if expanded is not None:
                    if len(expanded)>64: raise UnresolvedShellPath('for-loop analysis limit')
                    for value in expanded:
                        # Already expanded once; assignment never evaluates the result again.
                        state['vars'][name] = value; state['unbound_vars'].discard(name)
                        evaluate(body,depth+1)
                    functions = merge_functions([before_functions,clone_functions()])
                    state = merge(before,state)  # break/return and zero-iteration alternatives
                else:
                    invalidate(name)
                    entry = clone(state); evaluate(body,depth+1)
                    changed = clone(state)
                    functions = merge_functions([before_functions,clone_functions()])
                    if changed['here'] != entry['here'] or changed['vars'] != entry['vars']:
                        state = merge(entry,changed)
                    if changed['here'] != entry['here']:
                        state['here']=state['stack']=None; sync_directories(state)
                    if changed['here'] != entry['here'] or changed['vars'] != entry['vars']:
                        evaluate(body,depth+1)  # inspect later iterations with unresolved cwd
                    state = merge(entry,state)
            elif kind == 'loop':
                truth = literal_truth(node[1])
                evaluate(node[1],depth+1)
                if truth is (True if node[3] else False):
                    pipeline, alternative = outer_pipeline, outer_alternative
                    prior_cd = None
                    continue
                entry = clone(state); evaluate(node[2],depth+1)
                changed = clone(state)
                functions = merge_functions([before_functions,clone_functions()])
                state = merge(entry,changed)
                if changed['here'] != entry['here'] or changed['vars'] != entry['vars']:
                    if changed['here'] != entry['here']:
                        state['here']=state['stack']=None; sync_directories(state)
                    evaluate(node[1],depth+1); evaluate(node[2],depth+1)
                    state = merge(entry,state)
            if isolated: state, functions = before, before_functions
            elif outer_pipeline is not None:
                state = merge(before,state)
                functions = merge_functions([before_functions,functions])
            pipeline, alternative = outer_pipeline, outer_alternative
            prior_cd = None
            if state['here'] is not None and len(state['here'])>64:
                raise UnresolvedShellPath('directory-state analysis limit')
        flush()

    evaluate(program)

    return targets

def main():
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        _fail_closed(f"stdin parse: {e}")
    try:
        tool = data.get("tool_name", "") or ""
        ti = data.get("tool_input", {}) or {}
        cwd = data.get("cwd") or os.getcwd() or ALLOWED_ROOTS_RAW[0]
        roots = _allowed_roots()

        if tool in ("Write", "Edit", "MultiEdit"):
            path = ti.get("file_path", "") or ""
            if path and not _under_allowed(_resolve(path, cwd), roots):
                _deny(
                    f"BLOCKED by out-of-bounds guardrail: writing to '{path}' is OUTSIDE the allowed "
                    "roots. Deliverables go in THIS project only — your own chat folder is "
                    "'sessions/the roster lane/'. Never write into another agent's workspace "
                    "(e.g. the Codex workspace) or anywhere outside the workspace root "
                    f"('{ALLOWED_ROOTS_RAW[0]}'). Produce the file here and hand off the "
                    "path; the other chat/agent pulls it. See memory: shared-tool-and-corpus-boundary, "
                    "patch-chat-folder-is-only-place.")
            return 0

        if tool == "NotebookEdit":
            path = ti.get("notebook_path", "") or ti.get("file_path", "") or ""
            if path and not _under_allowed(_resolve(path, cwd), roots):
                _deny(f"BLOCKED by out-of-bounds guardrail: editing notebook '{path}' is OUTSIDE the "
                      "allowed roots (this project + .claude + tmp). Work inside "
                      f"'{ALLOWED_ROOTS_RAW[0]}' only.")
            return 0

        if tool == "Bash":
            cmd = ti.get("command", "") or ""
            bad = [t for t in bash_write_targets(cmd, cwd) if not _under_allowed(t, roots)]
            if bad:
                _deny(
                    "BLOCKED by out-of-bounds guardrail: this Bash command WRITES to a path outside "
                    f"this project: {bad[:4]}. Never write into another agent's workspace (e.g. "
                    "the Codex workspace) or outside the workspace root "
                    f"('{ALLOWED_ROOTS_RAW[0]}'). Reading such a path is fine; only the "
                    "write target is blocked. Produce the file in this project and hand off the path. "
                    "See memory: shared-tool-and-corpus-boundary.")
            return 0

        return 0
    except (UnresolvedShellPath, ValueError) as e:
        _deny(f"Cannot bind this Bash write safely: {e}. Use an explicit resolved path or a simpler command.")
    except SystemExit:
        raise
    except Exception as e:
        _fail_closed(f"main: {e}")

if __name__ == "__main__":
    main()
