from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

SOURCES = {
    "PRESTUS": {
        "url": "https://github.com/Donders-Institute/PRESTUS/archive/refs/heads/main.zip",
        "output_dir": Path("data/source_code_refs/PRESTUS_source"),
    },
    "BabelBrain": {
        "url": "https://github.com/ProteusMRIgHIFU/BabelBrain/archive/refs/heads/main.zip",
        "output_dir": Path("data/source_code_refs/BabelBrain_source"),
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_replace_dir(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    src.rename(dst)


def download_and_extract(name: str, url: str, output_dir: Path, cache_dir: Path, timeout_s: int) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / f"{name}.zip"
    tmp_extract = cache_dir / f"{name}_extract"
    if tmp_extract.exists():
        shutil.rmtree(tmp_extract)
    result: dict[str, Any] = {
        "name": name,
        "url": url,
        "output_dir": rel(output_dir),
        "zip_path": rel(zip_path),
        "status": "not_started",
        "started_at": now_iso(),
    }
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_extract)
        children = [child for child in tmp_extract.iterdir() if child.is_dir()]
        if len(children) != 1:
            raise RuntimeError(f"Expected one top-level directory in {zip_path}, found {len(children)}")
        safe_replace_dir(children[0], output_dir)
        result.update(
            {
                "status": "downloaded",
                "finished_at": now_iso(),
                "file_count": sum(1 for item in output_dir.rglob("*") if item.is_file()),
                "dir_count": sum(1 for item in output_dir.rglob("*") if item.is_dir()),
            }
        )
    except Exception as exc:  # noqa: BLE001 - write failure to status file instead of retrying blindly.
        result.update({"status": "failed", "finished_at": now_iso(), "error": repr(exc)})
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download public source-code reference archives into the fus-sim workspace.")
    parser.add_argument("--output-summary", default="outputs/source_formula_extraction/source_download_summary.json")
    parser.add_argument("--cache-dir", default=".tmp/source-code-cache")
    parser.add_argument("--timeout-s", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cache_dir = ROOT / args.cache_dir
    results = []
    for name, info in SOURCES.items():
        results.append(
            download_and_extract(
                name=name,
                url=info["url"],
                output_dir=ROOT / info["output_dir"],
                cache_dir=cache_dir,
                timeout_s=args.timeout_s,
            )
        )
    summary = {
        "generated_at": now_iso(),
        "scope": "source-code archives only; no dependency install and no external code execution",
        "results": results,
    }
    write_json(ROOT / args.output_summary, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
