from __future__ import annotations

import io
import zipfile
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "prompt3"


def zip_fixtures(*names: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in names:
            archive.writestr(name, (FIXTURES / name).read_bytes())
    return buffer.getvalue()
