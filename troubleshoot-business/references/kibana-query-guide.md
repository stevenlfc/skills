# Kibana 日志查询向导

本文件是查询 Kibana/Elasticsearch 日志系统的参数指南。独立维护，可单独更新。

---

## 会话隔离（多 agent 并发）

每个 agent 执行时必须指定 `--session <session_id>`，结果保存到 `temps/<session_id>/` 子目录，清理时也只清自己的子目录，不影响其他并发 agent。

session_id 使用当前会话的唯一标识前8位，格式如 `sess_abc12345`。

---

## 核心流程：探测 → 查询 → 分析

四个步骤，两个脚本配合使用：

```
第0步: 读取 Kibana 配置  →  从 kibana-config.json 获取 fastUrlPre 和 index
第1步: 探测字段结构     →  kibana_query.py --discover     →  终端输出
第2步: 查询并保存结果   →  kibana_query.py (默认)          →  temps/<hash>.log
第3步: 分析结果文件     →  kibana_analyze.py               →  终端输出
第4步: 清理临时文件     →  kibana_analyze.py --clean
```

**不同服务的 `_source` 字段结构可能不一致**，不能假设字段名。必须先探测再查询。

---

## 查询策略：追踪字段优先，降级兜底

**核心原则**：无论代码中是否存在异步模式，都**优先用追踪字段（TID/SID）查询**。只有当追踪字段查询无法定位问题时，才降级到业务ID/关键字模糊查询。

```
第一步（优先）：用追踪字段（TID/SID）查询 → 拉出完整链路 → 分析
                                                    ↓ 无法定位
第二步（降级）：用 SID 查询（跨线程场景 SID 通常不变）
                                                    ↓ 仍无法定位
第三步（兜底）：用业务ID + 关键字模糊查询 → 缩小范围 → 人工分析时序
```

### 第一步：追踪字段优先（始终执行）

**核心思路**：先用业务ID查到一条关键日志 → 提取其追踪字段 → 用追踪字段拉出完整链路。

```
业务ID 查询 → 命中关键日志 → 提取 TID/SID → 追踪字段查询 → 完整请求链路
```

**优势**：
- 追踪字段（如 TID）是请求级别的唯一标识，能精确拉出同一请求的所有日志
- 避免业务ID匹配到大量无关日志
- 一次追踪即可看到完整的调用链路，包括跨服务的日志

**操作步骤**：
1. 用业务ID + 入口日志文本查询，命中关键日志
2. 用 `--mode traces` 提取追踪字段
3. **立即用追踪字段发起第二次查询**（不等用户指示）：
   ```bash
   python scripts/kibana_query.py \
     --server <fastUrlPre> --index "<index>" \
     --filter 'match_phrase:<追踪字段>:<TID值>' \
     --minutes 30
   ```
4. 用 `--mode chain` 分析链路，查看完整请求流程

### 第二步：降级 — 用 SID 查询（跨线程场景）

**触发条件**：第一步用 TID 查询后，发现日志链路不完整（缺失异步线程中的日志），且代码分析检测到异步模式。

**原因**：异步执行时，TID 会在提交到线程池时发生变化，导致主线程和子线程的 TID 不同。但 SID 通常在请求级别保持不变。

**操作**：
```bash
python scripts/kibana_query.py \
  --server <fastUrlPre> --index "<index>" \
  --filter 'match_phrase:SID:<SID值>' \
  --minutes 30
```

### 第三步：兜底 — 业务ID + 关键字模糊查询

**触发条件**：前两步都无法定位问题（如 TID/SID 都查不到、结果为空或无法分析）。

**操作**：
- **用业务ID查询**：业务ID（如订单号、用户ID）贯穿整个业务流程，不受线程影响
- **用 `should` 组合多个追踪字段**：
  ```bash
  python scripts/kibana_query.py \
    --server <fastUrlPre> --index "<index>" \
    --filter 'should:<追踪字段1>:<值1>,<值2>' \
    --minutes 30
  ```
- **按时间窗口 + 业务ID**：缩小时间范围，用业务ID 查出所有相关日志，再人工分析时序
- **用 `--mode search` 搜索关键字**：在结果中搜索代码分析阶段发现的分支日志关键字

### 异步模式识别（供参考）

代码中出现以下模式时，TID 可能无法串联完整链路，但**仍优先用 TID 查询**，查不出再降级：
- `@Async` 注解的方法
- `CompletableFuture.supplyAsync()` / `runAsync()`
- `ExecutorService.submit()` / `execute()`
- `ThreadPoolTaskExecutor`
- `new Thread()` / `Runnable`
- `parallelStream()`

---

## 第1步：探测字段结构

```bash
python scripts/kibana_query.py --server <前缀> --index "<索引>" --discover
```

探测查询最近 5 分钟的数据，分析 `_source` 中的所有字段，输出：
- **内容字段** — 日志正文/业务数据（如 `logDetail`、`data`、`message`、`msg`）
- **追踪字段** — 链路追踪ID（如 `TID`、`SID`、`traceId`）
- **元数据字段** — 日志级别、类名、主机等
- **查询建议** — 用哪个字段搜索、用哪个字段追踪

---

## 第2步：查询并保存结果

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:logDetail:2000000168999804' \
  --minutes 30
```

**默认行为**：
- 查询结果保存到 `temps/<hash>_<时间>.log`（JSON 格式，包含请求参数+响应）
- 终端只打印文件路径和统计信息
- 同一查询参数不会重复创建文件（hash 相同会覆盖）

**可选参数**：
- `--print` — 保存文件的同时在终端打印摘要
- `--stdout` — 直接输出到终端，不保存文件（兼容旧用法）
- `--out <路径>` — 指定输出文件路径

### 查询参数说明

| 参数 | 说明 | 必填 |
|------|------|------|
| `--session` | 会话ID，如 `sess_abc12345`，隔离多 agent 的 temps 子目录 | 否 |
| `--server` | 服务器前缀，如 `fast107` | 是 |
| `--index` | ES 索引，如 `index-12961-13160*` | 是 |
| `--filter` | filter 条件，可多次使用 | 否 |
| `--must-not` | must_not 排除条件，可多次使用 | 否 |
| `--query-string` | must 中的全文搜索关键字 | 否 |
| `--minutes` | 查询最近 N 分钟，默认 30 | 否 |
| `--start` | 开始时间（UTC） | 否 |
| `--end` | 结束时间（UTC） | 否 |
| `--cookie` | Cookie 字符串 | 否 |
| `--size` | 返回条数，默认 1500 | 否 |

### filter 格式

- `match_phrase:字段:值` — 精确匹配
- `should:字段:值1,值2` — OR 条件
- `exists:字段` — 字段存在

### must_not 格式

- `match_phrase:字段:值` — 排除匹配
- `exists:字段` — 排除字段存在

---

## 第3步：分析结果文件

```bash
# 查看摘要（默认）
python scripts/kibana_analyze.py temps/<hash>_<时间>.log

# 提取所有追踪ID
python scripts/kibana_analyze.py temps/<hash>_<时间>.log --mode traces

# 字段值统计
python scripts/kibana_analyze.py temps/<hash>_<时间>.log --mode stats

# 搜索关键字（高亮显示）
python scripts/kibana_analyze.py temps/<hash>_<时间>.log --mode search --keyword "无id字段"

# 按追踪ID分组展示日志链路
python scripts/kibana_analyze.py temps/<hash>_<时间>.log --mode chain
```

### 分析模式说明

| 模式 | 用途 | 示例场景 |
|------|------|----------|
| `summary`（默认） | 每条日志的摘要：时间、级别、类名、TID、消息 | 首次查看结果 |
| `traces` | 提取所有不重复的 TID/SID | 找到追踪ID用于下一步查询 |
| `stats` | 每个字段的值分布统计 | 了解日志级别分布、哪些类在输出日志 |
| `search` | 按关键字搜索，高亮匹配 | 在大量日志中找特定信息 |
| `chain` | 按 TID 分组，按时间排序展示链路 | 追踪一个请求的完整处理流程 |

### 文件管理

```bash
# 列出所有结果文件
python scripts/kibana_analyze.py --list

# 清理所有结果文件（删除 temps/ 目录）
python scripts/kibana_analyze.py --clean
```

---

## 完整排查流程示例

### 第0步：询问环境 & 读取 Kibana 配置

**首先询问用户要查询哪个环境**（prd/pre/test），然后将服务名与环境后缀拼接去匹配配置。

```bash
# 读取配置文件（优先级：项目目录 > 当前目录 > skill 默认配置）
Read <项目目录>/kibana-config.json
# 或
Read <skill>/references/kibana-config.json
```

配置文件示例（键名格式为 `[服务名]-[环境]`）：
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

匹配逻辑：服务名 `huiju-house-cloudkeeper` + 环境 `prd` → 查找键名 `huiju-house-cloudkeeper-prd`

如果配置文件中没有目标服务，需要询问用户输入并追加到配置文件。

### 第1步：探测

```bash
python scripts/kibana_query.py --server fast107 --index "index-12961-13160*" --discover
```

输出告诉我们：内容字段是 `logDetail`，追踪字段是 `TID` 和 `SID`。

### 第2步：查询入口日志

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:logDetail:2000000168999804' \
  --filter 'match_phrase:logDetail:SessionAssignStatusChangeConsumer received msg' \
  --minutes 30
```

输出：`结果已保存到: temps/36af0e23d11f_20260603_205906.log`

### 第3步：分析结果

```bash
# 先看摘要
python scripts/kibana_analyze.py temps/36af0e23d11f_20260603_205906.log

# 提取追踪ID
python scripts/kibana_analyze.py temps/36af0e23d11f_20260603_205906.log --mode traces

# 搜索特定关键字
python scripts/kibana_analyze.py temps/36af0e23d11f_20260603_205906.log --mode search --keyword "sessionStatus"
```

### 第4步：用 TID 追踪链路

```bash
# 查询 TID 相关的所有日志
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:TID:511686-10.226.98.31-528-1780491522630-8919' \
  --minutes 30

# 分析链路
python scripts/kibana_analyze.py temps/<新文件名>.log --mode chain
```

### 第5步：清理

```bash
python scripts/kibana_analyze.py --clean
```

---

## 接口概述

### URL 模板

```
https://<SERVER_PREFIX>-kibana-logcenter-intra.intra.ke.com/internal/search/es
```

- `<SERVER_PREFIX>`：服务器前缀，如 `fast101`、`fast107`
- **优先从配置文件读取**，如果配置文件中没有则询问用户

### Cookie

默认不带 Cookie。如果请求失败（401/403），询问用户提供 Cookie。

---

## Kibana 配置文件

### 配置文件位置

按以下优先级查找 `kibana-config.json`：

1. 用户提供的项目目录下的 `kibana-config.json`
2. 当前工作目录下的 `kibana-config.json`
3. 默认配置：`<skill>/references/kibana-config.json`

### 配置文件格式

键名格式为 `[服务名]-[环境]`，如 `huiju-house-cloudkeeper-prd`：

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

查询时将服务名（从代码目录提取）与用户选择的环境（prd/pre/test）拼接后匹配键名。

### 配置读取流程

1. 调用 `AskUserQuestion` 询问用户要查询的环境（prd/pre/test）
2. 使用 `Read` 工具读取配置文件
3. 将服务名称与环境后缀拼接（如 `huiju-house-cloudkeeper` + `-prd` → `huiju-house-cloudkeeper-prd`），在配置中查找对应的 `fastUrlPre` 和 `index`
4. 如果未找到配置：
   - 询问用户输入 `fastUrlPre` 和 `index`
   - **配置文件存在**：使用 `Edit` 工具追加新配置，键名为 `[服务名]-[环境]`
   - **配置文件不存在**：使用 `Write` 工具在用户指定目录或当前目录创建 `kibana-config.json`，写入包含新服务配置的完整 JSON
5. **【强制写回规则】**：只要本次排查中获取到了 `fastUrlPre` 和 `index` 信息（无论是从配置文件读取还是用户手动输入），且配置文件中**不存在**对应的 `[服务名]-[环境]` 键，**必须**执行写回操作，确保切换环境后新配置被持久化。
6. 使用获取到的配置进行查询

---

## 需要用户提供的参数

1. **服务器前缀** — 如 `fast107`，不同前缀对应不同服务器（优先从配置文件读取）
2. **ES 索引** — 如 `index-12961-13160*`，通常以 `index-` 开头，`*` 结尾（优先从配置文件读取）

---

## 查询条件类型 (query.bool)

### must — 必须匹配

```json
{"match_all": {}}
```

```json
{"query_string": {"query": "\"关键字1\" and \"关键字2\"", "analyze_wildcard": true, "time_zone": "Asia/Shanghai"}}
```

### filter — 过滤条件（AND 关系）

**match_phrase** — 精确匹配：
```json
{"match_phrase": {"logDetail": "2000000168999804"}}
{"match_phrase": {"TID": "511686-10.22.64.181-566-1780485018037-4641"}}
```

**range** — 时间范围：
```json
{"range": {"timestamp": {"gte": "2026-06-03T10:41:10.904Z", "lte": "2026-06-03T11:11:10.904Z", "format": "strict_date_optional_time"}}}
```

**bool.should** — OR 条件：
```json
{"bool": {"should": [{"match_phrase": {"logLevel": "ERROR"}}, {"match_phrase": {"logLevel": "WARN"}}], "minimum_should_match": 1}}
```

### must_not — 排除

```json
{"match_phrase": {"TID": "222"}}
{"exists": {"field": "deprecated_field"}}
```

---

## 常见 _source 字段参考

不同服务的字段名可能不同，先用 `--discover` 探测确认。

| 分类 | 常见字段名 |
|------|-----------|
| 内容字段 | `logDetail`, `data`, `message`, `msg`, `info`, `warring`, `warning`, `error`, `logMsg`, `content` |
| 追踪字段 | `TID`, `SID`, `SpanID`, `traceId`, `spanId`, `trace_id`, `requestId` |
| 元数据字段 | `logLevel`, `logClass`, `host_name`, `hostname`, `timestamp`, `@timestamp`, `level`, `logger` |

### logDetail 格式

```
日期 时间 [TID:xxx] [SID:xxx][SpanID:xxx] [线程名] 级别 类名- 日志内容
```

---

## 返回结果结构

```json
{
  "rawResponse": {
    "hits": {
      "total": 2,
      "hits": [
        {
          "_source": {
            "logLevel": "WARN",
            "logDetail": "...",
            "TID": "...",
            "SID": "...",
            "timestamp": "..."
          }
        }
      ]
    }
  }
}
```
