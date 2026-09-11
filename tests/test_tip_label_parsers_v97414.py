"""Portable parser regressions; these display helpers do not verify taxonomy."""
import pytest
from mamey.tip_label import binomial, host_taxon


@pytest.mark.parametrize('source,expected', [
 ('Nocardioides flavus (ex Ruan and Zhang 1979) Yoon et al. 2005', 'Nocardioides flavus'),
 ('NR_112543.1 Streptomyces coelicolor', 'Streptomyces coelicolor'),
 ('Streptomyces_sp.', 'Streptomyces sp.'),
 ('Bacillus subtilis subsp. subtilis', 'Bacillus subtilis subsp. subtilis'),
 ('', ''),
])
def test_binomial(source, expected):
    assert binomial(source) == expected


@pytest.mark.parametrize('source,expected', [
 ('Atta sp. CF180404-02\x20\x27\x27Joan Call', 'Atta sp.'),
 ('Cladonia and Moss', 'Cladonia and Moss'),
 ('Bombus sp.', 'Bombus sp.'),
 ('Rotten log.', 'Rotten log'),
 ('colony sample from unlabeled site', 'colony sample from unlabeled…'),
 ('Enterobacteriaceae uncultured bacterium clone examples here today', 'Enterobacteriaceae uncultured…'),
])
def test_host_display(source, expected):
    assert host_taxon(source) == expected


def test_first_word_cannot_be_severed():
    assert host_taxon('Enterobacteriaceae', width=5) == '…'


@pytest.mark.parametrize('width', [0, -1, True, 1.5])
def test_invalid_width(width):
    with pytest.raises(ValueError):
        host_taxon('Moss', width=width)


def test_unclosed_parenthesis():
    out = host_taxon('Moss (Bryophyta undetermined species growing on rock unclosed')
    assert out.count('(') == out.count(')')
