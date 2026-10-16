# FastSurfer

FastSurfer 是一个面向脑 MRI 的快速结构分割工具，常被看作 FreeSurfer 相关工作流的深度学习加速版本。

## 在本项目中的位置

当前 `fus-sim` 知识库主体是 CT/颅骨声学映射和 [[05_论文与概念/concepts/k-Wave|k-Wave]] 声场仿真，项目材料中还没有把 FastSurfer 纳入正式流程。

如果后续需要从 MRI 中获得脑结构、皮层/脑区分区、靶点定位或 MRI-only 路线，FastSurfer 才可能进入“影像预处理”层。

## 需要先确认

- 输入是 MRI 还是 CT？
- 目标是分割脑结构，还是分割颅骨？
- 输出是否需要和 CT 或换能器坐标做 [[05_论文与概念/concepts/配准|配准]]？
- 结果是否会进入声学模型，还是只用于靶区定位？

## 关联

- [[05_论文与概念/concepts/NIfTI]]
- [[05_论文与概念/concepts/影像分割]]
- [[05_论文与概念/concepts/配准]]
- [[05_论文与概念/concepts/synthetic CT]]
- [[MOC_影像预处理与颅骨建模]]
