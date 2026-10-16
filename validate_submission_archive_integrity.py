"""Independently rehash and validate the local submission archive candidate."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_BLOCKERS = {"project_license_unresolved", "source_revision_not_frozen", "archive_doi_not_minted"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(root: Path) -> dict:
    archive_dir = root / "paper/submission_archive_20260829"
    manifest = json.loads((archive_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    rows = manifest["files"]
    paths = [row["path"] for row in rows]
    bad_paths = [path for path in paths if Path(path).is_absolute() or ".." in Path(path).parts]
    mismatches = []
    for row in rows:
        path = root / row["path"]
        if not path.is_file():
            mismatches.append({"path": row["path"], "reason": "missing"})
            continue
        if path.stat().st_size != row["size_bytes"]:
            mismatches.append({"path": row["path"], "reason": "size"})
        if sha256(path) != row["sha256"]:
            mismatches.append({"path": row["path"], "reason": "sha256"})
    digest_input = "\n".join(f"{row['path']}\t{row['size_bytes']}\t{row['sha256']}" for row in rows).encode("utf-8")
    recomputed_digest = hashlib.sha256(digest_input).hexdigest()
    with (archive_dir / "files.csv").open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    csv_normalized = [{"path": row["path"], "size_bytes": int(row["size_bytes"]), "sha256": row["sha256"]} for row in csv_rows]
    checks = {
        "manifest_has_136_files": manifest.get("file_count") == 136 and len(rows) == 136,
        "paths_are_unique": len(paths) == len(set(paths)),
        "paths_are_repository_relative": not bad_paths,
        "all_sizes_and_hashes_match": not mismatches,
        "total_size_matches": sum(row["size_bytes"] for row in rows) == manifest.get("total_size_bytes"),
        "content_digest_matches": recomputed_digest == manifest.get("content_digest_sha256"),
        "csv_matches_manifest": csv_normalized == rows,
        "no_missing_or_prohibited": not manifest.get("missing") and not manifest.get("prohibited_matches"),
        "archive_remains_blocked": manifest.get("archive_ready") is False and manifest.get("status") == "blocked_local_candidate",
        "exact_release_blockers_retained": set(manifest.get("blockers", [])) == EXPECTED_BLOCKERS,
        "three_external_dependencies_recorded": len(manifest.get("external_dependencies", [])) == 3,
        "restricted_and_large_artifacts_excluded": len(manifest.get("excluded", [])) >= 5,
    }
    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "trace_id": "TRACE-20260829-001",
        "status": "passed_archive_integrity_blocked_release" if all(checks.values()) else "failed",
        "archive_ready": False,
        "file_count": len(rows),
        "mismatches": mismatches,
        "bad_paths": bad_paths,
        "recomputed_content_digest_sha256": recomputed_digest,
        "checks": checks,
        "failed_checks": [key for key, value in checks.items() if not value],
        "claim_boundary": "Bitwise archive integrity and exclusion checks do not establish physical validation or release authorization.",
    }


def render(report: dict) -> str:
    lines = ["# Submission archive integrity validation", "", f"Status: `{report['status']}`  ", f"Files rehashed: `{report['file_count']}`  ", f"Digest: `{report['recomputed_content_digest_sha256']}`", "", "## Checks", ""]
    lines += [f"- [{'x' if value else ' '}] `{key}`" for key, value in report["checks"].items()]
    lines += ["", report["claim_boundary"], ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.root.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "archive_integrity.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "archive_integrity.md").write_text(render(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "files": report["file_count"], "failed": report["failed_checks"]}))
    return 0 if not report["failed_checks"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
