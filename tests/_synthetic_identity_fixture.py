"""Declared fabricated identities for parser/privacy tests, never empirical subjects.

Case indices are independent test parameters, not encodings of removed identities.
A canary remains private-shaped and must fail the unchanged privacy gate when seeded
into an isolated negative-control input. This helper grants no public exception.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

_ID = re.compile(r"\b(?:AS|AJS)-?\d+\b|\bPENDING-[A-Z0-9]+\b", re.I)
_TEXT_SUFFIXES = {".py", ".json", ".txt", ".csv", ".tsv", ".md", ".yml", ".yaml"}


def _normalise(value: str) -> str:
    return re.sub(r"^(AS|AJS)(\d)", r"\1-\2", value.upper())


@lru_cache(maxsize=1)
def _repository_identity_tokens() -> frozenset[str]:
    """Read authority/roster text in place; never echo entries or traverse research."""
    root = Path(__file__).resolve().parents[1]
    allowlist = root / "tools" / "test_synthetic_ids.txt"
    if not allowlist.is_file() or allowlist.is_symlink():
        raise AssertionError("synthetic identity fixture requires the bound repository allowlist")
    tokens: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in {"tests", ".git", "__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        named_authority = any(word in path.name.lower() for word in
                              ("roster", "registry", "exclusion", "synthetic_ids"))
        policy_authority = path.name in {"redact_private_ids.py", "redact_public_tier.py", "public_release_audit.py",
                                           "privacy_profile.py", "private_policy.py", "published_registry.py"}
        if not (named_authority or policy_authority or "OFFICIAL_DATA" in relative.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            raise AssertionError("synthetic identity fixture cannot read repository authority") from None
        tokens.update(_normalise(match.group()) for match in _ID.finditer(text))
    return frozenset(tokens)


def synthetic_namespace_id(namespace: str, *, width: int | None = 3,
                           case_index: int = 917, separator: bool = True) -> str:
    """Fabricate a namespace canary; a collision fails setup, never adds an exemption."""
    if namespace not in {"AS", "AJS", "PENDING"} or type(case_index) is not int or case_index < 0:
        raise AssertionError("invalid synthetic identity parameters")
    if namespace == "PENDING":
        token = namespace + "-" + "SYNTHETICCASE" + str(case_index)
    else:
        if type(width) is not int or width < 1 or case_index >= 10 ** width:
            raise AssertionError("synthetic numeric identity must preserve its declared width")
        token = namespace + ("-" if separator else "") + str(case_index).zfill(width)
    if _normalise(token) in _repository_identity_tokens():
        raise AssertionError("synthetic identity collides with repository authority; fixture setup refused")
    return token
