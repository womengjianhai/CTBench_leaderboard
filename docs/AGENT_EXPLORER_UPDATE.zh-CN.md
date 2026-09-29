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
- **效率指标**来自本地运行记录，页面明确标记为 `Local measurements`，不声称与论文 Table 5 属于同一批实验。各 Harness 的轮次、Token 统计定义及数据覆盖率可能不同，应同时阅读定义和有效样本数。缺失值不按零处理，也不宜据此直接做跨 Harness 效率排名。
- **耗时**目前只有 Codex 的记录可提供；其他 Agent 的未验证耗时显示为不可用，不进行推算。
- **演示轨迹**目前是各 Agent 共用的合成示例，使用虚构设备和文档专用 IP 地址。它们说明页面如何展示诊断过程，**不是任何真实 Agent 的运行表现，也不是 Benchmark 原题或论文证据**。

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

Agent 以 **`harness` + `model`** 精确匹配论文榜单，大小写和拼写都应一致。不能只按模型名匹配，也不能把某个 Agent 的轨迹挂到其他 Agent 名下。顶层 `examples.rca` / `examples.path` 是共用的合成示例；真实运行示例应放在相应 Agent 自己的 `examples` 下。

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
