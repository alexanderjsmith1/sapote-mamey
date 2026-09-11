#!/usr/bin/env python3
"""
Mamey Standalone ChatGPT Bundle runner.

Works without pip install — use this in ChatGPT, Colab, or any environment
where a previously installed version of mamey may be cached.

Usage:
    python mamey_run.py run --strain X --input-zip Y [options]
    python mamey_run.py run --strains A.zip B.zip C.zip --master master.xlsx
    python mamey_run.py validate ./path/to/package_dir
    python mamey_run.py run --help
"""
import sys
import os
# Force the local mamey/ package to take precedence over any installed version.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mamey.cli import main
sys.exit(main())
