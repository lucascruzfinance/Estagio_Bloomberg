from __future__ import annotations

import argparse
import json
from pathlib import Path

from networking_intel.scoring.pipeline import run_scoring


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prompt 4 explainable opportunity scoring")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=Path("config/scoring/opportunity_v1.yaml"))
    parser.add_argument("--draws", type=int, default=1000, help="Dirichlet sensitivity draws")
    args = parser.parse_args(argv)
    manifest = run_scoring(args.root, args.root / args.config, draws=args.draws)
    print(
        json.dumps(
            {k: manifest[k] for k in ("model_version", "units_scored", "sanity", "sensitivity")},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
