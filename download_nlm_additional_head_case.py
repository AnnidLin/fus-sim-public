from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
CASE_ID = "nlm_additional_head_72m"
SERIES = {
    "ct": {
        "url": "https://data.lhncbc.nlm.nih.gov/public/Visible-Human/Additional-Head-Images/MR_CT_DICOM/CAT/",
        "pattern": r"J\.\d+\.gz",
        "destination": "ct_dicom",
        "expected_count": 463,
    },
    "t2": {
        "url": "https://data.lhncbc.nlm.nih.gov/public/Visible-Human/Additional-Head-Images/MR_CT_DICOM/MRI/T2_512/",
        "pattern": r"I\.\d+\.gz",
        "destination": "t2_dicom",
        "expected_count": 229,
    },
}


class DownloadError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_bytes(url: str, timeout_s: int = 60) -> bytes:
    request = Request(url, headers={"User-Agent": "fus-sim-research-data-import/1.0"})
    with urlopen(request, timeout=timeout_s) as response:
        return response.read()


def parse_index(html: str, file_pattern: str) -> list[tuple[str, int]]:
    rows = re.findall(r"href='([^']+)'.*?class='size'>(\d+)<", html)
    selected = [(name, int(size)) for name, size in rows if re.fullmatch(file_pattern, name)]
    if not selected:
        raise DownloadError("no matching files found in NLM directory index")
    return sorted(selected)


def commit_download(temporary: Path, target: Path, expected_size: int) -> None:
    if target.is_file():
        if target.stat().st_size != expected_size:
            raise DownloadError(f"concurrent target has unexpected size: {target}")
        temporary.unlink(missing_ok=True)
        return
    try:
        temporary.rename(target)
    except (FileExistsError, PermissionError):
        if not target.is_file() or target.stat().st_size != expected_size:
            raise
        temporary.unlink(missing_ok=True)


def download_one(base_url: str, name: str, expected_size: int, source_dir: Path, dicom_dir: Path) -> dict:
    source_path = source_dir / name
    dicom_path = dicom_dir / name.removesuffix(".gz")
    if source_path.is_file() and source_path.stat().st_size != expected_size:
        raise DownloadError(f"existing compressed file has unexpected size: {source_path}")
    if not source_path.is_file():
        payload = fetch_bytes(urljoin(base_url, name))
        if len(payload) != expected_size:
            raise DownloadError(f"download size mismatch for {name}: {len(payload)} vs {expected_size}")
        temporary = source_path.with_name(
            f"{source_path.name}.part.{uuid.uuid4().hex}.{threading.get_ident()}"
        )
        temporary.write_bytes(payload)
        commit_download(temporary, source_path, expected_size)
    if not dicom_path.is_file():
        temporary = dicom_path.with_name(f"{dicom_path.name}.part.{uuid.uuid4().hex}")
        with gzip.open(source_path, "rb") as source, temporary.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        try:
            temporary.rename(dicom_path)
        except (FileExistsError, PermissionError):
            if not dicom_path.is_file():
                raise
            temporary.unlink(missing_ok=True)
    return {
        "source_name": name,
        "source_size_bytes": source_path.stat().st_size,
        "source_sha256": sha256_file(source_path),
        "dicom_name": dicom_path.name,
        "dicom_size_bytes": dicom_path.stat().st_size,
        "dicom_sha256": sha256_file(dicom_path),
    }


def clean_stale_parts(directory: Path, valid_names: set[str]) -> int:
    removed = 0
    for path in directory.glob("*.part*"):
        target_name = path.name.split(".part", 1)[0]
        target = directory / target_name
        if target_name in valid_names and target.is_file():
            path.unlink()
            removed += 1
    return removed


def download_series(key: str, case_root: Path, workers: int) -> dict:
    config = SERIES[key]
    index_url = urljoin(config["url"], "index.html")
    html = fetch_bytes(index_url).decode("utf-8", errors="replace")
    rows = parse_index(html, config["pattern"])
    if len(rows) != config["expected_count"]:
        raise DownloadError(f"{key}: expected {config['expected_count']} files, found {len(rows)}")
    source_dir = case_root / "source_gz" / key
    dicom_dir = case_root / config["destination"]
    source_dir.mkdir(parents=True, exist_ok=True)
    dicom_dir.mkdir(parents=True, exist_ok=True)
    clean_stale_parts(source_dir, {name for name, _ in rows})
    clean_stale_parts(dicom_dir, {name.removesuffix('.gz') for name, _ in rows})
    records = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(download_one, config["url"], name, size, source_dir, dicom_dir)
            for name, size in rows
        ]
        for future in as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda item: item["source_name"])
    return {
        "series": key,
        "official_base_url": config["url"],
        "index_url": index_url,
        "file_count": len(records),
        "compressed_bytes": sum(item["source_size_bytes"] for item in records),
        "dicom_bytes": sum(item["dicom_size_bytes"] for item in records),
        "source_dir": str(source_dir.relative_to(ROOT)),
        "dicom_dir": str(dicom_dir.relative_to(ROOT)),
        "files": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the public NLM Additional Head CT and T2 DICOM series.")
    parser.add_argument("--case-root", type=Path, default=ROOT / "data" / "raw_ct" / "public" / CASE_ID)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "nlm_additional_head_import_20260722")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 12:
        raise DownloadError("workers must be between 1 and 12")
    case_root = args.case_root.resolve()
    case_root.mkdir(parents=True, exist_ok=True)
    series = [download_series(key, case_root, args.workers) for key in ("ct", "t2")]
    manifest = {
        "manifest_version": "1.0.0",
        "case_id": CASE_ID,
        "source": "NLM Visible Human Project Additional Head Images",
        "source_page": "https://www.nlm.nih.gov/research/visible/visible_human.html",
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "subject_semantics": "72_year_old_male_formalin_preserved_donor",
        "license_note": "Publicly available NLM data; acknowledge NLM Visible Human Project.",
        "series": series,
        "pressure_executed": False,
        "clinical_safety_claim": False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "raw_data_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = {key: value for key, value in manifest.items() if key != "series"}
    summary["series"] = [{key: value for key, value in item.items() if key != "files"} for item in series]
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
