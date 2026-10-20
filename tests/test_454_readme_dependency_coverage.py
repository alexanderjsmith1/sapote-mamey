"""v9.7.454: everything the shipped code depends on is named in README.md.

The scan reads the shipped code and collects:
- third-party Python imports (not standard library, not a bundle module);
- external programs started by name (shutil.which, a subprocess argument list, `command -v`);
- R packages loaded by shipped .R scripts;
- web hosts written into the code.

Each must be named in README.md, or be listed in ALLOWED below with a reason. A new dependency therefore
fails the cut until the README says what it is and why a user would need it.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("mamey", "tools", "deliverable_tools", "bundle_support", "hooks", "sapote_hooks", "scripts", "packaging")
SKIP_PARTS = {"__pycache__", "_vendor", "tests", "templates"}

# Import names whose README spelling differs (PyPI distribution names).
ALIASES = {
    "Bio": ("Biopython",), "PIL": ("Pillow",), "docx": ("python-docx",), "pptx": ("python-pptx",),
    "yaml": ("PyYAML",), "shapefile": ("pyshp",), "dna_features_viewer": ("dna-features-viewer",),
    "cairosvg": ("CairoSVG",), "iqtree3": ("IQ-TREE 3",), "dot": ("Graphviz",),
    "pdftotext": ("Poppler",), "pdfinfo": ("Poppler",), "pdffonts": ("Poppler",), "pdfimages": ("Poppler",),
    "hmmsearch": ("HMMER",), "hmmfetch": ("HMMER",), "hmmpress": ("HMMER",),
    "makeblastdb": ("BLAST+",), "blastn": ("BLAST+",), "blastp": ("BLAST+",), "blastdbcmd": ("BLAST+",),
    "Rscript": ("R",), "swiftc": ("Swift",),
}

# Names that need no README row, each with its reason.
ALLOWED = {
    # POSIX and macOS base system commands present on every supported host.
    **{name: "base system command" for name in (
        "python", "python3", "bash", "sh", "zsh", "git", "env", "cat", "ls", "cp", "mv", "rm", "mkdir", "find",
        "sort", "grep", "sed", "awk", "tar", "unzip", "zip", "shasum", "sha256sum", "chmod", "echo", "test", "true",
        "false", "head", "tail", "wc", "date", "uname", "which", "nice", "ps", "kill", "tee", "xargs", "touch", "ln",
        "dirname", "basename", "mktemp", "realpath", "readlink", "stat", "du", "df", "id", "cut", "tr", "printf",
        "pwd", "cd", "sleep", "pgrep", "patch", "open", "getconf", "sw_vers", "diff", "cmp", "file", "osascript")},
    "sandbox-exec": "macOS base system sandbox; the release import check documents its macOS-only backend",
    "pytest": "test runner; named in the [test] extra and CONTRIBUTING",
    "build": "test extra; packaging smoke only",
    "pdfplumber": "test extra; reads PDFs in tests only",
    "pkg_resources": "setuptools compatibility probe",
    "setuptools": "packaging",
    # Hosts that are XML/JSON namespaces or documentation links, never contacted at run time.
    "www.w3.org": "XML/SVG namespace identifier",
    "schemas.openxmlformats.org": "Office Open XML namespace identifier",
    "json-schema.org": "JSON Schema identifier",
    "doi.org": "citation links",
    "openpyxl.readthedocs.io": "documentation link",
    "numpy.org": "documentation link",
    "matplotlib.org": "documentation link",
    "pytest.org": "documentation link",
    "github.com": "upstream project links",
    "raw.githubusercontent.com": "upstream project links",
    "cloud.r-project.org": "CRAN mirror used by the R package installer; R is named in README",
}


def _named_in_readme(readme: str, name: str) -> bool:
    for spelling in (name, *ALIASES.get(name, ())):
        if re.search(r"(?<![A-Za-z0-9_-])" + re.escape(spelling) + r"(?![A-Za-z0-9_])", readme, re.I):
            return True
    return False


def _local_names() -> set[str]:
    names = {"mamey", "tools", "deliverable_tools", "tests", "conftest", "mamey_run"}
    for directory in SCAN_DIRS:
        base = ROOT / directory
        if base.is_dir():
            for path in base.rglob("*"):
                if path.suffix == ".py":
                    names.add(path.stem)
                elif path.is_dir():
                    names.add(path.name)
    return names


def scan() -> dict[str, dict[str, set[str]]]:
    found = {kind: {} for kind in ("python import", "program", "R package", "web host")}
    stdlib, local = set(sys.stdlib_module_names), _local_names()
    program = re.compile(r"""shutil\.which\(\s*['"]([A-Za-z0-9_.+-]+)['"]"""
                         r"""|subprocess\.\w+\(\s*\[\s*['"]([A-Za-z0-9_.+-]+)['"]"""
                         r"""|command -v ([A-Za-z0-9_.+-]+)""")
    for directory in SCAN_DIRS:
        base = ROOT / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or SKIP_PARTS & set(path.relative_to(ROOT).parts) or path.suffix not in (".py", ".sh", ".R"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            where = path.relative_to(ROOT).as_posix()
            if path.suffix == ".py":
                try:
                    tree = ast.parse(text)
                except SyntaxError:
                    tree = None
                for node in ast.walk(tree) if tree else ():
                    modules = ([a.name for a in node.names] if isinstance(node, ast.Import)
                               else [node.module] if isinstance(node, ast.ImportFrom) and node.module and node.level == 0
                               else [])
                    for module in modules:
                        top = module.split(".")[0]
                        if top not in stdlib and top not in local and not top.startswith("_"):
                            found["python import"].setdefault(top, set()).add(where)
            for match in program.finditer(text):
                name = next(group for group in match.groups() if group)
                found["program"].setdefault(name, set()).add(where)
            if path.suffix == ".R":
                for match in re.finditer(r"""(?:library|require|requireNamespace)\(\s*['"]?([A-Za-z][A-Za-z0-9.]+)""", text):
                    if match.group(1) != "pkg":
                        found["R package"].setdefault(match.group(1), set()).add(where)
            for match in re.finditer(r"https?://([A-Za-z0-9.-]+\.[a-z]{2,})", text):
                host = match.group(1).lower()
                if not re.search(r"(example\.(com|org)|\.invalid$|localhost|\.test$)", host):
                    found["web host"].setdefault(host, set()).add(where)
    return found


def test_every_code_dependency_is_named_in_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = []
    for kind, names in scan().items():
        for name, files in sorted(names.items()):
            if name in ALLOWED or _named_in_readme(readme, name):
                continue
            missing.append(f"{kind}: {name} (used in {len(files)} file(s), e.g. {sorted(files)[0]})")
    assert not missing, ("README.md does not name these code dependencies. Add a README row saying what each "
                         "is for, or an ALLOWED entry with a reason:\n  " + "\n  ".join(missing))


def test_allowlist_entries_carry_a_reason():
    assert all(isinstance(reason, str) and reason.strip() for reason in ALLOWED.values())


def test_every_registered_companion_tool_is_named_in_readme():
    """Tools reached through the companion registry are invisible to the code scan; the registry lists them."""
    import json
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    registry = json.loads((ROOT / "mamey" / "data" / "companion_tools.json").read_text(encoding="utf-8"))
    missing = []
    for tool in registry["tools"]:
        names = {tool["id"], tool["name"], tool["name"].split(" (")[0]}
        names |= {part.strip() for part in tool["name"].split(" (")[0].split("/")}
        if not any(_named_in_readme(readme, name) for name in names if name):
            missing.append(f"{tool['id']} ({tool['name']})")
    assert not missing, "README.md does not name these registered companion tools:\n  " + "\n  ".join(missing)
