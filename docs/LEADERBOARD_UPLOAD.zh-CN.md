# 将 CTBench Leaderboard 发布到 netopt-team/ctbench

代码仓库：https://github.com/netopt-team/ctbench

部署成功后的默认主页地址：**https://netopt-team.github.io/ctbench/**

本说明使用 GitHub Actions 自动构建，再由 GitHub Pages 展示网页。主页包含 Leaderboard、论文入口、Hugging Face 数据入口及 GitHub 仓库入口。仅展示主页无需安装 Python、Node.js，也无需配置模型密钥；构建由 GitHub 执行。

## 1. 上传哪个文件

本次先上传主页，使用 **CTBench-Leaderboard-netopt-team.zip**。

先在电脑上解压，打开其中的 `CTBench-Leaderboard-netopt-team` 文件夹，再把它里面的文件和文件夹上传到 `netopt-team/ctbench` 的**仓库根目录**。ZIP 是传输包，GitHub 不会自动解压并部署上传的 ZIP。

上传完成后的关键目录应该如下。外面不要再套一层 `CTBench-Leaderboard-netopt-team/`。

```text
ctbench/                         ← GitHub 仓库根目录
├─ .github/
│  └─ workflows/pages.yml         ← 自动构建与发布
├─ website/
│  ├─ index.html                 ← 主页
│  ├─ assets/
│  │  ├─ app.js                  ← Leaderboard 交互
│  │  ├─ styles.css              ← 页面样式
│  │  └─ favicon.svg
│  ├─ site-config.json           ← netopt-team/ctbench、论文及数据链接
│  └─ citation.bib
├─ results/
│  └─ published/paper-v1.json    ← 论文 Table 5 的公开榜单数据
├─ scripts/build_site.py         ← 生成网页及下载用 CSV
├─ tests/test_site_build.py      ← 发布前校验
├─ docs/LEADERBOARD_UPLOAD.zh-CN.md
└─ LICENSE
```

总共 12 个文件。这个包只增加主页所需文件，不包含评测数据、原始轨迹、运行环境、模型密钥或 Git 历史。若仓库已有同名文件，请对照确认后更新对应文件；其他已有代码保持原样。

单独上传 `index.html` 会缺少样式、脚本和榜单数据。只上传 `paper-v1.json` 则不会产生网页。

## 2. 通过 GitHub 网页上传

1. 登录有该仓库写入权限的 GitHub 账号，打开 https://github.com/netopt-team/ctbench 。
2. 在 **Code** 页面选择默认分支，通常是 `main`。
3. 点击 **Add file → Upload files**。如果仓库还是空的，点击页面中的 **uploading an existing file**。
4. 从解压目录中选择 `.github`、`website`、`results`、`scripts`、`tests`、`docs` 和 `LICENSE`，拖到上传区域。不要拖入外层同名目录，也不要直接拖 ZIP。
5. 检查上传列表包含 `.github/workflows/pages.yml` 和 `website/index.html`，路径与上图一致。
6. 在 **Commit changes** 中填写 `Add CTBench research homepage and leaderboard`，提交到默认分支。如果默认分支受保护，就提交新分支并创建、合并 Pull Request。

如果网页上传漏掉了 `.github`：通过 **Add file → Create new file**，文件名输入 `.github/workflows/pages.yml`，把解压包中对应文件的完整内容粘贴进去，再提交。

工作流自动触发分支已配置为 `main`、`master`。如果仓库使用其他默认分支名，修改 `.github/workflows/pages.yml` 中 `branches` 为实际名字。

## 3. 开启 GitHub Pages

1. 在仓库顶部点击 **Settings**。
2. 左侧点击 **Pages**。
3. 找到 **Build and deployment → Source**。
4. 选择 **GitHub Actions**。

本包已提供发布工作流，无需再选择 Jekyll 或创建另一套模板。配置 Pages 需要仓库的管理员或维护者权限。公共仓库可使用 GitHub Free/组织免费计划的 Pages 服务；如果仓库是私有的，能否启用取决于账号或组织计划。

官方说明：[配置 GitHub Pages 发布源](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)。

## 4. 手动启动首次部署

1. 点击仓库顶部 **Actions**。
2. 左侧选择 **Publish CTBench homepage**。
3. 点击 **Run workflow**，选择默认分支，再点击绿色 **Run workflow** 按钮。
4. 打开这次运行，等待 `build` 和 `deploy` 都显示绿色成功标记。
5. 打开 **https://netopt-team.github.io/ctbench/**，或点击 **Settings → Pages → Visit site**。

第一次上传可能在 Pages 尚未开启时就自动触发构建。如果首次运行失败，完成第 3 步设置后重新运行即可。以 Actions 中实际成功状态为准。

运行过程：校验榜单 → 构建 9 个公开静态文件到 `dist/` → 上传 Pages 构建产物 → 部署主页。你不需要手动上传 `dist/`，也不需要云服务器或域名。

## 5. 检查展示结果并添加仓库入口

- 打开主页，分别点击 **Root Cause Analysis** 和 **Path Restoration**，确认各有 5 个 Agent/Model 结果。
- 测试筛选、搜索、按指标排序及 **Download CSV**。
- 点击 **Paper**、**Dataset**、**GitHub**，分别跳转到论文、Hugging Face 数据集和 `netopt-team/ctbench`。
- 确认路径准确率等数值来自论文 Table 5，例如 ClaudeCode + Qwen3.7-Plus 为 17.59%。
- 回到仓库 **Code** 页面，在右侧 **About** 点击齿轮，将 **Website** 填为 `https://netopt-team.github.io/ctbench/`，保存。也可以在仓库 README 加入 `[Leaderboard](https://netopt-team.github.io/ctbench/)`。

## 6. 后续更新

- 页面内容：编辑 `website/index.html`。
- 页面样式：编辑 `website/assets/styles.css`。
- 论文、数据与仓库入口：对应更新 `website/site-config.json` 和 HTML 内的入口链接。
- 榜单数据：当前唯一数据源是 `results/published/paper-v1.json`，保持论文 Table 5 的版本来源。新增评测结果应经审核并明确版本，不直接用本地复算覆盖论文数值。

将更新提交到 `main`/`master` 后，Pages 工作流会自动重新构建和发布。GitHub 仓库页面展示文件与 README；前端网页在 `netopt-team.github.io/ctbench/` 展示。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| Actions 看不到 Publish CTBench homepage | 检查 `.github/workflows/pages.yml` 是否位于仓库根目录的正确路径，并已进入默认分支；确认仓库允许 GitHub Actions |
| `No such file` / 找不到构建脚本或结果 JSON | 检查是否误套了外层目录，或漏传 `scripts/`、`results/`、`website/`、`tests/` |
| `Get Pages site failed` / Pages 尚未开启 | 在 Settings → Pages 中选择 GitHub Actions，然后重新运行 |
| 发布作业等待批准 | 查看 `github-pages` 环境是否有组织要求的审批，由有权限的维护者处理 |
| 主页 404 | 确认 build/deploy 均成功，使用小写 `/ctbench/`，并以 Settings → Pages 中的实际网址为准 |
| 无法配置 Pages 或 Actions | 请仓库维护者检查你的权限和组织策略 |
| 上传 ZIP 后只有下载入口 | 解压后把包内文件按上述结构上传到仓库根目录 |

工作流依据：[GitHub 官方自定义 Pages 工作流说明](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。
