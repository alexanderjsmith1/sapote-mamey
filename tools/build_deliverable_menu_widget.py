#!/usr/bin/env python3
"""build_deliverable_menu_widget.py — render the self-contained Deliverable Menu widget.

The authoritative list of what this bundle can produce is the set of top-level CLI
subcommands in ``mamey/cli.py`` (introspected live from ``build_parser()``, so the widget
cannot drift from the code).  Each subcommand is annotated, where one maps, with the
salvaged registry facets from ``mamey/data/deliverables_registry.json``:

  * the availability class (DETERMINISTIC_BUILT_IN / OPTIONAL_LOCAL_ADAPTER /
    POST_SEAL_JUDGMENT / OPTIONAL_EXTERNAL_WORKFLOW / GOVERNANCE_AND_QA /
    HUMAN_REVIEW_PROTOCOL),
  * a short claim-ceiling line, and
  * the plain-language "ask for" trigger phrases.

The output is one self-contained HTML file: inline JSON payload, no external calls, no
network, theme-aware (light/dark), and XSS-safe (every value is written to the DOM with
``textContent`` — never ``innerHTML`` — and the JSON blob is angle-bracket-escaped so it
cannot break out of its ``<script>`` element).  It is deterministic: identical inputs
produce a byte-identical file (no timestamps, everything sorted).

Usage:
  python tools/build_deliverable_menu_widget.py                       # -> deliverable_menu_widget.html
  python tools/build_deliverable_menu_widget.py --out menu.html
  python tools/build_deliverable_menu_widget.py --stdout              # HTML to stdout
  python tools/build_deliverable_menu_widget.py --json                # payload to stdout (debug)
  python tools/build_deliverable_menu_widget.py --root /path/to/bundle

Import:
  from tools.build_deliverable_menu_widget import build_payload, render_html
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Data assembly (mamey is imported lazily so ``--help`` never needs the package;
# this keeps the front door open from any cwd — see tests/test_tool_front_doors.py).
# ---------------------------------------------------------------------------
def _load_mamey(root: Path):
    root = Path(root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import argparse as _ap  # noqa: F401 (kept local; symmetry with cli introspection)
    from mamey.cli import build_parser
    from mamey.deliverables_registry import load_registry
    from mamey import BUNDLE_VERSION, __version__
    return build_parser, load_registry, BUNDLE_VERSION, __version__


def collect_subcommands(parser) -> list[dict]:
    """Distinct top-level subcommands (aliases folded in) with their help text."""
    import argparse as _ap
    action = next(a for a in parser._actions if isinstance(a, _ap._SubParsersAction))
    help_by_name = {ca.dest: ca.help for ca in action._choices_actions}
    seen: set[int] = set()
    rows: list[dict] = []
    for name, sub in action.choices.items():
        if id(sub) in seen:
            continue
        seen.add(id(sub))
        aliases = sorted(
            other for other, osub in action.choices.items()
            if osub is sub and other != name
        )
        rows.append({
            "name": name,
            "aliases": aliases,
            "help": (help_by_name.get(name) or "").strip(),
        })
    rows.sort(key=lambda r: r["name"])
    return rows


def build_command_index(registry: dict) -> dict[str, list[dict]]:
    """Map a CLI command token (first word of a registry ``commands`` entry) to the
    salvaged annotation of every deliverable that names it."""
    index: dict[str, list[dict]] = {}
    for item in registry["deliverables"]:
        annotation = {
            "id": item["id"],
            "label": item["label"],
            "name": item["name"],
            "delivery_class": item["delivery_class"],
            "claim_ceiling": item["claim_ceiling"],
            "triggers": list(item["triggers"]),
        }
        for command in item["commands"]:
            token = command.split()[0]
            bucket = index.setdefault(token, [])
            if annotation["id"] not in {a["id"] for a in bucket}:
                bucket.append(annotation)
    return index


def assemble(registry: dict, subcommands: list[dict], bundle_version: str,
             engine_version: str) -> dict:
    index = build_command_index(registry)
    annotated: list[dict] = []
    mapped = 0
    for row in subcommands:
        matches = index.get(row["name"], [])
        if matches:
            mapped += 1
        classes = sorted({m["delivery_class"] for m in matches})
        deliverables = [
            {
                "label": m["label"],
                "name": m["name"],
                "delivery_class": m["delivery_class"],
                "claim_ceiling": m["claim_ceiling"],
                "ask_for": m["triggers"],
            }
            for m in sorted(matches, key=lambda m: m["label"])
        ]
        annotated.append({
            "name": row["name"],
            "aliases": row["aliases"],
            "help": row["help"],
            "classes": classes,
            "deliverables": deliverables,
        })

    menu = []
    for item in sorted(registry["deliverables"], key=lambda i: i["label"]):
        menu.append({
            "label": item["label"],
            "name": item["name"],
            "group": item["group"],
            "question": item["question"],
            "delivery_class": item["delivery_class"],
            "commands": list(item["commands"]),
            "claim_ceiling": item["claim_ceiling"],
            "ask_for": list(item["triggers"]),
        })

    return {
        "title": "Sapote-Mamey Deliverable Menu",
        "generated_from": "mamey/cli.py subcommands + mamey/data/deliverables_registry.json",
        "bundle_version": bundle_version,
        "engine_version": engine_version,
        "identity_contract": registry["identity_contract"],
        "global_claim_ceiling": registry["global_claim_ceiling"],
        "delivery_classes": [
            {"name": name, "description": description}
            for name, description in registry["delivery_classes"].items()
        ],
        "subcommand_count": len(annotated),
        "annotated_count": mapped,
        "menu_count": len(menu),
        "subcommands": annotated,
        "menu": menu,
    }


def build_payload(root: Path | str = ROOT) -> dict:
    build_parser, load_registry, bundle_version, engine_version = _load_mamey(Path(root))
    subcommands = collect_subcommands(build_parser())
    registry = load_registry()
    return assemble(registry, subcommands, bundle_version, engine_version)


# ---------------------------------------------------------------------------
# Rendering.  Chrome is static; every payload value reaches the page as JSON and
# is placed with textContent by the inline script.  No value is interpolated
# server-side, so the output cannot carry an injection from its inputs.
# ---------------------------------------------------------------------------
def _safe_json(payload: dict) -> str:
    import json
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=None)
    # Neutralise anything that could close the <script> element or start markup.
    return (blob.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))


_TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
:root{--bg:#f6f7f9;--panel:#ffffff;--line:#dfe3ea;--tx:#1c2028;--mut:#6a7180;--acc:#2f6bd6;
  --banner:#fff7e6;--bline:#e7d199;--btx:#7a5b00;
  --c-det:#189e52;--c-loc:#2f6bd6;--c-jud:#8a4fd0;--c-ext:#c8850f;--c-gov:#0e8f9c;--c-hum:#c04a4a;--c-non:#9aa1ad;}
@media (prefers-color-scheme:dark){:root{--bg:#0e0f12;--panel:#16181d;--line:#262a31;--tx:#e7e9ee;
  --mut:#8b91a0;--acc:#5b8def;--banner:#241f12;--bline:#4d411f;--btx:#e6c86a;
  --c-det:#4bd07a;--c-loc:#5b8def;--c-jud:#b487ee;--c-ext:#f2b13d;--c-gov:#3fc6d3;--c-hum:#e77b7b;--c-non:#5b6472;}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);
  font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:20px}
h1{font-size:17px;font-weight:600;margin:0 0 2px}
.sub{color:var(--mut);font-size:12px;margin:0 0 12px}
.contract{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--tx)}
.banner{background:var(--banner);border:1px solid var(--bline);color:var(--btx);
  border-radius:10px;padding:9px 13px;font-size:12.5px;margin:10px 0 16px}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}
.legend .lg{display:flex;gap:7px;align-items:flex-start;background:var(--panel);border:1px solid var(--line);
  border-radius:9px;padding:7px 10px;max-width:340px}
.badge{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.02em;color:#fff;
  border-radius:5px;padding:2px 6px;white-space:nowrap}
.lg .d{color:var(--mut);font-size:11.5px;line-height:1.35}
.b-DETERMINISTIC_BUILT_IN{background:var(--c-det)}
.b-OPTIONAL_LOCAL_ADAPTER{background:var(--c-loc)}
.b-POST_SEAL_JUDGMENT{background:var(--c-jud)}
.b-OPTIONAL_EXTERNAL_WORKFLOW{background:var(--c-ext)}
.b-GOVERNANCE_AND_QA{background:var(--c-gov)}
.b-HUMAN_REVIEW_PROTOCOL{background:var(--c-hum)}
.b-UNCLASSIFIED{background:var(--c-non)}
.bar{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin:6px 0 14px}
.bar input[type=search]{flex:1;min-width:200px;background:var(--panel);border:1px solid var(--line);
  color:var(--tx);border-radius:8px;padding:8px 11px;font-size:13px}
.chk{display:inline-flex;align-items:center;gap:6px;color:var(--mut);font-size:12px;cursor:pointer;user-select:none}
.count{color:var(--mut);font-size:12px}
.sec{margin:22px 0 10px;font-size:13px;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:13px}
thead th{text-align:left;color:var(--mut);font-weight:600;font-size:11.5px;text-transform:uppercase;
  letter-spacing:.03em;border-bottom:1px solid var(--line);padding:7px 9px}
tbody td{border-bottom:1px solid var(--line);padding:9px;vertical-align:top}
tbody tr:hover{background:color-mix(in srgb,var(--panel) 60%,transparent)}
.cmd{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-weight:600;white-space:nowrap}
.alias{color:var(--mut);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}
.help{color:var(--tx)}.ceil{color:var(--mut);font-size:12px}
.ask{color:var(--acc);font-size:12px}.ask b{font-weight:600;color:var(--tx)}
.badges{display:flex;flex-wrap:wrap;gap:4px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:12px 14px;margin:0 0 10px}
.card h3{margin:0 0 3px;font-size:13.5px;font-weight:600}
.card .q{color:var(--mut);font-size:12px;font-style:italic;margin:0 0 7px}
.card .row{font-size:12px;margin:3px 0}.card .k{color:var(--mut)}
.foot{color:var(--mut);font-size:11.5px;margin-top:22px;border-top:1px solid var(--line);padding-top:12px}
.hidden{display:none}
</style></head><body><div class="wrap">
<h1 id="h1"></h1>
<p class="sub" id="sub"></p>
<p class="sub">Required exact-locus display: <span class="contract" id="contract"></span></p>
<div class="banner" id="banner"></div>

<div class="sec">Availability language</div>
<div class="legend" id="legend"></div>

<div class="sec">Deliverables — the <span id="cmdcount"></span> CLI subcommands</div>
<div class="bar">
  <input type="search" id="q" placeholder="Filter by command, description, claim ceiling…" autocomplete="off">
  <label class="chk"><input type="checkbox" id="mappedonly"> annotated only</label>
  <span class="count" id="shown"></span>
</div>
<table><thead><tr><th>Command</th><th>What it does</th><th>Availability</th><th>Claim ceiling</th><th>Ask for</th></tr></thead>
<tbody id="rows"></tbody></table>

<div class="sec">Salvaged menu — <span id="menucount"></span> plain-language deliverables</div>
<div id="menu"></div>

<p class="foot" id="foot"></p>
</div>
<script type="application/json" id="payload">__PAYLOAD__</script>
<script>
(function(){
  var DATA = JSON.parse(document.getElementById("payload").textContent);
  function el(tag,cls,text){var e=document.createElement(tag);if(cls)e.className=cls;
    if(text!=null)e.textContent=text;return e;}
  function badge(cls){var short=cls.replace(/^(DETERMINISTIC_BUILT_IN|OPTIONAL_LOCAL_ADAPTER|POST_SEAL_JUDGMENT|OPTIONAL_EXTERNAL_WORKFLOW|GOVERNANCE_AND_QA|HUMAN_REVIEW_PROTOCOL)$/, "$1");
    var map={DETERMINISTIC_BUILT_IN:"BUILT-IN",OPTIONAL_LOCAL_ADAPTER:"LOCAL ADAPTER",
      POST_SEAL_JUDGMENT:"JUDGMENT",OPTIONAL_EXTERNAL_WORKFLOW:"EXTERNAL",
      GOVERNANCE_AND_QA:"GOVERNANCE/QA",HUMAN_REVIEW_PROTOCOL:"HUMAN REVIEW",UNCLASSIFIED:"—"};
    var b=el("span","badge b-"+cls,map[cls]||cls);b.title=cls;return b;}

  document.getElementById("h1").textContent=DATA.title;
  document.getElementById("sub").textContent=
    "Bundle Sapote-Mamey v"+DATA.bundle_version+" · engine Mamey "+DATA.engine_version+
    " · generated from "+DATA.generated_from;
  document.getElementById("contract").textContent=DATA.identity_contract;
  document.getElementById("banner").textContent=DATA.global_claim_ceiling;
  document.getElementById("cmdcount").textContent=DATA.subcommand_count;
  document.getElementById("menucount").textContent=DATA.menu_count;

  var legend=document.getElementById("legend");
  DATA.delivery_classes.forEach(function(c){
    var w=el("div","lg");w.appendChild(badge(c.name));
    w.appendChild(el("span","d",c.description));legend.appendChild(w);});

  var tbody=document.getElementById("rows");
  DATA.subcommands.forEach(function(s){
    var tr=el("tr");tr.dataset.mapped=s.deliverables.length?"1":"0";
    var haystack=[s.name].concat(s.aliases||[]);haystack.push(s.help||"");
    var td0=el("td");td0.appendChild(el("div","cmd",s.name));
    if(s.aliases&&s.aliases.length){td0.appendChild(el("div","alias","aka "+s.aliases.join(", ")));}
    tr.appendChild(td0);
    tr.appendChild(el("td","help",s.help||"—"));
    var tdc=el("td");var bw=el("div","badges");
    (s.classes.length?s.classes:["UNCLASSIFIED"]).forEach(function(c){bw.appendChild(badge(c));});
    tdc.appendChild(bw);tr.appendChild(tdc);
    var ceil=el("td","ceil");var asks=el("td","ask");
    if(s.deliverables.length){
      s.deliverables.forEach(function(d){
        ceil.appendChild(el("div",null,d.claim_ceiling));
        d.ask_for.forEach(function(a){haystack.push(a);var p=el("div");
          p.appendChild(el("b",null,"“"));p.appendChild(document.createTextNode(a));
          p.appendChild(el("b",null,"”"));asks.appendChild(p);});
      });
    }else{ceil.textContent="—";asks.textContent="—";}
    (s.deliverables||[]).forEach(function(d){haystack.push(d.claim_ceiling);});
    tr.appendChild(ceil);tr.appendChild(asks);
    tr.dataset.hay=haystack.join("  ").toLowerCase();
    tbody.appendChild(tr);});

  var menu=document.getElementById("menu");
  DATA.menu.forEach(function(m){
    var c=el("div","card");
    var h=el("h3");h.appendChild(document.createTextNode(m.label+" — "+m.name+"  "));
    h.appendChild(badge(m.delivery_class));c.appendChild(h);
    c.appendChild(el("p","q",m.question));
    var r1=el("div","row");r1.appendChild(el("span","k","Claim ceiling: "));
    r1.appendChild(document.createTextNode(m.claim_ceiling));c.appendChild(r1);
    if(m.ask_for.length){var r2=el("div","row ask");r2.appendChild(el("span","k","Ask for: "));
      r2.appendChild(document.createTextNode(m.ask_for.map(function(a){return "“"+a+"”";}).join("  ·  ")));
      c.appendChild(r2);}
    if(m.commands.length){var r3=el("div","row");r3.appendChild(el("span","k","Commands: "));
      r3.appendChild(document.createTextNode(m.commands.join(", ")));c.appendChild(r3);}
    menu.appendChild(c);});

  var q=document.getElementById("q"),mo=document.getElementById("mappedonly"),
      shown=document.getElementById("shown"),trs=Array.prototype.slice.call(tbody.children);
  function apply(){var needle=q.value.trim().toLowerCase(),onlyMapped=mo.checked,n=0;
    trs.forEach(function(tr){var ok=(!needle||tr.dataset.hay.indexOf(needle)>=0)&&
      (!onlyMapped||tr.dataset.mapped==="1");tr.classList.toggle("hidden",!ok);if(ok)n++;});
    shown.textContent=n+" of "+trs.length+" shown";}
  q.addEventListener("input",apply);mo.addEventListener("change",apply);apply();

  document.getElementById("foot").textContent=
    DATA.annotated_count+" of "+DATA.subcommand_count+
    " subcommands carry a registry annotation. Offline, self-contained, deterministic. "+
    "Gate success is not owner acceptance, release approval, or publication readiness. "+
    "Capacity is not production; similarity is not identity; missing evidence is not biological absence.";
})();
</script></body></html>"""


def render_html(payload: dict) -> str:
    return (_TEMPLATE
            .replace("__TITLE__", payload["title"])
            .replace("__PAYLOAD__", _safe_json(payload)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="deliverable_menu_widget.html",
                        help="output HTML path (default: deliverable_menu_widget.html)")
    parser.add_argument("--root", default=str(ROOT),
                        help="bundle root holding mamey/ (default: this tool's bundle)")
    parser.add_argument("--stdout", action="store_true", help="write HTML to stdout, not a file")
    parser.add_argument("--json", action="store_true", help="write the JSON payload to stdout (debug)")
    args = parser.parse_args(argv)

    payload = build_payload(args.root)
    if args.json:
        import json
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        return 0
    html_text = render_html(payload)
    if args.stdout:
        sys.stdout.write(html_text)
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    sys.stdout.write(str(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
