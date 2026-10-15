"""ID-resolver Markdown cells cannot add columns or rows; source values stay unchanged."""
import re

from mamey.id_resolver import COLUMNS, resolver_md, resolver_rows

_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _cells(line):
    return len(_UNESCAPED_PIPE.findall(line)) - 1


def test_pipe_newline_and_cr_cells_keep_table_shape():
    bank = [{"sid": "S1", "organism": "Streptomyces sp.", "bgc_id": "BGC01",
             "contig": "NODE_1|length_9", "region": "region\n001",
             "source_kcb_file": "a\r\nb|c\rd\\e`f"}]
    rows = resolver_rows(bank)
    md = resolver_md(rows)
    lines = md.split("\n")
    assert len(lines) == 3  # header, separator, one body row
    assert {_cells(line) for line in lines} == {len(COLUMNS)}
    assert rows[0]["contig/NODE"] == "NODE_1|length_9"       # source text kept in the row
    assert rows[0]["antiSMASH_file"] == "a\r\nb|c\rd\\e`f"
    assert "NODE_1\\|length_9" in lines[2] and "region 001" in lines[2]


def test_unicode_and_ordinary_cells_unchanged():
    bank = [{"sid": "S1", "organism": "Streptomyces sp.", "bgc_id": "BGC04",
             "contig": "NODE_12", "region": "region004", "source_kcb_file": "NODE_12_µ.txt"}]
    md = resolver_md(resolver_rows(bank))
    body = md.split("\n")[2]
    assert body == ("| BGC04 | Streptomyces_S1_BGC04 (derived) | NODE_12 | region004 | "
                    "NODE_12_µ.txt |  |")
