"""Thin wrapper kept for compatibility: the universe now lives in networking_intel.universe.

    python scripts/expansion_universe.py [--offline] [--skip-geocode]

Same as ``python -m networking_intel.universe.cli``; see docs/universe.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from networking_intel.universe.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
