"""Active prose view for Mode B verification; offsets and line numbers stay stable.

Comments and code examples cannot supply section headings, profile declarations or
comparison tables. This small scanner covers HTML comments, CommonMark-style
backtick/tilde fences, and indented code without a rendering dependency.
"""
from __future__ import annotations

import re


def _mask(text: str) -> str:
    return ''.join(char if char in '\r\n' else ' ' for char in text)


def active_markdown(text: str, *, preserve_comments: bool = False) -> str:
    # Comment preservation is only for explicit author-placeholder diagnostics;
    # callers must use the default masked view for evidence and heading admission.
    out, fence_char, fence_size, in_comment = [], None, 0, False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if fence_char is not None:
            closing = re.fullmatch(r" {0,3}" + re.escape(fence_char) + "{" + str(fence_size) + r",}[ \t]*", stripped)
            out.append(_mask(line))
            if closing:
                fence_char, fence_size = None, 0
            continue
        # Code takes precedence over comment syntax: a literal '<!--' inside a
        # fenced example must not conceal the following active document.
        if not in_comment:
            opening = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", stripped)
            if opening and not (opening.group(1)[0] == "`" and "`" in opening.group(2)):
                fence_char, fence_size = opening.group(1)[0], len(opening.group(1))
                out.append(_mask(line))
                continue
            if re.match(r"^(?: {4}|\t)", line):
                out.append(_mask(line))
                continue
        parts, position = [], 0
        while position < len(line):
            if in_comment:
                end = line.find("-->", position)
                stop = len(line) if end < 0 else end + 3
                parts.append(line[position:stop] if preserve_comments else _mask(line[position:stop]))
                position = stop
                in_comment = end < 0
            else:
                start = line.find("<!--", position)
                if start < 0:
                    parts.append(line[position:])
                    break
                parts.append(line[position:start])
                position, in_comment = start, True
        out.append("".join(parts))
    return "".join(out)


_PROFILE_TOKENS = frozenset({"FINISHED_CURRENT_EVIDENCE", "FINISHED_FULL48_CURRENT_EVIDENCE",
                             "FINISHED_FULL50_CURRENT50_V2", "PUBLICATION_REVIEW_CANDIDATE"})


def verification_markdown(text: str) -> str:
    """Active view plus the deliberate first-line canonical metadata profile.

    A canonical `MODE B | canonical_identity: ...` header is machine metadata,
    not a historical example. Its recognized profile may activate stricter
    checks even though the header itself is hidden from readers. This does not
    validate its identity, contract hash or evidence; those remain separate
    bindings. Only the current first line is admitted, never later comments.
    """
    view = active_markdown(text)
    first = text.splitlines(keepends=True)[0] if text else ""
    header = re.fullmatch(r"<!--\s*MODE B\s*\|([^\r\n]*)-->[ \t]*(?:\r?\n)?", first)
    if not header:
        return view
    fields = {}
    for item in header.group(1).split("|"):
        key, separator, value = item.partition(":")
        if separator:
            fields[key.strip()] = value.strip()
    profile = fields.get("profile")
    if not fields.get("canonical_identity") or profile not in _PROFILE_TOKENS:
        return view
    # Do not claim this metadata verifies its contract or identity. Retaining the
    # declared strict profile prevents a hidden header from downgrading a card.
    declaration = "**Document state:** " + profile
    width = len(first.rstrip("\r\n"))
    if len(declaration) > width:
        return view  # a canonical header is always longer than its profile
    replacement = declaration + " " * (width - len(declaration))
    return replacement + view[width:]
