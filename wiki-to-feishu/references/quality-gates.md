# Quality Gates (质量关卡)

验证决定了是否允许上传文档。

## 阻塞性错误 (Blocking Errors)

如果存在任何阻塞性错误，调用 Agent 切勿上传文档：

- `converted.json` 缺失或非合法 JSON。
- `title` 为空。
- `blocks` 缺失或为空。
- 某个块包含不支持的 `type`。
- 标题层级不在 1 到 6 的范围内。
- 表格行的列数不一致。
- 表格既没有标题（headers）也没有数据行（rows）。
- 源表格被展平成了单个段落，而不是以表格或结构化列表的形式存在。
- 代码块为空。
- 代码块被转换成了普通段落，而非代码。
- 图片块缺少 `local_path`，或引用的本地文件不存在。
- 本地图片文件为空（大小为 0）。
- 插入媒体后，渲染出的 Docx 仍包含 `WIKI_TO_FEISHU_IMAGE_` 占位符。
- 最终的飞书 Docx 图片数量少于 `quality-report.json.summary.images`。

## 警告 (Warnings)

除非用户要求严格的还原度，否则警告不会阻塞上传：

- 标题层级跳跃超过一级（例如从 H1 直接跳到 H3）。
- 表格缺失 headers。
- 标题包含转义的 Markdown 伪影（如 `\*1、`）且已被规范化。
- 代码块语言（language）未知。
- 图片没有替代文本（alt text）。
- 不支持的 Wiki 宏被转换为了文本。
- 缺失源 Wiki URL。

## 重试行为 (Retry Behavior)

Node 脚本仅报告验证结果，它不会调用模型。

调用 Agent 决定是否重试转换。如果停止重试且阻塞性错误依然存在，则必须询问用户是否上传已知存在问题的版本。

## 报告要求 (Report Requirements)

`quality-report.json` 必须包含：

- `status`：`pass` 或 `fail`。
- `summary`：包含标题、表格、代码块、图片、警告和错误数量的计数。
- `errors`：机器可读的阻塞性问题。
- `warnings`：机器可读的非阻塞性问题。

对用户的最终响应必须用通俗的语言概括该报告。

## 飞书验证要求 (Feishu Verification Requirements)

上传后，获取飞书 Docx 并验证：

- 该文档是一个 Docx 文档链接，而不是云空间 Markdown 文件的链接。
- Markdown 语法已被正确渲染，而不是作为原始语法文本显示。
- 没有残留的 `WIKI_TO_FEISHU_IMAGE_` 占位符。
- 飞书文档包含制造预期数量的 `<img>` 块。
- 重要的需求章节未被表示为一整段超长文本。
