#!/usr/bin/env python3
"""Resolve local Markdown image resources for a portable LaTeX fallback.

SVGs are converted only with an available local vector converter; unavailable
or malformed resources refuse the render. No network fetch or missing-image drop.
"""
from pathlib import Path
import io
import os
import re
import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote, urlsplit

def reject_svg_external_image_refs(svg_bytes):
    """Refuse direct SVG image references that may be silently omitted.

    This check covers image and use hrefs, CSS imports, and URLs in selected
    presentation attributes and styles. It is not a complete SVG policy.
    """
    try:
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as exc:
        raise ValueError("PDF_SVG_XML_INVALID") from exc
    # ElementTree's default tree omits processing instructions. Refuse them
    # before invoking a converter because they can supply external stylesheets
    # or other resources that are not captured by the conversion binding.
    # An XML declaration is not a processing-instruction event.
    for _event, _node in ET.iterparse(io.BytesIO(svg_bytes), events=("pi",)):
        raise ValueError("PDF_SVG_PROCESSING_INSTRUCTION_REFUSED")
    for element in root.iter():
        # A base URI can redirect fragment references away from this SVG.
        # Retain the same-file interpretation by refusing a nonempty base.
        if element.attrib.get("{http://www.w3.org/XML/1998/namespace}base", "") != "":
            raise ValueError("PDF_SVG_XML_BASE_REFUSED")
        tag = element.tag.rsplit("}", 1)[-1]
        hrefs = [value.strip() for key, value in element.attrib.items()
                 if key.rsplit("}", 1)[-1] == "href"]
        if tag == "image":
            if (len(hrefs) != 1 or not hrefs[0].lower().startswith("data:image/")
                    or hrefs[0].lower().startswith("data:image/svg+xml")):
                raise ValueError("PDF_SVG_EXTERNAL_IMAGE_REFUSED")
        elif tag == "use":
            if len(hrefs) != 1 or not hrefs[0].startswith("#") or len(hrefs[0]) == 1:
                raise ValueError("PDF_SVG_EXTERNAL_USE_REFUSED")
        elif tag != "a" and hrefs:
            # Other SVG elements can load external resources too (for example,
            # gradient and pattern templates). Hyperlinks are navigation, not
            # converter inputs; keep them as links. Only unambiguous same-file
            # fragment references are supported for other elements.
            if len(hrefs) != 1 or not hrefs[0].startswith("#") or len(hrefs[0]) == 1:
                raise ValueError("PDF_SVG_EXTERNAL_HREF_REFUSED")
        # SVG presentation attributes and style attributes may contain CSS URLs.
        # A literal URL or CSS escape requires tokenization, including escaped
        # spellings of "url"; ordinary colors need no parser.
        css_attributes = {"style", "fill", "stroke", "filter", "clip-path",
                          "mask", "marker", "marker-start", "marker-mid",
                          "marker-end", "cursor", "color-profile",
                          "shape-inside", "shape-subtract"}
        css_texts = []
        if tag == "style":
            css_texts.append("".join(element.itertext()))
        for key, value in element.attrib.items():
            if key.rsplit("}", 1)[-1].lower() in css_attributes:
                if "url" in value.lower() or "\\" in value:
                    css_texts.append(value)
        if css_texts:
            try:
                import tinycss2
            except ImportError as exc:
                raise ValueError("PDF_SVG_CSS_PARSER_UNAVAILABLE") from exc
            def walk(tokens):
                for token in tokens:
                    yield token
                    for attribute in ("content", "arguments"):
                        children = getattr(token, attribute, None)
                        if children is not None:
                            yield from walk(children)
            for css in css_texts:
                tokens = list(walk(tinycss2.parse_component_value_list(css)))
                if any(t.type == "at-keyword" and t.value.lower() == "import" for t in tokens):
                    raise ValueError("PDF_SVG_CSS_IMPORT_REFUSED")
                for token in tokens:
                    if token.type == "error":
                        raise ValueError("PDF_SVG_CSS_INVALID")
                    if token.type == "url":
                        value = token.value.strip()
                    elif token.type == "function" and token.name.lower() == "url":
                        args = [a for a in token.arguments if a.type not in ("whitespace", "comment")]
                        if len(args) != 1 or args[0].type != "string":
                            raise ValueError("PDF_SVG_CSS_URL_REFUSED")
                        value = args[0].value.strip()
                    else:
                        continue
                    if not value.startswith("#") or len(value) == 1:
                        raise ValueError("PDF_SVG_CSS_URL_REFUSED")

def parsed_images(text, pandoc, *, companion_targets=None):
    result = subprocess.run([pandoc, "-f", "markdown", "-t", "json"],
                            input=text, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f"PDF_PANDOC_PARSE_FAILED: {result.stderr.strip()}")
    ast = json.loads(result.stdout)
    targets = []
    def safe_html_comment(value):
        return (value.startswith("<!--") and value.endswith("-->")
                and value.count("<!--") == 1 and value.count("-->") == 1)
    def visit(node):
        if isinstance(node, dict):
            tag = node.get("t")
            if tag == "Image":
                try:
                    target = node["c"][2][0]
                except (KeyError, IndexError, TypeError) as exc:
                    raise ValueError("PDF_PANDOC_IMAGE_AST_INVALID") from exc
                if not isinstance(target, str):
                    raise ValueError("PDF_PANDOC_IMAGE_AST_INVALID")
                targets.append(target)
            elif tag == "Link" and companion_targets is not None:
                try:
                    target = node["c"][2][0]
                    if isinstance(target, str):
                        companion_targets.append(target)
                except (KeyError, IndexError, TypeError) as exc:
                    raise ValueError("PDF_PANDOC_LINK_AST_INVALID") from exc
            elif tag in ("RawInline", "RawBlock"):
                try:
                    raw_format, raw = node["c"]
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError("PDF_PANDOC_RAW_AST_INVALID") from exc
                if not (raw_format == "html" and isinstance(raw, str)
                        and safe_html_comment(raw)):
                    raise ValueError("PDF_RAW_IMAGE_RESOURCE_REFUSED")
            elif tag in ("Div", "Span"):
                attributes = node["c"][0][2]
                if any(key.lower() == "style" and re.search(r"url\s*\(", value, re.IGNORECASE)
                       for key, value in attributes):
                    raise ValueError("PDF_RAW_IMAGE_RESOURCE_REFUSED")
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(ast)
    return ast.get("pandoc-api-version"), targets

def prepare(source, destination, *, pandoc=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    map_destination = destination.with_suffix(".resource_map.json")
    if destination.exists():
        raise FileExistsError("PDF_RESOURCE_DESTINATION_EXISTS")
    if map_destination.exists():
        raise FileExistsError("PDF_RESOURCE_MAP_EXISTS")
    text = source.read_text(encoding="utf-8")
    pandoc = pandoc or os.environ.get("PANDOC") or shutil.which("pandoc")
    if not pandoc:
        raise ValueError("PDF_PANDOC_UNAVAILABLE")
    companion_targets = []
    api_version, image_targets = parsed_images(text, pandoc, companion_targets=companion_targets)
    companion_map = {}
    output_dir = os.environ.get("MAMEY_PDF_LINK_OUTPUT_DIR")
    if output_dir:
        for raw in companion_targets:
            try:
                parsed = urlsplit(raw)
            except ValueError:
                continue
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or raw.startswith("//"):
                continue
            try:
                path = (source.parent / unquote(parsed.path)).resolve()
                if path.suffix.lower() != ".svg" or not path.is_file():
                    continue
                relative = os.path.relpath(path, Path(output_dir).resolve())
            except (OSError, ValueError, RuntimeError):
                continue
            companion_map[raw] = quote(Path(relative).as_posix(), safe="/-._~")
    converted_cache = {}
    def image(raw):
        name = unquote(raw)
        parsed = urlsplit(name)
        if parsed.scheme or parsed.netloc or name.startswith("//"):
            raise ValueError("PDF_REMOTE_RESOURCE_REFUSED")
        path = (source.parent / name).resolve()
        if not path.is_file():
            raise ValueError(f"PDF_IMAGE_UNAVAILABLE: {path}")
        if path.suffix.lower() == ".svg":
            svg_bytes = path.read_bytes()
            source_sha = hashlib.sha256(svg_bytes).hexdigest()
            if path in converted_cache:
                previous_sha, previous_pdf = converted_cache[path]
                if source_sha != previous_sha:
                    raise ValueError("PDF_SVG_SOURCE_CHANGED_DURING_PREPARATION")
                return str(previous_pdf)
            reject_svg_external_image_refs(svg_bytes)
            converted = destination.parent / (hashlib.sha256(str(path).encode()).hexdigest() + ".pdf")
            receipt_path = converted.with_suffix(".pdf.conversion.json")
            if receipt_path.exists():
                raise FileExistsError("PDF_SVG_RECEIPT_EXISTS")
            if converted.exists():
                raise FileExistsError("PDF_SVG_CONVERTED_EXISTS")
            with tempfile.TemporaryDirectory(prefix="pdf-svg-", dir=destination.parent) as stage_dir:
                staged = Path(stage_dir) / "converted.pdf"
                try:
                    import cairosvg
                    cairosvg.svg2pdf(url=str(path), write_to=str(staged))
                    converter = "cairosvg"
                except Exception as exc:
                    if shutil.which("rsvg-convert"):
                        subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(staged), str(path)], check=True)
                        converter = "rsvg-convert"
                    elif shutil.which("inkscape"):
                        subprocess.run(["inkscape", str(path), "--export-type=pdf", f"--export-filename={staged}"], check=True)
                        converter = "inkscape"
                    else:
                        raise ValueError("PDF_SVG_CONVERTER_UNAVAILABLE: install cairosvg, rsvg-convert or inkscape") from exc
                if hashlib.sha256(path.read_bytes()).hexdigest() != source_sha:
                    raise ValueError("PDF_SVG_SOURCE_CHANGED_DURING_CONVERSION")
                converted_sha = hashlib.sha256(staged.read_bytes()).hexdigest()
                try:
                    os.link(staged, converted)
                except FileExistsError as exc:
                    raise FileExistsError("PDF_SVG_CONVERTED_EXISTS") from exc
            receipt = {"schema": "sapote_svg_pdf_conversion_v1", "source_svg": str(path),
                       "source_svg_sha256": source_sha, "converted_pdf": str(converted),
                       "converted_pdf_sha256": converted_sha,
                       "converter": converter,
                       "scope": "Conversion binding only; neither renderer provenance nor scientific validity is asserted."}
            with receipt_path.open("x", encoding="utf-8") as out:
                out.write(json.dumps(receipt, indent=2) + "\n")
            converted_cache[path] = (source_sha, converted)
            path = converted
        return str(path)
    mapping = {}
    for raw in image_targets:
        mapping[raw] = image(raw)
    with map_destination.open("x", encoding="utf-8") as out:
        json.dump({"schema": "sapote_pdf_image_map_v1", "source_md": str(source),
                   "source_md_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                   "pandoc_api_version": api_version, "targets": mapping, "svg_companions": companion_map}, out, indent=2)
        out.write("\n")
    with destination.open("x", encoding="utf-8") as out:
        out.write(text)

if __name__ == "__main__":
    prepare(sys.argv[1], sys.argv[2])
