from __future__ import annotations

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
        raise ValueError(f"Missing replacement anchor in {path}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


def insert_before(path: Path, marker: str, block: str, sentinel: str) -> None:
    text = read(path)
    if sentinel in text:
        return
    if marker not in text:
        raise ValueError(f"Missing insertion marker in {path}: {marker!r}")
    write(path, text.replace(marker, block.rstrip() + "\n\n" + marker, 1))


def main() -> None:
    route = LIT / "17_四篇本地论文整合与个体化治疗规划路线.md"
    insert_before(
        route,
        "## 统一要解决的问题",
        """> [!important] 主要应用校正
> 项目的首要应用是聚焦超声联合微泡开放 BBB、促进药物进入目标脑区。HIFU 热消融综述主要提供经颅路径、相控校正和热点抑制方法，不是本项目的主要剂量机制。详细主线见 [[18_BBB个体化药物递送规划主线]]。""",
        "项目的首要应用是聚焦超声联合微泡开放 BBB",
    )
    replace_once(
        route,
        "3. 目标结构获得多大声压、声强或热剂量；",
        "3. 目标结构获得多大 in-situ PNP、MI 与声发射剂量，并使用什么脉冲和微泡协议；",
    )
    replace_once(
        route,
        "最终输出应是带约束、置信度和备选方案的个体化照射计划，而不是单一“最大靶点声压”。",
        "最终输出应是带约束、置信度和备选方案的 BBB 个体化照射计划，而不是单一“最大靶点声压”或固定功率。",
    )
    insert_before(
        route,
        "## 个体化规划的七层架构",
        """## 主应用与方法来源的关系

- 主应用：FUS + 微泡 BBB 开放和靶向药物递送。
- 主要机制论文：潘婷 2021 及 BBB/PCD 外部研究。
- 经颅声场方法：高鹏皓 2022、韩珍珍 2015、Leduc 2012，以及当前 TR 结果。
- 风险边界：孙天宇 2021 的高负压溶栓路线和韩珍珍 2015 的 HIFU 热消融功率不能进入 BBB 剂量推荐。

所谓最短路径应改为最小声学代价路径；需联合颅骨厚度/HU、入射角、衰减、热点、ROI 覆盖和不确定性。""",
        "## 主应用与方法来源的关系",
    )
    replace_once(
        route,
        "5. 将选中方案接入与治疗机制匹配的剂量模块；未过声场门的方案不进入热学。",
        "5. 建立 BBB 协议接口：in-situ PNP/MI、脉冲、微泡和 PCD/AE；未过声场门的方案不进入 BBB 剂量研究。",
    )
    replace_once(
        route,
        "现阶段可以声称平台正在实现患者特异性的声场与照射轨迹优化；不能声称已能推荐临床 HIFU 功率、完成脑肿瘤消融规划，或证明某一频率和剂量对不同患者最优。",
        "现阶段可以声称平台正在实现患者特异性的 BBB 声场、照射轨迹和热点约束；不能声称已找到临床最短安全路径、最佳 BBB 开放能量、药物递送量或患者治疗方案。",
    )
    insert_before(route, "## 证据入口", "- [[18_BBB个体化药物递送规划主线]]", "[[18_BBB个体化药物递送规划主线]]")

    bbb = LIT / "MOC_BBB微泡与空化监测.md"
    insert_before(
        bbb,
        "## 核心问题",
        """> [!important] 当前项目主应用
> BBB 开放与药物递送现为平台首要应用。当前声场 TR 和热点抑制工作是其上游基础；声场门未通过前不启动微泡剂量扫描。完整路线见 [[18_BBB个体化药物递送规划主线]]。""",
        "BBB 开放与药物递送现为平台首要应用",
    )
    replace_once(
        bbb,
        "- [[concepts/MI|MI]]：常用安全有效区间可先按 `0.3 <= MI <= 0.7` 建模。",
        "- [[concepts/MI|MI]]：潘婷论文的 `0.3 <= MI <= 0.7` 只能作为本地模型种子范围，不是跨微泡、设备、物种或患者通用的安全窗口。",
    )
    replace_once(
        bbb,
        "5. BBB 开放风险分区图。",
        "5. 患者 CT/MRI 上的声学代价路径排名和 ROI 覆盖。\n6. PCD/AE 闭环调节与宽带风险停止规则。\n7. MRI 对比增强开放体积与损伤指标验证。",
    )
    insert_before(
        bbb,
        "## 关联 MOC",
        """## 患者级闭环证据

- 972 次患者 sonication 的声发射剂量与 BBB 开放关联：<https://pubmed.ncbi.nlm.nih.gov/41395575/>。
- 9 名胶质母细胞瘤患者、38 次治疗的次谐波反馈控制：<https://pubmed.ncbi.nlm.nih.gov/38897294/>。
- 10 名胶质瘤患者的设备、耦合和治疗过程声学 QA：<https://pubmed.ncbi.nlm.nih.gov/38531173/>。""",
        "## 患者级闭环证据",
    )

    board = LIT / "实验平台阶段看板.md"
    replace_once(
        board,
        "- 项目主目标明确为：输入个体影像、目标脑结构和设备约束，输出照射位置、幅相、剂量范围、热点风险和不确定性。",
        "- 项目主应用明确为：输入个体 CT/MRI、BBB 药物递送 ROI、设备和微泡协议，输出最小声学代价路径、幅相、起始暴露范围、热点风险和不确定性；最终剂量依赖 PCD/AE 闭环与影像确认。",
    )
    replace_once(
        board,
        "| P4 个体化升级 | 解剖 ROI、物理阵元、多受试者、剂量与不确定性 | 未完成 | [[17_四篇本地论文整合与个体化治疗规划路线]] |",
        "| P4 BBB 个体化升级 | 解剖 ROI、物理阵元、声学路径、微泡/PCD、多受试者 | 未完成 | [[18_BBB个体化药物递送规划主线]] |",
    )
    replace_once(
        board,
        "按新文献对齐的双点路线推进：由新 Evidence Brief 授权 exactly-one 热点校准，先离线计算目标保留与热点抑制；只有离线门通过，才考虑 exactly-one 约束 refocus。随后将点目标升级为解剖 ROI，并建立轨迹、幅相和剂量的个体化联合输出。",
        "先完成双点热点声场门：新 Evidence Brief 授权 exactly-one 热点校准，离线计算目标保留与热点抑制，通过后才考虑一次约束 refocus。随后把点目标升级为 BBB 药物递送 ROI，并实现最小声学代价路径、物理阵元幅相和 PCD/AE 数据接口；当前不做患者剂量推荐。",
    )
    replace_once(
        board,
        "- 不优先扩展 BBB、溶栓、AI 替代模型或 FastSurfer 路线。",
        "- BBB 是主要应用，但在声场和热点门通过前不启动微泡/能量扫描；不优先扩展溶栓或无关 AI 路线。",
    )

    knowledge = LIT / "知识库总索引.md"
    insert_before(
        knowledge,
        "## 当前知识支持",
        "- [[18_BBB个体化药物递送规划主线]]：主要应用、最小声学代价路径、微泡/PCD 闭环和开发顺序。",
        "[[18_BBB个体化药物递送规划主线]]：主要应用",
    )

    ai_index = LIT / "AI_LITERATURE_INDEX.md"
    insert_before(
        ai_index,
        "## Paper Notes by Tag",
        "- [18_BBB个体化药物递送规划主线.md](18_BBB个体化药物递送规划主线.md) — Primary BBB drug-delivery planning route",
        "Primary BBB drug-delivery planning route",
    )

    note = LIT / "notes" / "28_Han2015_transcranial_brain_tumor_HIFU_review.md"
    insert_before(
        note,
        "## 一句话总结",
        """> [!note] 应用定位
> 本项目定位为微泡辅助 BBB 开放和药物递送。本文的 HIFU 热消融剂量不是平台主目标；其价值主要是经颅相控阵、CT 建模、时间反转和热点消除方法。""",
        "本项目定位为微泡辅助 BBB 开放",
    )

    todo = ROOT / "AI_TODO.md"
    text = read(todo)
    marker = "## 2026-07-20 BBB Drug-Delivery Application Anchor"
    if marker not in text:
        write(
            todo,
            text.rstrip()
            + "\n\n"
            + marker
            + "\n\n"
            + "- Primary application: patient-specific microbubble-assisted FUS BBB opening for targeted drug delivery.\n"
            + "- Path objective: minimum acoustic cost, not minimum Euclidean distance.\n"
            + "- Dose objective: in-situ PNP/MI, pulse and microbubble protocol plus PCD/AE closed-loop feedback; no fixed clinical power recommendation.\n"
            + "- Immediate dependency: finish dual-point acoustic hotspot control before BBB pressure or microbubble scans.\n"
            + "- Next implementation after the acoustic gate: anatomical ROI masks, physical array elements and path-ranking metrics.\n",
        )

    registry = ROOT / "generate_evidence_registry.py"
    text = read(registry)
    anchor = '        "dual_point_tr_validation": "outputs/dual_point_hotspot_constrained_tr_20260720/validation.json",'
    new_line = '        "bbb_personalized_route_brief": "outputs/evidence_briefs/bbb_personalized_drug_delivery_route/evidence_brief.json",'
    if new_line not in text:
        if anchor not in text:
            raise ValueError("Missing evidence registry dual-point anchor")
        write(registry, text.replace(anchor, anchor + "\n" + new_line, 1))

    print(json.dumps({"status": "ok", "primary_application": "FUS_BBB_drug_delivery", "path_metric": "minimum_acoustic_cost"}))


if __name__ == "__main__":
    main()
