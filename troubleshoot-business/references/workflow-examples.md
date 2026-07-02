# 排查流程示例

本文件记录完整的排查流程示例，帮助理解 skill 的使用方式。

---

## 示例：用户分配后未创建 sessionId

### 用户提问

> 这个用户 2000000168999804 分配成功后为啥没有创建 sessionId，为啥没有分配成功

### 第一轮：询问服务

**Skill 回复**：基于哪个服务去分析问题？

**用户输入**：huiju-cloudkeeper-core

### 第二轮：代码分析

**Skill 处理**：

1. 扫描代码库 `huiju-cloudkeeper-core`
2. 搜索"分配"、"sessionId"、"Consumer"等关键词
3. 找到入口：`com.ke.huiju.cloudkeeper.entry.mq.SessionAssignStatusChangeConsumer#listen`
4. 分析入口日志：`log.info("SessionAssignStatusChangeConsumer received msg: {}", msgText);`
5. 梳理后续逻辑中的多种跳过情况：
   - 消息数据为空
   - 消息中无 id 字段
   - 非当前业务线的分配事件跳过
   - 会话已处理，跳过
   - 等等...
6. 结论：通过代码无法判断从哪个阶段跳过，需要查询日志

**Skill 回复**：经过代码分析，会话分配事件的入口在 `SessionAssignStatusChangeConsumer#listen`，入口日志为 `SessionAssignStatusChangeConsumer received msg`。后续有多种情况会跳过创建 sessionId，需要查询日志确认。请提供要查询的 ES 的 URL 前缀和索引？

**用户输入**：fast107, index-12961-13160

### 第三轮：日志查询

**Skill 处理**：

1. 读取 `references/kibana-query-guide.md` 获取 Python 脚本用法
2. **先探测字段结构**（不同服务的字段可能不同）：

```bash
python scripts/kibana_query.py --server fast107 --index "index-12961-13160*" --discover
```

探测输出示例：
```
【内容字段】- 日志正文/业务数据
  logDetail (str, 出现 5/5 条)
    样本1: 2026/06/03-20:21:55:796 [TID:xxx] [SID:xxx] ... INFO  com.ke.xxx- 日志内容...

【追踪字段】- 链路追踪ID
  TID (出现 5/5 条)
  SID (出现 5/5 条)

【查询建议】
  可用于搜索业务关键字的字段: logDetail
  追踪链路字段: TID
```

3. 根据探测结果，确认用 `logDetail` 搜索关键字，用 `TID` 追踪链路
4. 构建精准查询命令：

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:logDetail:2000000168999804' \
  --filter 'match_phrase:logDetail:SessionAssignStatusChangeConsumer received msg' \
  --minutes 30
```

输出：`结果已保存到: temps/36af0e23d11f_20260603_205906.log`

5. 用分析脚本查看结果：

```bash
python scripts/kibana_analyze.py temps/36af0e23d11f_20260603_205906.log
```

输出：
```
查询结果分析
文件: temps/36af0e23d11f_20260603_205906.log
服务器: fast107
总记录数: 2，返回: 3
内容字段: logDetail
追踪字段: TID=TID, SID=SID

日志级别分布: {'INFO': 2, 'WARN': 1}

[1] 2026-06-03T19:10:18.037+08:00  [INFO]
    类: SessionAssignStatusChangeConsumer
    TID: 511686-10.22.64.181-566-1780485018037-4641
    日志: SessionAssignStatusChangeConsumer received msg: {
      "data": {"customerBusinessId": "2000000168999804", "sessionStatus": 0, ...}
    }

[2] 2026-06-03T19:10:18.037+08:00  [WARN]
    类: SessionAssignStatusChangeConsumer
    TID: 511686-10.22.64.181-566-1780485018037-4641
    日志: 消息中无id字段，跳过. msg={...}
```

6. 从结果中提取关键信息：
   - `sessionStatus = 0` → 没有分配成功
   - `waitAssignReason = "未找到承接城市匹配的客服组"` → 分配失败原因
   - `TID: 511686-10.22.64.181-566-1780485018037-4641` → 用于链路追踪
   - 第 2 条日志已经是 `消息中无id字段，跳过`，说明已经可以直接定位问题

### 第四轮：日志查询（链路追踪，可选）

如果需要查看更完整的链路，可以用 TID 追踪：

```bash
# 查询 TID 相关的所有日志
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:TID:511686-10.22.64.181-566-1780485018037-4641' \
  --start '2026-06-03T11:05:56.639Z' \
  --end '2026-06-03T11:35:56.639Z'

# 输出: 结果已保存到: temps/7a2b3c4d5e6f_20260603.log

# 分析链路（按 TID 分组，按时间排序）
python scripts/kibana_analyze.py temps/7a2b3c4d5e6f_20260603.log --mode chain

# 搜索特定关键字
python scripts/kibana_analyze.py temps/7a2b3c4d5e6f_20260603.log --mode search --keyword "跳过"
```

### 第五轮：给出结论

**Skill 回复**：

根据代码逻辑分析和日志查询结果：

1. **未创建 sessionId 的原因**：消息中无 id 字段，跳过了创建 sessionId 的逻辑
2. **未分配成功的原因**：`waitAssignReason = "未找到承接城市匹配的客服组"`，说明没有找到匹配的客服组

**建议排查方向**：
- 检查消息发送方为什么没有携带 id 字段
- 检查城市"大连"(cityCode: 210200) 对应的客服组配置是否存在

---

## 查询条件构建示例

### 基本查询：匹配特定业务ID + 入口日志

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:logDetail:2000000168999804' \
  --filter 'match_phrase:logDetail:SessionAssignStatusChangeConsumer received msg' \
  --minutes 30
```

等价的 query.bool：
```json
{
  "must": [{"match_all": {}}],
  "filter": [
    {"match_phrase": {"logDetail": "2000000168999804"}},
    {"match_phrase": {"logDetail": "SessionAssignStatusChangeConsumer received msg"}},
    {"range": {"timestamp": {"gte": "...", "lte": "...", "format": "strict_date_optional_time"}}}
  ]
}
```

### OR 条件：匹配多个日志级别

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:TID:xxx' \
  --filter 'should:logLevel:ERROR,WARN' \
  --minutes 30
```

等价的 query.bool：
```json
{
  "must": [{"match_all": {}}],
  "filter": [
    {"match_phrase": {"TID": "xxx"}},
    {
      "bool": {
        "should": [
          {"match_phrase": {"logLevel": "ERROR"}},
          {"match_phrase": {"logLevel": "WARN"}}
        ],
        "minimum_should_match": 1
      }
    },
    {"range": {"timestamp": {"gte": "...", "lte": "...", "format": "strict_date_optional_time"}}}
  ]
}
```

### 排除条件：排除特定 TID 和字段

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:TID:xxx' \
  --must-not 'match_phrase:TID:222' \
  --must-not 'exists:deprecated_field' \
  --minutes 30
```

等价的 query.bool：
```json
{
  "must": [{"match_all": {}}],
  "filter": [
    {"match_phrase": {"TID": "xxx"}},
    {"range": {"timestamp": {"gte": "...", "lte": "...", "format": "strict_date_optional_time"}}}
  ],
  "must_not": [
    {"match_phrase": {"TID": "222"}},
    {"exists": {"field": "deprecated_field"}}
  ]
}
```

### 全文搜索 + 过滤

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --query-string '"SessionAssign" and "received"' \
  --filter 'match_phrase:TID:xxx' \
  --minutes 30
```

等价的 query.bool：
```json
{
  "must": [
    {"query_string": {"query": "\"SessionAssign\" and \"received\"", "analyze_wildcard": true, "time_zone": "Asia/Shanghai"}}
  ],
  "filter": [
    {"match_phrase": {"TID": "xxx"}},
    {"range": {"timestamp": {"gte": "...", "lte": "...", "format": "strict_date_optional_time"}}}
  ]
}
```

### 指定时间范围

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:TID:xxx' \
  --start '2026-06-03T11:05:56.639Z' \
  --end '2026-06-03T11:35:56.639Z'
```

### 调试模式：只输出查询 JSON 不执行

```bash
python scripts/kibana_query.py \
  --server fast107 \
  --index "index-12961-13160*" \
  --filter 'match_phrase:logDetail:test' \
  --minutes 30 \
  --dump-query
```

---

## 排查流程总结

```
用户提问
  ↓
询问：基于哪个服务？
  ↓
代码分析 → 找到入口 → 分析入口日志 → 梳理分支路径
  ↓
询问：ES URL 前缀和索引？
  ↓
日志查询1：用入口日志+业务ID 查询 → 找到入口日志记录
  ↓
分析入口日志 → 提取关键信息（状态、原因、TID）
  ↓
日志查询2（可选）：用 TID 追踪链路 → 找到后续处理日志
  ↓
综合代码分析 + 日志结果 → 给出结论和建议
```
