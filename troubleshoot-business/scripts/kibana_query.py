#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
# Windows 终端默认 GBK 编码，遇到   等 Unicode 字符会报错，强制使用 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

"""
Kibana 日志查询脚本

查询 Kibana/Elasticsearch 日志系统，结果保存到 temps/ 目录，
配合 kibana_analyze.py 分析结果文件。

用法：
    # 探测字段结构（首次查询时使用）
    python kibana_query.py --server fast107 --index "index-12961-13160*" --discover

    # 正式查询，结果保存到 temps/<hash>.log
    python kibana_query.py --server fast107 --index "index-12961-13160*" \
        --filter 'match_phrase:logDetail:2000000168999804' \
        --minutes 30

    # 指定输出文件名
    python kibana_query.py --server fast107 --index "index-12961-13160*" \
        --filter 'match_phrase:TID:xxx' --minutes 30 \
        --out temps/my_query.log

    # 同时在终端打印摘要（默认只保存文件不打印）
    python kibana_query.py --server fast107 --index "index-12961-13160*" \
        --filter 'match_phrase:logDetail:xxx' --minutes 30 --print

    # 直接输出到终端（兼容旧用法，不保存文件）
    python kibana_query.py --server fast107 --index "index-12961-13160*" \
        --filter 'match_phrase:logDetail:xxx' --minutes 30 --stdout
"""

import argparse
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timedelta, timezone


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
TEMPS_DIR = os.path.join(SKILL_DIR, "temps")


def get_temps_dir(session=None):
    """根据会话ID返回对应的 temps 子目录，隔离多 agent 并发操作"""
    if session:
        return os.path.join(TEMPS_DIR, session)
    return TEMPS_DIR


# 重点关注的内容字段
CONTENT_FIELDS = ["logDetail", "data", "message", "msg", "info", "warring", "warning", "error"]


def build_time_range(minutes=None, start=None, end=None):
    """构建时间范围条件"""
    if start and end:
        return {
            "range": {
                "timestamp": {
                    "gte": start,
                    "lte": end,
                    "format": "strict_date_optional_time"
                }
            }
        }
    now = datetime.now(timezone.utc)
    if minutes is None:
        minutes = 30
    start_time = now - timedelta(minutes=minutes)
    return {
        "range": {
            "timestamp": {
                "gte": start_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "lte": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "format": "strict_date_optional_time"
            }
        }
    }


def parse_filter(filter_str):
    """解析 --filter 参数，格式：类型:字段:值"""
    parts = filter_str.split(":", 2)
    if len(parts) < 2:
        raise ValueError(f"filter 格式错误: {filter_str}，应为 类型:字段:值")
    filter_type = parts[0]
    if filter_type == "match_phrase":
        if len(parts) < 3:
            raise ValueError(f"match_phrase 格式错误: {filter_str}")
        return {"match_phrase": {parts[1]: parts[2]}}
    elif filter_type == "should":
        if len(parts) < 3:
            raise ValueError(f"should 格式错误: {filter_str}")
        field = parts[1]
        values = parts[2].split(",")
        return {"bool": {"should": [{"match_phrase": {field: v.strip()}} for v in values], "minimum_should_match": 1}}
    elif filter_type == "exists":
        return {"exists": {"field": parts[1]}}
    else:
        raise ValueError(f"未知的 filter 类型: {filter_type}")


def parse_must_not(must_not_str):
    """解析 --must-not 参数"""
    parts = must_not_str.split(":", 2)
    if len(parts) < 2:
        raise ValueError(f"must-not 格式错误: {must_not_str}")
    filter_type = parts[0]
    if filter_type == "match_phrase":
        if len(parts) < 3:
            raise ValueError(f"match_phrase 格式错误: {must_not_str}")
        return {"match_phrase": {parts[1]: parts[2]}}
    elif filter_type == "exists":
        return {"exists": {"field": parts[1]}}
    else:
        raise ValueError(f"未知的 must-not 类型: {filter_type}")


def build_query(args):
    """构建完整的 ES 查询 JSON"""
    must = []
    filter_conditions = []
    must_not = []

    if args.query_string:
        must.append({"query_string": {"query": args.query_string, "analyze_wildcard": True, "time_zone": "Asia/Shanghai"}})
    else:
        must.append({"match_all": {}})

    for f in args.filter:
        filter_conditions.append(parse_filter(f))
    filter_conditions.append(build_time_range(args.minutes, args.start, args.end))
    for mn in args.must_not:
        must_not.append(parse_must_not(mn))

    return {
        "params": {
            "ignoreThrottled": True,
            "preference": 1780483834299,
            "index": args.index,
            "body": {
                "version": True,
                "size": args.size,
                "sort": [{"timestamp": {"order": "desc", "unmapped_type": "boolean"}}],
                "aggs": {"2": {"date_histogram": {"field": "timestamp", "fixed_interval": "30s", "time_zone": "Asia/Shanghai", "min_doc_count": 1}}},
                "stored_fields": ["*"],
                "script_fields": {},
                "docvalue_fields": [{"field": "timestamp", "format": "date_time"}],
                "_source": {"excludes": []},
                "query": {"bool": {"must": must, "filter": filter_conditions, "should": [], "must_not": must_not}},
                "highlight": {"pre_tags": ["@kibana-highlighted-field@"], "post_tags": ["@/kibana-highlighted-field@"], "fields": {"*": {}}, "fragment_size": 2147483647}
            },
            "rest_total_hits_as_int": True,
            "ignore_unavailable": True,
            "ignore_throttled": True,
            "timeout": "30000ms"
        },
        "serverStrategy": "es"
    }


def build_discover_query(index, minutes=5):
    """构建探测查询"""
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=minutes)
    return {
        "params": {
            "ignoreThrottled": True,
            "preference": 1780483834299,
            "index": index,
            "body": {
                "version": True,
                "size": 5,
                "sort": [{"timestamp": {"order": "desc", "unmapped_type": "boolean"}}],
                "aggs": {},
                "stored_fields": ["*"],
                "script_fields": {},
                "docvalue_fields": [{"field": "timestamp", "format": "date_time"}],
                "_source": {"excludes": []},
                "query": {"bool": {"must": [{"match_all": {}}], "filter": [{"range": {"timestamp": {"gte": start_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z", "lte": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z", "format": "strict_date_optional_time"}}}], "should": [], "must_not": []}},
                "highlight": {"pre_tags": ["@kibana-highlighted-field@"], "post_tags": ["@/kibana-highlighted-field@"], "fields": {"*": {}}, "fragment_size": 2147483647}
            },
            "rest_total_hits_as_int": True,
            "ignore_unavailable": True,
            "ignore_throttled": True,
            "timeout": "30000ms"
        },
        "serverStrategy": "es"
    }


def compute_hash(params_json):
    """根据请求参数计算唯一 hash"""
    return hashlib.md5(params_json.encode("utf-8")).hexdigest()[:12]


def send_request(server_prefix, body, cookie=None):
    """发送请求到 Kibana ES 接口"""
    url = f"https://{server_prefix}-kibana-logcenter-intra.intra.ke.com/internal/search/es"
    headers = {"kbn-version": "7.7.0", "Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        if e.code in (401, 403):
            print("请求需要认证，请通过 --cookie 参数提供 Cookie", file=sys.stderr)
        else:
            print(f"响应内容: {error_body[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"请求失败: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求异常: {e}", file=sys.stderr)
        sys.exit(1)


def save_query_log(server, index, params, response, out_path=None):
    """保存查询日志到 temps/ 目录，返回文件路径"""
    params_str = json.dumps(params, ensure_ascii=False, sort_keys=True)
    hash_val = compute_hash(params_str)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if out_path is None:
        filename = f"{hash_val}_{timestamp}.log"
        out_path = os.path.join(_active_temps_dir, filename)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    log_data = {
        "meta": {
            "server": server,
            "index": index,
            "query_time": datetime.now().isoformat(),
            "hash": hash_val,
        },
        "request": params,
        "response": response,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    return out_path


def format_summary(results):
    """格式化为简洁摘要（终端输出用）"""
    raw = results.get("rawResponse", {})
    hits = raw.get("hits", {})
    total = hits.get("total", 0)
    records = hits.get("hits", [])

    lines = []
    lines.append(f"查询结果: 共 {total} 条记录，返回 {len(records)} 条")
    lines.append(f"耗时: {raw.get('took', '?')} ms")
    if raw.get("timed_out"):
        lines.append("⚠️ 查询超时!")
    shards = raw.get("_shards", {})
    if shards.get("failed", 0) > 0:
        lines.append(f"⚠️ 分片失败: {shards.get('failed')}/{shards.get('total')}")
    lines.append("")

    if not records:
        lines.append("未找到匹配的日志记录。")
        return "\n".join(lines)

    for i, record in enumerate(records):
        source = record.get("_source", {})
        log_detail = source.get("logDetail", source.get("data", source.get("message", source.get("msg", ""))))
        log_level = source.get("logLevel", source.get("level", ""))
        log_class = source.get("logClass", source.get("logger", ""))
        timestamp = source.get("timestamp", source.get("@timestamp", ""))
        tid = source.get("TID", source.get("traceId", source.get("trace_id", "")))
        sid = source.get("SID", source.get("spanId", source.get("span_id", "")))

        msg = log_detail
        if " - " in log_detail:
            parts = log_detail.split(" - ", 1)
            if len(parts) > 1:
                msg = parts[1]
        msg_stripped = msg.strip()
        if msg_stripped.startswith("{") and msg_stripped.endswith("}"):
            try:
                parsed = json.loads(msg_stripped)
                msg = json.dumps(parsed, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass

        lines.append(f"{'='*60}")
        lines.append(f"[{i+1}] {timestamp}  [{log_level}]")
        if log_class:
            lines.append(f"    类: {log_class}")
        if tid:
            lines.append(f"    TID: {tid}")
        if sid:
            lines.append(f"    SID: {sid}")
        host = source.get("host_name", source.get("hostname", source.get("host", "")))
        if host:
            lines.append(f"    主机: {host}")
        lines.append(f"    日志: {msg[:500]}")
        if len(msg) > 500:
            lines.append(f"    ... (共 {len(msg)} 字符)")
        lines.append("")

    return "\n".join(lines)


def format_discover(results, server, index):
    """格式化探测结果"""
    raw = results.get("rawResponse", {})
    hits = raw.get("hits", {})
    total = hits.get("total", 0)
    records = hits.get("hits", [])

    lines = []
    lines.append(f"{'='*70}")
    lines.append(f"字段结构探测报告")
    lines.append(f"{'='*70}")
    lines.append(f"服务器: {server}")
    lines.append(f"索引: {index}")
    lines.append(f"总记录数: {total}")
    lines.append(f"分析样本: {len(records)} 条")
    lines.append(f"耗时: {raw.get('took', '?')} ms")
    lines.append("")

    if not records:
        lines.append("最近 5 分钟内无数据。建议:")
        lines.append("  1. 检查索引名称是否正确")
        lines.append("  2. 尝试用 --minutes 指定更长的时间范围")
        lines.append("  3. 确认该服务是否有日志输出")
        return "\n".join(lines)

    # 分析字段
    field_counter = Counter()
    field_samples = {}
    field_types = {}

    for record in records:
        source = record.get("_source", {})
        for key, value in source.items():
            field_counter[key] += 1
            value_type = type(value).__name__
            if key not in field_types:
                field_types[key] = set()
            field_types[key].add(value_type)
            if key not in field_samples:
                field_samples[key] = []
            if len(field_samples[key]) < 3:
                sample = str(value)
                if len(sample) > 300:
                    sample = sample[:300] + "..."
                field_samples[key].append(sample)

    # 分类
    known_content = {"logDetail", "data", "message", "msg", "info", "warring", "warning", "error",
                     "logMsg", "logMsgCn", "logMsgEn", "content", "detail", "desc", "description"}
    known_trace = {"TID", "SID", "SpanID", "traceId", "spanId", "trace_id", "span_id", "requestId"}
    known_meta = {"logLevel", "logClass", "host_name", "hostname", "host", "level", "logger",
                  "thread", "threadName", "className", "methodName", "timestamp", "@timestamp",
                  "appName", "serviceName"}

    classified = {"content": [], "trace": [], "meta": [], "other": []}
    for field in field_counter:
        if field in known_content:
            classified["content"].append(field)
        elif field in known_trace:
            classified["trace"].append(field)
        elif field in known_meta:
            classified["meta"].append(field)
        else:
            samples = field_samples.get(field, [])
            has_json = any(s.strip().startswith(("{", "[")) for s in samples)
            has_long = any(len(s) > 100 for s in samples)
            if has_json or has_long:
                classified["content"].append(field)
            else:
                classified["other"].append(field)

    for cat in classified:
        classified[cat].sort()

    lines.append(f"{'='*70}")
    lines.append(f"【内容字段】- 日志正文/业务数据，用于搜索和分析")
    lines.append(f"{'='*70}")
    if classified["content"]:
        for field in classified["content"]:
            types = ", ".join(field_types[field])
            lines.append(f"  {field} ({types}, 出现 {field_counter[field]}/{len(records)} 条)")
            for i, sample in enumerate(field_samples[field]):
                lines.append(f"    样本{i+1}: {sample}")
            lines.append("")
    else:
        lines.append("  未发现明确的内容字段。\n")

    lines.append(f"{'='*70}")
    lines.append(f"【追踪字段】- 链路追踪ID，用于查询同一请求链路")
    lines.append(f"{'='*70}")
    if classified["trace"]:
        for field in classified["trace"]:
            lines.append(f"  {field} (出现 {field_counter[field]}/{len(records)} 条)")
            for i, s in enumerate(field_samples[field][:2]):
                lines.append(f"    样本: {s}")
            lines.append("")
    else:
        lines.append("  未发现追踪字段。\n")

    lines.append(f"{'='*70}")
    lines.append(f"【元数据字段】- 日志级别、类名、主机等")
    lines.append(f"{'='*70}")
    if classified["meta"]:
        for field in classified["meta"]:
            types = ", ".join(field_types[field])
            unique = set(s for s in field_samples[field] if len(s) < 50)
            lines.append(f"  {field} ({types}) = {', '.join(sorted(unique))}")
    lines.append("")

    if classified["other"]:
        lines.append(f"{'='*70}")
        lines.append(f"【其他字段】")
        lines.append(f"{'='*70}")
        for field in classified["other"]:
            types = ", ".join(field_types[field])
            s = field_samples[field][0] if field_samples[field] else ""
            if len(s) > 100:
                s = s[:100] + "..."
            lines.append(f"  {field} ({types}) = {s}")
        lines.append("")

    lines.append(f"{'='*70}")
    lines.append(f"【查询建议】")
    lines.append(f"{'='*70}")
    searchable = [f for f in classified["content"] if any(len(s) > 20 for s in field_samples.get(f, []))]
    if searchable:
        lines.append(f"  可用于搜索业务关键字的字段: {', '.join(searchable)}")
        lines.append(f"  示例: --filter 'match_phrase:{searchable[0]}:<你的关键字>'")
    else:
        lines.append(f"  建议使用 query_string 全文搜索:")
        lines.append(f"  示例: --query-string '\"你的关键字\"'")
    if classified["trace"]:
        tf = classified["trace"][0]
        lines.append(f"  追踪链路字段: {tf}")
        lines.append(f"  示例: --filter 'match_phrase:{tf}:<追踪ID>'")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Kibana 日志查询脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 探测字段结构
  python kibana_query.py --server fast107 --index "index-12961-13160*" --discover

  # 查询并保存到 temps/（默认行为）
  python kibana_query.py --server fast107 --index "index-12961-13160*" \\
      --filter 'match_phrase:logDetail:2000000168999804' --minutes 30

  # 查询并在终端同时打印摘要
  python kibana_query.py --server fast107 --index "index-12961-13160*" \\
      --filter 'match_phrase:logDetail:xxx' --minutes 30 --print

  # 直接输出到终端（不保存文件，兼容旧用法）
  python kibana_query.py --server fast107 --index "index-12961-13160*" \\
      --filter 'match_phrase:logDetail:xxx' --minutes 30 --stdout
        """
    )

    parser.add_argument("--server", required=True, help="服务器前缀")
    parser.add_argument("--index", required=True, help="ES 索引")
    parser.add_argument("--filter", action="append", default=[], help="filter 条件，格式: 类型:字段:值")
    parser.add_argument("--must-not", action="append", default=[], help="must_not 排除条件")
    parser.add_argument("--query-string", default=None, help="全文搜索关键字")
    parser.add_argument("--minutes", type=int, default=30, help="查询最近 N 分钟，默认 30")
    parser.add_argument("--start", default=None, help="开始时间 (UTC)")
    parser.add_argument("--end", default=None, help="结束时间 (UTC)")
    parser.add_argument("--cookie", default=None, help="Cookie 字符串")
    parser.add_argument("--size", type=int, default=1500, help="返回条数，默认 1500")
    parser.add_argument("--out", default=None, help="指定输出文件路径（默认 temps/<hash>_<时间>.log）")
    parser.add_argument("--stdout", action="store_true", help="直接输出到终端，不保存文件（兼容旧用法）")
    parser.add_argument("--print", action="store_true", help="保存文件的同时在终端打印摘要")
    parser.add_argument("--dump-query", action="store_true", help="只输出查询 JSON，不执行")
    parser.add_argument("--discover", action="store_true", help="探测模式：查最近5分钟，分析字段结构")
    parser.add_argument("--session", default=None, help="会话ID，用于隔离多 agent 的 temps 子目录（如 sess_abc123）")

    args = parser.parse_args()

    # 设置本次运行使用的 temps 目录（全局变量，供 save_query_log 使用）
    global _active_temps_dir
    _active_temps_dir = get_temps_dir(args.session)

    # 探测模式
    if args.discover:
        body = build_discover_query(args.index, minutes=5)
        print(f"正在探测 {args.server} 索引 {args.index} 的字段结构 (最近5分钟) ...", file=sys.stderr)
        results = send_request(args.server, body, args.cookie)
        print(format_discover(results, args.server, args.index))
        return

    # 构建查询
    body = build_query(args)

    if args.dump_query:
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return

    # 发送请求
    print(f"正在查询 {args.server} 索引 {args.index} ...", file=sys.stderr)
    results = send_request(args.server, body, args.cookie)

    # stdout 模式：直接输出，不保存文件（兼容旧用法）
    if args.stdout:
        print(format_summary(results))
        return

    # 默认模式：保存到 temps/ 文件
    out_path = save_query_log(args.server, args.index, body, results, args.out)

    # 统计信息
    raw = results.get("rawResponse", {})
    total = raw.get("hits", {}).get("total", 0)
    count = len(raw.get("hits", {}).get("hits", []))
    took = raw.get("took", "?")

    print(f"查询完成: {total} 条记录，返回 {count} 条，耗时 {took} ms", file=sys.stderr)
    print(f"结果已保存到: {out_path}", file=sys.stderr)

    # --print 模式：同时在终端打印摘要
    if getattr(args, "print", False):
        print(format_summary(results))

    # 输出文件路径到 stdout（方便管道或脚本获取）
    print(out_path)


if __name__ == "__main__":
    main()
