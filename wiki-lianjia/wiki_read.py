#!/usr/bin/env python3
"""
读取 wiki.lianjia.com (Confluence) 页面内容或导出为 PDF
用法:
  python3 wiki_read.py <pageId或URL> [--pdf [output.pdf]]

选项:
  --pdf [output.pdf]  导出为 PDF（不指定文件名则输出到 <pageId>.pdf）

Cookie 优先级: 环境变量 WIKI_LIANJIA_COOKIE > ~/.wiki_lianjia_cookie
Cookie 失效时交互式询问用户名和密码（密码不回显）
"""
import sys
import os
import re
import gzip
import json
import getpass
import urllib.parse
import http.client


COOKIE_FILE = os.path.expanduser("~/.wiki_lianjia_cookie")
HOST        = "wiki.lianjia.com"


def load_cookie():
    """从多个来源加载 Cookie"""
    env = os.environ.get("WIKI_LIANJIA_COOKIE", "")
    if env:
        return env
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE) as f:
            return f.read().strip()
    return ""


def prompt_credentials():
    """交互式询问用户名和密码（密码不回显）"""
    print("[Cookie 已过期] 请输入 wiki.lianjia.com 账号：", file=sys.stderr)
    username = input("用户名: ").strip()
    password = getpass.getpass("密码: ")
    return username, password


def _http_get(path, headers=None):
    """底层 GET，返回 (status, resp_headers_dict, body_bytes)"""
    conn = http.client.HTTPConnection(HOST, timeout=20)
    conn.request("GET", path, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/json",
        "Connection": "close",
        **(headers or {}),
    })
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    hdrs = {k.lower(): v for k, v in resp.getheaders()}
    if hdrs.get("content-encoding") == "gzip":
        raw = gzip.decompress(raw)
    return resp.status, hdrs, raw


def _http_post(path, body, headers=None):
    """底层 POST，返回 (status, resp_headers_dict, body_bytes)"""
    conn = http.client.HTTPConnection(HOST, timeout=20)
    conn.request("POST", path, body=body, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/json",
        "Connection": "close",
        **(headers or {}),
    })
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    hdrs = {k.lower(): v for k, v in resp.getheaders()}
    if hdrs.get("content-encoding") == "gzip":
        raw = gzip.decompress(raw)
    return resp.status, hdrs, raw


def login(username, password):
    """
    用用户名密码登录，返回 cookie 字符串并写入 ~/.wiki_lianjia_cookie。
    关键：GET /login.action 和 POST /dologin.action 必须复用同一个 TCP 连接，
    否则安全网关（i.sec-gateway.ke.com）会超时拦截新连接。
    """
    conn = http.client.HTTPConnection(HOST, timeout=20)

    # Step 1: GET /login.action (keep-alive，保持连接)
    conn.request("GET", "/login.action", headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html",
        "Connection": "keep-alive",
    })
    resp1 = conn.getresponse()
    raw1 = resp1.read()
    if resp1.getheader("Content-Encoding") == "gzip":
        raw1 = gzip.decompress(raw1)
    if resp1.status != 200:
        conn.close()
        raise RuntimeError(f"获取登录页失败: HTTP {resp1.status}")

    # 提取 JSESSIONID
    set_cookie1 = resp1.getheader("set-cookie", "")
    m = re.search(r'JSESSIONID=([^;]+)', set_cookie1)
    if not m:
        conn.close()
        raise RuntimeError("未能从登录页获取 JSESSIONID")
    jsessionid = m.group(1)

    # 提取 atlassian-token (CSRF token)
    html1 = raw1.decode("utf-8", errors="replace")
    tm = re.search(r'atlassian-token[^>]*content=["\']([^"\']+)["\']', html1)
    if not tm:
        conn.close()
        raise RuntimeError("未能从登录页获取 atlassian-token")
    atl_token = tm.group(1)

    # Step 2: POST /dologin.action (同一连接，避免安全网关超时)
    form_data = urllib.parse.urlencode({
        "os_username":    username,
        "os_password":    password,
        "os_cookie":      "true",
        "os_destination": "",
        "atl_token":      atl_token,
    }).encode()
    conn.request("POST", "/dologin.action", body=form_data, headers={
        "Content-Type":   "application/x-www-form-urlencoded",
        "Cookie":         f"JSESSIONID={jsessionid}",
        "User-Agent":     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer":        f"http://{HOST}/login.action",
        "Connection":     "close",
    })
    resp2 = conn.getresponse()
    raw2 = resp2.read()
    conn.close()

    # 登录失败：302 跳回 /login.action，或 200 含错误提示
    location = resp2.getheader("location", "")
    if "login" in location.lower():
        raise PermissionError("用户名或密码错误")
    if resp2.status == 200:
        body2 = raw2
        if resp2.getheader("Content-Encoding") == "gzip":
            body2 = gzip.decompress(raw2)
        text2 = body2.decode("utf-8", errors="replace")
        if "用户名或密码" in text2 or "invalid" in text2.lower():
            raise PermissionError("用户名或密码错误")

    # 解析登录后的 Set-Cookie（包含新 JSESSIONID + seraph.confluence）
    # http.client 对多个 Set-Cookie 只保留最后一个，需要用逗号分隔的原始值解析
    set_cookie2 = resp2.getheader("set-cookie", "")
    all_cookies = {"JSESSIONID": jsessionid}  # 保底用初始 session
    for pair in re.findall(r'([A-Za-z0-9_.%-]+)=([^;,]*)', set_cookie2):
        k, v = pair
        if k.lower() not in ("path", "httponly", "secure", "samesite", "domain", "expires", "max-age"):
            all_cookies[k] = v

    if resp2.status not in (302, 200):
        raise PermissionError(f"登录失败: HTTP {resp2.status}")

    cookie_str = "; ".join(f"{k}={v}" for k, v in all_cookies.items())

    # 写入 cookie 文件（权限 600，仅本人可读）
    with open(COOKIE_FILE, "w") as f:
        f.write(cookie_str)
    os.chmod(COOKIE_FILE, 0o600)
    print(f"[登录成功] Cookie 已保存到 {COOKIE_FILE}", file=sys.stderr)
    return cookie_str


def extract_page_id(arg):
    """从 URL 或纯 pageId 中提取 pageId"""
    m = re.search(r'pageId=(\d+)', arg)
    if m:
        return m.group(1)
    if arg.isdigit():
        return arg
    raise ValueError(f"无法解析 pageId: {arg}")


def fetch_page(page_id, cookie):
    """调用 Confluence REST API 获取页面内容，返回 (data, cookie)"""
    path = f"/rest/api/content/{page_id}?expand=title,body.view,version,space,ancestors"
    status, hdrs, raw = _http_get(path, headers={
        "Cookie": cookie,
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    })

    if status == 401:
        raise PermissionError("COOKIE_EXPIRED")
    if status == 404:
        # 404 可能是页面不存在，也可能是 cookie 失效导致无权访问
        # 通过检查 JSON 响应中的 authorized 字段判断
        body = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
            if isinstance(data, dict) and data.get("data", {}).get("authorized") is False:
                raise PermissionError("COOKIE_EXPIRED")
        except (json.JSONDecodeError, AttributeError):
            pass
        raise FileNotFoundError(f"页面 {page_id} 不存在或无权访问")
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {raw[:200]}")

    return json.loads(raw.decode("utf-8")), cookie


def html_to_text(html):
    """将 Confluence HTML 转为纯文本"""
    # 保留换行语义
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</p>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</tr>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</th>', '\t', html, flags=re.IGNORECASE)
    html = re.sub(r'</td>', '\t', html, flags=re.IGNORECASE)
    html = re.sub(r'<h[1-6][^>]*>', '\n## ', html, flags=re.IGNORECASE)
    html = re.sub(r'</h[1-6]>', '\n', html, flags=re.IGNORECASE)
    # 去掉所有剩余标签
    text = re.sub(r'<[^>]+>', '', html)
    # 清理空白
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def format_output(data):
    """格式化页面数据为可读文本"""
    title = data.get("title", "")
    space = data.get("space", {}).get("name", "")
    version = data.get("version", {}).get("number", "")
    ancestors = data.get("ancestors", [])
    breadcrumb = " > ".join(a.get("title", "") for a in ancestors) + (" > " + title if ancestors else title)

    html = data.get("body", {}).get("view", {}).get("value", "")
    text = html_to_text(html)

    lines = [
        f"# {title}",
        f"空间: {space}  |  版本: {version}  |  路径: {breadcrumb}",
        "",
        text,
    ]
    return "\n".join(lines)


def export_pdf(page_id, cookie):
    """
    导出 Confluence 页面为 PDF
    返回: (pdf_bytes, cookie) 或抛出异常
    """
    # Confluence PDF 导出 URL
    url = f"/spaces/flyingpdf/pdfpageexport.action?pageId={page_id}"

    status, hdrs, raw = _http_get(url, headers={
        "Cookie": cookie,
        "Accept": "application/pdf,*/*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    })

    # 401 = cookie 失效
    if status == 401:
        raise PermissionError("COOKIE_EXPIRED")

    # 302 重定向
    if status == 302:
        location = hdrs.get('location', '')
        # 重定向到登录页 = cookie 失效
        if 'login' in location.lower():
            raise PermissionError("COOKIE_EXPIRED")
        # 跟随 PDF 下载重定向（Confluence 生成 PDF 后重定向到临时文件）
        if location:
            status, hdrs, raw = _http_get(location, headers={
                "Cookie": cookie,
                "Accept": "application/pdf,*/*",
            })

    # 成功返回 PDF
    if status == 200:
        content_type = hdrs.get('content-type', '').lower()
        if 'pdf' in content_type or raw[:4] == b'%PDF':
            return raw, cookie
        # 可能返回了 HTML 任务页面（异步导出）
        raise RuntimeError("PDF 导出未就绪，可能需要稍后重试")

    if status == 404:
        raise FileNotFoundError(f"页面 {page_id} 不存在或无权访问")

    raise RuntimeError(f"PDF 导出失败: HTTP {status}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    # 解析参数
    args = sys.argv[1:]
    pdf_mode = False
    pdf_output = None
    page_arg = None

    i = 0
    while i < len(args):
        if args[i] == '--pdf':
            pdf_mode = True
            # 检查下一个参数是否为输出文件名（以 .pdf 结尾或包含路径分隔符）
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                next_arg = args[i + 1]
                if next_arg.endswith('.pdf') or '/' in next_arg:
                    pdf_output = next_arg
                    i += 2
                    continue
            i += 1
        elif not page_arg:
            page_arg = args[i]
            i += 1
        else:
            i += 1

    if not page_arg:
        print("错误: 缺少 pageId 或 URL 参数", file=sys.stderr)
        print(__doc__)
        sys.exit(1)

    try:
        page_id = extract_page_id(page_arg)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    # 默认 PDF 输出文件名
    if pdf_mode and not pdf_output:
        pdf_output = f"{page_id}.pdf"

    cookie = load_cookie()

    # 有 cookie，先尝试直接使用
    if cookie:
        try:
            if pdf_mode:
                pdf_data, cookie = export_pdf(page_id, cookie)
                with open(pdf_output, 'wb') as f:
                    f.write(pdf_data)
                print(f"[PDF 导出成功] {pdf_output} ({len(pdf_data)} 字节)", file=sys.stderr)
                return
            else:
                data, cookie = fetch_page(page_id, cookie)
            print(format_output(data))
            return
        except PermissionError as e:
            if "COOKIE_EXPIRED" in str(e):
                print("[Cookie 已过期] 正在清理并重新登录...", file=sys.stderr)
                # 自动删除失效的 cookie 文件
                if os.path.exists(COOKIE_FILE):
                    os.remove(COOKIE_FILE)
            else:
                print(f"错误: {e}", file=sys.stderr)
                sys.exit(1)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)

    # Cookie 不存在或已过期，交互式询问账号密码
    username, password = prompt_credentials()

    try:
        cookie = login(username, password)
        if pdf_mode:
            pdf_data, _ = export_pdf(page_id, cookie)
            with open(pdf_output, 'wb') as f:
                f.write(pdf_data)
            print(f"[PDF 导出成功] {pdf_output} ({len(pdf_data)} 字节)", file=sys.stderr)
        else:
            data, _ = fetch_page(page_id, cookie)
            print(format_output(data))
    except PermissionError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
