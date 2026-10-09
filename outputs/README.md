# 视频生成结果

默认运行结果写入 `synthetic/`。使用 `--out` 为不同输入选择新的目录。

每次运行包含 MP4、可选 PNG 预览以及 `run.json`。随包参考结果位于上一级 `reference/`，输入样例位于 `examples/`。

输出默认不提交到 Git。要保留某次结果用于交付，可复制到 `reference/` 并同时保留运行记录。
