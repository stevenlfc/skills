# Dependency Setup (依赖配置)

在转换前检查依赖项。

## 必需工具

### opencli

用途：

- 通过现有的浏览器或 CLI 能力读取内部 Wiki 页面。
- 在可能的情况下保留结构并导出图片。

如果缺失：

1. 向用户解释需要 `opencli` 来读取 Wiki 页面。
2. 在安装前征求用户同意。
3. 安装完成后，运行 doctor/check 命令（如果可用）。

### 浏览器扩展或浏览器捕获支持 (Browser Extension or Browser Capture Support)

用途：

- 复用用户已登录的浏览器会话，以读取内部 Wiki 页面和受保护的图片。

如果缺失：

1. 向用户解释内部 Wiki 页面可能需要浏览器的登录状态。
2. 提供或打开安装指南（如果可用）。
3. 在用户安装后，验证捕获是否正常工作。

请勿静默安装浏览器扩展。

### lark-cli

用途：

- 将渲染后的 Markdown 文档创建或上传至飞书。

如果缺失：

1. 向用户解释仅在上传步骤中需要 `lark-cli`。
2. 在安装前征求用户同意。
3. 安装完成后，运行 doctor/check 命令（如果可用）。

## 征求同意规则 (Consent Rules)

- 在安装任何 CLI 工具前，必须征得用户同意。
- 当较窄范围的命令已足够时，不要请求过于宽泛的权限。
- 请勿静默安装浏览器扩展。
- 如果安装失败，在可能的情况下，继续使用本地转换包。

## 降级模式 (Degraded Mode)

如果 `opencli` 无法读取页面，请要求用户提供导出的 HTML 或 Markdown，并将其作为 `raw.html` 或 `raw.md` 保存到运行目录中。

如果 `lark-cli` 不可用，仍需生成以下文件：

- `converted.json`
- `lark-doc.md`
- `quality-report.json`

然后告知用户，由于缺少依赖，上传已被阻止。
