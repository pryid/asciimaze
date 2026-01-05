"""Test configuration.

Pytest sometimes runs with the current working directory set to ``tests/``.
Make sure the project root (and thus the ``maze3d`` package) is importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
