"""Read-only advisory report-path admission; not a privacy-clearance API."""
from pathlib import Path
import argparse
import os
import re

REPORT_EXT = {'.md', '.csv', '.txt', '.tsv', '.docx'}
PRIVATE_PARTS = {'private', 'official_data', 'cohort', 'merged_cohort', '.git'}
PRIVATE_LEAVES = {'strain_genus.csv', 'exclusions.json', 'assembly_authority.tsv',
                  'roster.csv', 'roster.tsv'}
EXEMPT = ('scratchpad', '_provenance', 'guardrail', 'claim_safety', 'patches for next cut')


def _private_parts(path):
    return any(part.casefold() in PRIVATE_PARTS for part in path.parts)


def _private_selection(candidate, root):
    """Check a selected home and its distinct ancestry, excluding shared/OS prefixes."""
    common = Path(os.path.commonpath((root, candidate)))
    relative = candidate.relative_to(common)
    parts = relative.parts
    if common == Path(candidate.anchor) and parts[:2] in (('private', 'tmp'), ('private', 'var')):
        parts = parts[1:]  # macOS OS prefix, not a project payload directory
    return candidate.name.casefold() in PRIVATE_PARTS or _private_parts(Path(*parts))


def in_scope(value, workspace, report_root=None):
    try:
        raw = str(value)
        path = Path(raw)
        if not raw or re.match(r'^[A-Za-z]:[\\/]|^\\\\', raw) or '..' in path.parts:
            return False
        root = Path(workspace).resolve(strict=True)
        lexical = path if path.is_absolute() else root / path
        target = lexical.resolve(strict=True)
        if target.suffix.lower() not in REPORT_EXT or not target.is_file():
            return False
        if target.name.casefold() in PRIVATE_LEAVES:
            return False
        # Examine paths relative to the selected workspace, not an OS /private prefix.
        for candidate in (lexical, target):
            if candidate.is_relative_to(root) and _private_parts(candidate.relative_to(root)):
                return False
        conventional = root / 'strain_data'
        allowed = [(conventional, False)]
        if report_root:
            selected = Path(report_root)
            selected = selected if selected.is_absolute() else root / selected
            allowed.append((Path(os.path.abspath(selected)), True))
        for lexical_home, explicit in allowed:
            if not lexical_home.is_dir():
                continue
            home = lexical_home.resolve(strict=True)
            # An implicit conventional symlink cannot grant external admission.
            if not explicit and not home.is_relative_to(root):
                continue
            if _private_selection(lexical_home, root) or _private_selection(home, root):
                continue
            if not target.is_relative_to(home):
                continue
            relative = target.relative_to(home)
            if _private_parts(relative) or any(token in str(relative).casefold() for token in EXEMPT):
                return False
            if lexical.is_relative_to(home) and _private_parts(lexical.relative_to(home)):
                return False
            return True
        return False
    except (OSError, ValueError, RuntimeError):
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--report-root')
    args = parser.parse_args()
    raise SystemExit(0 if in_scope(args.path, args.root, args.report_root) else 1)
