from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LIT = ROOT / "literature_tFUS_review"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: Path, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        raise ValueError(f"Missing replacement anchor in {path}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def insert_before(path: Path, marker: str, block: str, sentinel: str) -> None:
    text = read(path)
    if sentinel in text:
        return
    if marker not in text:
        raise ValueError(f"Missing insertion marker in {path}: {marker!r}")
    write(path, text.replace(marker, block.rstrip() + "\n\n" + marker, 1))


def update_docs() -> None:
    seed = LIT / "01_seed_papers_summary.md"
    replace_once(seed, "# 三篇本地论文主要内容与实验步骤", "# 四篇本地论文主要内容与实验步骤")
    insert_before(
        seed,
        "## 关联",
        """## 4. 韩珍珍 2015：经颅脑肿瘤 HIFU 治疗技术的研究现状

### 研究目标

该综述从热消融角度总结经颅脑肿瘤 HIFU 的相控阵设计、CT 个体建模、时间反转、幅值补偿、热点消除、声热仿真与临床验证问题。

### 对平台最关键的路线

1. 根据患者 CT 建立颅骨声学模型。
2. 通过相控阵和时间反转把焦点校正到目标结构。
3. 在目标点与颅骨热点分别建立传递向量，联合调整阵元幅相以压低二次峰。
4. 在声场通过后计算 Pennes 温度场与热剂量，并结合实验或 MR 温控验证。

### 关键结论与边界

- 该文直接支持当前双点热点约束 TR 方向。
- 文中 0.5-1.0 MHz、半球阵列和 650-800 W 均为历史综述或特定设备数据，不是当前个体推荐值。
- HIFU 热消融剂量不能与前三篇中的神经调控、BBB 或溶栓阈值混用。
- 详见 [[notes/28_Han2015_transcranial_brain_tumor_HIFU_review]] 与 [[17_四篇本地论文整合与个体化治疗规划路线]]。""",
        "## 4. 韩珍珍 2015",
    )

    index = LIT / "知识库总索引.md"
    replace_once(
        index,
        "- `notes/`：27 篇结构化论文笔记。",
        "- [[17_四篇本地论文整合与个体化治疗规划路线]]：四篇本地论文统一为患者特异性照射位置、幅相和剂量规划问题。\n"
        "- [[notes/28_Han2015_transcranial_brain_tumor_HIFU_review]]：参考的经颅脑肿瘤 HIFU 综述及项目映射。\n"
        "- `notes/`：28 篇结构化论文笔记。",
    )

    sound = LIT / "MOC_声场仿真与相位校正.md"
    replace_once(
        sound,
        "> 这是当前平台的主 MOC。Case 079 `(+5,0)` 厚颅骨标准运行已完成但聚焦失败：target-window 0.5957 MPa、global skull peak 9.6982 MPa、target/global 0.055。当前任务是 source-safe quick hotspot mitigation，详见 [[当前实验基线_Case079]] 和 [[实验平台阶段看板]]。",
        "> 这是当前平台的主 MOC。A5 held-out TR 已完成，3 条轨迹中 1 条通过；两条失败轨迹保留约 57 mm 远端颅骨热点。固定 Hamming 加窗使结果恶化，已停止扫窗；双点热点约束 TR 已完成实现与 dry-run，等待单次热点校准证据。详见 [[实验平台阶段看板]]。",
    )
    insert_before(
        sound,
        "## 外部论文",
        "- [[notes/28_Han2015_transcranial_brain_tumor_HIFU_review|韩珍珍 2015 - 经颅脑肿瘤 HIFU 综述]]",
        "韩珍珍 2015 - 经颅脑肿瘤 HIFU 综述",
    )
    replace_once(
        sound,
        "6. 声压场、焦点偏移、温升输出。",
        "6. 对目标与颅骨热点建立双点传递向量，联合优化阵元幅相和旁瓣。\n7. 声压场通过后，再按治疗机制输出焦点偏移、声强、温升或热剂量。",
    )

    params = LIT / "MOC_参数与指标.md"
    insert_before(
        params,
        "## 关联主题",
        """## HIFU 热消融专属参数

- [[notes/28_Han2015_transcranial_brain_tumor_HIFU_review|韩珍珍 2015]]：半球相控阵、目标/热点双点时间反转、Pennes 温度场和 MRI 温控的历史路线综述。
- HIFU 的设备声功率、持续时间、焦点温度、CEM43 和消融体积必须成套报告。
- 文献中的 650-800 W 是特定历史设备功率，不能换算为当前模型的 1 MPa 源归一化，也不能作为患者剂量建议。
- 热消融、神经调控、BBB 和溶栓必须使用不同的剂量目标与安全门。""",
        "## HIFU 热消融专属参数",
    )

    questions = LIT / "MOC_研究问题与争议.md"
    insert_before(
        questions,
        "- CT 个体化建模相对简化颅骨模型带来多少收益？",
        """- 单纯相位校正后仍存在远端颅骨热点时，目标/热点双点时间反转能否在保留 ROI 覆盖的同时稳定压低二次峰？
  - [[notes/28_Han2015_transcranial_brain_tumor_HIFU_review|韩珍珍 2015]] 回溯 Leduc 2012 的迭代热点消除路线；当前 fus-sim 已实现复数投影版本，但尚无热点校准压力证据。
- 如何从单体素焦点升级为解剖结构 ROI，并联合优化覆盖率、颅骨热点、非靶区暴露和剂量？""",
        "目标/热点双点时间反转能否",
    )

    synthesis = LIT / "04_theme_synthesis.md"
    replace_once(synthesis, "## 1. 三篇论文的共同问题", "## 1. 四篇论文的共同问题")
    replace_once(synthesis, "三篇中文论文看似应用不同，但核心技术链相同：", "四篇中文论文看似应用不同，但核心技术链相同：")
    insert_before(
        synthesis,
        "## 5. 推荐的复现优先级",
        """## 5. 脑肿瘤 HIFU 综述给出的路线

[[notes/28_Han2015_transcranial_brain_tumor_HIFU_review|韩珍珍 2015]] 将 CT 个体建模、相控阵、时间反转、幅值补偿、热点消除、Pennes 温度场和 MRI 温控串成完整治疗规划流程。其最直接的项目价值是为当前双点热点约束 TR 提供历史方法依据。

这篇文章是 2015 年叙述性综述，参数和临床状态必须与原始论文及近年证据交叉验证。统一路线见 [[17_四篇本地论文整合与个体化治疗规划路线]]。""",
        "## 5. 脑肿瘤 HIFU 综述给出的路线",
    )
    replace_once(synthesis, "## 5. 推荐的复现优先级", "## 6. 推荐的复现优先级")

    readme = LIT / "00_README.md"
    replace_once(readme, "围绕工作区中的三篇中文学位论文", "围绕四篇中文本地核心论文")
    replace_once(readme, "扩展为 27 篇（notes/01-27）", "扩展为 28 篇（notes/01-28）")
    insert_before(
        readme,
        "## 筛选标准",
        """4. `经颅脑肿瘤HIFU治疗技术的研究现状_韩珍珍.pdf`
   - 主线：脑肿瘤 HIFU 热消融、半球相控阵、CT 个体建模、时间反转、热点消除、Pennes 温度场与 MRI 温控。
   - 来源：参考的本地 PDF；原文件保留在 `<LOCAL_REFERENCE_DATA>\\科研项目\\`，知识库记录 SHA256，不复制或改写原文。""",
        "经颅脑肿瘤HIFU治疗技术的研究现状_韩珍珍.pdf",
    )
    replace_once(readme, "三篇本地论文的主要内容和实验步骤", "四篇本地论文的主要内容和实验步骤")
    replace_once(readme, "三篇本地论文的完整复刻蓝图", "四篇本地论文的统一规划与分路线复刻蓝图")

    ai_index = LIT / "AI_LITERATURE_INDEX.md"
    insert_before(
        ai_index,
        "## Paper Notes by Tag",
        "- [17_四篇本地论文整合与个体化治疗规划路线.md](17_四篇本地论文整合与个体化治疗规划路线.md) — Four local papers integrated into individualized planning",
        "Four local papers integrated into individualized planning",
    )
    note_line = "- [经颅脑肿瘤 HIFU 治疗技术的研究现状](notes/28_Han2015_transcranial_brain_tumor_HIFU_review.md)"
    text = read(ai_index)
    if text.count(note_line) < 2:
        anchor = "- [Experimental Validation of Skull Acoustic Modelling Strategies for Transcranial Focused Ultrasound Simulation: A Cross-Comparison Study](notes/27_Li2026_experimental_validation_of.md)"
        if text.count(anchor) < 2:
            raise ValueError("Expected two Li2026 note anchors in AI literature index")
        text = text.replace(anchor, anchor + "\n" + note_line)
        write(ai_index, text)

    board = LIT / "实验平台阶段看板.md"
    replace_once(
        board,
        "> 状态依据：`AI_PROJECT_SNAPSHOT.md`、`AI_TODO.md`、`NEXT_PHASE_EXECUTION_PLAN.md`，同步至 2026-07-10。",
        "> 状态依据：`AI_TODO.md`、`ACOUSTIC_NIGHT_SHIFT_HANDOFF_20260719.md` 和本轮文献整合，同步至 2026-07-20。",
    )
    insert_before(
        board,
        "## 阶段状态",
        """## 2026-07-20 文献整合后的当前状态

- A5 held-out TR：3 条轨迹中 1 条通过；两条失败轨迹的全局峰位于距目标约 57 mm 的颅骨。
- 固定 Hamming 加窗使 target/global 从 0.915 降至 0.554，已停止固定窗扫描。
- 双点热点约束 TR 已完成求解器、校准点解耦和严格 dry-run；尚未执行热点校准压力。
- 参考的韩珍珍 2015 综述及其 Leduc 2012 原始研究，为目标/热点双点时间反转提供直接方法依据。
- 项目主目标明确为：输入个体影像、目标脑结构和设备约束，输出照射位置、幅相、剂量范围、热点风险和不确定性。""",
        "## 2026-07-20 文献整合后的当前状态",
    )
    replace_once(
        board,
        "设计一个 **source-safe 的快速声学热点缓解候选**：先在 quick screening 中降低 skull-entry hotspot，同时观察有效焦点距离和靶区递送。只有候选可解释后，才申请 exactly-one 标准压力运行；通过声学门控后再考虑 Pennes。",
        "按新文献对齐的双点路线推进：由新 Evidence Brief 授权 exactly-one 热点校准，先离线计算目标保留与热点抑制；只有离线门通过，才考虑 exactly-one 约束 refocus。随后将点目标升级为解剖 ROI，并建立轨迹、幅相和剂量的个体化联合输出。",
    )


def update_parameter_matrices() -> None:
    fields = [
        "paper_id", "title", "year", "application", "parameter_name", "value", "unit_or_definition",
        "parameter_context", "evidence_level", "source_locator", "definition_status", "relevance_to_platform",
        "review_status", "notes",
    ]
    title = "经颅脑肿瘤HIFU治疗技术的研究现状"
    base = {
        "paper_id": "Han2015_local_review",
        "title": title,
        "year": "2015",
        "application": "transcranial_HIFU_ablation_review",
        "evidence_level": "综述转述/关键项已回溯原始论文",
        "definition_status": "historical_review_not_consensus",
        "relevance_to_platform": "individualized_planning_and_hotspot_control",
        "review_status": "usable_with_strict_boundary",
    }
    items = [
        ("frequency_range", "0.5-1.0", "MHz", "historical transcranial HIFU focusing range", "PDF p8; Fry 1978 cited", "范围参考，非个体最优频率"),
        ("exablate_frequency_options", "0.22/0.65", "MHz", "historical ExAblate 4000 options", "PDF p9", "设备历史参数"),
        ("hemispherical_aperture", "300", "mm", "historical large-aperture hemispherical arrays", "PDF p8-p9", "不可迁移到当前 D60 单碗"),
        ("exablate_element_count", "1024", "elements", "historical ExAblate 4000 hemispherical array", "PDF p9", "阵元数不等于 source-mask 网格点"),
        ("hotspot_to_main_peak_stop_ratio", "<=0.67", "pressure ratio", "iterative hot-spot elimination termination criterion", "PDF p11; Leduc 2012 DOI 10.1299/jbse.7.43", "探索性算法门，非安全阈值"),
        ("historical_patient_max_acoustic_power", "650-800", "W", "three-patient early brain-tumor study", "PDF p11; McDannold 2010 PMID 20087132", "不得换算为推荐剂量"),
        ("legacy_bone_sound_speed", "3200", "m/s", "old porosity-map endpoint", "PDF p10; Pernot 2001 cited", "历史映射端点，不作为默认"),
        ("target_skull_distance_hotspot_warning", "<30", "mm", "reviewed warning for skull heating near surface targets", "PDF p8", "需原始研究和现代模型复核"),
    ]
    new_rows = []
    for name, value, unit, context, source, notes in items:
        new_rows.append({**base, "parameter_name": name, "value": value, "unit_or_definition": unit,
                         "parameter_context": context, "source_locator": source, "notes": notes})

    for path in (ROOT / "paper_parameter_matrix.csv", LIT / "structured" / "paper_parameter_matrix.csv"):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows = [row for row in rows if row.get("paper_id") != "Han2015_local_review"] + new_rows
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    json_path = LIT / "structured" / "paper_parameter_matrix.json"
    data = json.loads(read(json_path))
    data = [item for item in data if item.get("paper_id") != "Han2015_local_review"]
    data.append({
        "paper_id": "Han2015_local_review",
        "title": title,
        "application": "transcranial_HIFU_ablation_review",
        "key_parameters": {
            "frequency_range_mhz": {"value": "0.5-1.0", "evidence_level": "综述转述", "definition": "historical focusing range, not an individualized optimum"},
            "exablate_configuration": {"value": "30 cm; 0.22/0.65 MHz; 1024 elements", "evidence_level": "综述明确", "definition": "historical device configuration"},
            "hotspot_to_main_peak_stop_ratio": {"value": "<=0.67", "evidence_level": "综述转述并回溯 Leduc 2012", "definition": "algorithmic stopping criterion, not a clinical safety threshold"},
            "historical_patient_power_w": {"value": "650-800", "evidence_level": "综述转述并回溯 McDannold 2010", "definition": "device acoustic power, not a recommended dose"},
        },
        "platform_role": "patient-specific CT, phased-array, dual-point TR, hotspot and thermal planning route",
        "do_not_mix_with": "neuromodulation, BBB or thrombolysis dose thresholds",
        "source_locator": "local PDF SHA256 5EC5F2A0A982DB7AA59806382374DF7AE7D60CD7684F5B244ADB7462FF87A618",
    })
    write(json_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    update_docs()
    update_parameter_matrices()
    print(json.dumps({"status": "ok", "paper_id": "Han2015_local_review", "notes": 28, "csv_rows_added": 8}))


if __name__ == "__main__":
    main()
