#!/usr/bin/env python3
"""build_chat_export.py  (candidate patch P09)

Render a session transcript into a clean, chat-styled **markdown + PDF** deliverable — the conversation
"as it looks in chat": Human prompts and Assistant replies, code/tool calls summarised, thinking hidden
by default (``--include-thinking`` to keep it).

  python tools/build_chat_export.py --transcript <file.txt> --out-dir <dir> --title "..." [--include-thinking]

Pipeline: parse transcript -> markdown -> HTML (chat CSS) -> PDF (wkhtmltopdf).

PRIVATE GUARD: a transcript that mentions unpublished AS-### strains produces an INTERNAL export. The
tool detects AS-### and stamps the header accordingly; it does not auto-scrub (use the public redactor
for a release cut).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import html as _html
import json
import os
import re
import subprocess
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_write_text

TURN = re.compile(r'^(Human|Assistant):\s*$', re.M)


def parse_transcript(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    parts, turns = TURN.split(raw), []
    # split() yields [pre, role, body, role, body, ...]
    it = iter(parts[1:])
    for role, body in zip(it, it):
        turns.append((role, body))
    return turns


def _render_events(events, include_thinking):
    out = []
    for e in events:
        t = e.get("type")
        if t == "text":
            out.append(e.get("text", ""))
        elif t == "thinking" and include_thinking:
            out.append("\n> *💭 thinking (elided detail)*\n>\n> " +
                       e.get("thinking", "").strip().replace("\n", "\n> ")[:1200])
        elif t == "tool_use":
            name = e.get("name", "tool")
            out.append(f"\n`🔧 {name}`\n")
        elif t == "tool_result":
            out.append("")  # results are noise in a reading view
        elif t == "json_block":
            blk = json.dumps(e.get("json", e.get("content", "")), indent=2)[:600]
            out.append(f"\n```json\n{blk}\n```\n")
        elif t == "table":
            out.append("\n*(table)*\n")
        elif t == "local_resource":
            nm = e.get("name") or e.get("file_path") or "file"
            out.append(f"\n📎 **{os.path.basename(str(nm))}**\n")
    return "\n".join(s for s in out if s is not None)


def to_markdown(turns, include_thinking):
    md = []
    for role, body in turns:
        if role == "Human":
            # drop the Files: listing header, keep the human's words
            txt = re.sub(r'^Files:.*?(?=\n\S|\Z)', '', body, flags=re.S).strip()
            txt = re.sub(r'^Content:\s*', '', txt).strip()
            if txt:
                md.append(f"\n### 🧑 Human\n\n{txt}\n")
        else:
            body = re.sub(r'^Content:\s*', '', body.strip())
            events = None
            try:
                events = json.loads(body)
            except Exception:
                m = re.search(r'\[.*\]', body, re.S)
                if m:
                    try:
                        events = json.loads(m.group(0))
                    except Exception:
                        events = None
            rendered = _render_events(events, include_thinking) if isinstance(events, list) else body
            if rendered.strip():
                md.append(f"\n### 🤖 Assistant\n\n{rendered}\n")
    return "\n".join(md)


CSS = """
body{font-family:-apple-system,'Segoe UI',Arial,sans-serif;font-size:11pt;line-height:1.55;color:#1a1a1a;max-width:820px;margin:0 auto;}
h1{color:#1a2f4a;border-bottom:3px solid #2d4a6b;padding-bottom:6px;}
h3{margin:20px 0 4px;font-size:11.5pt;}
h3:contains('Human'){color:#37618a;}
.turn-human{background:#eef3f8;border-left:4px solid #37618a;border-radius:6px;padding:2px 14px;margin:10px 0;}
.turn-asst{background:#fff;border-left:4px solid #2b7a5b;border-radius:6px;padding:2px 14px;margin:10px 0;}
code{background:#f4f1ea;padding:1px 5px;border-radius:3px;font-size:9.5pt;}
pre{background:#1a2f4a;color:#e6edf3;padding:10px 12px;border-radius:6px;overflow-x:auto;font-size:8.5pt;}
pre code{background:transparent;color:inherit;}
blockquote{color:#6b6b6b;border-left:3px solid #cfcabf;margin:6px 0;padding:2px 12px;font-size:9.5pt;}
table{border-collapse:collapse;font-size:9.5pt;} td,th{border:1px solid #ddd;padding:3px 7px;}
.privacy{background:#7a1f1f;color:#fff;text-align:center;font-size:8pt;font-weight:700;letter-spacing:.1em;padding:5px;text-transform:uppercase;border-radius:4px;margin-bottom:10px;}
"""


class OptionalDependencyMissing(RuntimeError):
    """Raised when an optional renderer package is absent. Message is user-facing and
    tells the caller exactly what to ``pip install`` and which output is skipped."""


def to_html(md_text, title, private):
    # v9.7.409 (CLAUDE_409_optional_deps_guard): `markdown` is an OPTIONAL renderer dep and is
    # NOT declared in the core install. It was hard-imported here, so its absence crashed the
    # whole tool with a bare ModuleNotFoundError -- even though the .md deliverable had already
    # been written. Guard it: raise a typed, actionable error that main() catches to SKIP only
    # the HTML+PDF pass (the markdown output is unaffected).
    try:
        import markdown as _md
    except ImportError as e:
        raise OptionalDependencyMissing(
            "HTML+PDF export skipped: the 'markdown' package is not installed. "
            "The markdown (.md) deliverable was still written. "
            "To enable HTML+PDF, run:  pip install markdown  "
            "(or:  pip install '.[documents]')."
        ) from e
    body = _md.markdown(md_text, extensions=["fenced_code", "tables"])
    # tag turn blocks for bubble styling
    body = body.replace("<h3>🧑 Human</h3>", '<h3 style="color:#37618a">🧑 Human</h3>')
    banner = ('<div class="privacy">Internal — contains unpublished AS-### strain data · '
              'not for public release</div>') if private else ""
    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
            f"{banner}<h1>{_html.escape(title)}</h1>{body}</body></html>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--title", default="Sapote–Mamey session")
    ap.add_argument("--include-thinking", action="store_true")
    a = ap.parse_args()

    raw = open(a.transcript, encoding="utf-8", errors="ignore").read()
    # v9.7.374 fix (AUDIT_374): lacked re.I -- the module's own docstring calls this the
    # "PRIVATE GUARD" that stamps the exported header/banner INTERNAL when a transcript mentions
    # an AS-### strain, but a strain mentioned in lowercase prose ("discussing AS-XXX today", a
    # very plausible casual-chat wording) silently failed to trip it, exporting that transcript
    # without the internal banner. Safety-positive only: can only catch MORE transcripts as
    # INTERNAL, never fewer -- same fix already applied to this exact bug class elsewhere this
    # session (audit_public_cut.py RESEARCH_STRAIN, v9.7.371).
    private = bool(re.search(r'\bAS-\d{2,4}\b', raw, re.I))

    turns = parse_transcript(a.transcript)
    md = to_markdown(turns, a.include_thinking)
    os.makedirs(a.out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(a.transcript))[0]
    md_path = os.path.join(a.out_dir, f"{base}.md")
    hdr = (f"# {a.title}\n\n" +
           ("> **INTERNAL — contains unpublished AS-### strain data.**\n\n" if private else "") +
           f"_{sum(1 for r,_ in turns if r=='Human')} prompts · "
           f"{sum(1 for r,_ in turns if r=='Assistant')} replies · rendered from transcript._\n\n---\n")
    atomic_write_text(md_path, hdr + md)

    emit(f"markdown -> {md_path}")
    try:
        html_path = os.path.join(a.out_dir, f"{base}.html")
        atomic_write_text(html_path, to_html(hdr + md, a.title, private))
        pdf_path = os.path.join(a.out_dir, f"{base}.pdf")
        rc = subprocess.run(["wkhtmltopdf", "--quiet", "--enable-local-file-access",
                             "-s", "Letter", html_path, pdf_path],
                            capture_output=True, text=True).returncode
        emit(f"pdf      -> {pdf_path}" if rc == 0 and os.path.exists(pdf_path) else f"pdf FAILED (rc={rc})")
    except OptionalDependencyMissing as e:
        emit(f"[build_chat_export] {e}")
    emit(f"private={private} · {len(turns)} turns")


if __name__ == "__main__":
    main()
