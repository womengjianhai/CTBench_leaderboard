# CTBench Leaderboard

公开主页：https://womengjianhai.github.io/CTBench_leaderboard/

本仓库包含 CTBench 主页、论文榜单数据和 GitHub Pages 自动发布工作流。

- [本地保存后自动同步](docs/AUTO_SYNC.zh-CN.md)：后台提交、推送、暂停与恢复。
- 页面源文件：`website/`；榜单数据：`results/published/paper-v1.json`。
- [发布进度](https://github.com/womengjianhai/CTBench_leaderboard/actions)。

本地验证与构建：

```powershell
python -m unittest discover -s tests -v
python scripts/build_site.py
```