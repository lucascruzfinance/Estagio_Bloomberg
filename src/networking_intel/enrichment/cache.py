from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from networking_intel.enrichment.sources import require_real_source

MANIFEST_NAME = "manifest.jsonl"


@dataclass(frozen=True)
class RawArtifact:
    source_id: str
    request_key: str
    url: str
    path: str
    sha256: str
    size_bytes: int
    http_status: int
    fetched_at: str
    content_type: str | None

    @property
    def fetched_datetime(self) -> datetime:
        return datetime.fromisoformat(self.fetched_at)


def request_key(url: str, params: dict[str, str] | None = None) -> str:
    payload = json.dumps({"url": url, "params": params or {}}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RawCache:
    """Content-addressed, write-once store for raw source payloads.

    Files are never overwritten: identical content is deduplicated by SHA-256 and
    every fetch appends a manifest line, so earlier snapshots stay reproducible.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = root / MANIFEST_NAME

    def store(
        self,
        *,
        source_id: str,
        url: str,
        content: bytes,
        http_status: int,
        suffix: str,
        params: dict[str, str] | None = None,
        content_type: str | None = None,
        fetched_at: datetime | None = None,
    ) -> RawArtifact:
        require_real_source(source_id)
        digest = hashlib.sha256(content).hexdigest()
        target = self.root / source_id / f"{digest}{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"immutable cache entry was modified: {target}")
        else:
            with target.open("xb") as handle:
                handle.write(content)
            os.chmod(target, stat.S_IREAD)
        artifact = RawArtifact(
            source_id=source_id,
            request_key=request_key(url, params),
            url=url,
            path=target.relative_to(self.root).as_posix(),
            sha256=digest,
            size_bytes=len(content),
            http_status=http_status,
            fetched_at=(fetched_at or datetime.now(UTC)).isoformat(),
            content_type=content_type,
        )
        with self.manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(artifact), ensure_ascii=False) + "\n")
        return artifact

    def entries(self) -> list[RawArtifact]:
        if not self.manifest_path.exists():
            return []
        with self.manifest_path.open(encoding="utf-8") as handle:
            return [RawArtifact(**json.loads(line)) for line in handle if line.strip()]

    def latest(
        self,
        source_id: str,
        url: str,
        params: dict[str, str] | None = None,
        *,
        max_age_seconds: float | None = None,
        now: datetime | None = None,
    ) -> RawArtifact | None:
        key = request_key(url, params)
        matches = [
            entry
            for entry in self.entries()
            if entry.source_id == source_id and entry.request_key == key
        ]
        if not matches:
            return None
        newest = max(matches, key=lambda entry: entry.fetched_at)
        if max_age_seconds is not None:
            age = ((now or datetime.now(UTC)) - newest.fetched_datetime).total_seconds()
            if age > max_age_seconds:
                return None
        return newest

    def path_of(self, artifact: RawArtifact) -> Path:
        return self.root / artifact.path

    def read_bytes(self, artifact: RawArtifact) -> bytes:
        content = self.path_of(artifact).read_bytes()
        if hashlib.sha256(content).hexdigest() != artifact.sha256:
            raise RuntimeError(f"cache entry failed integrity check: {artifact.path}")
        return content
