# tFUS 文献整理说明

本文件夹围绕工作区中的三篇中文学位论文整理相关高质量文献，用于后续搭建 `fus-sim` 经颅聚焦超声仿真平台和撰写综述。

## 本地种子论文

1. `经颅聚焦超声调控系统的参数仿真研究_高鹏皓.pdf`
   - 主线：tFUS 神经调控、CT 颅骨建模、k-Wave 声压仿真、换能器定位、热效应安全性。
2. `经颅聚焦超声联合微泡开放血脑屏障的数值仿真研究_潘婷.pdf`
   - 主线：FUS + 微泡开放 BBB、Keller-Miksis 微泡动力学、Westervelt/Pennes 数值仿真、被动空化检测。
3. `经颅聚焦超声治疗脑血栓的数值仿真研究_孙天宇.pdf`
   - 主线：经颅/开颅聚焦超声溶栓、82 阵元相控换能器、时间反转相位校正、声压阈值与温升。

## 筛选标准

- 必须能通过 DOI、PMID、PMCID、出版社页面或期刊页面核验。
- 优先选择实验步骤、模型参数或复现价值明确的研究论文。
- 三条主题线都覆盖：声场仿真/相位校正、BBB + 微泡、超声溶栓。
- 对无法访问全文的论文，只记录可核验元数据、摘要级信息和可确认方法，不补写无法确认的实验细节。
- 不下载版权不明确的 PDF；`papers_oa/` 仅用于保存开放获取且许可允许下载的原文。

## 文件说明

- `01_seed_papers_summary.md`：三篇本地论文的主要内容和实验步骤。
- `02_selected_papers_matrix.csv`：12 篇外部文献矩阵。
- `03_experimental_steps.md`：按研究主题整理的复现实验/SOP。
- `04_theme_synthesis.md`：主题综合和对 `fus-sim` 的启发。
- `references.bib`：12 篇外部文献 BibTeX。
- `notes/`：每篇外部论文的单独笔记。

## 建议阅读顺序

1. 先读 `01_seed_papers_summary.md`，明确三篇中文论文的共同问题。
2. 再读 `03_experimental_steps.md`，把声场仿真、BBB、溶栓三条流程分清。
3. 用 `02_selected_papers_matrix.csv` 和 `notes/` 查具体论文。
4. 最后读 `04_theme_synthesis.md`，把这些文献转化为 `fus-sim` 的下一步实现路线。

