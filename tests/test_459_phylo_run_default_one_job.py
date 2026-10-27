"""phylo-run defaults to 4 threads and one GToTree job at a time (house limit: four threads)."""
from mamey import cli

BASE = ["phylo-run", "--genome-list", "/abs/g.txt", "--workdir", "/abs/w", "--outgroup", "OG"]


def test_phylo_run_defaults_are_four_threads_one_job():
    args = cli.build_parser().parse_args(BASE)
    assert args.threads == 4
    assert args.parallel == 1
    assert args.threads * args.parallel <= 4


def test_phylo_run_explicit_parallel_is_still_honoured():
    args = cli.build_parser().parse_args(BASE + ["--threads", "2", "--parallel", "2"])
    assert (args.threads, args.parallel) == (2, 2)
