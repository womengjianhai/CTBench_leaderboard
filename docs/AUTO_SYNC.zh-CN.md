# 本地保存后自动更新 GitHub 与主页

仓库：https://github.com/womengjianhai/CTBench_leaderboard

主页：https://womengjianhai.github.io/CTBench_leaderboard/

本地 `main` 跟踪 `origin/main`，保留远程原有提交历史。修改并保存文件后，后台每 5 秒检测一次，连续 15 秒没有改动后运行现有主页测试与构建，生成 commit 并 push。GitHub Actions 随后构建、发布 GitHub Pages，网页通常还需等待几分钟。部署进度以仓库 Actions 为准。

## 常用操作

在本目录 PowerShell 中运行：

```powershell
# 查看后台任务、状态和最近日志
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\auto_sync.ps1 Status

# 暂停自动提交；已开始的推送可能继续完成
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\auto_sync.ps1 Pause

# 恢复自动提交
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\auto_sync.ps1 Resume

# 重新安装本机登录启动任务
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\auto_sync.ps1 Install

# 关闭自动同步并删除登录启动任务
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\auto_sync.ps1 Uninstall
```

自动任务名为 `CTBench-Leaderboard-AutoSync`，使用当前 Windows 用户权限，在用户登录后后台运行。电脑关闭、用户退出或断网时无法实时上传；恢复连接后会重试。目录移动后，需要在旧目录卸载任务，再在新目录安装。

## 修改哪些文件

- 页面内容：`website/index.html`
- 样式与交互：`website/assets/`
- 仓库、论文、数据入口：`website/site-config.json`
- 已发布榜单：`results/published/paper-v1.json`，保留数据来源与版本标记。

所有未被 `.gitignore` 排除的改动（包括新文件与删除）都会自动提交到公开仓库。`dist/`、Python 缓存、虚拟环境、`.env` 和常见密钥文件已排除；其他本地私有文件应先加入 `.gitignore`。Git 凭据继续由本机 Git Credential Manager 管理，脚本不保存口令或 token。

需要长时间修改多个文件时，先暂停，完成后恢复。自动同步按保存的文件版本工作；主页校验失败会保留本地改动并稍后重试。仅在 `main` 分支工作；切换分支、解决冲突、变更远程地址期间会暂停推送。远程出现本地尚未包含的提交时会停止自动推进，需先暂停并手动合并远程改动，再恢复；不会强制推送。

后台日志与状态位于 `.git/auto-sync/sync.log`、`.git/auto-sync/status.json`，不会提交。当前机器的 GitHub 网络代理仅配置在本仓库 `.git/config`，迁移到另一台机器时需要按该机器网络环境重新配置。

主页部署已有 `.github/workflows/pages.yml`，发布源为 GitHub Actions。只有页面、榜单、构建脚本和相应测试等工作流列出的文件变化时才会自动部署；文档更新仅更新 GitHub 代码。Actions 页面：https://github.com/womengjianhai/CTBench_leaderboard/actions