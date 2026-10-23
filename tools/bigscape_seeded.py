#!/usr/bin/env python3
"""Seed BiG-SCAPE's process-local RNGs without modifying upstream code."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.logging_setup import get_logger
log = get_logger(__name__)

def seed_value(value):
    number = int(value)
    if not 0 <= number <= 4294967295:
        raise argparse.ArgumentTypeError("seed must be in [0, 4294967295]")
    return number

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hash-seed", type=seed_value, default=0)
    parser.add_argument("--numpy-seed", type=seed_value, default=0)
    parser.add_argument("--random-seed", type=seed_value, default=0)
    parser.add_argument("--allow-unseeded", action="store_true")
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    actual = os.environ.get("PYTHONHASHSEED")
    if actual != str(args.hash_seed) and not args.allow_unseeded:
        log.error("Refusing: start Python with PYTHONHASHSEED=%s (observed %r)", args.hash_seed, actual)
        return 2
    arguments = args.arguments
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    receipt = {"schema_version": 1, "hash_seed": actual,
               "requested_hash_seed": args.hash_seed, "numpy_seed": args.numpy_seed,
               "random_seed": args.random_seed, "allow_unseeded": args.allow_unseeded,
               "argv": arguments, "python": sys.version, "executable": sys.executable,
               "versions": {}, "status": "STARTING", "exit_code": None}
    # Exclusive reservation prevents accidentally replacing a prior run's receipt.
    with args.receipt.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
    code = 1
    try:
        import numpy
        numpy.random.seed(args.numpy_seed)
        random.seed(args.random_seed)
        receipt["versions"]["numpy"] = numpy.__version__
        for distribution in ("big-scape", "scikit-learn"):
            try:
                receipt["versions"][distribution] = importlib.metadata.version(distribution)
            except importlib.metadata.PackageNotFoundError:
                receipt["versions"][distribution] = "UNAVAILABLE"
        from big_scape.__main__ import main as external_main
        sys.argv = ["bigscape", *arguments]
        result = external_main()
        code = int(result) if result is not None else 0
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else (0 if error.code is None else 1)
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        log.error("BiG-SCAPE launcher failed: %s", receipt["error"])
    finally:
        receipt.update(status="EXITED" if code == 0 else "FAILED", exit_code=code)
        with args.receipt.open("w", encoding="utf-8") as handle:
            json.dump(receipt, handle, indent=2)
            handle.write("\n")
    return code

if __name__ == "__main__":
    sys.exit(main())
