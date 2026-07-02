---
name: troubleshoot-business
description: "排查业务问题的 skill。当用户描述一个业务异常现象（如某用户操作失败、某个流程没走通、数据状态不对），需要分析代码逻辑或查询日志定位原因时使用。触发关键词：排查、问题定位、为什么没、为什么没有、为啥没、为啥没有、分析问题、查看日志、查日志、业务问题、定位问题、troubleshoot、debug 业务。即使用户没有明确说'排查'，只要在描述一个需要定位原因的业务异常，就应该触发。"
---

# 排查业务问题

帮助用户从代码逻辑和日志系统两个维度排查业务问题。

## 向导文件

- `references/code-analysis-guide.md` — 代码逻辑分析指南
- `references/kibana-query-guide.md` — Kibana 日志查询完整指南
- `references/workflow-examples.md` — 排查流程示例

## 工具脚本

- `scripts/kibana_query.py` — 查询日志，结果保存到 `temps/<hash>.log`
- `scripts/kibana_analyze.py` — 分析结果文件，支持多种分析模式

---

## 排查流程

### 阶段一：理解问题

1. 记录用户描述的业务现象（什么用户、什么操作、期望结果 vs 实际结果）
2. 提取关键信息：业务ID、时间、服务名称等

### 阶段二：代码逻辑分析

**先读取向导**：读取 `references/code-analysis-guide.md` 获取详细指南。

1. **【必须执行】询问用户代码目录** — 必须调用 `AskUserQuestion` 工具，不可跳过、不可默认使用当前目录：
   ```
   AskUserQuestion({
     questions: [{
       question: '请提供需要分析的代码目录路径（绝对路径或相对路径均可）：',
       header: '代码目录',
       options: [
         { label: '当前工作目录', description: '<当前工作目录路径>' },
         { label: '自定义路径', description: '手动输入代码目录路径' }
       ],
       multiSelect: false
     }]
   })
   ```
   - 用户选了"自定义路径" → 要求用户输入具体路径
   - 用户选了"当前工作目录" → 使用当前工作目录

2. **【重要】提取服务名称**：从代码目录路径中提取最后一个文件夹名作为服务名称
   - 例如：`/home/user/projects/huiju-house-cloudkeeper` → 服务名为 `huiju-house-cloudkeeper`
   - 记录此服务名，用于阶段三的 Kibana 配置查询

3. **检查 codegraph 工具是否可用**：
   - 检测当前环境是否有 `codegraph` 相关工具（如 CodeGraph MCP server）
   - 如果**没有** codegraph，**必须**向用户展示以下提示（不可跳过、不可简化）：
     > 💡 当前环境未检测到 CodeGraph 代码图谱工具。CodeGraph 基于 tree-sitter 解析代码结构，可以毫秒级定位符号定义、调用关系和影响范围，比 grep 搜索更快更准确。
     > 如果需要安装，可以运行：`npm install -g @anthropic/codegraph`，然后在项目目录执行 `codegraph init -i` 初始化索引。
     > 当前将使用 grep/glob 等基础工具继续分析，功能不受影响，只是搜索效率会低一些。
   - 如果**有** codegraph → 优先使用 codegraph 进行结构性搜索（符号查找、调用链追踪等）
4. 使用可用工具（codegraph、grep、glob 等）定位业务入口
5. 分析入口方法的完整逻辑，找到入口日志文本
6. 梳理所有可能的分支路径（正常/跳过/异常）
7. 输出结构化的分析结论

### 阶段三：日志查询与分析

**先读取向导**：读取 `references/kibana-query-guide.md`。

**重要**：不同服务的 `_source` 字段结构可能不一致，必须先探测再查询。

**Step 0 — 读取 Kibana 配置**（必须）：

1. **询问查询环境**：在读取配置文件之前，必须先调用 `AskUserQuestion` 询问用户要查询哪个环境：
   ```
   AskUserQuestion({
     questions: [{
       question: '请确认要查询哪个环境的日志？',
       header: '查询环境',
       options: [
         { label: '生产环境 (prd)', description: '查询生产环境的日志' },
         { label: '预发环境 (pre)', description: '查询预发环境的日志' },
         { label: '测试环境 (test)', description: '查询测试环境的日志' }
       ],
       multiSelect: false
     }]
   })
   ```
   记录用户选择的环境后缀（如 `prd`、`pre`、`test`）。

2. **查找配置文件**：按以下优先级查找 `kibana-config.json`：
   - 用户提供的项目目录下的 `kibana-config.json`
   - 当前工作目录下的 `kibana-config.json`
   - 默认配置：`<skill>/references/kibana-config.json`

3. **读取配置**：使用 `Read` 工具读取找到的配置文件，格式示例：
   ```json
   {
       "huiju-cloudkeeper-core-prd": {
           "fastUrlPre": "fast107",
           "index": "index-12961-13160*"
       },
       "huiju-house-cloudkeeper-prd": {
           "fastUrlPre": "fast103",
           "index": "index-13762-14164*"
       }
   }
   ```

4. **查找服务配置**：将**阶段二提取的服务名称**与**用户选择的环境后缀**拼接，组成完整的配置键名（如 `huiju-house-cloudkeeper` + `-prd` → `huiju-house-cloudkeeper-prd`），然后在配置中查找对应的 `fastUrlPre` 和 `index`

5. **如果未找到配置**：
   - 调用 `AskUserQuestion` 询问用户输入：
     ```
     AskUserQuestion({
       questions: [{
         question: '配置文件中未找到服务 [服务名-环境] 的 Kibana 配置，请提供：\n1. 服务器前缀（如 fast107）：\n2. ES 索引（如 index-12961-13160*）：',
         header: 'Kibana 配置',
         options: [
           { label: '手动输入', description: '输入 fast 前缀和索引' }
         ],
         multiSelect: false
       }]
     })
     ```
   - 获取用户输入的 `fastUrlPre` 和 `index`
   - **追加到配置文件**：
     - 如果配置文件存在：使用 `Edit` 工具追加新配置，键名为 `[服务名]-[环境]`
     - 如果配置文件不存在（用户指定目录或当前目录下无 `kibana-config.json`）：使用 `Write` 工具创建新文件，写入包含新服务配置的完整 JSON

6. **【强制写回规则】**：只要本次排查中获取到了 `fastUrlPre` 和 `index` 信息（无论是从配置文件读取还是用户手动输入），且配置文件中**不存在**对应的 `[服务名]-[环境]` 键，**必须**执行写回操作。这确保用户切换环境（如 prd → pre/test）后，新环境的配置会被持久化。写回方式同第5点。

7. **使用配置**：将获取到的 `fastUrlPre` 作为 `--server` 参数，`index` 作为 `--index` 参数

**【重要】会话隔离**：每个 agent 在执行查询前，必须确定本次会话的 session ID（使用当前会话的唯一标识，如 `sess_<会话ID前8位>`），所有命令都要带 `--session <session_id>` 参数，确保 `temps/<session_id>/` 目录相互隔离，清理时只清自己的目录。

**Step 1 — 探测字段结构**（必须）：
```bash
python scripts/kibana_query.py --server <前缀> --index "<索引>" --discover --session <session_id>
```
确认：用哪个字段搜索关键字、用哪个字段追踪链路。

**Step 2 — 查询入口日志**（结果自动保存到 `temps/<session_id>/`）：
```bash
python scripts/kibana_query.py \
  --server <前缀> --index "<索引>" \
  --filter 'match_phrase:<内容字段>:<业务ID>' \
  --filter 'match_phrase:<内容字段>:<入口日志文本>' \
  --minutes 30 \
  --session <session_id>
```
输出文件路径，如 `temps/<session_id>/36af0e23d11f_20260603.log`。

**Step 3 — 分析结果文件**：
```bash
# 看摘要
python scripts/kibana_analyze.py temps/<session_id>/<文件名>.log

# 提取追踪ID
python scripts/kibana_analyze.py temps/<session_id>/<文件名>.log --mode traces

# 搜索关键字
python scripts/kibana_analyze.py temps/<session_id>/<文件名>.log --mode search --keyword "无id字段"

# 按追踪ID分组展示链路
python scripts/kibana_analyze.py temps/<session_id>/<文件名>.log --mode chain
```

**Step 4 — 用 TID 追踪链路**（可选）：
```bash
python scripts/kibana_query.py \
  --server <前缀> --index "<索引>" \
  --filter 'match_phrase:<追踪字段>:<TID值>' \
  --minutes 30 \
  --session <session_id>
```
然后再次用 `kibana_analyze.py` 分析新文件。

**4b. 降级 — TID 链路不完整时用 SID 查询**（跨线程场景）：
如果 4a 的链路缺失异步线程中的日志，且代码分析检测到异步模式，改用 SID 查询：
```bash
python scripts/kibana_query.py \
  --server <fastUrlPre> --index "<index>" \
  --filter 'match_phrase:SID:<SID值>' \
  --minutes 30 \
  --session <session_id>
```

**4c. 兜底 — 业务ID + 关键字模糊查询**：
如果前两步都无法定位问题，用业务ID + 关键字缩小范围，人工分析时序。

### 阶段四：综合分析

结合代码分析和日志查询结果，给出结论：

1. **问题原因**：具体是代码中的哪个分支/逻辑导致的
2. **日志证据**：支撑结论的日志内容
3. **建议方向**：下一步可以排查的方向

### 阶段五：清理

```bash
python scripts/kibana_analyze.py --clean --session <session_id>
```

只清理本会话的 `temps/<session_id>/` 子目录，不影响其他 agent。

---

## 注意事项

- **服务名称提取**：自动从用户提供的代码目录路径中提取最后一个文件夹名作为服务名称，用于查询 Kibana 配置
- **环境感知查询**：在读取配置前必须先询问用户查询环境（prd/pre/test），然后将服务名与环境后缀拼接（如 `huiju-house-cloudkeeper-prd`）去匹配配置文件中的键名
- **配置文件优先**：先从 `kibana-config.json` 读取 `[服务名]-[环境]` 对应的 `fastUrlPre` 和 `index`，配置文件中没有时才询问用户
- **配置文件位置**：优先查找项目目录，其次当前目录，最后使用 `<skill>/references/kibana-config.json`
- **自动创建与追加**：用户输入的新配置会自动追加到配置文件中；如果用户指定目录或当前目录下不存在 `kibana-config.json`，会自动创建该文件
- **【强制写回】切换环境必须写入**：当用户切换到配置文件中不存在的环境（如只有 prd 配置，用户要查 pre/test），获取到 fast/index 后**必须立即写回配置文件**，不可跳过。这是最容易遗漏的场景——配置文件中已有该服务的 prd 配置，但没有 pre/test 配置，此时 `serviceName-pre` 未命中，必须走写回流程
- 探测步骤不能跳过，不同服务字段结构不同
- **追踪字段优先，逐步降级**：查到关键日志后，优先用 TID 查询拉出完整链路；TID 链路不完整时降级用 SID；都无法定位时才用业务ID + 关键字模糊查询
- **异步场景不跳过 TID**：即使代码中存在线程池/异步执行，仍优先用 TID 查询，查不出再降级，不要直接跳过
- 查询结果默认保存到文件，不直接输出到终端
- 用 `kibana_analyze.py` 分析结果文件，支持摘要/追踪/统计/搜索/链路 五种模式
- Cookie 默认不带，失败后再询问用户
- 时间默认最近 30 分钟，除非用户明确给了时间
- 如果查询结果为空，尝试放宽条件（如只用业务ID，去掉入口日志条件）
- 多个 `--filter` 条件之间是 AND 关系
- `--must-not` 用于排除条件
- `--filter 'should:字段:值1,值2'` 用于 OR 条件
- 排查结束后用 `--clean` 清理 temps/ 目录
