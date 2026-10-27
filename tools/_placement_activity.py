"""Read explicitly recorded, strain-level activity for separate display strips."""
import csv
import json
import math
from pathlib import Path

LABELS = ('C. albicans', 'C. auris', 'C. albicans or C. auris (not recorded)')
ALIASES = {
    LABELS[0]: ('C. albicans', 'Candida albicans', 'anti_C_albicans'),
    LABELS[1]: ('C. auris', 'Candida auris', 'anti_C_auris'),
    LABELS[2]: (LABELS[2], 'Candida (species not named)', 'anti_Candida_unspecified'),
    'MRSA': ('MRSA', 'anti_MRSA'),
}


POOLED = '*Candida*'
# .452: pooled Candida state = the strongest state recorded for any Candida reading of that strain. A positive anywhere
# gives a positive; then a tested negative; then not tested; then blank. States are never converted into one another.
# The three-state labels (--activity-states three) rank inside the same order: a state of either mode sorts by strength.
POOL_ORDER = ('strong (≥80%)', '+', 'moderate (50–79%)', 'tested, below 80%', 'tested, below 50%', '−', 'n.t.', '')

# Numeric readings are classed by --activity-states. 'two' (default): 80% or more is strong, everything else is tested,
# below 80%. 'three': strong 80% or more, moderate 50-79%, tested below 50% ("active" means 50% or more).
# The labels are palette values (tools/phylo_display_palette.tsv) and legend text.
STATES = {'two': ('strong (≥80%)', 'tested, below 80%'),
          'three': ('strong (≥80%)', 'moderate (50–79%)', 'tested, below 50%')}


def pool_candida(result, labels):
    """(result, labels) -> the same with the Candida species readings pooled into one POOLED column."""
    cand = [label for label in labels if label in LABELS]
    pooled = {}
    for sid, row in result.items():
        states = [row.get(label, '') for label in cand]
        new = {k: v for k, v in row.items() if k not in LABELS}
        new[POOLED] = min(states, key=POOL_ORDER.index) if states else ''
        pooled[sid] = new
    return pooled, [POOLED] + [label for label in labels if label not in LABELS]


def profile(layout='', path=None):
    if not layout:
        return {}
    profiles = json.loads(Path(path or Path(__file__).resolve().parents[1]/'mamey/data/bioassay_layouts.json').read_text())
    if layout.startswith('_') or layout not in profiles or not isinstance(profiles[layout], dict):
        raise ValueError('UNKNOWN_BIOASSAY_LAYOUT')
    result = profiles[layout]
    if 'split_candida' in result and not isinstance(result['split_candida'], bool):
        raise ValueError('SPLIT_CANDIDA_MUST_BE_BOOLEAN')
    if 'tree_pool_candida' in result and not isinstance(result['tree_pool_candida'], bool):
        raise ValueError('TREE_POOL_CANDIDA_MUST_BE_BOOLEAN')
    return result


def state(value, states='two'):
    if states not in STATES:
        raise ValueError('ACTIVITY_STATES_UNKNOWN: ' + str(states))
    text = value.strip()
    if text in ('', '+', '−', 'n.t.'):
        return text
    if text == '-':
        return '−'
    known = {'positive': '+', 'negative': '−', 'not_tested': 'n.t.'}
    if text.lower() in known:
        return known[text.lower()]
    try:
        number = float(text)
    except ValueError:
        raise ValueError('ACTIVITY_STATE_INVALID: ' + text) from None
    if not math.isfinite(number):
        raise ValueError('ACTIVITY_PERCENT_INVALID')
    if states == 'three':
        return STATES['three'][0] if number >= 80 else STATES['three'][1] if number >= 50 else STATES['three'][2]
    return STATES['two'][0] if number >= 80 else STATES['two'][1]


def load(path, material='Crude extract', pool=False, states='two'):
    with Path(path).open(newline='', encoding='utf-8-sig') as handle:
        first = handle.readline(); handle.seek(0)
        reader = csv.DictReader(handle, delimiter='\t' if '\t' in first else ',')
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or 'strain' not in fields:
            raise ValueError('ACTIVITY_SCHEMA')
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError('ACTIVITY_SCHEMA')
    result = {}; present = set(); recorded = set()
    if {'organism','material','best_pct'} <= set(fields):
        names = {alias:label for label,aliases in ALIASES.items() for alias in aliases}
        for row in rows:
            if row['material'] != material or row['organism'] not in names:
                continue
            sid = row['strain'].strip(); label = names[row['organism']]
            if not sid or (sid,label) in recorded:
                raise ValueError('ACTIVITY_DUPLICATE_OR_EMPTY_STRAIN')
            recorded.add((sid,label)); present.add(label)
            result.setdefault(sid,{})[label] = state(row['best_pct'], states)
    else:
        columns = {}
        for label,aliases in ALIASES.items():
            found = [name for name in aliases if name in fields]
            if len(found)>1:
                raise ValueError('ACTIVITY_AMBIGUOUS_COLUMNS: '+label)
            if found:columns[label]=found[0]
        if not set(LABELS[:2]) <= set(columns):
            raise ValueError('SPLIT_CANDIDA_COLUMNS_REQUIRED')
        present = set(columns)
        for row in rows:
            sid=row['strain'].strip()
            if not sid or sid in result:raise ValueError('ACTIVITY_DUPLICATE_OR_EMPTY_STRAIN')
            result[sid]={label:state(row[column], states) for label,column in columns.items()}
    labels=[label for label in (*LABELS,'MRSA') if label in present]
    if not set(LABELS[:2]) <= present:
        raise ValueError('SPLIT_CANDIDA_SPECIES_REQUIRED')
    # The unknown-species strip appears only when at least one explicit reading
    # or not-tested state was recorded; blank-only columns do not invent readings.
    if LABELS[2] in labels and not any(row.get(LABELS[2],'') for row in result.values()):
        labels.remove(LABELS[2])
    if pool:
        result, labels = pool_candida(result, labels)
    return result, [{'column':f'activity_{i+1}','label':label} for i,label in enumerate(labels)]


def decorate(rows, measurements, strips, normalize=lambda x:x):
    bound={normalize(key):value for key,value in measurements.items()}
    if len(bound)!=len(measurements):raise ValueError('ACTIVITY_NORMALIZED_DUPLICATE')
    for row in rows:
        measured=bound.get(normalize(row['tip']),{}) if row['role']=='query' else {}
        for strip in strips:
            row[strip['column']]=measured.get(strip['label'],'')
    return rows
