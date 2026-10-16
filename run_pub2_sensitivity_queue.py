"""Serial PUB.2 sensitivity queue orchestrator.

Runs the remaining one-variable sensitivity cells back-to-back, independent of
any interactive session, so an overnight batch survives disconnects. Each cell is
executed through ``run_pub2_sensitivity_cell.run`` (preflight + guarded monitor
+ artifact validation). The queue stops at the first non-completed cell.

Progress and per-cell results are written to ``queue_status.json``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import run_pub2_sensitivity_cell as cell_runner

ROOT = Path(__file__).resolve().parent
QUEUE_ROOT = ROOT / "outputs" / "pub2_sensitivity_queue_20260814"

# 顺序按验证合同优先级: 网格 → TR 时间步 → 域扩域。dx0p625 网格第二层暂不纳入(可选)。
QUEUE = [
    ("dx0p5_grid", "baseline"),
    ("dx0p5_grid", "tr"),
    ("dx0p75_cfl0p1", "tr"),
    ("dx0p75_domain_lat34_post20", "baseline"),
    ("dx0p75_domain_lat34_post20", "tr"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    QUEUE_ROOT.mkdir(parents=True, exist_ok=True)
    status_path = QUEUE_ROOT / "queue_status.json"
    log_path = QUEUE_ROOT / "queue.log"

    def log(message: str) -> None:
        line = f"[{utc_now()}] {message}"
        print(line, flush=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    log(f"队列启动，共 {len(QUEUE)} 单元: {QUEUE}")
    results = []
    for idx, (cell_id, method) in enumerate(QUEUE, 1):
        log(f"=== 单元 {idx}/{len(QUEUE)}: {cell_id} {method} ===")
        try:
            cell = cell_runner.cell_for(cell_id)
            result = cell_runner.run(cell, method)
        except Exception as exc:  # preflight 失败或任何运行时错误
            result = {"status": "error", "cell_id": cell_id, "method": method, "error": str(exc)}
            log(f"单元异常: {exc}")
        results.append(result)
        summary = {
            "status": "running",
            "at_utc": utc_now(),
            "queue": QUEUE,
            "current_index": idx,
            "results": results,
        }
        cell_runner.pair.atomic_json(status_path, summary)
        if result.get("status") != "completed":
            log(f"单元 {cell_id}/{method} 状态={result.get('status')}，停止队列。")
            break
        log(f"单元 {cell_id}/{method} 完成。")

    final_status = "completed" if results and all(r.get("status") == "completed" for r in results) else "stopped"
    cell_runner.pair.atomic_json(
        status_path,
        {"status": final_status, "finished_at_utc": utc_now(), "results": results},
    )
    log(f"队列结束: {final_status}")
    return 0 if final_status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
