# Conversion Contract (转换契约)

调用此 skill 的 Agent 必须将捕获的 Wiki 内容转换为 `converted.json`。

## 顶层结构 (Top-Level Shape)

```json
{
  "title": "Document title",
  "source_url": "https://wiki.example.com/pages/viewpage.action?pageId=123",
  "blocks": []
}
```

必需字段：

- `title`：非空字符串。
- `source_url`：原始 Wiki URL（若已知）。
- `blocks`：非空的 block 对象数组。

## 支持的块类型 (Supported Blocks)

### Heading (标题)

```json
{ "type": "heading", "level": 1, "text": "Overview" }
```

规则：

- `level` 必须是 1 到 6。
- `text` 必须非空。
- 尽可能保留源文档的层级结构。
- 清除标题中转义的 Markdown 伪影。例如，将 `\*1、背景及目标` 或 `*1、背景及目标` 转换为 `1、背景及目标`。
- 不要保留来自加粗 Markdown 转换的装饰性前导星号（`*`）。

### Paragraph (段落)

```json
{ "type": "paragraph", "text": "Body text." }
```

规则：

- 在可能的情况下，保留 Markdown 语法中的有意义链接。
- 避免添加源文档中不存在的注释或解说。

### Table (表格)

```json
{
  "type": "table",
  "caption": "Optional caption",
  "headers": ["Name", "Owner"],
  "rows": [
    ["Service A", "Team A"],
    ["Service B", "Team B"]
  ]
}
```

规则：

- `headers` 是可选的。
- 每一行的列数必须一致。
- 如果源表格包含合并单元格，请重复填充可见的值，并添加一个 warning 块以说明保真度可能有所降低。
- **切勿**将复杂的 Confluence 表格展平成一个段落。如果表格无法精确表示，请将其拆分为较小的语义表格加列表，并添加一个 warning 块。
- 对于产品需求（PRD）章节，字段/规则/展示逻辑首选表格，操作规则首选列表。

### Code Block (代码块)

```json
{ "type": "code_block", "language": "bash", "code": "npm test\nnpm run build" }
```

规则：

- 保留换行和缩进。
- 不要翻译、总结、标准化或纠正命令。
- `language` 在未知时可以为空。

### Image (图片)

```json
{
  "type": "image",
  "alt": "Architecture diagram",
  "src": "https://wiki.example.com/download/attachments/1/diagram.png",
  "local_path": "assets/diagram.png"
}
```

规则：

- 包含源文档中的每一张图片。
- 优先选择指向运行目录下文件的 `local_path`。
- 即使存在 `local_path`，也要保留 `src` 以保证可追溯性。
- 如果图片无法下载，保留图片块并允许验证失败。

### Link (链接)

```json
{ "type": "link", "text": "Original page", "url": "https://wiki.example.com/pages/viewpage.action?pageId=123" }
```

对独立链接使用 link 块。行内链接可以保留在段落的 Markdown 文本内。

### Warning (警告)

```json
{ "type": "warning", "text": "Confluence status macro was converted to plain text." }
```

对于无法在 Markdown 或飞书中忠实表示的源文档元素，使用 warning 块。

## 输出规范 (Output Discipline)

- `converted.json` 必须且仅输出合法的 JSON 文本。
- 不要在 JSON 周围包含 Markdown 代码块围栏（` ``` `）。
- 保持源文档的顺序。
- 宁可遗漏可选字段，也不要凭空捏造数据。
- 在改进文本表述之前，优先保留标题、标题层级、表格、代码块和图片。
- 将图片作为一等公民（first-class）的图片块保留。在 `converted.json` 中，**切勿**将图片替换为替代文本、普通链接或占位符。
- 段落文本中出现未渲染的 Markdown 表格管道符（`| ... |`）应被视为转换缺陷，除非源文档本身就是在记录 Markdown 语法。
