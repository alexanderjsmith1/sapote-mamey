"""Pure-text regressions for a shipped claim rule; inputs are quoted test fiction."""
import pytest
from mamey.claim_safety_gate import lint_text, _normalize_for_detection, _ANCHOR_LABEL_RE, _orig_span

# Expected raw fragments assert user-visible original spelling/offsets, not a
# normalized re-expression. Encoded arrows are inside the matched span.
@pytest.mark.parametrize('text,fragment', [
    ('prefix KNOWN -> tetrachlorizine tail', 'KNOWN -> tetrachlorizine'),
    ('prefix KNOWN → tetrachlorizine tail', 'KNOWN → tetrachlorizine'),
    ('prefix KNOWN -&gt; tetrachlorizine tail', 'KNOWN -&gt; tetrachlorizine'),
    ('prefix KNOWN &#45;&#62; tetrachlorizine tail', 'KNOWN &#45;&#62; tetrachlorizine'),
    ('prefix KNOWN &#x2d;&#x3e; tetrachlorizine tail', 'KNOWN &#x2d;&#x3e; tetrachlorizine'),
    ('prefix KNOWN &rarr; tetrachlorizine tail', 'KNOWN &rarr; tetrachlorizine'),
    ('prefix **KNOWN** -> **tetrachlorizine** tail', 'KNOWN** -> **tetrachlorizine'),
    ('prefix `KNOWN` -> `tetrachlorizine` tail', 'KNOWN` -> `tetrachlorizine'),
    ('prefix \u200bKNOWN -> tetrachlorizine tail', 'KNOWN -> tetrachlorizine'),
    ('prefix KNO&#87;N -&gt; tetrachlorizine tail', 'KNO&#87;N -&gt; tetrachlorizine'),
    ('prefix ＫＮＯＷＮ -> tetrachlorizine tail', 'ＫＮＯＷＮ -> tetrachlorizine'),
    ('prefix KNOWN \\-> tetrachlorizine tail', 'KNOWN \\-> tetrachlorizine'),
    ('prefix KNOWN -\\> tetrachlorizine tail', 'KNOWN -\\> tetrachlorizine'),
    ('ＫＮＯＷＮ －＞ ｔｅｔｒａｃｈｌｏｒｉｚｉｎｅ', 'ＫＮＯＷＮ －＞ ｔｅｔｒａｃｈｌｏｒｉｚｉｎｅ'),
    ('KNOWN -\u200b> tetrachlorizine', 'KNOWN -\u200b> tetrachlorizine'),
    ('KNOWN -&#8203;> tetrachlorizine', 'KNOWN -&#8203;> tetrachlorizine'),
    ('KNOWN -> [tetrachlorizine]', 'KNOWN -> [tetrachlorizine'),
    ('KNOWN \\-\\> tetrachlorizine', 'KNOWN \\-\\> tetrachlorizine'),
    ('preface 雪 | K\u200bNOWN → tetra\u200bchlorizine |', 'K\u200bNOWN → tetra\u200bchlorizine'),
])
def test_anchor_arrow_flags_and_reports_exact_original_span(text, fragment):
    norm, mapping = _normalize_for_detection(text)
    match = _ANCHOR_LABEL_RE.search(norm)
    assert match is not None
    assert len(mapping) == len(norm)
    assert mapping == sorted(mapping)
    assert all(0 <= i < len(text) for i in mapping)
    assert _orig_span(text, mapping, match.start(), match.end()) == fragment
    findings = lint_text(text)
    assert any(row.startswith('possible anchor-as-product-identity overclaim: ') and repr(fragment) in row for row in findings)

@pytest.mark.parametrize('text', [
    'anchor -> tetrachlorizine family (2/17 genes)',
    'anchor → tetrachlorizine family (2/17 genes)',
    'anchor -&gt; tetrachlorizine family (2/17 genes)',
    'anchor -> tetrachlorizine class',
    'anchor -> tetrachlorizine families',
    'anchor -> tetrachlorizine group',
    'anchor -> tetrachlorizine type',
    'anchor -> tetrachlorizine cluster',
    'Cannot be claimed: KNOWN -> tetrachlorizine',
    "We can't claim: KNOWN -> tetrachlorizine",
    'similarity anchor -> tetrachlorizine',
    'No evidence that KNOWN -> tetrachlorizine.',
    'The evidence does not support KNOWN -> tetrachlorizine.',
    'capacity consistent with anchor -> tetrachlorizine',
    'weak anchor (2/17 genes -> tetrachlorizine family); not a product call',
    'The deep assembly line makes it a strong capacity candidate.',
])
def test_safe_family_negation_and_capacity_contexts_remain_clean(text):
    norm, mapping = _normalize_for_detection(text)
    # Shape expectations are fixed input properties; a missed matcher is a
    # failure, never a reason to skip a safe-context assertion.
    expected_match = not text.startswith(('weak anchor (', 'The deep assembly'))
    assert bool(_ANCHOR_LABEL_RE.search(norm)) is expected_match
    assert lint_text(text) == []

@pytest.mark.parametrize('text', [
    'No evidence for identity; KNOWN -> tetrachlorizine.',
    'No evidence for identity — KNOWN -> tetrachlorizine.',
    'KNOWN -> tetrachlorizine; capacity consistent with a family is discussed below.',
    'KNOWN -> tetrachlorizine (not identity)',
    '<not identity> KNOWN -> tetrachlorizine',
    '[not identity] KNOWN -> tetrachlorizine',
    '(not identity) KNOWN -> tetrachlorizine',
])
def test_adjacent_independent_clauses_do_not_hide_anchor(text):
    assert any('anchor-as-product-identity' in row for row in lint_text(text))

@pytest.mark.parametrize('text', [
    '<div>(alpha)[beta]{gamma}> -> <!--note-->',
    '<section data-tag="x-">text</section> -> <!-- note -->',
])
def test_only_literal_arrow_greater_than_survives_wrapper_fold(text):
    norm, mapping = _normalize_for_detection(text)
    arrow = text.index('->') + 1
    assert norm.count('>') == 1
    for i, char in enumerate(text):
        if char not in '()[]{}<>':
            continue
        normalized = [norm[j] for j, source in enumerate(mapping) if source == i]
        assert normalized == (['>'] if i == arrow else ['\n'])
    assert mapping == list(range(len(text)))

@pytest.mark.parametrize('text', [
    'KNOWN -> tetrachlorizine (comment)',
    '<b>KNOWN -&gt; tetrachlorizine</b>',
    '**KNOWN** → tetrachlorizine',
])
def test_mild_delegate_fold_preserves_punctuation_contract(text):
    norm, mapping = _normalize_for_detection(text, fold_wrappers=False)
    assert len(norm) == len(mapping)
    assert '(' not in text or '(' in norm
    assert '*' not in text or '*' in norm
    assert '->' not in text or '->' in norm
    assert mapping == sorted(mapping)
