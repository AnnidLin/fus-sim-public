from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Archive paths must be repository-relative: {value}")
    return path.as_posix()


def is_under(path: str, prefix: str) -> bool:
    normalized = path.rstrip("/")
    root = prefix.rstrip("/")
    return normalized == root or normalized.startswith(root + "/")


def build_manifest(root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    base_manifest = load_json(root / normalize_relative_path(spec["base_manifest"]))
    candidate_paths = [item["path"] for item in base_manifest["files"]]
    candidate_paths.extend(spec.get("extra_files", []))
    candidate_paths = sorted({normalize_relative_path(value) for value in candidate_paths})

    prohibited_prefixes = [
        normalize_relative_path(value) for value in spec.get("prohibited_inclusions", [])
    ]
    prohibited = [
        path for path in candidate_paths
        if any(is_under(path, prefix) for prefix in prohibited_prefixes)
    ]

    files: list[dict[str, Any]] = []
    missing: list[str] = []
    for relative in candidate_paths:
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        files.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    digest_input = "\n".join(
        f"{item['path']}\t{item['size_bytes']}\t{item['sha256']}" for item in files
    ).encode("utf-8")
    content_digest = hashlib.sha256(digest_input).hexdigest()

    blockers: list[str] = []
    if missing:
        blockers.append("missing_candidate_files")
    if prohibited:
        blockers.append("prohibited_data_in_candidate")
    if spec.get("project_license_status") != "resolved":
        blockers.append("project_license_unresolved")
    if spec.get("source_revision_status") != "frozen":
        blockers.append("source_revision_not_frozen")
    if not spec.get("release_version"):
        blockers.append("release_version_missing")
    if not spec.get("archive_doi"):
        blockers.append("archive_doi_not_minted")

    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": spec["trace_id"],
        "release_version": spec.get("release_version"),
        "source_revision": spec.get("source_revision"),
        "source_revision_status": spec.get("source_revision_status"),
        "project_license_status": spec.get("project_license_status"),
        "archive_doi": spec.get("archive_doi"),
        "archive_ready": not blockers,
        "status": "ready" if not blockers else "blocked_local_candidate",
        "blockers": blockers,
        "file_count": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in files),
        "content_digest_sha256": content_digest,
        "missing": missing,
        "prohibited_matches": prohibited,
        "files": files,
        "external_dependencies": spec.get("external_dependencies", []),
        "excluded": spec.get("excluded", []),
        "claim_boundary": spec["claim_boundary"],
    }


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# DOI-ready local archive manifest",
        "",
        f"Trace: `{manifest['trace_id']}`  ",
        f"Status: `{manifest['status']}`  ",
        f"Archive ready: `{str(manifest['archive_ready']).lower()}`  ",
        f"Files: {manifest['file_count']}  ",
        f"Total bytes: {manifest['total_size_bytes']}  ",
        f"Content digest: `{manifest['content_digest_sha256']}`",
        "",
        "## Blocking items",
        "",
    ]
    lines.extend(
        [f"- `{item}`" for item in manifest["blockers"]]
        or ["- None"]
    )
    lines.extend(["", "## Candidate files", "", "| Path | Bytes | SHA-256 |", "|---|---:|---|"])
    for item in manifest["files"]:
        lines.append(f"| `{item['path']}` | {item['size_bytes']} | `{item['sha256']}` |")
    lines.extend(["", "## Exclusions", ""])
    for item in manifest["excluded"]:
        lines.append(f"- `{item['path']}` — {item['reason']}")
    lines.extend(["", "## External dependencies", ""])
    for item in manifest["external_dependencies"]:
        lines.append(f"- {item['name']}: {item['access']} ({item['license']})")
    lines.extend(["", "## Claim boundary", "", manifest["claim_boundary"], ""])
    return "\n".join(lines)


def write_csv(path: Path, files: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local submission archive manifest.")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    spec = load_json(args.spec)
    manifest = build_manifest(root, spec)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "manifest.md").write_text(render_markdown(manifest), encoding="utf-8")
    write_csv(args.output_dir / "files.csv", manifest["files"])
    print(json.dumps({
        "status": manifest["status"],
        "archive_ready": manifest["archive_ready"],
        "file_count": manifest["file_count"],
        "total_size_bytes": manifest["total_size_bytes"],
        "blockers": manifest["blockers"],
    }))


if __name__ == "__main__":
    main()
