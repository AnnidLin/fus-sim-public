from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ModuleSpec:
    module: str
    title: str
    goal: str
    paper_keywords: tuple[str, ...]
    tool_keywords: tuple[str, ...]
    consensus: tuple[str, ...]
    divergence: tuple[str, ...]
    platform_current_state: tuple[str, ...]
    platform_gaps: tuple[str, ...]
    recommended_decisions: tuple[str, ...]
    do_not_mix: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    risks: tuple[str, ...]
    next_steps: tuple[str, ...]


MODULES: dict[str, ModuleSpec] = {
    "freefield_calibration": ModuleSpec(
        module="freefield_calibration",
        title="自由场/水槽换能器校准",
        goal="先在均匀水/软组织介质中验证单阵元 bowl source 的几何焦点、焦域宽度和声压放大，再进入经颅 CT 仿真。",
        paper_keywords=("frequency", "pressure", "aperture", "radius", "transducer", "Gao", "500", "25", "30"),
        tool_keywords=("TUSX", "Kranion", "HAS", "water", "hydrophone", "transducer", "k-Wave", "bowl"),
        consensus=(
            "Gao2022 可作为当前单阵元 baseline：500 kHz、aperture 25 mm、curvature radius 30 mm、source pressure 1 MPa。",
            "公开工具侧可借鉴 TUSX 的水槽验证思路和 k-Wave 单阵元组织方式。",
            "自由场校准应输出 axial profile、lateral profile、focus coordinate、FWHM、focal region 和 peak/source ratio。",
        ),
        divergence=(
            "500 kHz 是 Gao baseline，不是 tFUS 领域唯一频率共识。",
            "1 MPa 是 source/excitation pressure，不能等同 free-field peak pressure 或经颅 in-situ pressure。",
            "ap30/r35 是 079 quick tuned 参数，不是文献共识，必须作为 current tuned 对照而非默认真值。",
        ),
        platform_current_state=(
            "已有 `generate_platform_parameter_profile.py` 和参数来源报告。",
            "已有 `simulate_freefield_transducer.py`，已跑通 ap25/r30/f500 与 ap30/r35/f500 的 quick water sanity check。",
            "已有 `outputs/freefield_calibration/freefield_calibration_report.md`，明确 source/free-field/in-situ pressure 边界。",
        ),
        platform_gaps=(
            "自由场结果仍是 quick grid sanity check，尚未做 standard/paper preset、PPW/PML/CFL 或网格收敛报告。",
            "尚未接入真实水听器测量数据，也没有与 MATLAB k-Wave 或公开工具逐点对照。",
            "尚未把 transducer geometry 写成可复用 profile 文件。",
        ),
        recommended_decisions=(
            "保留 ap25/r30/f500 为 Gao baseline transducer profile。",
            "保留 ap30/r35/f500 为 current 079 tuned transducer profile，但报告中必须标注 project_current。",
            "后续经颅声场仿真 summary 必须引用对应 free-field calibration 输出路径。",
        ),
        do_not_mix=(
            "不要把 Visible Human 或 079 经颅结果当作换能器模型本身的校准依据。",
            "不要把自由场峰值写成经颅目标区 in-situ pressure。",
            "不要把 BBB、微泡、Histotripsy 或热消融压力阈值混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "brief 明确引用 Gao baseline 参数和 TUSX/Kranion/HAS 等公开工具校准思路。",
            "自由场校准输出 axial/lateral profiles、FWHM、focus coordinate、focal-region peak 和 source pressure 边界说明。",
            "报告明确区分 quick screening、standard validation 和 paper-grade reproduction。",
        ),
        risks=(
            "global peak 可能贴近 source mask，应使用 focal-region/effective peak 指标辅助判断。",
            "如果有效焦点偏离几何焦点，优先检查 bowl 朝向、source mask、相位/延迟定义和网格分辨率。",
            "CPU k-Wave 运行时间可能增长；超过预算时应降级为 smoke calibration 并明确标注。",
        ),
        next_steps=(
            "把 transducer 参数 profile 化，供 CT quick/standard/paper preset 引用。",
            "为 `ct_hu_mapping` 生成 evidence brief，进入 CT-HU acoustic mapping profile 化。",
            "后续补充 PPW/PML/CFL 与网格收敛报告。",
        ),
    ),
    "ct_hu_mapping": ModuleSpec(
        module="ct_hu_mapping",
        title="CT-HU 到声学参数映射",
        goal="把当前硬编码 HU 阈值和材料参数改成可审阅、可复用、可对照的 acoustic mapping profiles，并引入连续非均匀颅骨声学参数建模能力。",
        paper_keywords=("HU", "density", "attenuation", "sound", "skull", "CT", "threshold", "Pan", "Sun"),
        tool_keywords=("PRESTUS", "BabelBrain", "RapidBeam", "skull", "CT", "mapping"),
        consensus=(
            "HU 阈值、声速、密度、衰减必须以 profile 形式记录来源并写入模型 summary 中。",
            "250/300/400 HU 阈值对照应可复现以评估分割敏感性。",
            "连续映射模型（如 PRESTUS, BabelBrain）利用孔隙率或线性插值方法来映射颅骨非均匀物理属性，典型范围为：密度在 1500 至 2200 kg/m3，声速在 2200 至 3200 m/s，衰减在 4.0 至 12.0 dB/MHz/cm。",
        ),
        divergence=(
            "二值 skull threshold 与连续 skull mapping 适用场景不同：二值模型（如 Gao2022_local）适合快速工程筛选；连续模型（如 PRESTUS）更逼近真实颅骨不均匀性。",
            "关于连续映射的具体公式存在不同流派：如 PRESTUS/Aubry 采用孔隙率线性模型（Porosity = 1 - HU/HU_max），而某些方案（如 RapidBeam/HAS）则采用与 HU 呈幂函数拟合的衰减系数公式。",
            "极限皮质骨参数 HU_max 的选择不一（如 2000, 2500 或 3000），这会直接影响孔隙率和声学参数的计算缩放。",
        ),
        platform_current_state=(
            "已有 `build_ct_acoustic_model.py`，支持基于二值阈值的模型重建。",
            "已有 079 的 250/300/400 HU 分割敏感性评估结果。",
        ),
        platform_gaps=(
            "缺少 `acoustic_mapping_profiles/continuous_skull.json` 文件来提供规范的连续属性参数。",
            "现有 `build_ct_acoustic_model.py` 仅支持二值阈值判断分配，缺乏处理 `continuous_skull` 的非均匀分配逻辑。",
            "模型 summary 中尚未统一记录 mapping profile 的详细信息和极值配置。",
        ),
        recommended_decisions=(
            "新增 production-ready 的 `continuous_skull.json` 映射 profile，定义 HU [300, 2000] 的连续范围。",
            "扩展 `build_ct_acoustic_model.py --mapping-profile`，支持 `continuous_skull` 的线性插值，对于水和软组织维持二值属性，仅对颅骨体素进行连续插值。",
            "运行 `generate_case_report.py` 对比已有数据以产生阶段总结报告。",
        ),
        do_not_mix=(
            "不要把 BBB 或热消融材料参数直接作为 neuromodulation baseline。",
            "在连续映射下，不要把代表皮质骨的极大参数直接赋给全部骨体素。",
        ),
        acceptance_criteria=(
            "每个 CT 模型 summary 完整记录 profile 名称、阈值、映射类型和材料参数来源。",
            "079 可用 continuous_skull profile 成功重建声学模型，且不覆盖已验证的二值 baseline 模型。",
        ),
        risks=(
            "阈值或非均匀插值可能微调有效声速，进而影响 entry path 上的声传播和相位分布。",
            "如果输入 NIfTI 的数值范围非标准 HU，需在 QC 阶段输出 warning 警示。",
        ),
        next_steps=(
            "实现 continuous_skull 配置文件并更新构建脚本中的映射解析代码。",
            "重新运行 079 模型构建以生成连续映射声学模型 npz。",
            "运行 generate_case_report.py 编译阶段总结报告。",
        ),
    ),
    "thermal_safety": ModuleSpec(
        module="thermal_safety",
        title="热安全与剂量模型",
        goal="把 Pennes、protocol-averaged、explicit pulse 和 dose scan 的热参数证据化。",
        paper_keywords=("thermal", "temperature", "duty", "PRF", "train", "CEM", "Pennes"),
        tool_keywords=("BabelBrain", "PRESTUS", "thermal", "heating"),
        consensus=("必须区分 explicit pulse、protocol-averaged 和 constant averaged。", "42 C 只是粗安全阈值，不能替代热剂量评价。"),
        divergence=("Gao protocol 不是通用 tFUS 协议。", "constant averaged 是保守上界，不是真实协议温升。"),
        platform_current_state=("已有 `simulate_pennes_bioheat.py`、敏感性扫描和 dose scan。",),
        platform_gaps=("缺少 thermal material profile JSON。", "缺少 CEM43 或更完整热剂量指标。"),
        recommended_decisions=("把 thermal material 和 pulse protocol profile 化。",),
        do_not_mix=("不要把热消融参数作为 neuromodulation 默认安全协议。",),
        acceptance_criteria=("每个热结果记录 pulse mode、材料参数、灌注参数和安全边界。",),
        risks=("平均热源模式容易被误读为真实持续刺激。",),
        next_steps=("生成 thermal_safety brief 后再扩展 CEM43/skull max 指标。",),
    ),
    "entry_planning": ModuleSpec(
        module="entry_planning",
        title="目标点与入射路径规划",
        goal="把当前 left_x entry scan 升级成可解释的 target/entry planning 层。",
        paper_keywords=("target", "entry", "skull", "planning", "hippocampus"),
        tool_keywords=("PlanTUS", "Kranion", "neuronavigation", "entry", "target"),
        consensus=("entry planning 应记录 source-target distance、skull path、incidence angle 和 source safety。",),
        divergence=("几何最优不一定声场最优，必须保留 k-Wave 验证层。",),
        platform_current_state=("已有 `plan_ct_target_entry.py`、`scan_ct_entry_positions.py` 和 source safety。",),
        platform_gaps=("方向仍主要是 left_x，缺少 avoidance proxy 和多方向规划。",),
        recommended_decisions=("先默认只生成 ranked candidates，不自动运行 k-Wave。",),
        do_not_mix=("不要把几何目标点写成真实解剖治疗靶点。",),
        acceptance_criteria=("每个病例能生成 source-safe top candidates 和可复制命令。",),
        risks=("自动目标点可能没有解剖意义。",),
        next_steps=("扩展多方向和 avoidance proxy。",),
    ),
    "kwave_simulation_quality": ModuleSpec(
        module="kwave_simulation_quality",
        title="k-Wave 仿真质量与 preset 分层",
        goal="建立 quick、standard、paper-grade 三层为主的 k-Wave 仿真质量标准，并把 smoke 仅作为脚本连通性检查。",
        paper_keywords=("k-Wave", "grid", "PML", "CFL", "PPW", "simulation"),
        tool_keywords=("TUSX", "PRESTUS", "k-Wave", "PML", "grid", "CFL", "validation"),
        consensus=(
            "k-Wave 结果必须报告 dx、grid size、time step、CFL、PML 设置、runtime 和 backend。",
            "500 kHz 下的 PPW 应由介质声速、频率和 dx 明确计算并写入 summary，而不是只写网格尺寸。",
            "quick 只能用于 screening、连通性验证和候选排序；standard/paper-grade 才能支撑更强结论。",
            "paper-grade 需要 PPW/PML/CFL、网格收敛、边界反射风险、运行环境和内存估计记录。",
        ),
        divergence=(
            "不同论文和公开工具对 grid spacing、PML 厚度、CFL 与运行后端的要求不同，不能用一个 quick 默认值覆盖全部场景。",
            "CPU quick cropped-domain 与论文级大域/高分辨率模型不是同一证据等级。",
            "自由场 sanity check、经颅 quick screening 和 CT 论文式复现应分开标注，不应互相替代。",
        ),
        platform_current_state=(
            "已有 2D/3D quick k-Wave、CT quick pressure、Visible Human smoke 和 free-field sanity check。",
            "已有焦域指标、axis profile、source safety 和 runtime summary 的部分字段。",
            "已有 evidence-driven 开发规则，要求先生成模块 brief 再实现仿真质量升级。",
        ),
        platform_gaps=(
            "缺少 `simulation_presets.json`，尚未把 smoke/quick/standard/paper-grade 的数值质量要求配置化。",
            "现有 k-Wave summary 尚未统一记录 PPW、PML、CFL、memory estimate、backend 和 preset id。",
            "缺少 standard preset 与 paper-grade preset 的验收门槛。",
            "缺少网格收敛报告和 PML/边界反射风险复核。",
            "缺少运行前 dry-run 质量估计，容易误启动超预算 3D 仿真。",
        ),
        recommended_decisions=(
            "新增 `simulation_presets.json`，至少包含 smoke、quick、standard、paper_grade 四个 profile。",
            "扩展 k-Wave 脚本 summary：记录 preset、dx、PPW、PML、CFL、grid size、nt/dt、runtime、backend、memory estimate 和 output completeness。",
            "默认继续使用 quick 进行候选筛选；standard/paper-grade 必须由用户明确选择。",
            "先实现 metadata 和 dry-run 质量检查，再考虑运行任何 standard k-Wave。",
        ),
        do_not_mix=(
            "不要用 smoke 或 quick cropped-domain 结果支撑 paper-grade reproduction。",
            "不要把自由场峰值、source pressure 和经颅 in-situ pressure 混写成同一压力指标。",
            "不要在 neuromodulation baseline 中混入 BBB、微泡、血栓、Histotripsy 或热消融参数。",
        ),
        acceptance_criteria=(
            "`kwave_simulation_quality` brief 明确 quick/standard/paper-grade 的证据等级。",
            "brief 明确 PPW、PML、CFL、grid convergence、runtime、backend 和 memory estimate 的记录要求。",
            "brief 给出下一步 `simulation_presets.json` 建议，且本阶段不运行 k-Wave。",
            "后续 k-Wave summary 必须能区分 screening 结果和 paper-grade 复现结果。",
        ),
        risks=(
            "standard/paper-grade 3D CPU 运行可能显著超时，必须先做 dry-run 估计和检查点。",
            "PPW 或 PML 设置不足会导致焦点、峰值和边界反射判断偏差。",
            "如果继续盲目调 target/entry 而不记录数值质量，容易把数值误差误读成物理现象。",
        ),
        next_steps=(
            "先实现 `simulation_presets.json` 和 summary 质量字段。",
            "扩展 `simulate_kwave_3d_focus.py` 与自由场脚本的 dry-run/summary metadata，不默认运行新仿真。",
            "随后选择一个小型 free-field standard sanity run 做 preset 验证，并生成 gap_feedback。",
        ),
    ),
    "multicase_pipeline": ModuleSpec(
        module="multicase_pipeline",
        title="多病例流程与报告",
        goal="让新增病例能按 manifest -> QC -> model -> plan -> smoke -> report 的流程复用。",
        paper_keywords=("case", "cohort", "CT", "dataset"),
        tool_keywords=("TFUScapes", "PRESTUS", "batch", "dataset"),
        consensus=("批量流程默认不跑 k-Wave，只生成计划。",),
        divergence=("公开测试数据不等同真实治疗病例。",),
        platform_current_state=("已有 inventory/QC/batch/smoke/refinement/report 骨架。",),
        platform_gaps=("缺少统一 case package。",),
        recommended_decisions=("每例输出 `case_manifest.json`、QC、model summary、entry plan、pressure metrics 和 case report。",),
        do_not_mix=("不要把 synthetic DICOM 当真实病例统计。",),
        acceptance_criteria=("新病例放入 data/raw_ct 后可完成 dry-run 计划。",),
        risks=("公开数据下载/格式/许可不稳定。",),
        next_steps=("生成统一 case package schema。",),
    ),
    "kwave_runner_health": ModuleSpec(
        module="kwave_runner_health",
        title="k-Wave 稳定运行封装与健康检查",
        goal="把容易出问题的 Windows 启动链路收敛成可检查、可记录、默认不执行的 k-Wave runner，以减少盲跑和后台启动不确定性。",
        paper_keywords=("k-Wave", "simulation", "runtime", "grid", "PML", "CFL"),
        tool_keywords=("TUSX", "PRESTUS", "k-Wave", "validation", "pipeline"),
        consensus=(
            "长耗时 k-Wave 运行必须先做 dry-run quality，记录 PPW、PML、CFL、grid size、nt/dt 和内存估计。",
            "运行器必须捕获 stdout、stderr、exit code、核心输出是否存在和 checkpoint 记录。",
            "runner/health-check 只解决运行可靠性，不提供新的物理精度证据。",
        ),
        divergence=(
            "Windows `Start-Process` 在当前机器上出现过 Path/PATH 环境键冲突，导致 k-Wave 未启动。",
            "PowerShell Job 可跑通但查询时出现 ScheduledJobs 权限 warning，不适合作为默认长期入口。",
            "前台直接运行更可诊断，但必须有硬停止、输出检查和日志记录。",
        ),
        platform_current_state=(
            "已有 `simulation_presets.json`、`simulation_quality.py` 和 `--dry-run-quality`。",
            "已有自由场 standard sanity run，证明 k-Wave 求解器能跑通。",
            "已有 `AGENTS.md` 负反馈规则和禁止盲跑 k-Wave 的约束。",
        ),
        platform_gaps=(
            "缺少统一 runner；目前命令运行方式依赖人工选择。",
            "缺少 health-check 汇总 Python、依赖、临时目录和进程状态。",
            "缺少默认不执行的 runner plan 和统一 stdout/stderr/status 输出。",
        ),
        recommended_decisions=(
            "新增 `kwave_run_healthcheck.py`，只检查环境和进程，不启动 k-Wave。",
            "新增 `run_kwave_command.py`，默认只生成 plan，显式 `--execute` 才真实运行。",
            "runner 只允许白名单脚本，并强制先生成 dry-run quality。",
            "runner 使用前台 `subprocess`，不使用 `Start-Process` 或 PowerShell Job。",
        ),
        do_not_mix=(
            "不要把 runner plan 或 health-check 结果写成物理仿真结论。",
            "不要绕过 dry-run quality 直接执行 standard/paper-grade k-Wave。",
            "不要用 runner 自动覆盖已有 pressure/freefield/thermal 输出。",
        ),
        acceptance_criteria=(
            "`kwave_runner_health` evidence brief 先生成。",
            "health-check 输出 JSON/Markdown，记录 Python、依赖、临时目录和进程 warning。",
            "runner 默认 `execute=false`，生成 plan 和 dry-run quality，不生成压力场。",
            "runner 真实执行必须显式 `--execute`，并记录 stdout/stderr/status/checkpoints。",
        ),
        risks=(
            "runner 若默认执行真实 k-Wave，会重新引入盲跑风险。",
            "错误的输出目录策略可能覆盖已验证结果。",
            "过度封装可能隐藏底层错误；因此 stdout/stderr/status 必须保留。",
        ),
        next_steps=(
            "先实现 health-check 和 runner plan，不执行新的 k-Wave。",
            "后续如果使用 runner 真实执行，必须单独设定时间预算和硬停止条件。",
        ),
    ),
    "freefield_grid_convergence": ModuleSpec(
        module="freefield_grid_convergence",
        title="自由场网格收敛与边界质量复核",
        goal="在继续经颅 CT 或 Visible Human 仿真前，先用均匀水介质自由场模型设计 PPW/PML/CFL 和网格收敛复核路线，只做 dry-run 风险估算，不盲目启动多组 k-Wave。",
        paper_keywords=("k-Wave", "grid", "PML", "CFL", "PPW", "frequency", "transducer", "Gao"),
        tool_keywords=("TUSX", "PRESTUS", "k-Wave", "water", "hydrophone", "validation", "grid", "PML"),
        consensus=(
            "自由场/水槽模型是检查单阵元 bowl source 几何焦点、焦域宽度和数值设置的低干扰入口。",
            "PPW 必须由最小声速、频率和 dx 计算；500 kHz 水介质下 dx 越小，PPW 越高但运行成本快速上升。",
            "standard sanity 只能说明 preset/summary/输出链路可用；paper-grade 前还需要至少一次 finer-grid 或 convergence sanity check。",
            "PML、CFL、grid size、nt/dt、runtime 和 memory estimate 必须和压力指标一起记录，避免把数值误差误读成物理现象。",
        ),
        divergence=(
            "不同公开工具和论文对 dx、PML 厚度、CFL 与运行后端的设置并不统一，不能把当前 dx=1.0 mm 直接写成领域共识。",
            "source/global peak 可能贴近源面，因此收敛比较必须优先看 focal-region/effective peak、焦点坐标和 FWHM，而不是只看 global peak。",
            "0.5 mm 等更细网格可能成本明显上升，应该先 dry-run 估算体素数、nt 和内存，再决定是否只跑一个候选。",
        ),
        platform_current_state=(
            "已有 `simulate_freefield_transducer.py`，支持 `--preset` 和 `--dry-run-quality`。",
            "已有 `simulation_presets.json` 和 `simulation_quality.py`，可计算 PPW、PML、CFL、grid size、nt/dt 和 memory estimate。",
            "已有 Gao baseline `ap25/r30/f500/source=1 MPa` 的 free-field standard sanity 输出，但仍不是 paper-grade。",
            "已有 `run_kwave_command.py`，后续真实运行应通过 runner 显式 `--execute`。",
        ),
        platform_gaps=(
            "尚未有自由场网格收敛计划表，无法解释下一次 finer-grid 应该选 0.75 mm 还是 0.5 mm。",
            "尚未有按 dx 汇总的 PPW/体素数/nt/内存/风险等级，用于控制后续运行预算。",
            "尚未把 standard sanity 的下一步写成最多一个候选的 runner 命令，容易重新滑向批量盲跑。",
        ),
        recommended_decisions=(
            "新增 free-field grid convergence dry-run 计划脚本，默认比较 dx=1.0,0.75,0.5 mm。",
            "本阶段只输出计划表和推荐下一次最多一个 finer-grid 候选，不运行 k-Wave。",
            "默认推荐 0.75 mm 作为下一次实跑候选，除非 dry-run 显示成本超预算；0.5 mm 先作为风险估算点。",
            "后续真实运行必须通过 `run_kwave_command.py --execute`，并设置 2 分钟检查点和硬停止时间。",
        ),
        do_not_mix=(
            "不要把网格收敛 dry-run 写成物理仿真结果。",
            "不要把自由场峰值写成经颅 in-situ pressure。",
            "不要在本模块中混入 BBB、微泡、血栓、Histotripsy 或热消融参数。",
        ),
        acceptance_criteria=(
            "生成 `freefield_grid_convergence` evidence brief，明确本阶段不运行 k-Wave。",
            "生成 grid convergence plan CSV/JSON，包含 dx、PPW、PML、CFL、grid size、nt/dt、voxel count、memory estimate 和 risk level。",
            "生成 `recommended_next_run.md`，明确下一步最多只跑一个 finer-grid 候选并必须使用 runner。",
            "不生成 `pressure_max_mpa.npz`，不覆盖既有 freefield/CT/Visible/Pennes 输出。",
        ),
        risks=(
            "更细 dx 会显著增加体素数和时间步数，CPU 运行可能超时。",
            "PML 过薄或 CFL 设置不当会影响焦点和边界反射判断。",
            "如果只看 global peak，可能把源面近场峰值误判为焦点收敛。",
        ),
        next_steps=(
            "先生成 evidence brief。",
            "再生成自由场网格收敛 dry-run 计划表。",
            "如果计划表显示 0.75 mm 成本可控，再单独请求执行一个 runner `--execute` finer-grid sanity run。",
        ),
    ),
    "freefield_pml_boundary_review": ModuleSpec(
        module="freefield_pml_boundary_review",
        title="自由场 PML 与边界风险复核",
        goal="在继续加密网格或回到经颅 CT 前，先用自由场模型 dry-run 评估 PML 厚度、计算域边界距离和运行成本，避免把边界反射或 PML 设置不足误读成换能器焦域变化。",
        paper_keywords=("k-Wave", "PML", "boundary", "grid", "CFL", "PPW", "simulation"),
        tool_keywords=("TUSX", "PRESTUS", "k-Wave", "PML", "boundary", "validation", "water"),
        consensus=(
            "k-Wave summary 必须记录 PML size、PML 物理厚度、grid size、CFL、PPW、nt/dt 和 runtime。",
            "PML/边界设置是 standard/paper-grade 前的必要数值质量检查，尤其在焦点和峰值变化不大但运行成本升高时。",
            "边界复核应先用自由场均匀介质做低干扰 dry-run，再决定是否运行单个真实候选。",
        ),
        divergence=(
            "不同工具和论文对 PML 厚度、是否吸收到网格内、以及边界距离的选择不同，不能把当前 pml=8 直接当作充分。",
            "增加 PML 会改变网格尺寸和运行时间；它是数值质量检查，不是物理换能器调参。",
            "只比较压力峰值不足以证明 PML 充分，还需要检查焦点位置、FWHM、边界附近能量或至少输出边界风险说明。",
        ),
        platform_current_state=(
            "已有 `dx=1.0 mm` free-field standard sanity。",
            "已有 `dx=0.75 mm` free-field finer-grid sanity，PPW 约 3.95，焦点位置相对稳定。",
            "已有 `simulation_quality.py` 和 `plan_freefield_grid_convergence.py` 可估算 PML、grid、nt 和 memory。",
            "已有 `run_kwave_command.py`，后续真实运行必须显式 `--execute`。",
        ),
        platform_gaps=(
            "尚未有 PML size 扫描计划表，无法解释 pml=8 是否足够。",
            "现有 summary 记录 PML 字段，但缺少边界距离/风险等级的独立复核报告。",
            "尚未定义下一次如需运行时应该选择哪个 PML 候选以及为什么。",
        ),
        recommended_decisions=(
            "新增 PML/边界 dry-run 计划脚本，默认固定 `dx=0.75 mm`，比较 `pml=8,12,16`。",
            "本阶段只输出计划表、推荐候选和 runner 命令模板，不运行 k-Wave。",
            "优先推荐中等成本的 `pml=12` 作为下一次最多单跑候选，除非 dry-run 显示成本或边界风险不合适。",
            "真实运行前必须先确认不覆盖已有 `dx=0.75 mm` 输出，并通过 runner 执行。",
        ),
        do_not_mix=(
            "不要把 PML dry-run 写成物理声场结论。",
            "不要把 PML 设置变化当作换能器 aperture/radius 调参。",
            "不要在本模块中混入 BBB、微泡、血栓、Histotripsy 或热消融参数。",
        ),
        acceptance_criteria=(
            "生成 `freefield_pml_boundary_review` evidence brief，明确本阶段不运行 k-Wave。",
            "生成 PML review plan CSV/JSON，包含 PML size、PML 厚度、grid size、nt/dt、PPW、memory、relative work 和 risk level。",
            "生成推荐下一步文档，明确最多只跑一个 PML 候选并必须使用 runner。",
            "不生成 `pressure_max_mpa.npz`，不覆盖既有 freefield/CT/Visible/Pennes 输出。",
        ),
        risks=(
            "PML 增大可能增加运行时间，但 dry-run 工作量估计可能低估真实 runtime。",
            "只做 dry-run 不能证明边界反射被消除；它只能筛选下一次复核候选。",
            "若后续真实运行 PML 候选，应把 runtime 偏差写入 gap_feedback。",
        ),
        next_steps=(
            "先生成 PML evidence brief。",
            "再生成自由场 PML/边界 dry-run 计划表。",
            "如果需要真实验证，最多运行一个 `dx=0.75 mm, pml=12` 或计划推荐的候选。",
        ),
    ),
    "ct_standard_review": ModuleSpec(
        module="ct_standard_review",
        title="079 CT 经颅 standard-review 计划",
        goal="在自由场质量阶段收口后，把 079 当前 best 经颅配置整理成可审阅、可 dry-run、可通过 runner 单次执行的 standard-review 包，而不是继续盲调 target/entry 或 Visible Human。",
        paper_keywords=("CT", "skull", "k-Wave", "frequency", "pressure", "Gao", "PML", "PPW"),
        tool_keywords=("PRESTUS", "TUSX", "PlanTUS", "Kranion", "k-Wave", "pipeline", "planning"),
        consensus=(
            "经颅 CT 复核必须引用 CT-HU mapping、target/entry/source safety、free-field calibration 和 simulation_quality。",
            "source pressure、free-field pressure 和 transcranial in-situ pressure 必须分开报告。",
            "standard-review 可以作为工程复核层，但不能写成 paper-grade reproduction。",
        ),
        divergence=(
            "当前 079 target_020 是几何/工程候选，不是真实解剖治疗靶点。",
            "当前 ap30/r35 是 project tuned 参数，不是 Gao baseline 或文献共识。",
            "quick crop 与论文级全域/高分辨率 CT 模型不是同一证据等级。",
        ),
        platform_current_state=(
            "已有 079 tuned best：target_020、entry offset=(10,0)、standoff=16 mm、ap30/r35、cycles=8、sim-time=55 us。",
            "已有自由场质量报告，说明 free-field 阶段可暂时收口。",
            "已有 runner、simulation presets、dry-run quality 和 CT entry plan。",
        ),
        platform_gaps=(
            "079 tuned best 的历史 summary 缺少后续新增的 `simulation_quality` 字段。",
            "尚未有一个单独的 CT standard-review 计划包，把 free-field reference、mapping、entry/source safety 和 runner 命令汇总起来。",
            "尚未明确下一次 CT 复核是否只跑一个 standard candidate，以及输出目录如何避免覆盖旧结果。",
        ),
        recommended_decisions=(
            "先生成 CT standard-review plan，不运行 k-Wave。",
            "plan 内部先调用 `simulate_kwave_3d_focus.py --dry-run-quality --preset standard`，只生成质量 metadata。",
            "推荐下一次最多运行一个 079 candidate_006 standard-review，并通过 `run_kwave_command.py --execute`。",
            "保留 old tuned best 作为 reference，不覆盖 `outputs/case_refinement_runs/079_candidate_006_offset_10_0/`。",
        ),
        do_not_mix=(
            "不要把 079 quick/tuned result 写成论文级复现。",
            "不要把 free-field peak 写成经颅 target in-situ pressure。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 `ct_standard_review` evidence brief。",
            "生成 079 CT standard-review plan JSON/Markdown 和 dry-run quality summary。",
            "plan 明确引用自由场质量报告和 079 tuned best 指标。",
            "不运行 k-Wave，不生成新的 `pressure_max_mpa.npz`，不覆盖旧 CT/freefield/Visible/Pennes 输出。",
        ),
        risks=(
            "CT standard-review 即便执行也可能耗时显著，必须通过 runner 和硬停止条件。",
            "历史 tuned best 与新 dry-run metadata 的 summary schema 不完全一致，需要报告中明确这是计划层。",
            "如果回到 CT 后继续扩大参数搜索，会拖慢主线；应先只复核一个 best candidate。",
        ),
        next_steps=(
            "先生成 evidence brief。",
            "再生成 079 CT standard-review plan 和 dry-run quality summary。",
            "如果用户确认，再单独执行一个 CT standard-review run。",
        ),
    ),
    "kwave_alpha_power_interface_audit": ModuleSpec(
        module="kwave_alpha_power_interface_audit",
        title="k-Wave alpha_power 接口与衰减语义审计",
        goal="在允许 source-backed continuous CT-HU mapping 进入压力仿真前，先审计本平台如何把 alpha_coeff、alpha_power 和 alpha_mode 传入 k-wave-python，并确认 draft profile 的衰减语义是否仍有接口风险。",
        paper_keywords=("attenuation", "alpha", "skull", "CT", "HU", "k-Wave", "absorption"),
        tool_keywords=("k-Wave", "PRESTUS", "BabelBrain", "alpha_coeff", "alpha_power", "attenuation", "skull"),
        consensus=(
            "k-Wave 风格的 power-law absorption 需要同时定义 alpha_coeff 和 alpha_power。",
            "alpha_coeff 的语义必须与 alpha_power 配套，不能只比较数值大小。",
            "source-backed mapping profile 进入压力仿真前，应先证明模型文件、仿真脚本和 solver 接口使用的是同一套衰减语义。",
        ),
        divergence=(
            "不同工具对 skull attenuation 的经验公式、HU clamp 范围、参考频率和输出单位不完全一致。",
            "PRESTUS Mueller 路线把 500 kHz 下的衰减换算成 alpha0；这与直接写入 alpha(f) 不是同一概念。",
            "alpha_power=1 在部分 k-Wave power-law dispersion 路径中有特殊限制，可能需要 no_dispersion 或 solver 侧确认。",
        ),
        platform_current_state=(
            "已有 alpha unit audit，结论是 prestus_marsac_mueller_draft 不应直接跑压力。",
            "已有 alpha_semantics metadata 写入 profile、summary 和 NPZ。",
            "已有 simulate_kwave_3d_focus.py 和 simulate_freefield_transducer.py，但需要审计它们是否完整传递 alpha_power。",
        ),
        platform_gaps=(
            "尚未形成 kWaveMedium 接口审计报告。",
            "尚未确认 k-wave-python 0.6.1 对 alpha_coeff 单位、alpha_power 和 alpha_mode 的实际代码路径。",
            "尚未定义 draft profile 从 model-build-only 升级到 pressure-eligible 前的补丁门槛。",
        ),
        recommended_decisions=(
            "本轮只做只读接口审计，不运行 k-Wave。",
            "若发现脚本已经传递 alpha_power，也仍需记录 alpha_mode / dispersion 风险。",
            "在补齐接口审计和必要补丁前，prestus_marsac_mueller_draft 保持 review_pending，不作为默认压力 profile。",
        ),
        do_not_mix=(
            "不要把 source-backed draft profile 的 model-build 成功写成压力仿真已验证。",
            "不要把 alpha_at_500kHz 直接当成 alpha0，除非 profile 明确记录换算公式和 alpha_power。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融方向的高强度参数混入当前神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 kwave_alpha_power_interface_audit evidence brief。",
            "生成只读接口审计报告，覆盖本平台脚本、mapping profile 和 k-wave-python 关键源码路径。",
            "报告明确是否需要 patch，以及 patch 前是否允许 draft profile 进入压力仿真。",
            "不运行 k-Wave，不生成 pressure_max_mpa.npz 或 acoustic_model_3d.npz。",
        ),
        risks=(
            "只看注释不看 solver 路径会漏掉 alpha_power 默认值和 alpha_mode 分支。",
            "alpha_power=1 可能触发 dispersion 相关限制，不能只凭单位匹配就放行。",
            "已有 exploratory outputs 容易被误读为 validated evidence，需要保持状态标签。",
        ),
        next_steps=(
            "生成 evidence brief。",
            "审计 simulate_kwave_3d_focus.py、simulate_freefield_transducer.py、kmedium.py 和 solver absorption 代码。",
            "如果需要，下一轮再做最小补丁计划；本轮不跑压力仿真。",
        ),
    ),
    "alpha_semantics_propagation": ModuleSpec(
        module="alpha_semantics_propagation",
        title="alpha 语义字段传播与 dry-run 护栏",
        goal="把 alpha_power 之外的 alpha semantics 字段从 mapping profile/NPZ 传递到 k-Wave dry-run 和 summary，使 draft profile 在进入压力仿真前能被明确标记为 review pending。",
        paper_keywords=("attenuation", "alpha", "skull", "CT", "HU", "k-Wave", "absorption"),
        tool_keywords=("k-Wave", "PRESTUS", "BabelBrain", "alpha_coeff", "alpha_power", "alpha_mode", "attenuation"),
        consensus=(
            "alpha_coeff、alpha_power、alpha_mode 和 alpha_coeff_kind 应作为一组语义字段审计。",
            "执行前 evidence brief 与执行后 gap feedback 必须分离。",
            "review-pending mapping profile 不能因字段链路补齐就自动升级为 pressure-eligible。",
        ),
        divergence=(
            "alpha_mode 是否设置为 no_dispersion 需要 solver 和物理证据，不应由本轮自动决定。",
            "不同工具的 attenuation route 可能输出 alpha(f)、alpha0 或 Np/m，必须显式记录。",
            "legacy/simple profiles 缺少完整 alpha semantics，只能保留 backward-compatible fallback。",
        ),
        platform_current_state=(
            "已有 alpha_power 接口审计，确认 3D 脚本能传递 alpha_power。",
            "已有 `prestus_marsac_mueller_draft` profile 和 model-build-only validation。",
            "已有 dry-run quality 机制，但尚未完整记录 alpha_mode、alpha_coeff_kind 和 review status。",
        ),
        platform_gaps=(
            "NPZ 尚未保存 alpha_mode 字段。",
            "simulate_kwave_3d_focus.py 的 dry-run/model summary 尚未完整显示 alpha semantics。",
            "还缺少明确的 pressure_allowed 标记，容易误跑 review-pending profile。",
        ),
        recommended_decisions=(
            "本轮只传播 metadata，不运行 k-Wave。",
            "默认不设置 alpha_mode；如需 no_dispersion，必须后续单独 evidence review。",
            "dry-run summary 应明确 `pressure_allowed_by_alpha_semantics=false` for review-pending profiles。",
        ),
        do_not_mix=(
            "不要把 alpha semantics metadata 补齐写成 pressure validation。",
            "不要自动把 alpha_power=1 的 profile 设置为 no_dispersion。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 `alpha_semantics_propagation` evidence brief。",
            "profile/NPZ/dry-run summary 能记录 alpha_mode、alpha_coeff_kind、alpha_semantics_status。",
            "dry-run 不生成压力场，并明确 review-pending profile 不允许 pressure。",
            "不覆盖既有 best pressure/thermal 输出。",
        ),
        risks=(
            "自动设置 alpha_mode 可能改变物理路径，必须避免。",
            "legacy profile 可能没有 alpha semantics，应保留兼容 fallback。",
            "如果字段名不一致，后续 runner/summary 会失去追踪能力。",
        ),
        next_steps=(
            "补 profile/NPZ 字段。",
            "补 simulate_kwave_3d_focus.py 的 load/model/dry-run/summary 字段。",
            "生成 dry-run 验证，不跑 k-Wave。",
        ),
    ),
    "alpha_mode_policy_review": ModuleSpec(
        module="alpha_mode_policy_review",
        title="alpha_mode / no_dispersion 策略审查",
        goal="在 source-backed draft mapping 进入压力仿真前，审查 alpha_power=1.0 时是否应设置 alpha_mode=no_dispersion，或改走固定 alpha_power 拟合路线，并形成不自动放行 pressure 的工程策略。",
        paper_keywords=("attenuation", "alpha", "dispersion", "skull", "k-Wave", "CT", "HU"),
        tool_keywords=("k-Wave", "PRESTUS", "BabelBrain", "alpha_power", "alpha_mode", "no_dispersion", "fit_alpha_power"),
        consensus=(
            "k-Wave power-law absorption 需要 alpha_coeff 与 alpha_power 配套。",
            "alpha_power=1.0 在 k-Wave power-law dispersion 中是特殊情形，必须显式处理。",
            "是否忽略 dispersion 是物理/数值决策，不能由工程脚本自动替用户决定。",
        ),
        divergence=(
            "k-wave-python 提供 `alpha_mode=no_dispersion` 作为 alpha_power=1 的规避路径。",
            "PRESTUS 源码存在 `fit_alpha_power` 路线，默认将多组织 alpha 拟合到固定 alpha_power=2，而不是简单设置 no_dispersion。",
            "BabelBrain 出现 dispersion correction 相关代码，但它不是直接等价于 kWaveMedium.alpha_mode。",
        ),
        platform_current_state=(
            "已有 `prestus_marsac_mueller_draft`，其 alpha_power=1.0 且 alpha_mode=null。",
            "已有 alpha semantics dry-run，明确 `pressure_allowed_by_alpha_semantics=false`。",
            "已有 k-wave-python 本地源码和 PRESTUS/BabelBrain source snapshots。",
        ),
        platform_gaps=(
            "尚未形成 alpha_mode/no_dispersion 的策略报告。",
            "尚未决定 draft profile 的下一条可验证路线：no_dispersion pressure sanity，或 alpha_power=2 fitted model-build route。",
            "尚未把该策略写成 profile review gate。",
        ),
        recommended_decisions=(
            "本轮只做只读策略审查，不修改 profile 为 no_dispersion。",
            "默认保持 draft profile blocked for pressure。",
            "若后续要跑 pressure，应优先新建显式 experimental profile，而不是修改原 draft profile。",
        ),
        do_not_mix=(
            "不要把 `alpha_mode=no_dispersion` 当作默认物理真值。",
            "不要把 PRESTUS `fit_alpha_power` 与 k-wave-python `alpha_mode` 混写成同一个机制。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 `alpha_mode_policy_review` evidence brief。",
            "生成策略报告，列出 no_dispersion 路线、alpha_power=2 fitted 路线和继续 blocked 路线。",
            "报告必须明确本轮不运行 k-Wave、不修改压力结果、不升级 draft profile。",
            "给出下一步最多一个安全工程动作。",
        ),
        risks=(
            "把 solver workaround 写成文献共识会误导后续报告。",
            "直接改现有 draft profile 会破坏已生成 validation 的可追溯性。",
            "若忽略 PRESTUS fit_alpha_power 路线，可能错过更稳的 source-backed 策略。",
        ),
        next_steps=(
            "审计 kmedium.py、PRESTUS medium_setup.m 和 doc_pseudoCT.md。",
            "生成 policy review 报告。",
            "如果继续实现，优先新建 experimental profile 或 plan，不覆盖现有 draft。",
        ),
    ),
    "source_backed_alpha_profile_options": ModuleSpec(
        module="source_backed_alpha_profile_options",
        title="source-backed alpha profile 方案对照",
        goal="在不运行 k-Wave、不重建 CT 的前提下，把 no_dispersion 实验路线和 PRESTUS fit_alpha_power=2 路线整理成可审阅的 profile 草案与 dry-run-only 执行计划。",
        paper_keywords=("attenuation", "alpha", "dispersion", "skull", "k-Wave", "CT", "HU"),
        tool_keywords=("PRESTUS", "k-Wave", "alpha_power", "alpha_mode", "no_dispersion", "fitPowerLawParamsMulti"),
        consensus=(
            "review-pending profile 不能直接进入 pressure simulation。",
            "alpha_mode/no_dispersion 和 alpha_power fitting 是不同工程路线，必须分开记录。",
            "任何实验 profile 都必须与 baseline/simple profile 分离，避免覆盖可复现结果。",
        ),
        divergence=(
            "no_dispersion 路线是 k-wave-python 的接口规避选择，但不是文献共识。",
            "fit_alpha_power=2 路线更接近 PRESTUS source，但需要实现拟合公式，不能只改 alpha_power 数值。",
            "两条路线的物理解释和数值风险不同，不应混成一个 profile。",
        ),
        platform_current_state=(
            "已有 `prestus_marsac_mueller_draft`，仍 blocked for pressure。",
            "已有 alpha_mode policy review，推荐 keep_blocked。",
            "已有 build/dry-run metadata 机制，可用于未来 model-build-only 验证。",
        ),
        platform_gaps=(
            "尚未有两个候选路线的 profile 草案。",
            "尚未有对应 dry-run/model-build-only 命令计划。",
            "尚未明确哪个路线可先实现，哪个需要公式移植。",
        ),
        recommended_decisions=(
            "本轮只生成草案和计划，不把草案放进默认 acoustic_mapping_profiles。",
            "no_dispersion 草案标记为 experimental_dry_run_only。",
            "fit_alpha_power=2 草案标记为 plan_only，直到移植/验证 fitPowerLawParamsMulti。",
        ),
        do_not_mix=(
            "不要覆盖 `prestus_marsac_mueller_draft.json`。",
            "不要把 plan-only profile 交给 build 脚本执行。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 `source_backed_alpha_profile_options` evidence brief。",
            "输出两个候选 profile 草案和中文对照报告。",
            "报告明确没有运行 k-Wave、没有重建 CT、没有放行 pressure。",
            "给出下一步最多一个可执行的 model-build-only 方向。",
        ),
        risks=(
            "草案如果放到主 profile 目录，可能被后续误用为默认 profile。",
            "fit_alpha_power=2 如果只改字段不重拟合 alpha0，会产生错误模型。",
            "no_dispersion 如果未充分标注，会被误读成物理验证路线。",
        ),
        next_steps=(
            "生成 profile 草案与计划。",
            "如果继续，优先实现一个 build-only no_dispersion experimental profile 或 fit_alpha_power formula migration。",
            "任何 pressure run 都必须单独授权。",
        ),
    ),
    "no_dispersion_model_build_validation": ModuleSpec(
        module="no_dispersion_model_build_validation",
        title="no-dispersion 草案模型构建验证",
        goal="对 source-backed no-dispersion 实验草案做 isolated model-build-only validation，验证 profile/summary/NPZ alpha metadata 是否完整，并确认仍不允许 pressure simulation。",
        paper_keywords=("attenuation", "alpha", "dispersion", "skull", "k-Wave", "CT", "HU"),
        tool_keywords=("PRESTUS", "k-Wave", "alpha_power", "alpha_mode", "no_dispersion", "model build"),
        consensus=(
            "实验 profile 应在独立输出目录构建，不能覆盖 baseline。",
            "model-build-only 成功不等于 pressure validation。",
            "profile 中的 `pressure_allowed=false` 必须传递到 NPZ 和 dry-run summary。",
        ),
        divergence=(
            "no_dispersion 是 solver 接口选择，不是默认物理真值。",
            "该路线比 fit_alpha_power=2 更快，但证据稳健性较弱。",
            "是否进入 pressure 仍需后续单独授权。",
        ),
        platform_current_state=(
            "已有 no-dispersion experimental profile 草案，位于 `outputs/source_backed_alpha_profile_options/profile_drafts/`。",
            "已有 alpha semantics propagation 和 dry-run metadata。",
            "已有 `validate_mapping_model_build.py` 可做模型构建对照。",
        ),
        platform_gaps=(
            "尚未构建 isolated no-dispersion 模型。",
            "尚未验证 `pressure_allowed=false` 是否进入 NPZ/dry-run。",
            "尚未对比 no-dispersion 与原 draft 模型的 material ranges。",
        ),
        recommended_decisions=(
            "本轮允许重建一个独立 CT acoustic model，但不运行 k-Wave。",
            "输出目录必须独立于旧 best 和旧 draft。",
            "若 dry-run 中 `pressure_allowed_by_alpha_semantics` 不是 false，必须停止并修护栏。",
        ),
        do_not_mix=(
            "不要把 model-build-only 结果写成 pressure validation。",
            "不要覆盖 `outputs/ct_acoustic_model_3d_profile_prestus_marsac_mueller_draft/`。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 evidence brief。",
            "构建独立 no-dispersion 模型输出。",
            "summary/NPZ/dry-run 均记录 alpha_mode=no_dispersion 与 pressure_allowed=false。",
            "不生成 `pressure_max_mpa.npz`。",
        ),
        risks=(
            "若忽略 profile 的 pressure_allowed=false，后续可能误跑 pressure。",
            "只改 alpha_mode 不会改变材料数组，容易被误读为物理改进。",
            "构建输出若覆盖旧目录会破坏证据链。",
        ),
        next_steps=(
            "先补 pressure_allowed metadata 护栏。",
            "再执行 isolated model-build-only validation。",
            "最后生成对照报告并保持 pressure blocked。",
        ),
    ),
    "fit_alpha_power_migration": ModuleSpec(
        module="fit_alpha_power_migration",
        title="PRESTUS fit-alpha-power=2 衰减映射迁移",
        goal="把 PRESTUS fitPowerLawParamsMulti 路线迁移为可审计的 model-build-only CT-HU alpha profile，验证 alpha_power=2 的系数重标定、summary/NPZ metadata 和 dry-run 护栏，不运行 k-Wave pressure。",
        paper_keywords=("attenuation", "alpha", "skull", "CT", "HU", "k-Wave", "dispersion"),
        tool_keywords=("PRESTUS", "fitPowerLawParamsMulti", "alpha_power", "attenuation", "k-Wave", "skull"),
        consensus=(
            "PRESTUS 提供 fitPowerLawParamsMulti 路线，用于把原始 attenuation/power-law 参数重标定到固定 alpha_power。",
            "alpha_power=2 路线比直接 alpha_power=1 + no_dispersion 更接近 PRESTUS 源码中的拟合思路，但仍需要 model-build validation。",
            "model-build-only 成功不等于 pressure validation；pressure 必须继续由 profile 中的 pressure_allowed=false 阻断。",
        ),
        divergence=(
            "PRESTUS fit-alpha-power 路线与 k-wave-python alpha_mode=no_dispersion 是两条不同处理策略，不能混写。",
            "不同工具对 alpha_coeff 单位和频率幂次的约定不同，必须在 summary 中明确 dB/(MHz^y cm)、alpha_power 和 reference frequency。",
            "当前平台的 simple_hu300 仍是可复现 baseline，fit-alpha-power=2 只能作为 review-pending source-backed candidate。",
        ),
        platform_current_state=(
            "已有 PRESTUS source snapshot，包含 fitPowerLawParamsMulti.m、medium_pct_density.m、medium_pct_soundspeed.m 和 medium_pct_attenuation.m。",
            "已有 acoustic_mapping_profiles/prestus_fit_alpha_power_2.json 草案，标记 pressure_allowed=false。",
            "build_ct_acoustic_model.py 已出现 fit_power_law_params_multi 与 prestus_fit_alpha_power_2 构建路径，需要通过独立输出验证。",
            "simulate_kwave_3d_focus.py 已能读取 alpha_power、alpha_mode、alpha_coeff_kind 和 alpha_pressure_allowed，并在 dry-run 中报告 pressure_allowed_by_alpha_semantics。",
        ),
        platform_gaps=(
            "尚未生成 fit-alpha-power=2 的独立 evidence brief。",
            "尚未用 079 独立重建 profile-based 模型并对比 material ranges。",
            "尚未验证 fit-alpha-power=2 模型的 dry-run 是否继续阻断 pressure。",
            "尚未把该路线明确归类为 review-pending model-build-only，而非 validated continuous mapping baseline。",
        ),
        recommended_decisions=(
            "本轮只允许 isolated model-build validation 和 dry-run quality，不运行 k-Wave pressure。",
            "输出目录必须独立于 simple_hu300 baseline、no-dispersion experimental 和旧 best pressure 结果。",
            "若 alpha_pressure_allowed 或 pressure_allowed_by_alpha_semantics 不是 false，立即停止并修复护栏。",
            "fit-alpha-power=2 通过 model-build 后仍保持 review_pending_model_build_only_do_not_use_as_default。",
        ),
        do_not_mix=(
            "不要把 fit-alpha-power=2 的 model-build 成功写成 pressure validation。",
            "不要把 PRESTUS fitPowerLawParamsMulti 与 k-wave-python alpha_mode=no_dispersion 混成同一策略。",
            "不要覆盖 simple_hu300 当前 baseline 或 079 hand-tuned best 输出。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 fit_alpha_power_migration evidence brief。",
            "079 可用 prestus_fit_alpha_power_2 profile 独立重建 acoustic_model_3d.npz 和 summary。",
            "summary/NPZ/dry-run 均记录 alpha_power=2、alpha_coeff_kind=fit_alpha_power_2_prefactor、alpha_pressure_allowed=false。",
            "dry-run 不生成 pressure_max_mpa.npz，且 pressure_allowed_by_alpha_semantics=false。",
            "生成 model-build comparison 与 gap_feedback，明确该路线仍不是 validated pressure baseline。",
        ),
        risks=(
            "fitPowerLawParamsMulti 的单位换算若实现错误，会让 alpha_coeff 数值看似合理但物理含义错误。",
            "alpha_power=2 可能降低 k-Wave dispersion 风险，但不能替代网格、PML、CFL 和实验对照。",
            "已有草案文件未纳入 git，需避免把未审 profile 当作默认配置。",
        ),
        next_steps=(
            "生成 brief 后先编译相关脚本。",
            "构建独立 079 fit-alpha-power=2 模型并运行 model-build comparison。",
            "运行 dry-run quality 确认 pressure blocked。",
            "把结果写入 gap_feedback 和项目状态文档。",
        ),
    ),
    "fit_alpha_power_formula_audit": ModuleSpec(
        module="fit_alpha_power_formula_audit",
        title="PRESTUS fitPowerLawParamsMulti 公式与单位审计",
        goal="审计 fus-sim 中 `fit_power_law_params_multi` 与 PRESTUS `fitPowerLawParamsMulti.m` 的公式、单位换算和 alpha_power=2 数值行为，输出只读审计报告，不运行 k-Wave。",
        paper_keywords=("attenuation", "alpha", "power law", "Treeby", "Cox", "k-Wave", "skull"),
        tool_keywords=("PRESTUS", "fitPowerLawParamsMulti", "db2neper", "neper2db", "alpha_power", "k-Wave"),
        consensus=(
            "PRESTUS `fitPowerLawParamsMulti` 明确引用 Treeby & Cox 2014 Eq. 40，用于把目标 absorption 行为拟合到固定 reference alpha_power。",
            "k-Wave alpha_coeff 的接口语义是 `dB/(MHz^y cm)`，其中 y 必须与 alpha_power 配套。",
            "公式审计只能证明实现迁移一致性，不能证明 CT pressure 结果可信。",
        ),
        divergence=(
            "当 `y_ref=2` 时，`tan(pi*y_ref/2)=tan(pi)` 理论上为 0，二阶项几乎消失；这会让结果接近在 500 kHz 处的简单重标定。",
            "不同工具对 alpha 先按 dB/cm at reference frequency 还是 alpha0 prefactor 存储的约定不同，最容易造成单位误读。",
            "该审计不解决 HU->porosity->attenuation 原始物理模型是否适合 079 低 HU 入射路径的问题。",
        ),
        platform_current_state=(
            "已有 PRESTUS source snapshot：`data/source_code_refs/PRESTUS_source/functions/medium/fitPowerLawParamsMulti.m`。",
            "已有 Python 迁移实现：`build_ct_acoustic_model.py::fit_power_law_params_multi`。",
            "已有 `prestus_fit_alpha_power_2` profile 和 079 model-build-only 输出。",
        ),
        platform_gaps=(
            "尚未生成公式/单位审计报告。",
            "尚未用可读数值表说明 alpha_power=2 重标定后为何出现约 `16-34.8 dB/(MHz^2 cm)`。",
            "尚未明确该审计是否足以解除 pressure block。",
        ),
        recommended_decisions=(
            "本轮只做源码对照和小样本数值 sanity，不重建 CT 模型，不运行 k-Wave。",
            "报告必须区分 original alpha at 500 kHz、original alpha0 for y=1、fitted alpha0 for y_ref=2。",
            "若公式或单位证据不足，保持 profile blocked for pressure。",
        ),
        do_not_mix=(
            "不要把公式迁移一致性写成 pressure validation。",
            "不要把 alpha0 prefactor 与 500 kHz 下 dB/cm absorption 直接比较。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 `fit_alpha_power_formula_audit` evidence brief。",
            "生成 formula audit report、JSON 和 sample fit CSV。",
            "报告列出 PRESTUS 公式、Python 公式、单位换算、y_ref=2 的二阶项行为。",
            "报告明确仍不允许 pressure simulation，除非后续单独授权。",
        ),
        risks=(
            "MATLAB 源码依赖 k-Wave `db2neper/neper2db`，本轮只能审计调用语义和 Python 对应转换，不能替代完整 MATLAB 单元测试。",
            "若 profile/source_locator 指向不够精确，后续可能误追踪到 medium_pct_attenuation 而忽略 fitPowerLawParamsMulti。",
            "低 HU 边缘颅骨的物理映射仍可能是主风险，即使公式迁移正确。",
        ),
        next_steps=(
            "生成只读 evidence brief。",
            "运行公式/单位审计脚本，输出 sample table。",
            "根据报告决定是否进入 entry-path alpha profile 对照或继续保持 pressure blocked。",
        ),
    ),
    "fit_alpha_power_matlab_crosscheck": ModuleSpec(
        module="fit_alpha_power_matlab_crosscheck",
        title="PRESTUS fitPowerLawParamsMulti MATLAB/Python 交叉测试包",
        goal="生成 MATLAB/Python 数值交叉测试包，用同一组样本输入比较 PRESTUS `fitPowerLawParamsMulti.m` 与 fus-sim Python 实现的输出；本阶段不要求本机具备 MATLAB，也不运行 k-Wave。",
        paper_keywords=("attenuation", "alpha", "power law", "Treeby", "Cox", "k-Wave", "validation"),
        tool_keywords=("PRESTUS", "MATLAB", "fitPowerLawParamsMulti", "Python", "db2neper", "neper2db"),
        consensus=(
            "公式迁移审计之后，最稳的下一步是用固定样本做跨语言数值对照。",
            "MATLAB/Python 交叉测试只能验证实现一致性，不能验证 CT pressure 结果。",
            "如果本机没有 MATLAB，应生成可移交的测试包，而不是伪造已运行结果。",
        ),
        divergence=(
            "PRESTUS 源码依赖 MATLAB/k-Wave 工具函数，Python 环境不能直接替代完整 MATLAB 运行。",
            "y_ref=2 的样本可能过于简单，因为二阶项近似为零；测试包应同时包含 y_ref 非 2 的敏感样本。",
            "交叉测试通过后仍需要保持 `pressure_allowed=false`，除非后续另行授权 pressure sanity。",
        ),
        platform_current_state=(
            "已有 Python formula audit 和 sample fit table。",
            "已有 PRESTUS source snapshot，可生成 MATLAB runner 脚本。",
            "当前本机未发现可直接调用的 `matlab` 命令。",
        ),
        platform_gaps=(
            "尚未生成 MATLAB runner 脚本和输入 fixture。",
            "尚未生成 Python expected outputs 供外部 MATLAB 环境对照。",
            "尚未定义 MATLAB 结果导回后的比较标准。",
        ),
        recommended_decisions=(
            "本轮只生成 crosscheck package，不运行 k-Wave，不重建 CT。",
            "样本包含 y_ref=2 与一个非 2 的 sensitivity case。",
            "若 MATLAB 不可用，报告标记为 `matlab_not_run_package_ready`。",
            "比较阈值使用严格但合理的绝对/相对容差，并记录最大误差。",
        ),
        do_not_mix=(
            "不要把 crosscheck package 写成 MATLAB 已运行。",
            "不要把跨语言数值一致写成 pressure validation。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 `fit_alpha_power_matlab_crosscheck` evidence brief。",
            "输出 input fixture、Python expected CSV/JSON、MATLAB runner `.m` 和中文说明。",
            "若本机无 MATLAB，summary 明确 `matlab_available=false` 与 `matlab_executed=false`。",
            "不生成 `pressure_max_mpa.npz`。",
        ),
        risks=(
            "外部 MATLAB 版本或 path 配置不同可能导致 runner 需要手动调整。",
            "PRESTUS snapshot 中若缺少 k-Wave db2neper/neper2db，runner 需包含本地等价 helper。",
            "跨语言对照只覆盖选定样本，不能证明所有 CT voxel 映射都无风险。",
        ),
        next_steps=(
            "生成 fixture 和 MATLAB runner。",
            "如果未来获得 MATLAB 输出，再运行导回比较。",
            "交叉测试前后均保持 pressure blocked。",
        ),
    ),
    "source_backed_alpha_stage_report": ModuleSpec(
        module="source_backed_alpha_stage_report",
        title="source-backed alpha mapping 阶段收口报告",
        goal="汇总 source-backed alpha mapping 已完成的 evidence brief、model-build-only、公式审计、entry-path profile 和 MATLAB 交叉测试包状态，明确哪些结论可以保留、哪些仍然 blocked；本阶段只做状态报告，不运行 k-Wave、不重建 CT。",
        paper_keywords=("attenuation", "alpha", "skull", "CT", "HU", "k-Wave", "power law"),
        tool_keywords=("PRESTUS", "BabelBrain", "fitPowerLawParamsMulti", "alpha_power", "attenuation"),
        consensus=(
            "source-backed profile 的模型构建成功不等于 pressure validation。",
            "alpha_coeff 的单位语义必须与 alpha_power、alpha_mode 和 k-Wave 接口一起审计。",
            "执行后偏差和状态冲突应写入 gap_feedback 或阶段报告，不能覆盖执行前 evidence brief。",
        ),
        divergence=(
            "no-dispersion 路线和 fit-alpha-power=2 路线解决的是不同风险，不能混成同一个 validated profile。",
            "历史输出中可能同时存在 exploratory pressure run 与 review-pending/blocked 状态，需要上层 reconciliation。",
            "entry path 上低 HU 颅骨边缘的 PRESTUS-style c/rho 映射可能接近水/软组织，这需要单独复核。",
        ),
        platform_current_state=(
            "已有 source-backed alpha profile options、no-dispersion model-build validation、fit-alpha-power=2 model-build validation。",
            "已有 fitPowerLawParamsMulti formula audit、entry-path property profile 和 MATLAB/Python cross-check package。",
            "simple_hu300 仍是当前可复现 baseline；source-backed alpha 路线仍不应自动替代 baseline。",
        ),
        platform_gaps=(
            "MATLAB cross-check package 已准备，但本机尚未执行 MATLAB 侧输出比对。",
            "部分 summary/gap_feedback 对 pressure_allowed 状态存在不一致，需要在报告中显式标注。",
            "尚未形成可把 prestus_fit_alpha_power_2 升级为默认 pressure baseline 的证据门槛。",
        ),
        recommended_decisions=(
            "本轮只生成阶段报告和执行后反馈，不生成新的 acoustic_model_3d.npz 或 pressure_max_mpa.npz。",
            "将 source-backed alpha routes 标记为 exploratory/review-pending，直到 MATLAB cross-check、unit audit 和 model-build gates 全部收口。",
            "下一步优先做 profile promotion gate 或外部 MATLAB cross-check，而不是直接 pressure run。",
        ),
        do_not_mix=(
            "不要把 PRESTUS fit-alpha-power=2 的 model-build 成功写成经颅声压验证。",
            "不要把 dB/(MHz^2 cm) prefactor 与 dB/(MHz cm) attenuation 直接数值比较。",
            "不要把 BBB、微泡、血栓、Histotripsy 或热消融参数混入当前低强度神经调控 baseline。",
        ),
        acceptance_criteria=(
            "生成 `source_backed_alpha_stage_report` evidence brief。",
            "输出中文阶段报告和 JSON summary。",
            "报告明确已完成步骤、当前差距、状态冲突和下一步建议。",
            "不运行 k-Wave、不重建 CT、不覆盖已有 pressure/thermal 输出。",
        ),
        risks=(
            "如果只引用单个 gap_feedback，可能忽略 Antigravity 或历史输出造成的状态冲突。",
            "如果把 exploratory pressure run 当作 validated evidence，会破坏 EDD 门槛。",
            "如果继续盲跑 pressure，会绕过 alpha semantics 和 source formula 审计。",
        ),
        next_steps=(
            "读取现有 gap_feedback、dry-run summary、entry-path summary 和 cross-check summary。",
            "生成阶段报告和 gap_feedback。",
            "根据报告决定是执行 MATLAB cross-check，还是冻结 source-backed alpha route 并回到 simple_hu300 baseline。",
        ),
    ),
}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def row_text(row: dict[str, str]) -> str:
    return " ".join(str(value) for value in row.values()).lower()


def matches(row: dict[str, str], keywords: Iterable[str]) -> bool:
    text = row_text(row)
    return any(keyword.lower() in text for keyword in keywords)


def select_rows(rows: list[dict[str, str]], keywords: tuple[str, ...], limit: int = 8) -> list[dict[str, str]]:
    selected = [row for row in rows if matches(row, keywords)]
    if selected:
        return selected[:limit]
    return rows[: min(limit, len(rows))]


def compact_paper(row: dict[str, str]) -> dict[str, str]:
    keys = [
        "paper_id",
        "title",
        "year",
        "application",
        "parameter_name",
        "value",
        "unit_or_definition",
        "evidence_level",
        "source_locator",
        "definition_status",
        "review_status",
        "notes",
    ]
    return {key: row.get(key, "") for key in keys}


def compact_tool(row: dict[str, str]) -> dict[str, str]:
    keys = [
        "tool_id",
        "name",
        "language",
        "solver_backend",
        "transducer_model",
        "skull_modeling",
        "thermal_modeling",
        "validation",
        "evidence_level",
        "source_locator",
        "what_to_learn",
        "risk_or_limit",
        "next_action",
    ]
    return {key: row.get(key, "") for key in keys}


def build_brief(module: str) -> dict[str, object]:
    if module not in MODULES:
        raise ValueError(f"Unsupported module {module!r}. Supported modules: {', '.join(sorted(MODULES))}")
    spec = MODULES[module]
    paper_rows = read_csv_rows(PROJECT_ROOT / "paper_parameter_matrix.csv")
    tool_rows = read_csv_rows(PROJECT_ROOT / "tool_code_matrix.csv")
    related_papers = [compact_paper(row) for row in select_rows(paper_rows, spec.paper_keywords)]
    related_tools = [compact_tool(row) for row in select_rows(tool_rows, spec.tool_keywords)]
    return {
        "brief_type": "evidence_brief_pre_execution",
        "module": spec.module,
        "title": spec.title,
        "goal": spec.goal,
        "related_papers": related_papers,
        "related_tools": related_tools,
        "consensus": list(spec.consensus),
        "divergence": list(spec.divergence),
        "platform_current_state": list(spec.platform_current_state),
        "platform_gaps": list(spec.platform_gaps),
        "recommended_decisions": list(spec.recommended_decisions),
        "do_not_mix": list(spec.do_not_mix),
        "acceptance_criteria": list(spec.acceptance_criteria),
        "risks": list(spec.risks),
        "next_steps": list(spec.next_steps),
        "source_files": [
            "paper_parameter_matrix.csv",
            "tool_code_matrix.csv",
            "parameter_alignment_report.md",
            "reproduction_route_calibration.md",
        ],
        "post_execution_feedback_outputs": [
            f"outputs/evidence_briefs/{spec.module}/gap_feedback.md",
            f"outputs/evidence_briefs/{spec.module}/gap_feedback.json",
        ],
    }


def bullet_list(items: list[object]) -> str:
    if not items:
        return "- 暂无\n"
    return "".join(f"- {item}\n" for item in items)


def paper_list(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "- 暂无\n"
    lines = []
    for row in rows:
        label = row.get("parameter_name") or row.get("paper_id")
        value = row.get("value", "")
        unit = row.get("unit_or_definition", "")
        source = row.get("source_locator", "")
        note = row.get("notes", "")
        lines.append(f"- `{row.get('paper_id')}` / {label}: {value} {unit}；证据：{row.get('evidence_level')}；位置：{source}；备注：{note}\n")
    return "".join(lines)


def tool_list(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "- 暂无\n"
    lines = []
    for row in rows:
        lines.append(
            f"- `{row.get('tool_id')}`：{row.get('name')}；后端：{row.get('solver_backend')}；"
            f"可借鉴：{row.get('what_to_learn')}；验证/限制：{row.get('validation')} / {row.get('risk_or_limit')}\n"
        )
    return "".join(lines)


def build_markdown(brief: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# Evidence Brief：{brief['title']}",
            "",
            "> 类型：执行前证据 brief。执行后的结果、偏差、失败和调整建议应写入同目录 `gap_feedback.md/json`，不要混入本文件。",
            "",
            "## 模块目标",
            "",
            str(brief["goal"]),
            "",
            "## 相关论文",
            "",
            paper_list(brief["related_papers"]),  # type: ignore[arg-type]
            "## 相关公开工具",
            "",
            tool_list(brief["related_tools"]),  # type: ignore[arg-type]
            "## 参数共识",
            "",
            bullet_list(brief["consensus"]),  # type: ignore[arg-type]
            "## 参数分歧",
            "",
            bullet_list(brief["divergence"]),  # type: ignore[arg-type]
            "## 当前平台已有内容",
            "",
            bullet_list(brief["platform_current_state"]),  # type: ignore[arg-type]
            "## 当前平台缺口",
            "",
            bullet_list(brief["platform_gaps"]),  # type: ignore[arg-type]
            "## 推荐实现决策",
            "",
            bullet_list(brief["recommended_decisions"]),  # type: ignore[arg-type]
            "## 不应混用的参数或方向",
            "",
            bullet_list(brief["do_not_mix"]),  # type: ignore[arg-type]
            "## 验收标准",
            "",
            bullet_list(brief["acceptance_criteria"]),  # type: ignore[arg-type]
            "## 风险与检查点",
            "",
            bullet_list(brief["risks"]),  # type: ignore[arg-type]
            "## 下一步建议",
            "",
            bullet_list(brief["next_steps"]),  # type: ignore[arg-type]
            "## 来源文件",
            "",
            bullet_list(brief["source_files"]),  # type: ignore[arg-type]
            "## 执行后反馈输出位置",
            "",
            bullet_list(brief["post_execution_feedback_outputs"]),  # type: ignore[arg-type]
            "",
        ]
    )


def write_outputs(module: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    brief = build_brief(module)
    (output_dir / "evidence_brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "evidence_brief.md").write_text(build_markdown(brief), encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an evidence brief for a fus-sim platform module.")
    parser.add_argument("--module", required=True, choices=sorted(MODULES))
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else PROJECT_ROOT / "outputs" / "evidence_briefs" / args.module
    write_outputs(args.module, output_dir)
