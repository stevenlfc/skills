#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io
# Windows 终端默认 GBK 编码，遇到   等 Unicode 字符会报错，强制使用 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

"""
Kibana 查询结果分析脚本

读取 kibana_query.py 保存的查询结果文件，进行深度分析。

用法：
    # 分析单个结果文件
    python kibana_analyze.py temps/abc123_20260603.log

    # 分析并只看摘要
    python kibana_analyze.py temps/abc123_20260603.log --mode summary

    # 分析并提取所有追踪ID
    python kibana_analyze.py temps/abc123_20260603.log --mode traces

    # 分析并统计字段值分布
    python kibana_analyze.py temps/abc123_20260603.log --mode stats

    # 分析并搜索特定关键字
    python kibana_analyze.py temps/abc123_20260603.log --mode search --keyword "无id字段"

    # 按追踪ID分组展示日志链路
    python kibana_analyze.py temps/abc123_20260603.log --mode chain

    # 列出所有结果文件
    python kibana_analyze.py --list

    # 清理所有结果文件
    python kibana_analyze.py --clean
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
TEMPS_DIR = os.path.join(SKILL_DIR, "temps")


def get_temps_dir(session=None):
    """根据会话ID返回对应的 temps 子目录，隔离多 agent 并发操作"""
    if session:
        return os.path.join(TEMPS_DIR, session)
    return TEMPS_DIR


def load_log_file(path):
    """加载查询结果文件"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_records(log_data):
    """从日志数据中提取记录列表"""
    response = log_data.get("response", {})
    raw = response.get("rawResponse", {})
    hits = raw.get("hits", {})
    return hits.get("hits", [])


def get_source(record):
    """获取记录的 _source"""
    return record.get("_source", {})


def detect_content_field(records):
    """自动检测内容字段名"""
    known = ["logDetail", "data", "message", "msg", "info", "warring", "warning", "error", "logMsg", "content"]
    for field in known:
        for record in records[:3]:
            source = get_source(record)
            if field in source and source[field]:
                return field
    # 回退：找最长文本字段
    for record in records[:1]:
        source = get_source(record)
        longest = ""
        longest_len = 0
        for k, v in source.items():
            if isinstance(v, str) and len(v) > longest_len:
                longest = k
                longest_len = len(v)
        if longest:
            return longest
    return None


def detect_trace_fields(records):
    """自动检测追踪字段名"""
    known_tids = ["TID", "traceId", "trace_id", "requestId"]
    known_sids = ["SID", "spanId", "span_id"]
    tid_field = None
    sid_field = None
    for field in known_tids:
        for record in records[:3]:
            if field in get_source(record):
                tid_field = field
                break
        if tid_field:
            break
    for field in known_sids:
        for record in records[:3]:
            if field in get_source(record):
                sid_field = field
                break
        if sid_field:
            break
    return tid_field, sid_field


def detect_level_field(records):
    """自动检测日志级别字段名"""
    known = ["logLevel", "level", "severity"]
    for field in known:
        for record in records[:3]:
            if field in get_source(record):
                return field
    return None


def detect_class_field(records):
    """自动检测类名字段名"""
    known = ["logClass", "logger", "className"]
    for field in known:
        for record in records[:3]:
            if field in get_source(record):
                return field
    return None


def detect_timestamp_field(records):
    """自动检测时间戳字段名"""
    known = ["timestamp", "@timestamp"]
    for field in known:
        for record in records[:3]:
            if field in get_source(record):
                return field
    return None


def extract_message(source, content_field):
    """从内容字段中提取消息文本"""
    raw = source.get(content_field, "")
    if not raw:
        return ""
    # 尝试从 logDetail 格式中提取 "- " 后面的内容
    if " - " in raw:
        parts = raw.split(" - ", 1)
        if len(parts) > 1:
            raw = parts[1]
    # 尝试解析 JSON
    stripped = raw.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    return raw


def analyze_summary(log_data, file_path):
    """分析摘要：统计信息 + 每条日志的简要信息"""
    meta = log_data.get("meta", {})
    response = log_data.get("response", {})
    raw = response.get("rawResponse", {})
    records = get_records(log_data)
    total = raw.get("hits", {}).get("total", 0)

    content_field = detect_content_field(records)
    tid_field, sid_field = detect_trace_fields(records)
    level_field = detect_level_field(records)
    class_field = detect_class_field(records)
    ts_field = detect_timestamp_field(records)

    lines = []
    lines.append(f"{'='*70}")
    lines.append(f"查询结果分析")
    lines.append(f"{'='*70}")
    lines.append(f"文件: {file_path}")
    lines.append(f"服务器: {meta.get('server', '?')}")
    lines.append(f"索引: {meta.get('index', '?')}")
    lines.append(f"查询时间: {meta.get('query_time', '?')}")
    lines.append(f"总记录数: {total}，返回: {len(records)}")
    lines.append(f"ES 耗时: {raw.get('took', '?')} ms")
    if raw.get("timed_out"):
        lines.append("⚠️ 查询超时!")
    lines.append(f"内容字段: {content_field or '未检测到'}")
    lines.append(f"追踪字段: TID={tid_field or '?'}, SID={sid_field or '?'}")
    lines.append("")

    if not records:
        lines.append("无日志记录。")
        return "\n".join(lines)

    # 级别分布
    if level_field:
        level_counter = Counter(get_source(r).get(level_field, "?") for r in records)
        lines.append(f"日志级别分布: {dict(level_counter)}")
        lines.append("")

    # 逐条摘要
    for i, record in enumerate(records):
        source = get_source(record)
        ts = source.get(ts_field, "") if ts_field else ""
        level = source.get(level_field, "") if level_field else ""
        cls = source.get(class_field, "") if class_field else ""
        if cls and "." in cls:
            cls = cls.split(".")[-1]
        tid = source.get(tid_field, "") if tid_field else ""
        sid = source.get(sid_field, "") if sid_field else ""
        msg = extract_message(source, content_field) if content_field else ""

        lines.append(f"{'='*60}")
        lines.append(f"[{i+1}] {ts}  [{level}]")
        if cls:
            lines.append(f"    类: {cls}")
        if tid:
            lines.append(f"    TID: {tid}")
        if sid:
            lines.append(f"    SID: {sid}")
        lines.append(f"    日志: {msg[:500]}")
        if len(msg) > 500:
            lines.append(f"    ... (共 {len(msg)} 字符)")
        lines.append("")

    return "\n".join(lines)


def analyze_traces(log_data, file_path):
    """提取所有追踪ID"""
    records = get_records(log_data)
    tid_field, sid_field = detect_trace_fields(records)

    lines = []
    lines.append(f"追踪ID提取结果")
    lines.append(f"文件: {file_path}")
    lines.append("")

    if not records:
        lines.append("无记录。")
        return "\n".join(lines)

    tids = set()
    sids = set()
    for record in records:
        source = get_source(record)
        if tid_field and source.get(tid_field):
            tids.add(source[tid_field])
        if sid_field and source.get(sid_field):
            sids.add(source[sid_field])

    if tid_field:
        lines.append(f"TID ({tid_field}) - {len(tids)} 个:")
        for tid in sorted(tids):
            lines.append(f"  {tid}")
    else:
        lines.append("未检测到 TID 字段。")

    lines.append("")

    if sid_field:
        lines.append(f"SID ({sid_field}) - {len(sids)} 个:")
        for sid in sorted(sids):
            lines.append(f"  {sid}")
    else:
        lines.append("未检测到 SID 字段。")

    return "\n".join(lines)


def analyze_stats(log_data, file_path):
    """统计字段值分布"""
    records = get_records(log_data)

    lines = []
    lines.append(f"字段值统计")
    lines.append(f"文件: {file_path}")
    lines.append("")

    if not records:
        lines.append("无记录。")
        return "\n".join(lines)

    # 收集所有字段
    field_values = defaultdict(list)
    for record in records:
        source = get_source(record)
        for k, v in source.items():
            if isinstance(v, str) and len(v) < 200:
                field_values[k].append(v)

    for field in sorted(field_values.keys()):
        values = field_values[field]
        counter = Counter(values)
        if len(counter) <= 10:
            lines.append(f"{field} ({len(values)} 条, {len(counter)} 个不同值):")
            for val, count in counter.most_common():
                display = val if len(val) < 80 else val[:80] + "..."
                lines.append(f"  {count}x  {display}")
        else:
            lines.append(f"{field} ({len(values)} 条, {len(counter)} 个不同值, 前10):")
            for val, count in counter.most_common(10):
                display = val if len(val) < 80 else val[:80] + "..."
                lines.append(f"  {count}x  {display}")
        lines.append("")

    return "\n".join(lines)


def analyze_search(log_data, keyword, file_path):
    """搜索包含关键字的日志"""
    records = get_records(log_data)
    content_field = detect_content_field(records)
    tid_field, _ = detect_trace_fields(records)
    ts_field = detect_timestamp_field(records)

    lines = []
    lines.append(f"关键字搜索: '{keyword}'")
    lines.append(f"文件: {file_path}")
    lines.append("")

    if not records:
        lines.append("无记录。")
        return "\n".join(lines)

    matched = []
    for i, record in enumerate(records):
        source = get_source(record)
        # 在所有文本字段中搜索
        all_text = json.dumps(source, ensure_ascii=False)
        if keyword.lower() in all_text.lower():
            matched.append((i, record))

    if not matched:
        lines.append(f"未找到包含 '{keyword}' 的日志。")
        return "\n".join(lines)

    lines.append(f"找到 {len(matched)} 条匹配记录:")
    lines.append("")

    for idx, record in matched:
        source = get_source(record)
        ts = source.get(ts_field, "") if ts_field else ""
        tid = source.get(tid_field, "") if tid_field else ""
        msg = extract_message(source, content_field) if content_field else ""

        lines.append(f"{'='*60}")
        lines.append(f"[第{idx+1}条] {ts}")
        if tid:
            lines.append(f"    TID: {tid}")
        # 高亮关键字
        msg_display = msg[:800]
        if keyword.lower() in msg_display.lower():
            # 简单高亮
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            msg_display = pattern.sub(f"【{keyword}】", msg_display)
        lines.append(f"    日志: {msg_display}")
        lines.append("")

    return "\n".join(lines)


def analyze_chain(log_data, file_path):
    """按追踪ID分组，展示日志链路"""
    records = get_records(log_data)
    content_field = detect_content_field(records)
    tid_field, sid_field = detect_trace_fields(records)
    level_field = detect_level_field(records)
    ts_field = detect_timestamp_field(records)

    lines = []
    lines.append(f"日志链路分析")
    lines.append(f"文件: {file_path}")
    lines.append("")

    if not records:
        lines.append("无记录。")
        return "\n".join(lines)

    if not tid_field:
        lines.append("未检测到追踪字段，无法按链路分组。")
        lines.append("请用 --mode summary 查看完整日志。")
        return "\n".join(lines)

    # 按 TID 分组
    groups = defaultdict(list)
    for record in records:
        source = get_source(record)
        tid = source.get(tid_field, "unknown")
        groups[tid].append(record)

    for tid in sorted(groups.keys()):
        group_records = groups[tid]
        lines.append(f"{'='*60}")
        lines.append(f"TID: {tid} ({len(group_records)} 条日志)")
        lines.append(f"{'='*60}")

        # 按时间排序
        def get_ts(r):
            s = get_source(r)
            return s.get(ts_field, "") if ts_field else ""
        group_records.sort(key=get_ts)

        for record in group_records:
            source = get_source(record)
            ts = source.get(ts_field, "") if ts_field else ""
            level = source.get(level_field, "") if level_field else ""
            msg = extract_message(source, content_field) if content_field else ""

            lines.append(f"  [{ts}] [{level}]")
            lines.append(f"  {msg[:300]}")
            if len(msg) > 300:
                lines.append(f"  ... (共 {len(msg)} 字符)")
            lines.append("")

    return "\n".join(lines)


def list_files(active_dir=None):
    """列出当前会话的结果文件"""
    if active_dir is None:
        active_dir = TEMPS_DIR
    if not os.path.exists(active_dir):
        print(f"{active_dir} 目录不存在。")
        return

    files = sorted([f for f in os.listdir(active_dir) if f.endswith(".log")])
    if not files:
        print(f"{active_dir} 目录为空。")
        return

    print(f"{active_dir} 目录中有 {len(files)} 个结果文件:")
    for f in files:
        path = os.path.join(active_dir, f)
        size = os.path.getsize(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  {f}  ({size:,} bytes, {mtime})")


def clean_files(active_dir=None):
    """清理当前会话的结果文件及子目录"""
    import shutil
    if active_dir is None:
        active_dir = TEMPS_DIR
    if not os.path.exists(active_dir):
        print(f"{active_dir} 目录不存在，无需清理。")
        return

    files = [f for f in os.listdir(active_dir) if f.endswith(".log")]
    if not files:
        print(f"{active_dir} 目录已为空。")
        return

    for f in files:
        os.remove(os.path.join(active_dir, f))
    # 如果是子目录（session 隔离目录），整个删掉；根 temps/ 只清文件
    if active_dir != TEMPS_DIR:
        shutil.rmtree(active_dir, ignore_errors=True)
        print(f"已清理 {len(files)} 个结果文件，子目录 {active_dir} 已删除。")
    else:
        print(f"已清理 {len(files)} 个结果文件。")


def main():
    parser = argparse.ArgumentParser(
        description="Kibana 查询结果分析脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看摘要（默认）
  python kibana_analyze.py temps/abc123_20260603.log

  # 提取追踪ID
  python kibana_analyze.py temps/abc123_20260603.log --mode traces

  # 字段值统计
  python kibana_analyze.py temps/abc123_20260603.log --mode stats

  # 搜索关键字
  python kibana_analyze.py temps/abc123_20260603.log --mode search --keyword "无id字段"

  # 按追踪ID分组展示链路
  python kibana_analyze.py temps/abc123_20260603.log --mode chain

  # 列出所有文件
  python kibana_analyze.py --list

  # 清理所有文件
  python kibana_analyze.py --clean
        """
    )

    parser.add_argument("file", nargs="?", help="查询结果文件路径")
    parser.add_argument("--mode", choices=["summary", "traces", "stats", "search", "chain"],
                        default="summary", help="分析模式")
    parser.add_argument("--keyword", default=None, help="搜索关键字（--mode search 时使用）")
    parser.add_argument("--list", action="store_true", help="列出所有结果文件")
    parser.add_argument("--clean", action="store_true", help="清理所有结果文件")
    parser.add_argument("--session", default=None, help="会话ID，用于隔离多 agent 的 temps 子目录（如 sess_abc123）")

    args = parser.parse_args()

    active_dir = get_temps_dir(args.session)

    if args.list:
        list_files(active_dir)
        return

    if args.clean:
        clean_files(active_dir)
        return

    if not args.file:
        parser.error("请指定查询结果文件路径，或使用 --list 查看可用文件。")

    if not os.path.exists(args.file):
        print(f"文件不存在: {args.file}", file=sys.stderr)
        sys.exit(1)

    log_data = load_log_file(args.file)

    if args.mode == "summary":
        print(analyze_summary(log_data, args.file))
    elif args.mode == "traces":
        print(analyze_traces(log_data, args.file))
    elif args.mode == "stats":
        print(analyze_stats(log_data, args.file))
    elif args.mode == "search":
        if not args.keyword:
            parser.error("--mode search 需要配合 --keyword 使用")
        print(analyze_search(log_data, args.keyword, args.file))
    elif args.mode == "chain":
        print(analyze_chain(log_data, args.file))


if __name__ == "__main__":
    main()
