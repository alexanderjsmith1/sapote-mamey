from __future__ import annotations

import ast
from pathlib import Path
import re
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[1]
STATUS_LINE_RE = re.compile(
    r"^> \*\*(?:Build status|Current-tree status)\.\*\* (?P<body>.+)$",
    re.MULTILINE,
)
BUNDLE_VERSION_RE = re.compile(
    r"\*\*Bundle version:\*\*\s*`sapote-mamey-v([0-9]+\.[0-9]+\.[0-9]+)`",
    re.IGNORECASE,
)
AUTHORITATIVE_VERSION_RE = re.compile(
    r"\*\*Authoritative bundle version:\*\*\s*`([0-9]+\.[0-9]+\.[0-9]+)`",
    re.IGNORECASE,
)
ARTIFACT_STATUS_RE = re.compile(
    r"\*\*Artifact status:\*\*\s*(.+)",
    re.IGNORECASE,
)
VERSION_LITERAL_RE = re.compile(r"\bv[0-9]+\.[0-9]+\.[0-9]+\b")
def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _pyproject_bundle_version(text: str) -> str:
    data = tomllib.loads(text)
    value = data.get("tool", {}).get("sapote", {}).get("bundle_version")
    assert isinstance(value, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value)
    return value


def _package_bundle_version(text: str) -> str:
    tree = ast.parse(text)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "BUNDLE_VERSION" for target in node.targets):
            assert isinstance(node.value, ast.Constant)
            assert isinstance(node.value.value, str)
            return node.value.value
    raise AssertionError("mamey/__init__.py does not define a literal BUNDLE_VERSION")


def _manifest_contract(text: str) -> tuple[str, str]:
    bundle_match = BUNDLE_VERSION_RE.search(text)
    authority_match = AUTHORITATIVE_VERSION_RE.search(text)
    status_match = ARTIFACT_STATUS_RE.search(text)
    assert bundle_match, "RELEASE_MANIFEST.md lacks the bundle-version anchor"
    assert authority_match, "RELEASE_MANIFEST.md lacks the authoritative-version anchor"
    assert status_match, "RELEASE_MANIFEST.md lacks the artifact-status anchor"
    assert bundle_match.group(1) == authority_match.group(1)
    return bundle_match.group(1), status_match.group(1).strip()


def _assert_front_door_contract(text: str, version_locator: str, status_locator: str) -> None:
    match = STATUS_LINE_RE.search(text)
    assert match, "front door lacks the governed status line"
    status_line = match.group("body")
    assert "records its validation results in the release manifest" in status_line
    assert "validated software artifact" not in status_line
    assert "signed public release" not in status_line.lower()
    assert version_locator in status_line
    assert status_locator in status_line
    assert VERSION_LITERAL_RE.search(status_line) is None, (
        "front-door status must not hardcode a cut-specific bundle version"
    )
    assert "release profile: public_release" not in status_line.lower()


def _assert_release_status_contract(
    pyproject_text: str,
    package_init_text: str,
    manifest_text: str,
    start_here_text: str,
    public_guide_text: str,
) -> None:
    canonical_version = _pyproject_bundle_version(pyproject_text)
    assert _package_bundle_version(package_init_text) == canonical_version
    manifest_version, manifest_status = _manifest_contract(manifest_text)
    assert manifest_version == canonical_version, (
        "RELEASE_MANIFEST.md must match the canonical bundle version"
    )
    assert manifest_status in {"validated CODE archive", "CI correction candidate"}, (
        "unrecognized artifact status"
    )
    assert "signed public release" not in manifest_status.lower()
    _assert_front_door_contract(
        start_here_text,
        "[`pyproject.toml`](pyproject.toml)",
        "[`RELEASE_MANIFEST.md`](RELEASE_MANIFEST.md)",
    )
    _assert_front_door_contract(
        public_guide_text,
        "[`pyproject.toml`](../pyproject.toml)",
        "[`RELEASE_MANIFEST.md`](../RELEASE_MANIFEST.md)",
    )


def test_front_doors_bind_canonical_version_and_release_status_authorities():
    _assert_release_status_contract(
        _load_text(ROOT / "pyproject.toml"),
        _load_text(ROOT / "mamey" / "__init__.py"),
        _load_text(ROOT / "RELEASE_MANIFEST.md"),
        _load_text(ROOT / "README.md"),
        _load_text(ROOT / "docs" / "PUBLIC_RELEASE_GUIDE.md"),
    )
    assert (ROOT / "pyproject.toml").is_file()
    assert (ROOT / "RELEASE_MANIFEST.md").is_file()


def test_stale_front_door_and_manifest_agreement_cannot_override_pyproject():
    pyproject_text = _load_text(ROOT / "pyproject.toml")
    canonical_version = _pyproject_bundle_version(pyproject_text)
    stale_version = "0.0.0"
    assert stale_version != canonical_version

    stale_manifest = _load_text(ROOT / "RELEASE_MANIFEST.md").replace(
        f"sapote-mamey-v{canonical_version}",
        f"sapote-mamey-v{stale_version}",
    ).replace(
        f"`{canonical_version}`",
        f"`{stale_version}`",
    )
    stale_start = _load_text(ROOT / "README.md").replace(
        "This CODE archive",
        f"This v{stale_version} CODE tree",
        1,
    )
    stale_guide = _load_text(ROOT / "docs" / "PUBLIC_RELEASE_GUIDE.md").replace(
        "This CODE archive",
        f"This v{stale_version} CODE tree",
        1,
    )

    with pytest.raises(AssertionError, match="canonical bundle version"):
        _assert_release_status_contract(
            pyproject_text,
            _load_text(ROOT / "mamey" / "__init__.py"),
            stale_manifest,
            stale_start,
            stale_guide,
        )


def test_unsubstantiated_signed_release_language_is_not_admitted():
    manifest = ARTIFACT_STATUS_RE.sub(
        "**Artifact status:** signed public release",
        _load_text(ROOT / "RELEASE_MANIFEST.md"),
        count=1,
    )
    with pytest.raises(AssertionError):
        _assert_release_status_contract(
            _load_text(ROOT / "pyproject.toml"),
            _load_text(ROOT / "mamey" / "__init__.py"),
            manifest,
            _load_text(ROOT / "README.md"),
            _load_text(ROOT / "docs" / "PUBLIC_RELEASE_GUIDE.md"),
        )


@pytest.mark.parametrize("status", ["validated CODE archive", "CI correction candidate"])
def test_front_doors_defer_to_manifest_for_both_artifact_states(status):
    manifest = ARTIFACT_STATUS_RE.sub(
        "**Artifact status:** " + status,
        _load_text(ROOT / "RELEASE_MANIFEST.md"), count=1,
    )
    _assert_release_status_contract(
        _load_text(ROOT / "pyproject.toml"),
        _load_text(ROOT / "mamey" / "__init__.py"), manifest,
        _load_text(ROOT / "README.md"),
        _load_text(ROOT / "docs" / "PUBLIC_RELEASE_GUIDE.md"),
    )


@pytest.mark.parametrize("status", ["", "unknown", "signed public release"])
def test_unrecognized_artifact_status_is_rejected(status):
    manifest = ARTIFACT_STATUS_RE.sub(
        "**Artifact status:** " + status,
        _load_text(ROOT / "RELEASE_MANIFEST.md"), count=1,
    )
    with pytest.raises(AssertionError):
        _assert_release_status_contract(
            _load_text(ROOT / "pyproject.toml"),
            _load_text(ROOT / "mamey" / "__init__.py"), manifest,
            _load_text(ROOT / "README.md"),
            _load_text(ROOT / "docs" / "PUBLIC_RELEASE_GUIDE.md"),
        )


def test_front_door_cannot_replace_manifest_with_unconditional_validation_claim():
    readme = _load_text(ROOT / "README.md").replace(
        "records its validation results in the release manifest",
        "is a validated software artifact", 1,
    )
    with pytest.raises(AssertionError):
        _assert_release_status_contract(
            _load_text(ROOT / "pyproject.toml"),
            _load_text(ROOT / "mamey" / "__init__.py"),
            _load_text(ROOT / "RELEASE_MANIFEST.md"), readme,
            _load_text(ROOT / "docs" / "PUBLIC_RELEASE_GUIDE.md"),
        )
