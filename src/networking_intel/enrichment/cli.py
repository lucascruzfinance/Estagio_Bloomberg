from __future__ import annotations

import argparse
import json
from pathlib import Path

from networking_intel.enrichment.cache import RawCache
from networking_intel.enrichment.http import Fetcher
from networking_intel.enrichment.pipeline import EnrichmentPaths, run_enrichment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prompt 3 public-source enrichment")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--months", type=int, default=13, help="Informe Diário months to load")
    parser.add_argument("--offline", action="store_true", help="use only the raw cache")
    parser.add_argument("--skip-geocode", action="store_true")
    args = parser.parse_args(argv)

    root: Path = args.root
    paths = EnrichmentPaths(
        pilot_csv=root / "data/staging/pilot_accounts.csv",
        registry=root / "data/reference/identity_registry.yaml",
        raw_dir=root / "data/raw",
        output_dir=root / "data/enriched",
        review_queue=root / "data/review/conflicts.csv",
        report_doc=root / "docs/enrichment_quality_report.md",
    )
    fetcher = Fetcher(RawCache(paths.raw_dir), offline=args.offline)
    payload = run_enrichment(
        paths, fetcher=fetcher, months=args.months, geocode_addresses=not args.skip_geocode
    )
    print(json.dumps(payload["counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
