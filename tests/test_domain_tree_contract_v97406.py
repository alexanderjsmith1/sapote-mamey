from __future__ import annotations

import re
from pathlib import Path

from mamey import ks_phylogeny


GBK = """LOCUS       NODE_7_length_1000_cov_1 1000 bp DNA linear BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     aSDomain        100..300
                     /aSDomain="PKS_KS"
                     /locus_tag="gene_1"
                     /domain_id="gene_1_PKS_KS.1"
                     /translation="MKSAAAAAKS"
//
"""


def _marker(text, name):
    match = re.search(rf"<!-- {name}: ([^>]+) -->", text)
    assert match, f"missing {name} marker"
    return tuple(match.group(1).strip().split(","))


def test_contract_required_inputs_equal_what_ks_phylogeny_emits(tmp_path):
    regions = tmp_path / "regions"
    regions.mkdir()
    (regions / "SYN-001_NODE_7_region002.gbk").write_text(GBK, encoding="utf-8")
    result = ks_phylogeny.extract_module_core_domains(regions)
    contract = (Path(ks_phylogeny.__file__).parents[1] / "docs" / "DOMAIN_TREE_CONTRACT.md").read_text(encoding="utf-8")
    top = _marker(contract, "DOMAIN_TREE_REQUIRED_TOP_LEVEL")
    domain = _marker(contract, "DOMAIN_TREE_REQUIRED_DOMAIN_FIELDS")
    assert top == ks_phylogeny.DOMAIN_TREE_REQUIRED_TOP_LEVEL
    assert domain == ks_phylogeny.DOMAIN_TREE_REQUIRED_DOMAIN_FIELDS
    assert set(top) <= set(result)
    assert result["domains"] and set(domain) <= set(result["domains"][0])


def test_contract_requires_exact_alias_join_before_alignment():
    contract = (Path(ks_phylogeny.__file__).parents[1] / "docs" / "DOMAIN_TREE_CONTRACT.md").read_text(encoding="utf-8")
    assert "strain / full node-or-contig / region / BGC alias" in contract
    assert "raw extractor rows lack the BGC alias" in contract
    assert "DOMAIN_ONLY_HINT" in contract and "never a rescue" in contract
