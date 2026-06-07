from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

REPOS = {
    "PRESTUS": {
        "url": "https://github.com/Donders-Institute/PRESTUS",
        "paths": [
            Path("data/source_code_refs/PRESTUS_source"),
            Path("data/source_code_refs/PRESTUS"),
        ],
    },
    "BabelBrain": {
        "url": "https://github.com/ProteusMRIgHIFU/BabelBrain",
        "paths": [
            Path("data/source_code_refs/BabelBrain_source"),
            Path("data/source_code_refs/BabelBrain"),
        ],
    },
}

TEXT_SUFFIXES = {
    ".m",
    ".py",
    ".ipynb",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".txt",
    ".md",
    ".rst",
    ".csv",
    ".sh",
    ".ps1",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
}

SEARCH_PATTERNS = {
    "hu": re.compile(r"\bHU\b|hounsfield|hfield|ct\s*value|ctvalue", re.IGNORECASE),
    "ct": re.compile(r"\bCT\b|pseudo.?CT|pCT|ZTE|PETRA", re.IGNORECASE),
    "sound_speed": re.compile(r"sound\s*speed|soundspeed|speed\s*of\s*sound|\bc0?\b|SoS", re.IGNORECASE),
    "density": re.compile(r"density|\brho\b|mass\s*density", re.IGNORECASE),
    "attenuation": re.compile(r"attenuation|absorption|alpha|power.?law", re.IGNORECASE),
    "material": re.compile(r"material|medium|skull|bone|tissue|property|properties", re.IGNORECASE),
}

FORMULA_HINT = re.compile(
    r"=|polyfit|interp|interpol|clip|clamp|HUmax|HU_min|HUmax|slope|offset|linear|power|porosity|rho|alpha|c\s*\(",
    re.IGNORECASE,
)

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".github",
    "dist",
    "build",
    "docs/_build",
    "node_modules",
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


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8-sig")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        rows = [
            {
                "repo": "",
                "repo_url": "",
                "file": "",
                "line": "",
                "matched_terms": "",
                "classification": "",
                "snippet": "",
            }
        ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    return False


def iter_text_files(repo_path: Path, max_file_bytes: int) -> tuple[list[Path], list[dict[str, Any]]]:
    files: list[Path] = []
    skipped: list[dict[str, Any]] = []
    if not repo_path.exists():
        return files, skipped
    for path in repo_path.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        size = path.stat().st_size
        if size > max_file_bytes:
            skipped.append({"path": rel(path), "reason": "file_too_large", "size_bytes": size})
            continue
        files.append(path)
    return files, skipped


def classify_hit(matched: set[str], line: str) -> str:
    has_formula_domain = bool({"hu", "ct"} & matched) and bool({"sound_speed", "density", "attenuation", "material"} & matched)
    has_formula_hint = bool(FORMULA_HINT.search(line))
    if has_formula_domain and has_formula_hint:
        return "formula_candidate"
    if has_formula_domain:
        return "mapping_context"
    if bool({"hu", "ct"} & matched) or bool({"sound_speed", "density", "attenuation"} & matched):
        return "context_only"
    return "unrelated_or_low_priority"


def scan_file(repo: str, repo_url: str, path: Path, context_lines: int) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    hits: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        matched = {name for name, pattern in SEARCH_PATTERNS.items() if pattern.search(line)}
        if not matched:
            continue
        classification = classify_hit(matched, line)
        if classification == "unrelated_or_low_priority":
            continue
        start = max(1, idx - context_lines)
        end = min(len(lines), idx + context_lines)
        context = "\n".join(f"{line_no}: {lines[line_no - 1]}" for line_no in range(start, end + 1))
        hits.append(
            {
                "repo": repo,
                "repo_url": repo_url,
                "file": rel(path),
                "line": idx,
                "matched_terms": ",".join(sorted(matched)),
                "classification": classification,
                "snippet": line.strip()[:500],
                "context": context[:2000],
            }
        )
    return hits


def rank_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {"formula_candidate": 0, "mapping_context": 1, "context_only": 2}
    return sorted(hits, key=lambda row: (priority.get(row["classification"], 9), row["repo"], row["file"], int(row["line"])))


def make_report(summary: dict[str, Any], top_hits: list[dict[str, Any]]) -> str:
    hit_lines = []
    for hit in top_hits[:30]:
        hit_lines.append(
            f"- `{hit['classification']}` {hit['repo']} `{hit['file']}:{hit['line']}` "
            f"terms=`{hit['matched_terms']}`: {hit['snippet']}"
        )
    hit_text = "\n".join(hit_lines) if hit_lines else "- 未找到候选命中。"
    repo_lines = []
    for repo, info in summary["repositories"].items():
        repo_lines.append(
            f"- {repo}: exists={info['exists']}, files_scanned={info['files_scanned']}, "
            f"hits={info['hits']}, formula_candidates={info['formula_candidates']}"
        )
    return f"""# Source Code Formula Extraction Review

## 结论

本报告只定位源码证据，不验证公式，也不修改 fus-sim 参数。

当前扫描结论：

{chr(10).join(repo_lines)}

如果存在 `formula_candidate`，下一步仍需人工审查上下文、单位、调用路径和适用条件，不能直接写入 `continuous_skull` 默认 profile。

## 高优先命中

{hit_text}

## 解释边界

- 源码命中不是 validated formula。
- README/配置命中通常只是 context，需要追到实际函数调用。
- attenuation/absorption 命中必须额外审查单位和频率指数。
- 本轮没有运行 PRESTUS/BabelBrain，没有安装依赖，没有运行 k-Wave。

## 下一步

1. 人工阅读 `formula_candidate` 的上下文和调用链。
2. 将确认后的公式拆成 sound speed、density、attenuation、HU clamp 四类。
3. 做 model-build-only validation。
4. 仍不直接跑 pressure，除非 evidence brief 和 dry-run quality 都通过。
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan downloaded public source references for CT-HU acoustic mapping formula evidence.")
    parser.add_argument("--source-root", default="data/source_code_refs")
    parser.add_argument("--output-dir", default="outputs/source_formula_extraction")
    parser.add_argument("--max-file-mb", type=float, default=2.0)
    parser.add_argument("--context-lines", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    max_file_bytes = int(args.max_file_mb * 1024 * 1024)

    all_hits: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    repo_summary: dict[str, Any] = {}
    for repo, info in REPOS.items():
        path_candidates = [ROOT / item for item in info["paths"]]
        path = next((candidate for candidate in path_candidates if candidate.exists() and any(candidate.iterdir())), path_candidates[0])
        files, repo_skipped = iter_text_files(path, max_file_bytes)
        skipped.extend({"repo": repo, **item} for item in repo_skipped)
        repo_hits: list[dict[str, Any]] = []
        for file_path in files:
            repo_hits.extend(scan_file(repo, info["url"], file_path, args.context_lines))
        all_hits.extend(repo_hits)
        repo_summary[repo] = {
            "url": info["url"],
            "local_path": rel(path),
            "path_candidates": [rel(candidate) for candidate in path_candidates],
            "exists": path.exists(),
            "files_scanned": len(files),
            "hits": len(repo_hits),
            "formula_candidates": sum(1 for hit in repo_hits if hit["classification"] == "formula_candidate"),
            "skipped_files": len(repo_skipped),
        }

    ranked_hits = rank_hits(all_hits)
    summary = {
        "generated_at": now_iso(),
        "scope": "source text scan only; no dependency install, no external code execution, no k-Wave",
        "repositories": repo_summary,
        "total_hits": len(ranked_hits),
        "formula_candidates": sum(1 for hit in ranked_hits if hit["classification"] == "formula_candidate"),
        "classification_counts": {
            name: sum(1 for hit in ranked_hits if hit["classification"] == name)
            for name in ("formula_candidate", "mapping_context", "context_only")
        },
        "skipped_files": skipped,
        "top_hits": ranked_hits[:50],
    }

    write_csv(out_dir / "source_formula_hits.csv", ranked_hits)
    write_json(out_dir / "source_formula_hits.json", ranked_hits)
    write_json(out_dir / "source_formula_review.json", summary)
    write_md(out_dir / "source_formula_review.md", make_report(summary, ranked_hits))
    print(f"Wrote source formula extraction report to {rel(out_dir)}")


if __name__ == "__main__":
    main()
