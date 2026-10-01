#!/usr/bin/env python3
"""Build a standalone `rggmci` package from a Sapote-Mamey bundle's own source.

One source, two distributions. Nothing here re-implements the scorer: `mamey/rggmci.py`,
`ziputil.py`, `pair_scan_caps.py`, `_gbk_shim.py`, `residue_tiling.py` and `ref_completion.py` are copied byte-for-byte except three import
lines, `rescue_groups.py` is copied unchanged as `groups.py`, and the region-parsing and naming
helpers are lifted out of `parsers.py`, `crosswalk.py` and `antismash_evidence.py` by AST, with the
module-level helpers they need. Only the record type, the zip reader and the CLI are new.
PROVENANCE.json records the bundle version and the SHA-256 of every source file used, so a build
can always be traced to the bundle it came from.

Usage:
  python build_rggmci_package.py --bundle <sapote-mamey root> --out <empty dir>
"""
from __future__ import annotations

import argparse, ast, hashlib, json, pathlib, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"

VERBATIM = ["rggmci.py", "ziputil.py", "pair_scan_caps.py", "_gbk_shim.py", "csv_safety.py", "residue_tiling.py",
            "ref_completion.py"]
# Copied unchanged under another name. The engine and the package share one implementation of candidate groups.
RENAMED = {"rescue_groups.py": "groups.py"}
IMPORT_REWRITES = {
    "from .crosswalk import contig_key\n": "from ._ids import contig_key\n",
    "from .models import BGCRecord\n": "from ._records import BGCRecord\n",
    "from .antismash_evidence import _region_key_from_name  # internal stable-key helper\n":
        "from ._ids import _region_key_from_name  # lifted verbatim from mamey/antismash_evidence.py\n",
}
# The scorer reads antiSMASH's product-family table from class_architecture.py in bundles from v9.7.444. When the
# import is there, it is rewritten and the table is lifted; older bundles build as before.
IMPORT_REWRITES_IF_PRESENT = {
    "from .class_architecture import product_families\n":
        ("from ._families import product_families  # lifted verbatim from mamey/class_architecture.py\n",
         "_families.py", [("class_architecture.py", ["product_families"])]),
}
LIFT = {  # target module -> [(source module, [top-level names])]
    "_ids.py": [("crosswalk.py", ["contig_key"]), ("antismash_evidence.py", ["_region_key_from_name"])],
    "_parsers.py": [("parsers.py", ["_region_orig_bounds_from_zip", "_contig_length_map_from_zip",
                                     "_record_contig_id", "_feature_products", "_edge_status",
                                     "read_genbank_records", "is_macos_cruft", "_replicon_intake_key"])],
    # The BLASTp round trip uses the bundle's own FASTA header, NCBI-safe batching and result parsers, so a
    # user's results read the same way here and in the bundle's `blastp-followup`.
    "_blastp_io.py": [("bgc_blastp_panel.py", ["fasta_header", "wrap_fasta", "assign_rounds"]),
                      ("blastp_followup.py", ["HitRecord", "parse_hit_table_csv", "parse_xml2", "merge_hit_xml",
                                              "best_hits_by_query", "parse_query_id", "_cov_str", "CLAIM_SAFETY"])],
}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lift(src_path: pathlib.Path, names: list[str]) -> tuple[str, list[str], set[str]]:
    """Return (code, import lines, lifted names) for `names` plus the module-level helpers they use."""
    src = src_path.read_text()
    tree = ast.parse(src)
    top: dict[str, ast.AST] = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            top[n.name] = n
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    top[t.id] = n
    need: set[str] = set()
    todo = list(names)
    while todo:
        name = todo.pop()
        if name in need or name not in top:
            if name not in top:
                raise SystemExit(f"LIFT_FAILED: {name} is not a top-level name in {src_path.name}")
            continue
        need.add(name)
        for x in ast.walk(top[name]):
            if isinstance(x, ast.Name) and x.id in top and x.id not in need:
                todo.append(x.id)
    nodes = sorted({id(top[n]): top[n] for n in need}.values(), key=lambda n: n.lineno)
    lines = src.splitlines()

    def segment(n: ast.AST) -> str:   # keep decorators (e.g. @dataclass), which get_source_segment drops
        first = min([d.lineno for d in getattr(n, "decorator_list", [])] + [n.lineno])
        return "\n".join(lines[first - 1:n.end_lineno])
    code = "\n\n".join(segment(n) for n in nodes)
    used = {x.id for n in nodes for x in ast.walk(n) if isinstance(x, ast.Name)}
    imports = []
    for n in tree.body:   # keep only the module-level imports the lifted code actually uses
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            bound = {(a.asname or a.name).split(".")[0] for a in n.names}
            if getattr(n, "module", None) == "__future__" or bound & used:
                imports.append(ast.get_source_segment(src, n))
    return code, imports, need


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bundle", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    a = ap.parse_args(argv)
    m = a.bundle / "mamey"
    if not (m / "rggmci.py").is_file():
        print(f"not a Sapote-Mamey bundle root: {a.bundle}", file=sys.stderr)
        return 2
    if a.out.exists() and any(a.out.iterdir()):
        print(f"refusing to write into a non-empty directory: {a.out}", file=sys.stderr)
        return 2
    pkg = a.out / "src" / "rggmci"
    pkg.mkdir(parents=True)
    used: dict[str, str] = {}

    lift_extra = {}
    for f in VERBATIM:
        text = (m / f).read_text()
        if f == "rggmci.py":
            for old, new in IMPORT_REWRITES.items():
                if text.count(old) != 1:
                    raise SystemExit(f"IMPORT_REWRITE_FAILED: {old.strip()!r} not found exactly once")
                text = text.replace(old, new)
            for old, (new, target, specs) in IMPORT_REWRITES_IF_PRESENT.items():
                n = text.count(old)
                if n > 1:
                    raise SystemExit(f"IMPORT_REWRITE_FAILED: {old.strip()!r} found {n} times")
                if n == 1:
                    text = text.replace(old, new)
                    lift_extra[target] = specs
        (pkg / ("core.py" if f == "rggmci.py" else f)).write_text(text)
        used[f"mamey/{f}"] = sha(m / f)

    for f, target in RENAMED.items():
        text = (m / f).read_text()
        shipped = {m.removesuffix(".py") for m in VERBATIM}
        for line in text.splitlines():   # relative imports only of modules the package also ships
            if line.startswith("from .") and line.split()[1].lstrip(".") not in shipped:
                raise SystemExit(f"RENAMED_MODULE_NOT_STANDALONE: mamey/{f} imports from the engine: {line}")
        (pkg / target).write_text(text)
        used[f"mamey/{f}"] = sha(m / f)

    for target, specs in {**LIFT, **lift_extra}.items():
        parts, header = [], ['"""Lifted by build_rggmci_package.py from Sapote-Mamey source. Do not edit here."""',
                             "from __future__ import annotations"]
        for src_name, names in specs:
            code, imports, got = lift(m / src_name, names)
            used[f"mamey/{src_name}"] = sha(m / src_name)
            parts.append(f"# --- from mamey/{src_name}: {', '.join(sorted(got))}\n{code}")
            for imp in imports:
                if imp.startswith("from __future__"):
                    continue
                if imp.startswith("from ."):
                    if "ziputil" in imp:
                        header.append("from .ziputil import regular_file_names")
                    continue
                header.append(imp)
        body = "\n".join(dict.fromkeys(header)) + "\n\n\n" + "\n\n\n".join(parts) + "\n"
        defined = [n.name for n in ast.parse(body).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        dup = sorted({d for d in defined if defined.count(d) > 1})
        if dup:   # two source modules lifted the same name: one would silently shadow the other
            raise SystemExit(f"LIFT_NAME_CLASH in {target}: {dup}")
        (pkg / target).write_text(body)

    # Guard: every engine BGCRecord field the scorer touches must exist on the standalone record.
    eng_fields = [s.target.id for n in ast.parse((m / "models.py").read_text()).body
                  if isinstance(n, ast.ClassDef) and n.name == "BGCRecord"
                  for s in n.body if isinstance(s, ast.AnnAssign)]
    core_src = (m / "rggmci.py").read_text()
    touched = {x.attr for x in ast.walk(ast.parse(core_src)) if isinstance(x, ast.Attribute)}
    touched |= set(__import__("re").findall(r'getattr\(\s*\w+\s*,\s*"(\w+)"', core_src))
    needed = {f for f in eng_fields if f in touched}
    have = {s.target.id for n in ast.parse((TEMPLATES / "src/rggmci/_records.py").read_text()).body
            if isinstance(n, ast.ClassDef) for s in n.body if isinstance(s, ast.AnnAssign)}
    if needed - have:
        raise SystemExit(f"RECORD_FIELDS_MISSING: the scorer reads {sorted(needed - have)} but _records.BGCRecord lacks them")

    for t in TEMPLATES.rglob("*"):
        if t.is_file():
            dst = a.out / t.relative_to(TEMPLATES)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(t, dst)
    shutil.copy2(a.bundle / "LICENSE", a.out / "LICENSE")

    stamp = {}
    for line in (a.bundle / "BUILD_STAMP.txt").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            stamp[k.strip()] = v.strip()
    import tomllib
    pkg_version = tomllib.loads((TEMPLATES / "pyproject.toml").read_text())["project"]["version"]
    prov = {"package_version": pkg_version,
            "built_from_bundle": stamp.get("version"), "engine": stamp.get("engine"), "build": stamp.get("build"),
            "source_sha256": used}
    (pkg / "PROVENANCE.json").write_text(json.dumps(prov, indent=1) + "\n")
    print(f"built rggmci {pkg_version} from Sapote-Mamey {stamp.get('version')} (engine {stamp.get('engine')}) -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
