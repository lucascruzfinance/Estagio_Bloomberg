"""Build the territory universe.

python -m networking_intel.universe.cli                 # online, cache-first
python -m networking_intel.universe.cli --offline       # raw cache only
python -m networking_intel.universe.cli --skip-geocode  # no Nominatim calls
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from networking_intel.enrichment.cache import RawCache
from networking_intel.enrichment.http import Fetcher
from networking_intel.universe.pipeline import UniversePaths, run_universe
from networking_intel.universe.report import write_reports


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--offline", action="store_true", help="use only data/raw")
    parser.add_argument("--skip-geocode", action="store_true")
    parser.add_argument("--months", type=int, default=37, help="Informe Diário window")
    args = parser.parse_args()

    paths = UniversePaths(args.root.resolve())
    fetcher = Fetcher(RawCache(paths.raw_dir), offline=args.offline)
    report = run_universe(
        paths,
        fetcher=fetcher,
        months=args.months,
        geocode_buildings=not args.skip_geocode,
        progress=lambda message: print(f"[universe] {message}", flush=True),
    )
    write_reports(paths.root)
    print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
