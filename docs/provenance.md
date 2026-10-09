# 工具源码与示例来源

## 源码

渲染流程改编自 [My_SBR](https://github.com/yyzzzasdf/My_SBR) 的 `tools/plotting_3d/sweep_volume.py`，提取版本为 `ffd4193baee7cb96a2da220473e33b1326610d11`。

保留固定场景、三个方向切片扫描、VTK 深度合成、半透明建筑、发射点及内部透明掩码的处理方式。独立版本增加输入校验、配置文件、命令行参数、正确的功率单位标注和运行记录；使用普通数值场景输入，默认缩放改为 1.0，以显示完整场景。

主项目的 `src/`、仿真代码和原始渲染模块没有修改。工具运行时不导入主项目，也不使用 OneDrive 路径。

## 合成样例

`examples/synthetic/` 为 8×10×6 的解析合成场，带一个长方体建筑。功率数值仅用于演示渲染与测试输入格式，不表示实际电磁计算。运行 `scripts/generate_synthetic.py` 可以独立重建它。

## Manhattan 小样例

`examples/manhattan/` 在 2026 年 10 月 9 日基于主项目 `data/processed/manhattan.pkl` 新计算，网格为 40×55×9、体素间隔为 20×20×10 米。使用 ray 路线、20,000 条发射射线、最多五次反射、28 GHz，发射点为 `[-80,80,10]` 米。

对应的主项目场景 SHA256 为 `8577ffc919c931cb934a159ed3532262b87cb6625811f5cfc5c4f5fd78acaf33`。参数、覆盖数和几何自检结果保存在样例的 `metadata.json`。这是新的粗网格演示数据，不是旧 1 米 ray-d 数据的下采样。

## 历史参考视频

`reference/manhattan/` 从结果库的 `cases/grid3d_routes/run_20260716_1m3d/manhattan/` 只读复制，保留六个 MP4 和一张对比图。`original_run_meta.json` 是所属 run 的原始溯源记录，其中还列出其他场景；本包只包含 Manhattan 参考文件。

原始 run 时间为 2026 年 7 月 16 日，元数据记录 commit `eb7939b382f7c870ade5fc1781938c2546caee89`，并注明执行时 HEAD 为 `b7ccb6d`。这些历史对象不在当前克隆的 Git 历史中，因此本包不声称独立代码与历史视频逐帧相同。参考文件的 SHA256 校验结果记录在 `docs/validation.json`。

原始 1 米功率立方体和 beam 缓存未包含在结果目录中；本包没有该历史输入。若以后获得功率立方体和场景 overlay，可按输入格式说明补齐元数据并转换场景，再使用本工具导出。

## 交付边界

随包参考文件只用于查看既有结果。默认运行输出写入 `outputs/`；代码包可整体移出主项目或作为独立 Git 仓库。交付包不包含 Python 环境、临时缓存或其他研究案例。
