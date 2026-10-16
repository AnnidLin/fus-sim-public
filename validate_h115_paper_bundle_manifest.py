"""Verify every file in the fixed-scope H115 paper bundle manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    checks = {}
    for item in report.get("files", []):
        path = ROOT / item["path"]
        checks[item["path"]] = (
            path.is_file()
            and path.stat().st_size == item["size_bytes"]
            and sha256(path) == item["sha256"]
        )
    passed = (
        report.get("status") == "passed"
        and not report.get("missing")
        and len(checks) == report.get("expected_count")
        and all(checks.values())
    )
    failed = [path for path, value in checks.items() if not value]
    print(json.dumps({"manifest_valid": passed, "file_count": len(checks), "failed": failed}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
