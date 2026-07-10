---
name: wiki-to-feishu
description: 将 Wiki 页面（特别是通过 opencli 读取的 Confluence 页面）转换为带有质量关卡（Quality Gates）的飞书/Lark 文档。当用户请求迁移、复制、转换或上传 Wiki/Confluence 页面到飞书，并需要保留标题、表格、代码块和图像时使用。在转换 Wiki 内容之前，也用于检查 opencli、浏览器捕获支持或 lark-cli 等依赖项。
---

# Wiki to Feishu (Wiki 转飞书)

通过包含质量关卡的工作流，将 Wiki 页面转换为飞书文档：

1. 使用 `opencli` 读取源 Wiki 页面。
2. 将捕获的内容转换为结构化的 JSON。
3. 验证标题、表格、代码块和图片。
4. 仅在验证通过后，渲染面向 Docx 的 Markdown 文档。
5. 使用 `lark-cli docs +create` 创建飞书 Docx 文档。
6. 将本地图片插入到 Docx 中，并移除图片占位符。
7. 获取飞书分段（section），并修复任何被展平的复杂 Wiki 表格。

本 skill 与工具无关。请勿在生成的制品中限制或提及 Codex 特定的行为。调用此 skill 的 Agent 可以是 Codex、Claude Code、Agy 或其他兼容的 Agent。

## 必要参考文档

在执行操作前阅读这些文件：

- [dependency-setup.md](file:///D:/PJ/wiki-to-feishu/references/dependency-setup.md) 了解依赖检查和用户授权规则。
- [conversion-contract.md](file:///D:/PJ/wiki-to-feishu/references/conversion-contract.md) 在生成 `converted.json` 之前阅读。
- [quality-gates.md](file:///D:/PJ/wiki-to-feishu/references/quality-gates.md) 在决定是否允许上传之前阅读。

使用 [wiki-to-feishu.mjs](file:///D:/PJ/wiki-to-feishu/scripts/wiki-to-feishu.mjs) 执行确定性检查、运行工作区初始化、JSON 验证、图片检查、报告生成和 Markdown 渲染。

## 工作流

### 1. 确认输入

接受一个 Wiki URL，优选 Confluence 页面 URL，例如：

```text
https://wiki.example.com/pages/viewpage.action?pageId=123456
```

如果用户提供了标题覆盖（title override）或飞书目标文件夹，请保留这些信息供上传步骤使用。

### 2. 检查环境

运行：

```bash
node scripts/wiki-to-feishu.mjs check
```

如果缺少 `opencli` 或 `lark-cli`，请向用户解释它们的用途，并在安装任何内容之前询问用户。

对于浏览器扩展或浏览器登录捕获支持，进行检测和引导。不要在未经用户同意的情况下静默安装浏览器扩展。

### 3. 创建运行工作区

运行：

```bash
node scripts/wiki-to-feishu.mjs init-run "<wiki-url>" --title "<optional-title>"
```

该脚本会在 `.wiki-to-feishu-runs/` 下创建一个目录并写入 `input.json`。

### 4. 捕获 Wiki 内容

使用 `opencli` 读取 Wiki 页面。首选能够保留文档结构 and 图片的输出方式。

将捕获的内容保存到运行目录中：

- 当 Markdown 可用时，保存为 `raw.md`。
- 当 HTML 可用时，保存为 `raw.html`。
- `assets/` 目录用于存放 `opencli` 导出的图片。

如果存在图片，首选使用 `opencli` 或浏览器登录捕获来导出它们。直接进行未经身份验证的下载可能会由于 Confluence 内部资产保护而失败。

### 5. 准备转换

运行：

```bash
node scripts/wiki-to-feishu.mjs prepare-conversion "<run-dir>"
```

这将写入 `conversion-input.md`，调用此 skill 的 Agent 必须参考 [conversion-contract.md](file:///D:/PJ/wiki-to-feishu/references/conversion-contract.md) 将其转换为 `converted.json`。

### 6. 转换为结构化 JSON

在运行目录中生成 `converted.json`。此时先不要上传。

严格遵循转换契约，以确保确定性的验证：

- 保留标题层级。
- 保留表格的行和列。
- 保留代码块的换行和缩进。
- 表示每一张图片，并在可能时将其指向 `assets/` 中的本地文件。

### 7. 验证与渲染

运行：

```bash
node scripts/wiki-to-feishu.mjs validate "<run-dir>"
```

如果缺失的图片具有远程 `src` 值且没有本地文件，可以尝试运行：

```bash
node scripts/wiki-to-feishu.mjs resolve-images "<run-dir>"
node scripts/wiki-to-feishu.mjs validate "<run-dir>"
```

如果直接下载图片返回登录页面或无效的图片文件，请使用已加载 Wiki 页面的打开浏览器会话，并从浏览器网络缓存中导入图片内容：

```bash
node scripts/wiki-to-feishu.mjs import-network-images "<run-dir>" --session "<opencli-browser-session>" --tab "<tab-id>"
node scripts/wiki-to-feishu.mjs validate "<run-dir>"
```

如果验证通过，渲染 Docx 上传源：

```bash
node scripts/wiki-to-feishu.mjs render-docx-md "<run-dir>"
node scripts/wiki-to-feishu.mjs report "<run-dir>"
```

这将创建 `lark-docx.md` 和 `quality-report.json`。

### 8. 使用 lark-cli 上传

只有在验证通过后，才能从 `lark-docx.md` 创建真正的飞书 Docx 文档。

使用 `docs +create`，而不是 `markdown +create`：

```bash
lark-cli docs +create --api-version v2 --doc-format markdown --content @./lark-docx.md
```

在最终交付时，**不要**使用 `lark-cli markdown +create`。该命令会创建一个云空间 Markdown 文件，其中许多 Markdown 语法在用户端文件查看器中可能无法正常渲染。

`render-docx-md` 会故意写入形如 `【WIKI_TO_FEISHU_IMAGE_01】` 的图片占位符，而不是 Markdown 图片语法。创建 Docx 后：

1. 使用 `lark-cli docs +media-insert` 插入 `converted.json` 中的每个本地图片。
2. 当 CLI 支持目标块（target block）时，将图片放置在匹配的占位符附近；否则追加（append），然后根据需要手动移动或清理。
3. 删除所有 `WIKI_TO_FEISHU_IMAGE_XX` 占位符段落。
4. 获取文档并验证图片数量是否等于 `quality-report.json.summary.images`。

如果图片缺失，转换尚未完成。不要将文档作为最终结果呈报。

默认行为：

- 使用来自 `converted.json` 的 Wiki 标题。
- 尊重用户提供的标题覆盖（如果有的话）。
- 除非用户提供了文件夹的 Token 或 URL，否则在用户的默认飞书文档位置创建该文档。

在可行的情况下，将上传输出保存到 `upload-result.json`。

立即验证文档标题。某些 `docs +create --doc-format markdown` 运行后可能会将 Docx `<title>` 留为 `Untitled`，即使第一个 H1 是正确的：

```bash
lark-cli docs +fetch --api-version v2 --doc "<doc-token-or-url>" --scope keyword --keyword "<expected-title-prefix>" --detail with-ids
```

如果 `<title>` 为 `Untitled`，请在返回链接之前将其替换为最终的文档标题：

```bash
lark-cli docs +update --api-version v2 --doc "<doc-token-or-url>" --command str_replace --pattern "Untitled" --content "<final-title>"
```

### 9. 上传后修复流程

在返回文档前，始终检查已上传的 Docx：

```bash
lark-cli docs +fetch --api-version v2 --doc "<doc-token-or-url>" --scope outline --max-depth 3 --detail with-ids
```

然后使用 `--scope section --start-block-id <heading-id> --detail with-ids` 获取可疑的段落。

如果出现以下任何问题，使用 `lark-cli docs +update` 修复 Docx：

- 标题渲染为 `\*1、...`、`*1、...` 或包含转义的 Markdown 伪影。
- 文档 `<title>` 仍为 `Untitled`，而第一个 H1 已经有了真实的标题。
- Confluence 表格被展平成一个长段落。
- Markdown 管道表格（pipe tables）仍以纯文本形式显示。
- 媒体插入后，图片占位符仍然残留。
- 某个分段中包含多个本应是表格或列表的超长段落。

对于被展平的复杂表格，首选以下安全操作顺序：

1. 使用 `block_insert_after` 在分段标题后插入一个干净的 XML 结构。
2. 保留现有的图片块，除非用户明确要求将其删除。
3. 仅使用 `block_delete` 删除旧的畸形块。
4. 再次获取分段，以验证没有残留的畸形 Markdown/表格残留物。

### 10. 返回结果

返回：

- 飞书文档链接。
- 质量摘要（Quality summary）。
- 图片验证摘要。
- 任何警告或非阻塞性问题。

如果验证存在阻塞性错误，请勿静默上传。调用 Agent 可能会重试转换。如果决定不重试，请询问用户是否上传已知存在问题的版本。

## 失败规则

- 当 `quality-report.json` 的 `status` 为 `"fail"` 时，切勿上传。
- 不要隐藏缺失的图片、畸形的表格、空代码块或无效的 JSON。
- 不要将代码块重写为普通文本。
- 不要将标题扁平化为普通段落。
- 在 `lark-cli` 上传成功前，切勿声称飞书文档已完成。
- 当图片占位符仍然存在，或者飞书图片数量少于源图片数量时，切勿声称飞书文档已完成。
