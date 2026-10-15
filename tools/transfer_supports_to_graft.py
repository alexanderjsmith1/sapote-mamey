#!/usr/bin/env python3
"""Transfer only reference split supports to an admitted graft; preserve root and lengths."""
import argparse
import json
from pathlib import Path
from Bio import Phylo


def split_key(tips, all_tips):
    tips = frozenset(tips)
    return frozenset(all_tips - tips) if min(all_tips) in tips else tips


def support_splits(tree):
    refs = frozenset(t.name for t in tree.get_terminals())
    if len(refs) != len(tree.get_terminals()) or None in refs:
        raise ValueError('SUPPORT_TIP_IDENTITY')
    result = {}
    for node in tree.get_nonterminals():
        tips = {t.name for t in node.get_terminals()}
        if node.confidence is None or not 1 < len(tips) < len(refs)-1:
            continue
        key = split_key(tips, refs)
        if key in result and result[key] != node.confidence:
            raise ValueError('SUPPORT_SPLIT_CONFLICT')
        result[key] = node.confidence
    return refs, result


def rooted_signature(tree):
    return [(tuple(sorted(t.name for t in n.get_terminals())), n.branch_length)
            for n in tree.find_clades()]


def transfer_preserving_root(graft_path, support_path, output):
    graft = Phylo.read(graft_path, 'newick')
    support = Phylo.read(support_path, 'newick')
    refs, supports = support_splits(support)
    tips = [t.name for t in graft.get_terminals()]
    if len(tips) != len(set(tips)) or None in tips or not refs <= set(tips):
        raise ValueError('REFERENCE_TIPS_MISSING_OR_DUPLICATE')
    # A support tree is evidence only for the same reference splits. Lengths may
    # differ after placement; neither those lengths nor query pendants are changed.
    available = {split_key({t.name for t in n.get_terminals()} & refs, refs)
                 for n in graft.get_nonterminals()}
    if not set(supports) <= available:
        raise ValueError('REFERENCE_SUPPORT_SPLIT_NOT_IN_GRAFT')
    before = rooted_signature(graft)
    count = 0
    for node in graft.get_nonterminals():
        node.confidence = None
        node.name = None
        children = sum(bool({t.name for t in c.get_terminals()} & refs) for c in node.clades)
        key = split_key({t.name for t in node.get_terminals()} & refs, refs)
        if children >= 2 and key in supports:
            node.confidence = supports[key]
            count += 1
    with Path(output).open('x') as handle:
        Phylo.write(graft, handle, 'newick', format_branch_length='%.17g', format_confidence='%.17g')
    after = rooted_signature(Phylo.read(output, 'newick'))
    # Biopython writes absent root lengths as zero; no rooted edge is altered.
    norm = lambda sig: [(tips, length or 0.0) for tips, length in sig]
    if norm(before) != norm(after):
        raise ValueError('SUPPORT_TRANSFER_ROOT_OR_LENGTH_DRIFT')
    return {'labelled_nodes': count, 'root_policy': 'preserve_supplied', 'length_policy': 'unchanged'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graft'); parser.add_argument('support'); parser.add_argument('out')
    args = parser.parse_args()
    print(json.dumps(transfer_preserving_root(args.graft, args.support, args.out)))

if __name__ == '__main__':
    main()
