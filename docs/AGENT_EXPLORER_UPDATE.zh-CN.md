# Agent 详情与轨迹展示更新

这份增量包用于更新现有主页仓库 **womengjianhai/CTBench_leaderboard**。更新后，点击榜单中的 Agent，即可切换 RCA / Path Restoration，查看完整评分、交互轮次、耗时、Token 用量和任务演示。主页的 GitHub 入口继续指向框架仓库 **https://github.com/netopt-team/ctbench**。

## 上传与部署

1. 解压更新包，保留以下相对路径。上传的是文件内容，不是 ZIP；不要额外套一层文件夹。

   ```text
   website/index.html
   website/assets/styles.css
   website/assets/app.js
   website/assets/agent-details.js
   results/published/agent-details.json
   scripts/build_site.py
   tests/test_site_build.py
   docs/AGENT_EXPLORER_UPDATE.zh-CN.md
   ```

2. 在 [主页仓库](https://github.com/womengjianhai/CTBench_leaderboard) 的根目录选择 **Add file → Upload files**，按上述路径更新文件，提交到当前默认分支。其余已有文件继续保留，特别是 `results/published/paper-v1.json`、`website/site-config.json` 和 `.github/workflows/pages.yml`。
3. 本次不需要上传或新建工作流，也不需要再次配置 Pages。提交后，现有工作流自动构建并部署；在 **Actions** 查看此次运行。如果没有触发，可打开现有工作流并选择 **Run workflow**。
4. 等待构建和部署成功后，打开 **https://womengjianhai.github.io/CTBench_leaderboard/**，按 `Ctrl + F5` 刷新。检查绿色图示与页面的对齐，点击一个 Agent，再切换 RCA / Path Restoration，确认评分、效率指标及演示步骤均可查看。

如果构建失败，先查看 Actions 中的错误行。常见原因是缺少新文件、文件上传到了额外的外层目录，或 JSON 内容不符合校验规则。不要通过删除校验来跳过数据问题。

## 页面数据的含义

- **正式评分**仍来自论文 Table 5，由 `results/published/paper-v1.json` 提供；本次不修改榜单分数。
- **效率指标**改为论文 Table 6 的全部 30 个值：5 个 Agent、RCA / Path 两类任务、轮次 / 时延 / Token 三项指标。页面提供直达 Table 6 的链接。
- **精度与单位**按论文保留：轮次和秒数保留两位小数，Token 保留 `k` 单位（一千 Token）。论文未明确给出效率指标的 mean / median 标签、标准差或遥测覆盖率，因此不再显示本地统计的均值、覆盖数和缺失值。
- **参考题目与轨迹**：合成演示已移除。真实题目与对应专家参考步骤需要明确公开授权后再加入；未发布时页面显示 `Example pending`。
- **轨迹归属**：专家 golden steps 使用 `Expert reference trace` 标签，不能标为某个 Agent 的实际运行。真实 Agent 运行记录应单独匹配 Harness、模型、任务与运行来源。

## 更新论文效率指标或共享参考题

效率数据位于 `results/published/agent-details.json` 的 `agents[].efficiency`，来源为顶层 `efficiencySource`。`value` 保存数值，`displayValue` 保存论文显示精度，例如 `476.5k` 对应 `476500`；构建会验证两者一致。论文条目使用 `aggregation: "paper-reported"`，未披露的 `observed` / `total` 保留 `null`，不要用数据集题数填充遥测覆盖率。

获准公开后，共享专家参考题写入顶层 `examples.rca` / `examples.path`，使用 `kind: "reference"`，不可填写 `harness` / `model` 伪装成 Agent 轨迹。来源链接固定到 GitHub commit；步骤只展示原有命令、对应输出节选和原参考注释。没有提供原始输出时应显示缺失说明，不生成模拟输出。

## 替换为已批准公开的真实示例

请为每个准备展示的 Agent 分别提供一条 RCA 和一条 Path Restoration 示例；也可以先提供部分 Agent。每条示例需要：

1. Agent 的 Harness 和模型名称、任务类型，以及题目内容。
2. 可追溯的任务 ID、运行 ID 或其他来源标识。
3. 按实际执行顺序整理的工具调用、对应输出或观察，以及简短的诊断动作说明。
4. 最终答案；如需展示该样本的耗时、轮次或 Token，另外提供统计定义和原始计数来源。
5. 对该题目、工具输出、答案及来源说明的**明确公开授权**；先移除凭据、个人信息及不准备公开的数据。

无需提供原始私密思维过程。简短说明只需描述可观察的动作，例如“检查接口状态”“根据路由表确定下一跳”。

真实示例写入 `results/published/agent-details.json` 中对应的 `agents` 条目：

```text
agents[对应 Agent].examples.rca
agents[对应 Agent].examples.path
```

Agent 以 **`harness` + `model`** 精确匹配论文榜单，大小写和拼写都应一致。不能只按模型名匹配，也不能把某个 Agent 的轨迹挂到其他 Agent 名下。顶层 `examples.rca` / `examples.path` 是共用的专家参考题；真实 Agent 运行示例应放在相应 Agent 自己的 `examples` 下。

以下仅为字段模板；请替换内容并取得授权后，再把 `publicationApproved` 改为 `true`：

```json
{
  "kind": "recorded",
  "id": "待填：可追溯的示例 ID",
  "harness": "Codex",
  "model": "GPT-5.5",
  "publicationApproved": false,
  "sourceNote": "待填：任务 ID、运行 ID、记录来源及公开授权说明",
  "title": "待填：示例标题",
  "question": "待填：已批准公开的题目",
  "steps": [
    {
      "title": "待填：步骤标题",
      "command": "待填：实际工具调用或命令",
      "observation": "待填：对应工具结果或观察",
      "summary": "待填：简短、可观察的诊断动作说明"
    }
  ],
  "finalAnswer": "待填：该次运行的最终答案"
}
```

构建脚本会检查真实示例的 `publicationApproved` 必须为 `true`，`harness` / `model` 必须与所属 Agent 一致，且 `sourceNote` 非空；题目、答案和步骤也必须完整。该校验只检查声明和格式，不代替实际的内容审阅与授权。不要将模板占位内容作为正式示例提交。

以后只更新已有 Agent 的示例或效率指标时，修改 `results/published/agent-details.json` 并提交即可。效率指标同时保留 `definition`、`unit`、`observed`、`total`；不可用指标使用 `value: null` 并写明原因，正式评分继续独立维护。
