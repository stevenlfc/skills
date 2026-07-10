---
name: wiki-lianjia
description: 当用户提供 wiki.lianjia.com 的链接或 pageId，需要读取、提取或分析内部 wiki 页面内容，或导出为 PDF 时使用。支持 Cookie 自动认证和账号密码交互登录。
---

# wiki-lianjia：读取内部 Wiki 文档

## 功能介绍

帮助你直接读取 `wiki.lianjia.com`（公司内部 Confluence）的页面内容，并转换为结构清晰的纯文本，或导出为 PDF 文件，方便进一步分析、总结或引用。

**你只需要提供页面链接或 pageId，其余的认证和读取都自动完成。**

## 使用方式

### 1. 读取文本内容（默认）

直接把 wiki 链接或 pageId 发给我即可，例如：

- `http://wiki.lianjia.com/pages/viewpage.action?pageId=1502505707`
- `1502505707`

我会自动调用以下命令读取内容：

```bash
python3 ~/.claude/skills/wiki-lianjia/wiki_read.py "<用户提供的URL或pageId>"
```

### 2. 导出为 PDF

如果需要导出为 PDF，明确说明即可，例如：
- "把这个 wiki 导出成 PDF"
- "下载 PDF 版本"

我会自动调用：

```bash
python3 ~/.claude/skills/wiki-lianjia/wiki_read.py "<pageId或URL>" --pdf [output.pdf]
```

不指定输出文件名时，默认保存为 `<pageId>.pdf`。

## 认证说明

**首次使用 / Cookie 过期时**，脚本会在终端提示输入账号密码（密码不回显），登录成功后 Cookie 自动保存，下次无需再次输入。

```
用户名: your_username
密码:              ← 输入时不显示
[登录成功] Cookie 已保存
```

**已有 Cookie 时**，直接读取，无任何提示。

## 输出格式

**文本模式**（默认）：

```
# 页面标题
空间: xxx  |  版本: N  |  路径: 首页 > ... > 页面标题

正文内容（保留标题层级和段落结构）
```

**PDF 模式**：

导出成功后会在当前目录生成 PDF 文件，并输出确认信息：
```
[PDF 导出成功] 1502505707.pdf (123456 字节)
```

## 常见问题

| 现象 | 解决方式 |
|------|---------|
| 提示输入用户名密码 | 正常输入即可，登录后自动续期 |
| 提示用户名或密码错误 | 检查账号密码是否正确后重新输入 |
| 提示 HTTP 404 | 确认链接是否正确，或检查是否有页面访问权限 |
| 提示超时 | 确认当前网络处于公司内网环境 |
| 密码更改后无法登录 | 失效 cookie 会被自动清理，重新输入新密码即可 |
| PDF 导出未就绪 | 某些大型页面需要异步生成，可稍后重试 |
