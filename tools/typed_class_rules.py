"""Portable typed family-evidence evaluator. No product or completion scores."""
import json
import re
from pathlib import Path


def load_rules(path):
    obj = json.loads(Path(path).read_text())
    keys = set()
    for rule in obj['rules']:
        if rule['class_key'] in keys:
            raise ValueError('duplicate class')
        keys.add(rule['class_key'])
        for step in rule['steps']:
            if step['type'] not in {'required', 'optional', 'alternative_group'}:
                raise ValueError('unknown step type')
            if step['type'] != 'optional' and not step['models']:
                raise ValueError('mandatory signature has no models')
            if step['type'] == 'alternative_group' and len(set(step['models'])) < 2:
                raise ValueError('alternative group needs two distinct models')
    return obj


def evaluate(rule, evidence):
    """Evidence rows require locus_tag, exact model token, and source locator.

    A row is admitted annotation evidence, not a sequence/function assertion.
    Duplicate domain rows count once per locus; optional absence is silent.
    """
    rows = list(evidence)
    out = []
    for step in rule['steps']:
        hits = [r for r in rows if r.get('model') in step['models'] and r.get('locus_tag') and r.get('source')]
        genes = sorted({r['locus_tag'] for r in hits})
        models = sorted({r['model'] for r in hits})
        visible = bool(hits) or step['type'] != 'optional'
        out.append(dict(step=step['label'], type=step['type'], visible=visible,
                        state='FAMILY_SEEN' if hits else 'SILENT_OPTIONAL' if not visible else 'NOT_SEEN',
                        genes=genes, gene_count=len(genes), models=models,
                        evidence=hits, citations=step['citations'], interpretation=step['interpretation']))
    return out


def text_lines(rule, evidence):
    """Concise display lines: no warnings for absent optional rows."""
    lines = []
    for row in evaluate(rule, evidence):
        if not row['visible']:
            continue
        if row['genes']:
            lines.append(row['step'] + ': family evidence in ' + ', '.join(row['genes']))
        else:
            lines.append(row['step'] + ': not seen in the admitted annotations')
    return lines


def builder_evidence(D, bgc):
    """Adapt current builder gene/domain objects using exact tokens only.

    Caller must already have bound D to its current package/assembly. Free text,
    smCOG descriptions and generic product prose never satisfy a model.
    """
    out = []
    for g in D['genes'].get(bgc, []):
        tag = g['locus_tag']
        for d in D['dom'].get(tag, []):
            out.append(dict(locus_tag=tag, model=d[1], source=f'domains.csv:{bgc}:{tag}', evalue=d[0]))
        for model in g.get('sec_met_domains', '').split(';'):
            if model.strip():
                out.append(dict(locus_tag=tag, model=model.strip(), source=f'gene_by_gene_all_bgcs.csv:{bgc}:{tag}:sec_met_domains'))
        for model in re.findall(r'(\S+) \(E-value:', g.get('product_qualifier', '')):
            out.append(dict(locus_tag=tag, model=model, source=f'gene_by_gene_all_bgcs.csv:{bgc}:{tag}:product_qualifier'))
    return out


def builder_lines(D, bgc, rulebook):
    """Return family-only paragraphs for the six exact class keys/aliases.

    Integration: append these paragraphs beside legacy logic, retaining legacy
    CLASS_STEPS unchanged. Never feed these steps into its core-completeness test.
    """
    products = {p.strip() for p in D['inv'][bgc]['Products'].split(';')}
    evidence = builder_evidence(D, bgc)
    return [(r['class_key'], text_lines(r, evidence)) for r in rulebook['rules']
            if products.intersection({r['class_key'], *r.get('aliases', [])})]
