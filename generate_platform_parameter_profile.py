import os
import json

def main():
    # Setup paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    paper_matrix_path = os.path.join(script_dir, "paper_parameter_matrix.json")
    tool_matrix_path = os.path.join(script_dir, "tool_code_matrix.json")
    
    output_dir = os.path.join(script_dir, "outputs", "parameter_profiles")
    os.makedirs(output_dir, exist_ok=True)
    
    output_profile_json = os.path.join(output_dir, "platform_parameter_profile.json")
    output_report_md = os.path.join(output_dir, "platform_parameter_source_report.md")
    
    # Load matrices
    with open(paper_matrix_path, "r", encoding="utf-8") as f:
        paper_matrix = json.load(f)
        
    with open(tool_matrix_path, "r", encoding="utf-8") as f:
        tool_matrix = json.load(f)
        
    # Compile platform default parameters structure
    profile = {
        "platform_name": "tFUS Simulation Platform (fus-sim)",
        "version": "1.0.0",
        "description": "Default simulation parameters aligned with literature evidence and tuned project targets.",
        "acoustic_parameters": {
            "frequency_khz": {
                "value": 500,
                "unit": "kHz",
                "role": "baseline",
                "source_paper": "Gao2022_local",
                "source_title": "经颅聚焦超声调控系统的参数仿真研究",
                "evidence_level": "原文明确",
                "relevance": "种子论文声学主频，也是经颅神经调控（tFUS）领域的黄金标准基线频率（250-650 kHz）之一。",
                "status": "ready"
            },
            "source_pressure_mpa": {
                "value": 1.0,
                "unit": "MPa",
                "role": "baseline_excitation",
                "source_paper": "Gao2022_local",
                "evidence_level": "原文明确",
                "relevance": "换能器表面激发声压级。需要特别强调这代表发射源面声压，并非穿颅后原位（in situ）声压。原位声压由于颅骨衰减和反射通常大为降低，必须区分这两者。",
                "status": "ready"
            },
            "aperture_mm": {
                "value": 30.0,
                "unit": "mm",
                "role": "current_tuned",
                "baseline_value": 25.0,
                "source_paper": "Gao2022_local",
                "evidence_level": "原文明确（基线），经调参优化（当前值）",
                "relevance": "换能器孔径直径。高鹏皓基线为 25 mm，为提高聚焦性能和适应大网格穿颅聚焦，当前调参值为 30 mm。",
                "status": "tuned"
            },
            "curvature_radius_mm": {
                "value": 35.0,
                "unit": "mm",
                "role": "current_tuned",
                "baseline_value": 30.0,
                "source_paper": "Gao2022_local",
                "evidence_level": "原文明确（基线），经调参优化（当前值）",
                "relevance": "换能器曲率半径。高鹏皓基线为 30 mm（F=1.20），为了在 079 病例穿颅时达到更好的焦深，当前优化调参值为 35 mm（F=1.17）。",
                "status": "tuned"
            }
        },
        "stimulation_protocol": {
            "duty_cycle_percent": {
                "value": 6.0,
                "unit": "%",
                "role": "baseline_protocol",
                "source_paper": "Gao2022_local",
                "evidence_level": "原文明确",
                "relevance": "占空比。高鹏皓硕士论文中第 4 章采用的热效应仿真参数，非通用共识，需特别标注说明其为种子协议参数。",
                "status": "ready"
            },
            "prf_hz": {
                "value": 300,
                "unit": "Hz",
                "role": "baseline_protocol",
                "source_paper": "Gao2022_local",
                "evidence_level": "原文明确",
                "relevance": "脉冲重复频率。高鹏皓刺激协议中规定的 PRF，属于典型神经调控刺激模式参数。",
                "status": "ready"
            },
            "train_duration_ms": {
                "value": 67.0,
                "unit": "ms",
                "role": "baseline_protocol",
                "source_paper": "Gao2022_local",
                "evidence_level": "原文明确",
                "relevance": "单次刺激序列（train）持续时间。用于瞬态热仿真输入。",
                "status": "ready"
            },
            "train_interval_s": {
                "value": 2.5,
                "unit": "s",
                "role": "baseline_protocol",
                "source_paper": "Gao2022_local",
                "evidence_level": "原文明确",
                "relevance": "两个刺激序列之间的非活动间隔。用于 Pennes 生物热模型的刺激循环热剂量扫描计算。",
                "status": "ready"
            }
        },
        "biological_and_safety_parameters": {
            "ct_bone_threshold_hu": {
                "value": 300,
                "unit": "HU",
                "role": "baseline_threshold",
                "source_paper": "Gao2022_local",
                "evidence_level": "局部实验调参决定",
                "relevance": "划分颅骨与软组织的 CT Hounsfield 单位阈值。高于 300 HU 判定为颅骨，低于该值判定为软组织/背景。",
                "status": "needs_calibration"
            },
            "thermal_threshold_degC": {
                "value": 42.0,
                "unit": "degC",
                "role": "safety_threshold",
                "source_paper": "Gao2022_local",
                "evidence_level": "原文明确",
                "relevance": "脑组织及颅骨的最高温升安全硬界限。超过该温度需报警提示可能有非靶区热损伤风险。",
                "status": "ready"
            }
        }
    }
    
    # Save JSON Profile
    with open(output_profile_json, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
        
    # Generate Markdown Report
    report = []
    report.append("# tFUS 仿真平台默认参数可追溯性对齐报告")
    report.append(f"\n> 本报告由平台脚本 `generate_platform_parameter_profile.py` 自动生成。")
    report.append(f"> 生成时间：2026-05-20  ")
    report.append(f"> 对应数据源：[paper_parameter_matrix.json](file:///{paper_matrix_path}) 与 [tool_code_matrix.json](file:///{tool_matrix_path})")
    
    report.append("\n## 1. 核心声学参数对齐 (Acoustic Parameters)")
    report.append("\n| 参数名 | 默认值 | 单位 | 角色类型 | 证据来源 | 证据级别 | 说明与原位声压区别 |")
    report.append("| --- | --- | --- | --- | --- | --- | --- |")
    
    ap = profile["acoustic_parameters"]
    report.append(f"| 主频率 | `{ap['frequency_khz']['value']}` | {ap['frequency_khz']['unit']} | {ap['frequency_khz']['role']} | {ap['frequency_khz']['source_paper']} | {ap['frequency_khz']['evidence_level']} | {ap['frequency_khz']['relevance']} |")
    report.append(f"| 发射声压 | `{ap['source_pressure_mpa']['value']}` | {ap['source_pressure_mpa']['unit']} | {ap['source_pressure_mpa']['role']} | {ap['source_pressure_mpa']['source_paper']} | {ap['source_pressure_mpa']['evidence_level']} | {ap['source_pressure_mpa']['relevance']} |")
    report.append(f"| 换能器孔径 | `{ap['aperture_mm']['value']}` | {ap['aperture_mm']['unit']} | {ap['aperture_mm']['role']} | {ap['aperture_mm']['source_paper']} | {ap['aperture_mm']['evidence_level']} | {ap['aperture_mm']['relevance']} (基线值 `{ap['aperture_mm']['baseline_value']}` mm) |")
    report.append(f"| 曲率半径 | `{ap['curvature_radius_mm']['value']}` | {ap['curvature_radius_mm']['unit']} | {ap['curvature_radius_mm']['role']} | {ap['curvature_radius_mm']['source_paper']} | {ap['curvature_radius_mm']['evidence_level']} | {ap['curvature_radius_mm']['relevance']} (基线值 `{ap['curvature_radius_mm']['baseline_value']}` mm) |")

    report.append("\n## 2. 刺激协议参数对齐 (Stimulation Protocol)")
    report.append("\n| 参数名 | 默认值 | 单位 | 角色类型 | 证据来源 | 证据级别 | 说明 |")
    report.append("| --- | --- | --- | --- | --- | --- | --- |")
    
    sp = profile["stimulation_protocol"]
    report.append(f"| 占空比 | `{sp['duty_cycle_percent']['value']}` | {sp['duty_cycle_percent']['unit']} | {sp['duty_cycle_percent']['role']} | {sp['duty_cycle_percent']['source_paper']} | {sp['duty_cycle_percent']['evidence_level']} | {sp['duty_cycle_percent']['relevance']} |")
    report.append(f"| 脉冲重复频率 | `{sp['prf_hz']['value']}` | {sp['prf_hz']['unit']} | {sp['prf_hz']['role']} | {sp['prf_hz']['source_paper']} | {sp['prf_hz']['evidence_level']} | {sp['prf_hz']['relevance']} |")
    report.append(f"| 刺激持续时间 | `{sp['train_duration_ms']['value']}` | {sp['train_duration_ms']['unit']} | {sp['train_duration_ms']['role']} | {sp['train_duration_ms']['source_paper']} | {sp['train_duration_ms']['evidence_level']} | {sp['train_duration_ms']['relevance']} |")
    report.append(f"| 刺激间隔时间 | `{sp['train_interval_s']['value']}` | {sp['train_interval_s']['unit']} | {sp['train_interval_s']['role']} | {sp['train_interval_s']['source_paper']} | {sp['train_interval_s']['evidence_level']} | {sp['train_interval_s']['relevance']} |")

    report.append("\n## 3. 生物物理与安全性参数 (Safety & Biophysics)")
    report.append("\n| 参数名 | 默认值 | 单位 | 角色类型 | 证据来源 | 证据级别 | 说明 |")
    report.append("| --- | --- | --- | --- | --- | --- | --- |")
    
    bp = profile["biological_and_safety_parameters"]
    report.append(f"| 颅骨分割 HU 阈值 | `{bp['ct_bone_threshold_hu']['value']}` | {bp['ct_bone_threshold_hu']['unit']} | {bp['ct_bone_threshold_hu']['role']} | {bp['ct_bone_threshold_hu']['source_paper']} | {bp['ct_bone_threshold_hu']['evidence_level']} | {bp['ct_bone_threshold_hu']['relevance']} |")
    report.append(f"| 脑组织最高安全温升 | `{bp['thermal_threshold_degC']['value']}` | {bp['thermal_threshold_degC']['unit']} | {bp['thermal_threshold_degC']['role']} | {bp['thermal_threshold_degC']['source_paper']} | {bp['thermal_threshold_degC']['evidence_level']} | {bp['thermal_threshold_degC']['relevance']} |")

    report.append("\n## 4. 后续物理标定行动建议 (Future Calibration Actions)")
    report.append("\n为了将本平台的仿真结果有效用于物理实验，建议针对以下被标记为需要标定 (`needs_calibration`) 或已修改 (`tuned`) 的参数执行校准：")
    report.append("\n1. **声场物理校准 (Free-field Calibration)**:")
    report.append("   - 必须运行 `simulate_freefield_transducer.py` 进行水槽仿真，验证当前几何参数 `aperture=30mm, radius=35mm` 在均匀介质中的聚焦行为是否符合真实物理声阻抗。")
    report.append("2. **连续颅骨骨密度映射校准 (Continuous CT-HU Mapping)**:")
    report.append("   - 目前的单一阈值分类（`ct_bone_threshold_hu=300`）不能反映颅骨在厚度和松质骨/密质骨分布上的非均匀声速特性，建议下一步升级为 PRESTUS/BabelBrain 式连续映射模型。")
    report.append("3. **脑组织血灌注与热传导率标定**:")
    report.append("   - Pennes 模型对温度消散极为敏感。需确保在进行高强度实验前，对选定动物模型的灌注参数（perfusion rate）进行特异性边界约束，避免定性预测失真。")

    # Write report
    with open(output_report_md, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print("Parameter profile compiler completed successfully!")
    print(f"JSON profile saved to: {output_profile_json}")
    print(f"Markdown report saved to: {output_report_md}")

if __name__ == "__main__":
    main()
