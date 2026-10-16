from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ACTIVE_WORK_PATH = PROJECT_ROOT / "ACTIVE_WORK.md"
HANDOFF_LOG_PATH = PROJECT_ROOT / "HANDOFF_LOG.md"
RELAY_PROTOCOL_PATH = PROJECT_ROOT / "RELAY_PROTOCOL.md"
GIT_EXE = Path(r"D:\AIprogram\tools\Git\cmd\git.exe")

LOCKED_PATHS = [
    "outputs/ct_acoustic_model_3d/",
    "outputs/ct_transducer_stability_target_020/",
    "outputs/case_refinement_runs/079_candidate_006_offset_10_0/",
    "outputs/freefield_calibration/ap25_r30_f500/",
    "outputs/freefield_calibration/ap30_r35_f500/",
    "outputs/ct_acoustic_model_3d_profile_hu300/",
    "outputs/ct_acoustic_model_3d_profile_hu250/",
    "outputs/visible_human_quick_smoke_runs/visible_human_female_head_1mm_best_safe/",
    "outputs/visible_human_quick_smoke_runs/visible_human_female_head_1mm_candidate031_c6_t85/",
    "outputs/visible_human_quick_smoke_runs/visible_human_female_head_1mm_target037_s32_candidate005_c6_t65/",
    "outputs/visible_human_quick_smoke_runs/visible_human_female_head_1mm_target074_s40_t90/",
    "outputs/visible_human_quick_smoke_runs/visible_human_female_head_1mm_target040_s28_y0_z0_t65/",
]


def run_git_status() -> list[str]:
    """Get modified and untracked files in git."""
    try:
        res = subprocess.run(
            [str(GIT_EXE), "status", "--porcelain"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        files = []
        for line in res.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1].strip())
        return files
    except Exception:
        return []


def get_recent_outputs(hours: float) -> list[str]:
    """Scan outputs/ folder for files modified/created in the last N hours."""
    outputs_dir = PROJECT_ROOT / "outputs"
    if not outputs_dir.exists():
        return []

    now = datetime.datetime.now()
    threshold = datetime.timedelta(hours=hours)
    recent_files = []

    for root, _, files in os.walk(outputs_dir):
        for f in files:
            path = Path(root) / f
            try:
                mtime = datetime.datetime.fromtimestamp(path.stat().st_mtime)
                if now - mtime < threshold:
                    rel_path = path.relative_to(PROJECT_ROOT)
                    recent_files.append(rel_path.as_posix())
            except Exception:
                continue
    return sorted(recent_files)


def update_active_work_metadata(agent: str, status: str, date_str: str) -> None:
    """Updates metadata headers inside ACTIVE_WORK.md."""
    if not ACTIVE_WORK_PATH.exists():
        return
    content = ACTIVE_WORK_PATH.read_text(encoding="utf-8")

    # Replace metadata fields using regex
    content = re.sub(r"- active_agent:.*", f"- active_agent: `{agent}`", content)
    content = re.sub(r"- handoff_status:.*", f"- handoff_status: `{status}`", content)
    content = re.sub(r"- last_sync_date:.*", f"- last_sync_date: `{date_str}`", content)

    ACTIVE_WORK_PATH.write_text(content, encoding="utf-8")
    print(f"Updated ACTIVE_WORK.md metadata -> agent: {agent}, status: {status}")


def write_to_handoff_log(entry: str) -> None:
    """Appends a new entry to HANDOFF_LOG.md."""
    if not HANDOFF_LOG_PATH.exists():
        HANDOFF_LOG_PATH.write_text("# 接力日志\n\n> 追加式接力日志。每完成一个可验证步骤、发生偏差调节、或切换 Codex/Claude，都应新增记录。\n\n", encoding="utf-8")

    # Read existing content
    content = HANDOFF_LOG_PATH.read_text(encoding="utf-8").strip()

    # Append the new entry at the end, ensuring proper spacing
    new_content = content + "\n\n" + entry.strip() + "\n"
    HANDOFF_LOG_PATH.write_text(new_content, encoding="utf-8")
    print("Appended new entry to HANDOFF_LOG.md")


def handle_init(agent: str) -> None:
    """Renders the takeover/init recapitulation template for the agent."""
    print("=" * 60)
    print(f"【接手复述模板】请直接复制以下内容并在您的第一段回复中发送：")
    print("=" * 60)

    active_agent = "未知"
    last_sync = "未知"
    if ACTIVE_WORK_PATH.exists():
        txt = ACTIVE_WORK_PATH.read_text(encoding="utf-8")
        m_agent = re.search(r"- active_agent:\s*`([^`]+)`", txt)
        m_sync = re.search(r"- last_sync_date:\s*`([^`]+)`", txt)
        if m_agent:
            active_agent = m_agent.group(1)
        if m_sync:
            last_sync = m_sync.group(1)

    print(f"我读取到当前状态是：上一轮由 `{active_agent}` 完成，最后同步时间为 `{last_sync}`。")
    print(f"当前 active task 是：(请补充具体任务，如：配置 Gemini API 技能与本地接力工具)")
    print(f"上一个 agent 已完成：(请在此列出上一轮的完成点)")
    print(f"我本轮只会做：(列出本轮计划改动的文件/模块)")
    print(f"我不会动：(说明不会改动的部分，特别是 locked_paths 锁定的目录)")
    print(f"本轮验收标准：(说明本轮验证成功的判定条件)")
    print("=" * 60)


def handle_step(agent: str, message: str, hours: float, verify: str, next_step: str) -> None:
    """Creates a step log entry and updates state files."""
    now = datetime.datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M")
    date_str = now.strftime("%Y-%m-%d")

    modified_files = run_git_status()
    recent_outputs = get_recent_outputs(hours)

    log_lines = [
        f"## {time_str} {agent} Step",
        "",
        "完成内容：",
        f"- {message}",
        "",
        "修改文件："
    ]
    if modified_files:
        log_lines.extend([f"- [{os.path.basename(f)}](file:///{PROJECT_ROOT.as_posix()}/{f})" for f in modified_files])
    else:
        log_lines.append("- 无代码修改")

    log_lines.extend([
        "",
        "新增/更新输出："
    ])
    if recent_outputs:
        log_lines.extend([f"- [{os.path.basename(f)}](file:///{PROJECT_ROOT.as_posix()}/{f})" for f in recent_outputs])
    else:
        log_lines.append("- 无新输出生成")

    log_lines.extend([
        "",
        "验证结果：",
        f"- {verify if verify else '未指定详细验证信息，建议进行 py_compile 或脚本独立测试。'}",
        "",
        "下一步：",
        f"- {next_step if next_step else '待续。'}",
        "",
        "禁止覆盖："
    ])
    log_lines.extend([f"- `{p}`" for p in LOCKED_PATHS])

    entry = "\n".join(log_lines)
    write_to_handoff_log(entry)

    # Update active work
    update_active_work_metadata(agent, "in_progress", date_str)


def handle_exit(from_agent: str, to_agent: str, message: str, hours: float, next_step: str, warning: str) -> None:
    """Creates an exit snapshot log entry and hands over the active agent role."""
    now = datetime.datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M")
    date_str = now.strftime("%Y-%m-%d")

    modified_files = run_git_status()
    recent_outputs = get_recent_outputs(hours)

    log_lines = [
        f"## {time_str} {from_agent} -> {to_agent}",
        "",
        "当前目标：",
        f"- 完成阶段性收尾并移交给 `{to_agent}` 智能体。",
        "",
        "已完成：",
        f"- {message}",
        "",
        "改过的文件："
    ]
    if modified_files:
        log_lines.extend([f"- [{os.path.basename(f)}](file:///{PROJECT_ROOT.as_posix()}/{f})" for f in modified_files])
    else:
        log_lines.append("- 无代码修改")

    log_lines.extend([
        "",
        "新增输出："
    ])
    if recent_outputs:
        log_lines.extend([f"- [{os.path.basename(f)}](file:///{PROJECT_ROOT.as_posix()}/{f})" for f in recent_outputs])
    else:
        log_lines.append("- 无新输出生成")

    log_lines.extend([
        "",
        "正在运行：",
        "- 无正在运行的仿真任务或后台进程。",
        "",
        "失败和警告：",
        f"- {warning if warning else '无。'}",
        "",
        "下一步唯一建议：",
        f"- {next_step if next_step else '建议由接手 Agent 根据最新状态，制定细化的工程执行计划。'}",
        "",
        "禁止覆盖："
    ])
    log_lines.extend([f"- `{p}`" for p in LOCKED_PATHS])

    entry = "\n".join(log_lines)
    write_to_handoff_log(entry)

    # Handover metadata in ACTIVE_WORK.md
    update_active_work_metadata(to_agent, "review_completed_ready_for_next_task", date_str)


def main() -> None:
    parser = argparse.ArgumentParser(description="fus-sim Agent 接力状态自动维护与同步工具")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true", help="初始化接手：生成 Agent 接手复述模板")
    group.add_argument("--step", action="store_true", help="记录当前步骤：自动收集变更并更新状态文件")
    group.add_argument("--exit", action="store_true", help="退出移交：生成退出快照并交接执行权")

    parser.add_argument("--agent", default="Antigravity", help="当前运行的 Agent 名称 (默认: Antigravity)")
    parser.add_argument("--to", default="Codex", help="移交的目标 Agent 名称 (exit 模式下使用, 默认: Codex)")
    parser.add_argument("--message", default="", help="详细描述内容 (step 模式下的完成内容, 或 exit 模式下的已完成说明)")
    parser.add_argument("--output-hours", type=float, default=1.0, help="输出扫描时间窗口 (小时, 默认: 1.0)")
    parser.add_argument("--verify", default="", help="验证结果说明 (step 模式下使用)")
    parser.add_argument("--next-step", default="", help="下一步建议/建议下一步 (step/exit 模式下使用)")
    parser.add_argument("--warning", default="", help="警告或错误信息 (exit 模式下使用)")

    args = parser.parse_args()

    if args.init:
        handle_init(args.agent)
    elif args.step:
        if not args.message:
            parser.error("--message is required when using --step")
        handle_step(args.agent, args.message, args.output_hours, args.verify, args.next_step)
    elif args.exit:
        if not args.message:
            parser.error("--message is required when using --exit")
        handle_exit(args.agent, args.to, args.message, args.output_hours, args.next_step, args.warning)


if __name__ == "__main__":
    main()
