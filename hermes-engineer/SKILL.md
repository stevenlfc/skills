---
name: hermes-engineer
description: |
  通用 AI 开发交付流程。读取项目 AGENTS.md 获取上下文，按 5 阶段推进：
  准备→需求理解→技术方案→开发验证→交付测试。
  适用于所有已完成'Hermes 换装'（有 AGENTS.md）的项目。
  触发词（中文）：
  - 走开发流程、拉分支开发、提交到 test、合到 test
  - ONES 开发、需求开发、新需求
  - hermes engineer、AI 开发流程
version: 1.0.0
tags: [beike, hermes]
---

# Hermes Engineer — 通用 AI 开发交付流程

## 设计哲学

**一套流程，适配所有项目。** 项目专属配置留在 `AGENTS.md`，流程逻辑留在本 skill。

启动时读取项目根目录的 `AGENTS.md`，获取：
- 项目基本信息和关键规则
- 上下文文档路径（routes / api-registry / devops）
- 研发流程约定

## 前置条件

项目必须已完成「Hermes 换装」，即仓库根目录存在 `AGENTS.md`。

```bash
# 检查
test -f AGENTS.md && echo "✓ 已就绪" || echo "✗ 请先完成项目换装"
```

## Step 0 — 环境检查（前置）

**目标**：确认项目已就绪，AGENTS.md 存在。

**步骤**：

1. **检查 AGENTS.md**
   ```bash
   test -f AGENTS.md && echo "✓ 已就绪" || echo "✗ 请先完成项目 Hermes 换装"
   ```
   如文件不存在 → 停止，提示用户先完成换装（参考「存量项目AI换装验收标准」）

2. **读取 AGENTS.md** — 用 `read_file AGENTS.md` 获取项目上下文
   - 项目基本信息和技术栈
   - 关键规则（分支策略、commit 格式、禁止操作）
   - 上下文文档路径（routes / api-registry / devops / patterns）
   - 编译/部署命令

3. **确认 Git 状态**
   ```bash
   git status --short
   ```
   - 工作区干净？→ 继续
   - 有未提交改动？→ 先 stash 或提交，避免后续操作冲突

---

## 5 阶段流程

### Stage 1 — 准备

**目标**：保存需求原文，创建运行目录。

**步骤**：

1. **读取 AGENTS.md** — 用 `read_file AGENTS.md` 获取项目上下文和规则
2. **读取需求** — 支持多种来源：
   - ONES: 用 `web-fetcher` 抓取 `ones.ke.com/project/requirement/{id}`
   - 飞书: 用 `lark-cli` 或 `understanding-biz-requirements` skill
   - Wiki: 用 `wiki-lianjia` skill 或 Python 脚本
3. **创建运行目录** — `docs/agent-flow/runs/{需求ID}/`（如需求来自 ONES，ID 为 ONES 单号）
4. **输出产物** — `需求记录.md`，内容：

```markdown
# 需求记录：[标题]

## 需求来源
- 链接：[URL]
- 提出人：@某人
- 时间：YYYY-MM-DD

## 需求原文（摘要）
[关键内容]

## 改动范围初判
- 涉及模块：
- 涉及接口：
- 涉及表：
```

---

### Stage 2 — 需求理解

**目标**：确认需求没有误解，梳理改动范围。

**步骤**：

1. **深度分析需求**
   - 理解业务流程（"应"是什么）
   - 对照现有代码（"实"是什么）
   - 定位涉及模块和文件
   - 参照已有类似实现（先看有没有可复用的模式）

2. **列出待确认事项** — 补充到 `需求记录.md` 的「待确认事项」章节

3. **输出改动范围** — 补充到 `需求记录.md`：

```markdown
## 改动范围分析
- 涉及模块：fmp-book-xxx
- 涉及文件：
  - Controller: XxxController.java
  - Service: XxxBookService.java / XxxBookDirectService.java
  - Builder: XxxBookDirectRecordBuilder.java
  - SPI: XxxSpi.java
- 参照先例：YyyBookService.java

## 待确认事项
1. [ ] ...
2. [ ] ...

## 需求理解确认（门禁 1）
- 确认人：
- 确认时间：
- 确认结论：
```

4. ⚠️ **门禁 1 — 需求理解确认**：必须向用户展示理解结果，获得确认后才能进入 Stage 3。

---

### Stage 3 — 技术方案

**目标**：明确改什么、怎么改、怎么验证。

**步骤**：

1. **设计改动方案**
   - 列出每个文件的改动内容
   - 遵循项目现有模式（命名/继承/注解）
   - 考虑边界情况（null safe、异常处理）

2. **确定验证策略**
   - 编译验证：按 AGENTS.md → context/devops.md 中的编译命令
   - 功能验证：如何构造测试数据、调哪个接口

3. **输出产物** — `技术方案.md`：

```markdown
# 技术方案：[标题]

## 改动范围
| 文件 | 改动类型 | 内容 |
|------|---------|------|
| XxxService.java | 新增 | 台账创建核心逻辑 |
| XxxController.java | 新增 | HTTP 接口 |

## 设计要点
- 继承模式：extends AbstractBookService
- 关键字段：[列出]
- 校验规则：[列出]

## 验证策略
- 编译：`mvn compile -pl fmp-book-xxx -am`
- 部署：合 test → Dayu 自动部署
- 功能：POST /api/v2/book/create → 查询台账 → 确认字段

## 方案确认（门禁 2）
- 确认人：
- 确认时间：
- 确认意见：
```

4. ⚠️ **门禁 2 — 技术方案确认**：向用户展示方案，获得确认后才能动手写代码。

---

### Stage 4 — 开发验证

**目标**：按方案最小范围修改，验证通过。

**步骤**：

1. **创建 feature 分支** — 从 AGENTS.md 中获取 base_branch（如无约定，默认基于当前分支）
   ```bash
   git fetch origin
   git checkout --no-track -b YYYYMMDD_topic origin/{base_branch}
   ```
   分支命名：`YYYYMMDD_简要描述`
   ⚠️ 必须加 `--no-track`，防止 feature 分支的 upstream 指向 origin/{base_branch}，避免 commit 被意外推送到基准分支。

2. **按方案实现代码**
   - 最小范围修改，不改无关文件
   - 遵循项目命名/继承/注解约定
   - 中文注释说明背景和参照
   - 参照先例保持一致性
   - **每新增文件执行 `git add`**

3. **编译验证** — 从 AGENTS.md → context/devops.md 获取编译命令
   ```bash
   # 按需编译改动模块
   {compile_cmd} -pl {changed_module} -am
   ```
   - **本次改动引入的编译错误** → 必须修复
   - **依赖缺失（lombok/ke.cio 等环境问题）** → 不阻塞

   ⚠️ 编译报错时先做**错误分类**，不要盲目修：
   ```bash
   # 过滤掉已知环境错误，看剩余是否与改动相关
   mvn compile ... 2>&1 | grep ERROR | grep -v "程序包\|找不到符号\|lombok\|ke.cio\|fastjson"
   ```
   如果剩余 ERROR 涉及你改动的文件 → 是代码问题，必须修。
   如果全是依赖缺失 → 环境问题，不阻塞 Dayu 部署。
   
   另外注意检查项目是否指定了非默认 Maven settings（如 `-s ~/.m2/settings2.xml`），用错 settings 会导致依赖解析失败。

4. **提交**（含产物文档）
   ```bash
   git add {changed_files} docs/agent-flow/runs/{需求ID}/
   git commit -m "[需求][{id}]{标题}
   
   {改动要点}"
   ```
   提交格式从 AGENTS.md 中的 commit_format 约定获取。
   ⚠️ 产物文档（需求记录/技术方案/验证报告）必须随代码一起提交，不能留为 untracked。

5. **输出产物** — `验证报告.md`：

```markdown
# 验证报告：[标题]

## 代码检查
- 编译：{结果}
- 改动文件数：{N}

## 功能验证
1. 场景A：
   - 操作：
   - 结果：
   - 结论：通过/不通过

## 已知风险
- [ ] ...
```

---

### Stage 5 — 交付测试

**目标**：部署到测试环境，验证功能，沉淀经验。

**步骤**：

1. **推送 + 合并到 test**
   ```bash
   git push origin {branch}
   git checkout {target_branch}
   git pull origin {target_branch}
   git merge {branch} --no-ff -m "[需求][{id}]{标题}"
   git push origin {target_branch}
   ```

2. **部署** — 从 AGENTS.md → context/devops.md 获取部署方式（Dayu / K8s / 其他）

3. **测试环境验证**
   - 功能正确性
   - 不影响已有功能

4. **输出产物** — `交付总结.md`：

```markdown
# 交付总结：[标题]

## 交付物
- 分支：{branch_name}
- Commit：{hash}
- MR 链接：
- 部署时间：

## 遇到的问题与解决
1. **问题**：
   **解决**：
   **经验**：

## 上线确认（门禁 3）
- 回滚方案：
- 确认人：
- 确认时间：
```

5. ⚠️ **门禁 3 — 上线前确认**：确认回滚方案后上线。

6. **ONES 留痕** — 使用 `ones-comment` skill 将改动概要贴到对应 ONES 需求单。

---

## 人工门禁（不可跳过）

| 门禁 | 位置 | 作用 | 执行方式 |
|------|------|------|---------|
| 需求理解 | Stage 2 → 3 | 防止误解需求 | 向用户展示「待确认事项+改动范围」，用户回复确认 |
| 技术方案 | Stage 3 → 4 | 防止方案不合理 | 向用户展示「改动文件清单+验证策略」，用户回复确认 |
| 上线前 | Stage 5 最后 | 防止无回滚方案 | 向用户展示「回滚方案」，用户回复确认 |

门禁执行方式：Agent 输出确认内容 → 用户回复「确认」/「有问题：xxx」

## 产物目录结构

```
docs/agent-flow/runs/{需求ID}/
├── 需求记录.md       ← Stage 1-2 输出
├── 技术方案.md       ← Stage 3 输出
├── 验证报告.md       ← Stage 4 输出
└── 交付总结.md       ← Stage 5 输出
```

## 停机条件（以下情况暂停流程）

| 条件 | 处理 |
|------|------|
| 工作区有冲突性未提交改动 | `git stash` 暂存后再继续 |
| ONES/需求页面抓取失败 | 检查 SSO 认证，确认网络可达 |
| merge 冲突 | 手动解决冲突后再继续，不要盲目选一方 |
| 部署超时未完成（>15 分钟） | 检查 Dayu 构建日志，排查编译/镜像问题 |
| AGENTS.md 不存在 | 停止，提示用户先完成项目 Hermes 换装 |
| 用户说「先别改造」「停」 | 立刻停止代码操作，只讨论方案 |

## 关键规则（全流程遵守）

1. **先理解再动手** — 不要看到需求就直接改代码。Stage 2 必须做充分。
2. **最小改动** — 不改无关文件，不做「顺手重构」。
3. **参照先例** — 先搜项目中类似实现，保持一致性。
4. **门禁不跳过** — 3 个门禁必须执行，不可省略。
5. **产物齐全** — 每个 Stage 的输出文件要及时写，不要事后补。**产物文档必须 git add 随代码一起提交，不能留为 untracked。**
6. **改动前先确认** — 用户说「先别改造」时立刻停止，只讨论方案。

## 与项目 AGENTS.md 的协作

本 skill 不硬编码任何项目信息。以下信息从 AGENTS.md 获取：

| 需要的信息 | 来源 |
|-----------|------|
| 项目基本信息、技术栈 | AGENTS.md → 项目基本信息 |
| 编译命令 | AGENTS.md → context/devops.md |
| 分支策略 | AGENTS.md → context/devops.md |
| 部署方式 | AGENTS.md → context/devops.md |
| 接口路由 | AGENTS.md → context/routes.md |
| API 约定 | AGENTS.md → context/api-registry.md |
| Commit 格式 | AGENTS.md → 关键规则 |

## 常用子流程

以下子流程由本 skill 衍生，可按需触发：

- **understanding-biz-requirements** — 解析业财需求文档（飞书/wiki）
- **fmp-book-dev-flow** — fmp-book 专属流程（**已废弃，被本 skill 替代**）
- **accounting-dev-flow** — accounting 专属流程（**已废弃，被本 skill 替代**）
- **ones-comment** — ONES 留痕
- **dayu-deploy-guard** — Dayu 部署检查

## 参考文档

- [记账失败二次确认告警排查](references/debugging-accounting-failure-alerts.md) — 收到「记账失败二次确认汇总」企微告警时的排查与修复模式
