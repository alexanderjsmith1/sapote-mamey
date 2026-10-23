"""Synthetic PDF operator-order regression; no figure renderer is invoked."""
from pathlib import Path
import importlib.util
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

spec = importlib.util.spec_from_file_location("mincheck", Path(__file__).parents[1] / "tools/_min_text_check.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def pdf(tmp_path, operators):
    writer = PdfWriter()
    page = writer.add_blank_page(width=252, height=144)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F2"): writer._add_object(font)})})
    stream = DecodedStreamObject(); stream.set_data(operators.encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    path = tmp_path / "synthetic.pdf"
    with path.open("wb") as f: writer.write(f)
    return path

@pytest.mark.parametrize("ops, expected", [
    ("BT /F2 1 Tf 8 0 0 8 20 80 Tm (Bees) Tj ET", [8]),
    ("BT /F2 1 Tf 8 0 0 8 20 80 Tm [(Be) 0 (es)] TJ ET", [8]),
    ("BT /F2 8 Tf 1 0 0 1 20 80 Tm (Bees) Tj ET", [8]),
    ("q 2 0 0 2 0 0 cm BT /F2 1 Tf 4 0 0 4 10 40 Tm (Bees) Tj ET Q", [8]),
    ("BT /F2 1 Tf 8 0 0 8 20 80 Tm (Bees) Tj 6 0 0 6 20 40 Tm (Wasps) Tj ET", [8, 6]),
    ("BT /F2 1 Tf 8 0 0 8 20 80 Tm (Bees) Tj /F2 2 Tf 5 0 0 5 20 40 Tm (Wasps) Tj ET", [8, 10]),
])
def test_sizes(tmp_path, ops, expected):
    assert [v for v, _ in m.text_sizes(pdf(tmp_path, ops))] == expected

def test_floor(tmp_path):
    p = pdf(tmp_path, "BT /F2 1 Tf 8 0 0 8 20 80 Tm (Bees) Tj ET")
    assert m.check(p, 8, 3.5)["status"] == "PASS"
    p = pdf(tmp_path, "BT /F2 1 Tf 6 0 0 6 20 80 Tm (Bees) Tj ET")
    assert m.check(p, 8, 3.5)["status"] == "FAIL"

def test_boxes_use_drawn_matrix(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "_font_length", lambda text, font, size: len(text) * size / 2)
    p = pdf(tmp_path, "BT /F2 1 Tf 8 0 0 8 20 80 Tm (Bees) Tj ET")
    assert m.pdf_text_boxes(p) == [("Bees", 20.0, 36.0, 74.24, 81.68)]
