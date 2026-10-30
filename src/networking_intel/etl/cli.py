from __future__ import annotations

import json

from networking_intel.config import get_settings
from networking_intel.etl.load import run_etl


def main() -> int:
    settings = get_settings()
    result = run_etl(settings.etl_input_path, settings.database_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
