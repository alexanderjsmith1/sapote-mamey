"""Optional external fixture roots; bundled hermetic fixtures remain preferred.

Set SAPOTE_UPLOADS and SAPOTE_OUTPUTS to bind local test inputs. The legacy
paths are retained as fallbacks; absence still leaves external tests gated.
"""
import os
UPLOADS = os.environ.get("SAPOTE_UPLOADS", "/mnt/user-data/uploads")
OUTPUTS = os.environ.get("SAPOTE_OUTPUTS", "/mnt/user-data/outputs")
