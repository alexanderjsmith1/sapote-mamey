"""Portable outgroup registry location and provenance; location never confers authority."""
from pathlib import Path
import hashlib
import os


class RegistryAuthorityError(ValueError):
    """A reference snapshot cannot supply an implicitly approved project outgroup."""


def shipped_registry_path():
    return Path(__file__).resolve().parent / "data" / "outgroup_registry.tsv"


def outgroup_registry_path():
    explicit = os.environ.get("OUTGROUP_REGISTRY")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError("Explicit OUTGROUP_REGISTRY does not exist: " + str(path))
        return path
    marker = Path("OFFICIAL_DATA") / "OUTGROUP_REGISTRY.tsv"
    configured = [os.environ.get(k) for k in ("MAMEY_DATA_ROOT", "SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT")]
    for root in configured:
        if root:
            path = Path(root).expanduser().resolve() / marker
            if path.is_file():
                return path
    if any(configured):
        return shipped_registry_path()
    cwd = Path.cwd().resolve()
    here = Path(__file__).resolve().parent
    candidates = []
    for root in [cwd, *cwd.parents, here, *here.parents]:
        path = root / marker
        if path.is_file() and path not in candidates:
            candidates.append(path)
    if candidates:
        hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in candidates}
        if len(hashes) != 1:
            raise RegistryAuthorityError("Conflicting discovered registries; select OUTGROUP_REGISTRY explicitly")
        return candidates[0]
    return shipped_registry_path()


def registry_binding(path=None):
    path = Path(path) if path is not None else outgroup_registry_path()
    path = path.resolve()
    return {"name": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "authority": "BUNDLED_REFERENCE_ONLY" if path == shipped_registry_path() else "EXTERNAL_SELECTED",
            "scientific_acceptance": "NOT_ASSERTED"}
