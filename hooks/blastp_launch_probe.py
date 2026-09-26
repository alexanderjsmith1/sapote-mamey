#!/usr/bin/env python3
"""List local script operands a shell command would execute, without executing them."""
import os
import shlex
import sys


SEPARATORS = {";", "&&", "||", "|", "|&", "&"}
REDIRECTIONS = {">", ">>", "<", "<<", "<>", ">|", ">&", "<&", "&>", "&>>"}
FD_REDIRECTIONS = REDIRECTIONS - {"&>", "&>>"}
INTERPRETERS = {"bash", "sh", "zsh", "dash", "ksh", "python", "python2", "python3"}
WRAPPERS = {"env", "nohup", "caffeinate"}


def _strip_redirections(parts):
    """Remove shell redirection operands before looking for executable scripts."""
    out = []
    index = 0
    while index < len(parts):
        token = parts[index]
        # With punctuation tokens, `2>&1` is `2`, `>&`, `1` and `&>log` is
        # `&>`, `log`. Keep command separators such as `cmd & >log next` distinct.
        if token.isdecimal() and index + 1 < len(parts) and parts[index + 1] in FD_REDIRECTIONS:
            index += 1
            token = parts[index]
        if token in REDIRECTIONS:
            index += 1
            if index < len(parts) and parts[index] not in SEPARATORS | REDIRECTIONS:
                index += 1
            continue
        out.append(token)
        index += 1
    return out


def _assignment(token):
    if "=" not in token or token.startswith(("-", "/")):
        return False
    name = token.split("=", 1)[0]
    return name.replace("_", "").isalnum()


def _candidate(words):
    words = list(words)
    while words and _assignment(words[0]):
        words.pop(0)
    while words and os.path.basename(words[0]) in WRAPPERS:
        words.pop(0)
        while words and (words[0].startswith("-") or _assignment(words[0])):
            words.pop(0)
    if not words:
        return None
    if os.path.basename(words[0]) in INTERPRETERS:
        for token in words[1:]:
            if token in ("-c", "--command"):
                return None
            if token == "--" or token.startswith("-"):
                continue
            return token
        return None
    return words[0]


def candidates(command):
    # Refuse shell expansions and multiline commands rather than guessing their execution.
    if "$(" in command or "`" in command or "\n" in command:
        return []
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        lexer.commenters = ""
        parts = _strip_redirections(list(lexer))
    except ValueError:
        return []
    segments = [[]]
    for token in parts:
        if token in SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    found = []
    for segment in segments:
        path = _candidate(segment)
        if path and path not in found:
            found.append(path)
    return found


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return 2
    for path in candidates(args[0]):
        sys.stdout.buffer.write(os.fsencode(path) + b"\0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
