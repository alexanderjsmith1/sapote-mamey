"""Allow `python -m mamey` invocation.

Forces the parent directory onto sys.path so the local mamey/ package takes
precedence over any previously installed version in site-packages.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.cli import main
raise SystemExit(main())
