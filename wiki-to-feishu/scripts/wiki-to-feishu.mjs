#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { basename, dirname, isAbsolute, join, normalize, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const skillRoot = normalize(join(__dirname, ".."));
const defaultRunsRoot = join(process.cwd(), ".wiki-to-feishu-runs");

function usage() {
  console.log(`wiki-to-feishu

Usage:
  node scripts/wiki-to-feishu.mjs check [--json]
  node scripts/wiki-to-feishu.mjs init-run <url> [--title <title>] [--out <dir>]
  node scripts/wiki-to-feishu.mjs prepare-conversion <runDir>
  node scripts/wiki-to-feishu.mjs convert-md <runDir>
  node scripts/wiki-to-feishu.mjs resolve-images <runDir>
  node scripts/wiki-to-feishu.mjs import-network-images <runDir> --session <name> --tab <tabId>
  node scripts/wiki-to-feishu.mjs validate <runDir>
  node scripts/wiki-to-feishu.mjs render-md <runDir>
  node scripts/wiki-to-feishu.mjs render-docx-md <runDir>
  node scripts/wiki-to-feishu.mjs report <runDir>
`);
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (!item.startsWith("--")) {
      args._.push(item);
      continue;
    }
    const key = item.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

function fail(message, code = 1) {
  console.error(message);
  process.exit(code);
}

function commandExists(command) {
  const direct = process.platform === "win32" ? `${command}.cmd` : command;
  const checker = process.platform === "win32" ? "where" : "command";
  const args = process.platform === "win32" ? [command] : ["-v", command];
  const result = spawnSync(checker, args, { encoding: "utf8", shell: process.platform !== "win32" });
  if (result.status === 0) return true;
  for (const dir of fallbackBinDirs()) {
    if (existsSync(join(dir, direct)) || existsSync(join(dir, command))) return true;
  }
  return false;
}

function fallbackBinDirs() {
  const dirs = [];
  if (process.platform === "win32" && process.env.APPDATA) {
    dirs.push(join(process.env.APPDATA, "npm"));
  }
  if (process.env.npm_config_prefix) {
    dirs.push(process.env.npm_config_prefix);
    dirs.push(join(process.env.npm_config_prefix, "bin"));
  }
  return dirs;
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (error) {
    throw new Error(`Cannot read JSON ${path}: ${error.message}`);
  }
}

function writeJson(path, data) {
  writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}

function ensureDir(path) {
  mkdirSync(path, { recursive: true });
}

function slug(input) {
  return String(input || "wiki")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80) || "wiki";
}

function timestamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

function pageIdFromUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.searchParams.get("pageId") || parsed.searchParams.get("id") || "";
  } catch {
    return "";
  }
}

function runDirFromArg(value) {
  if (!value) fail("Missing runDir.");
  return isAbsolute(value) ? normalize(value) : normalize(join(process.cwd(), value));
}

function check() {
  const nodeMajor = Number(process.versions.node.split(".")[0]);
  const checks = [
    { name: "node", ok: nodeMajor >= 18, detail: process.version },
    { name: "opencli", ok: commandExists("opencli"), detail: "required for Wiki capture" },
    { name: "lark-cli", ok: commandExists("lark-cli"), detail: "required for Feishu upload" }
  ];
  const browserHint = checks.find((item) => item.name === "opencli")?.ok
    ? "Run opencli doctor/browser checks if protected Wiki capture fails."
    : "Install opencli before checking browser capture support.";
  return { status: checks.every((item) => item.ok) ? "pass" : "fail", checks, browser_capture: { status: "manual-check", detail: browserHint } };
}

function initRun(url, args) {
  if (!url) fail("Missing Wiki URL.");
  const id = pageIdFromUrl(url);
  const name = `${timestamp()}-${id ? `page-${id}` : slug(new URL(url).hostname)}`;
  const root = args.out ? runDirFromArg(args.out) : join(defaultRunsRoot, name);
  ensureDir(join(root, "assets"));
  const input = {
    source_url: url,
    page_id: id || null,
    title_override: args.title || null,
    created_at: new Date().toISOString(),
    skill_root: skillRoot
  };
  writeJson(join(root, "input.json"), input);
  console.log(root);
}

function prepareConversion(runDir) {
  const inputPath = join(runDir, "input.json");
  if (!existsSync(inputPath)) fail(`Missing ${inputPath}. Run init-run first.`);
  const input = readJson(inputPath);
  const rawMd = join(runDir, "raw.md");
  const rawHtml = join(runDir, "raw.html");
  let sourceType = "";
  let sourceText = "";
  if (existsSync(rawMd)) {
    sourceType = "markdown";
    sourceText = readFileSync(rawMd, "utf8");
  } else if (existsSync(rawHtml)) {
    sourceType = "html";
    sourceText = readFileSync(rawHtml, "utf8");
  } else {
    fail(`Missing raw.md or raw.html in ${runDir}. Capture the Wiki page with opencli first.`);
  }
  const contractPath = join(skillRoot, "references", "conversion-contract.md");
  const contract = readFileSync(contractPath, "utf8");
  const text = [
    "# Wiki to Feishu Conversion Input",
    "",
    `Source URL: ${input.source_url}`,
    input.title_override ? `Title override: ${input.title_override}` : "",
    `Source type: ${sourceType}`,
    "",
    "Use the following contract to produce converted.json:",
    "",
    contract,
    "",
    "## Captured Source",
    "",
    sourceText
  ].filter(Boolean).join("\n");
  writeFileSync(join(runDir, "conversion-input.md"), text, "utf8");
  console.log(join(runDir, "conversion-input.md"));
}

function convertMd(runDir) {
  const rawPath = join(runDir, "raw.md");
  if (!existsSync(rawPath)) fail(`Missing ${rawPath}.`);
  const input = existsSync(join(runDir, "input.json")) ? readJson(join(runDir, "input.json")) : {};
  const text = readFileSync(rawPath, "utf8");
  const lines = text.split(/\r?\n/);
  const blocks = [];
  let title = input.title_override || "";
  let paragraph = [];
  let inCode = false;
  let codeLang = "";
  let codeLines = [];

  const flushParagraph = () => {
    const content = paragraph.join("\n").trim();
    paragraph = [];
    if (!content) return;
    const imageMatch = content.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (imageMatch) {
      blocks.push(imageBlock(imageMatch[1], imageMatch[2], runDir));
    } else {
      blocks.push({ type: "paragraph", text: content });
    }
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].replace(/^\uFEFF/, "");
    const fence = line.match(/^```(.*)$/);
    if (fence) {
      if (inCode) {
        blocks.push({ type: "code_block", language: codeLang.trim(), code: codeLines.join("\n") });
        inCode = false;
        codeLang = "";
        codeLines = [];
      } else {
        flushParagraph();
        inCode = true;
        codeLang = fence[1] || "";
      }
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+?)\s*$/);
    if (heading) {
      flushParagraph();
      const level = heading[1].length;
      const headingText = cleanupHeadingText(heading[2]);
      if (!title && level === 1) title = headingText;
      blocks.push({ type: "heading", level, text: headingText });
      continue;
    }

    const table = tryReadTable(lines, i);
    if (table) {
      flushParagraph();
      blocks.push(table.block);
      i = table.nextIndex - 1;
      continue;
    }

    const image = line.match(/^!\[([^\]]*)\]\(([^)]+)\)\s*$/);
    if (image) {
      flushParagraph();
      blocks.push(imageBlock(image[1], image[2], runDir));
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      continue;
    }
    paragraph.push(cleanupText(line));
  }
  if (inCode) blocks.push({ type: "code_block", language: codeLang.trim(), code: codeLines.join("\n") });
  flushParagraph();

  const doc = {
    title: title || "Wiki Document",
    source_url: input.source_url || "",
    blocks: blocks.filter((block) => block.type !== "paragraph" || block.text.trim())
  };
  writeJson(join(runDir, "converted.json"), doc);
  console.log(join(runDir, "converted.json"));
}

function tryReadTable(lines, start) {
  const broken = tryReadBrokenConfluenceTable(lines, start);
  if (broken) return broken;
  if (!isTableLine(lines[start])) return null;
  const collected = [];
  let i = start;
  while (i < lines.length && (isTableLine(lines[i]) || !lines[i].trim())) {
    if (isTableLine(lines[i])) collected.push(lines[i]);
    i += 1;
  }
  if (collected.length < 2) return null;
  const rows = collected.map(parseTableLine).filter((row) => row.length);
  const separatorIndex = rows.findIndex((row) => row.every((cell) => /^:?-{3,}:?$/.test(cell.trim())));
  if (separatorIndex < 0) return null;
  const headers = rows[separatorIndex - 1] || [];
  const body = rows.slice(separatorIndex + 1);
  return { block: normalizeTableBlock({ type: "table", headers, rows: body }), nextIndex: i };
}

function tryReadBrokenConfluenceTable(lines, start) {
  if (String(lines[start] || "").trim() !== "|") return null;
  let separatorIndex = -1;
  for (let i = start + 1; i < Math.min(lines.length, start + 30); i += 1) {
    if (isSeparatorLine(lines[i])) {
      separatorIndex = i;
      break;
    }
  }
  if (separatorIndex < 0) return null;

  const headers = [];
  let current = [];
  for (let i = start + 1; i < separatorIndex; i += 1) {
    const line = String(lines[i] || "").trim();
    if (!line) continue;
    if (/^#{1,6}\s+/.test(line) || /<table\b/i.test(line)) return null;
    if (line === "|") {
      const value = current.join(" ").trim();
      if (value) headers.push(cleanupText(value));
      current = [];
      continue;
    }
    if (!isTableLine(line)) current.push(line);
  }
  const value = current.join(" ").trim();
  if (value) headers.push(cleanupText(value));
  if (!headers.length) return null;

  const rows = [];
  let i = separatorIndex + 1;
  while (i < lines.length && isTableLine(lines[i])) {
    rows.push(parseTableLine(lines[i]));
    i += 1;
  }
  return { block: normalizeTableBlock({ type: "table", headers, rows }), nextIndex: i };
}

function normalizeTableBlock(block) {
  const width = block.headers.length || Math.max(0, ...block.rows.map((row) => row.length));
  if (!width) return block;
  block.rows = block.rows.map((row) => {
    if (row.length >= width) return row;
    return [...row, ...Array.from({ length: width - row.length }, () => "")];
  });
  return block;
}

function isTableLine(line) {
  return /^\s*\|/.test(line || "");
}

function isSeparatorLine(line) {
  return isTableLine(line) && parseTableLine(line).every((cell) => /^:?-{3,}:?$/.test(cell.trim()));
}

function parseTableLine(line) {
  return String(line)
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cleanupText(cell.trim()));
}

function cleanupText(value) {
  return String(value || "").replace(/\uFFFD/g, "?").trim();
}

function cleanupHeadingText(value) {
  return cleanupText(value)
    .replace(/^\\?\*+\s*(?=\d+[、.．）)])/u, "")
    .replace(/^\\?\*+\s+/, "")
    .trim();
}

function imageBlock(alt, src, runDir) {
  const cleanSrc = String(src || "").trim();
  const local = cleanSrc && !/^https?:\/\//i.test(cleanSrc) ? cleanSrc : "";
  const resolved = local ? resolveInside(runDir, local) : null;
  return {
    type: "image",
    alt: cleanupText(alt || "image"),
    src: cleanSrc,
    local_path: resolved && existsSync(resolved) ? normalizePathForMd(local) : local
  };
}

function validate(runDir) {
  const convertedPath = join(runDir, "converted.json");
  const reportPath = join(runDir, "quality-report.json");
  const errors = [];
  const warnings = [];
  const summary = { headings: 0, tables: 0, code_blocks: 0, images: 0, warnings: 0, errors: 0 };
  let doc = null;
  try {
    doc = readJson(convertedPath);
  } catch (error) {
    const report = makeReport("fail", summary, [{ code: "invalid_json", message: error.message }], warnings);
    writeJson(reportPath, report);
    console.log(reportPath);
    process.exitCode = 2;
    return;
  }

  if (!doc || typeof doc !== "object") errors.push(err("invalid_root", "Root must be an object."));
  if (!nonEmpty(doc.title)) errors.push(err("missing_title", "title must be a non-empty string."));
  if (!nonEmpty(doc.source_url)) warnings.push(warn("missing_source_url", "source_url is missing."));
  if (!Array.isArray(doc.blocks) || doc.blocks.length === 0) {
    errors.push(err("missing_blocks", "blocks must be a non-empty array."));
  }

  let previousHeading = 0;
  for (const [index, block] of (doc.blocks || []).entries()) {
    const path = `blocks[${index}]`;
    if (!block || typeof block !== "object") {
      errors.push(err("invalid_block", `${path} must be an object.`, path));
      continue;
    }
    switch (block.type) {
      case "heading":
        summary.headings += 1;
        validateHeading(block, path, errors, warnings, previousHeading);
        previousHeading = Number(block.level);
        break;
      case "paragraph":
        if (!nonEmpty(block.text)) warnings.push(warn("empty_paragraph", `${path}.text is empty.`, path));
        break;
      case "table":
        summary.tables += 1;
        validateTable(block, path, errors, warnings);
        break;
      case "code_block":
        summary.code_blocks += 1;
        validateCodeBlock(block, path, errors, warnings);
        break;
      case "image":
        summary.images += 1;
        validateImage(block, path, runDir, errors, warnings);
        break;
      case "link":
        if (!nonEmpty(block.text)) warnings.push(warn("missing_link_text", `${path}.text is empty.`, path));
        if (!nonEmpty(block.url)) errors.push(err("missing_link_url", `${path}.url is required.`, path));
        break;
      case "warning":
        if (!nonEmpty(block.text)) warnings.push(warn("empty_warning", `${path}.text is empty.`, path));
        break;
      default:
        errors.push(err("unsupported_block_type", `${path}.type is unsupported: ${block.type}`, path));
    }
  }

  summary.warnings = warnings.length;
  summary.errors = errors.length;
  const report = makeReport(errors.length ? "fail" : "pass", summary, errors, warnings);
  writeJson(reportPath, report);
  console.log(reportPath);
  if (errors.length) process.exitCode = 2;
}

function validateHeading(block, path, errors, warnings, previousHeading) {
  const level = Number(block.level);
  if (!Number.isInteger(level) || level < 1 || level > 6) errors.push(err("invalid_heading_level", `${path}.level must be 1-6.`, path));
  if (!nonEmpty(block.text)) errors.push(err("missing_heading_text", `${path}.text is required.`, path));
  if (previousHeading > 0 && level > previousHeading + 1) warnings.push(warn("heading_level_jump", `${path}.level jumps from ${previousHeading} to ${level}.`, path));
}

function validateTable(block, path, errors, warnings) {
  const headers = Array.isArray(block.headers) ? block.headers : [];
  const rows = Array.isArray(block.rows) ? block.rows : [];
  if (!headers.length && !rows.length) errors.push(err("empty_table", `${path} has neither headers nor rows.`, path));
  if (!headers.length) warnings.push(warn("missing_table_headers", `${path}.headers is empty.`, path));
  const width = headers.length || (Array.isArray(rows[0]) ? rows[0].length : 0);
  for (const [rowIndex, row] of rows.entries()) {
    if (!Array.isArray(row)) {
      errors.push(err("invalid_table_row", `${path}.rows[${rowIndex}] must be an array.`, `${path}.rows[${rowIndex}]`));
    } else if (row.length !== width) {
      errors.push(err("table_column_mismatch", `${path}.rows[${rowIndex}] has ${row.length} columns; expected ${width}.`, `${path}.rows[${rowIndex}]`));
    }
  }
}

function validateCodeBlock(block, path, errors, warnings) {
  if (!nonEmpty(block.code)) errors.push(err("empty_code_block", `${path}.code is empty.`, path));
  if (!("language" in block) || !String(block.language || "").trim()) warnings.push(warn("missing_code_language", `${path}.language is missing.`, path));
  if (nonEmpty(block.code) && !block.code.includes("\n") && /\b(this code|the following|it does|this command)\b/i.test(block.code)) {
    errors.push(err("code_looks_like_prose", `${path}.code looks like prose.`, path));
  }
}

function validateImage(block, path, runDir, errors, warnings) {
  if (!nonEmpty(block.alt)) warnings.push(warn("missing_image_alt", `${path}.alt is missing.`, path));
  if (!nonEmpty(block.local_path)) {
    errors.push(err("missing_image_local_path", `${path}.local_path is required for upload.`, path));
    return;
  }
  const imagePath = resolveInside(runDir, block.local_path);
  if (!imagePath) {
    errors.push(err("image_path_outside_run", `${path}.local_path must stay inside run directory.`, path));
    return;
  }
  if (!existsSync(imagePath)) {
    errors.push(err("missing_image_file", `${path}.local_path does not exist: ${block.local_path}`, path));
    return;
  }
  if (statSync(imagePath).size <= 0) errors.push(err("empty_image_file", `${path}.local_path is empty: ${block.local_path}`, path));
  if (!isImageFile(imagePath)) errors.push(err("invalid_image_file", `${path}.local_path is not a valid image file: ${block.local_path}`, path));
}

function renderMd(runDir) {
  const reportPath = join(runDir, "quality-report.json");
  if (!existsSync(reportPath)) fail("Missing quality-report.json. Run validate first.");
  const report = readJson(reportPath);
  if (report.status !== "pass") fail("Quality gate failed. Refusing to render lark-doc.md.", 2);
  const doc = readJson(join(runDir, "converted.json"));
  const lines = [`# ${escapeMdText(doc.title)}`, ""];
  for (const block of doc.blocks) {
    switch (block.type) {
      case "heading":
        lines.push(`${"#".repeat(block.level)} ${escapeMdText(block.text)}`, "");
        break;
      case "paragraph":
        lines.push(block.text, "");
        break;
      case "table":
        lines.push(...renderTable(block), "");
        break;
      case "code_block":
        lines.push(`\`\`\`${block.language || ""}`, block.code || "", "```", "");
        break;
      case "image":
        lines.push(`![${escapeMdAlt(block.alt || "image")}](${normalizePathForMd(block.local_path)})`, "");
        break;
      case "link":
        lines.push(`[${escapeMdText(block.text)}](${block.url})`, "");
        break;
      case "warning":
        lines.push(`> ${block.text}`, "");
        break;
    }
  }
  const out = join(runDir, "lark-doc.md");
  writeFileSync(out, `${lines.join("\n").replace(/\n{3,}/g, "\n\n").trim()}\n`, "utf8");
  console.log(out);
}

function renderDocxMd(runDir) {
  const reportPath = join(runDir, "quality-report.json");
  if (!existsSync(reportPath)) fail("Missing quality-report.json. Run validate first.");
  const reportData = readJson(reportPath);
  if (reportData.status !== "pass") fail("Quality gate failed. Refusing to render lark-docx.md.", 2);
  const doc = readJson(join(runDir, "converted.json"));
  const lines = [`# ${doc.title}`, ""];
  let imageIndex = 0;
  let seenRealContent = false;
  for (const block of doc.blocks) {
    if (shouldSkipForDocx(block, doc, seenRealContent)) continue;
    if (block.type === "heading" && block.level === 1 && block.text.trim() === doc.title.trim()) continue;
    if (block.type === "heading") seenRealContent = true;
    switch (block.type) {
      case "heading":
        lines.push(`${"#".repeat(block.level)} ${escapeMdText(block.text)}`, "");
        break;
      case "paragraph":
        lines.push(cleanDocxParagraph(block.text), "");
        break;
      case "table":
        lines.push(...renderTable(block), "");
        break;
      case "code_block":
        lines.push(`\`\`\`${block.language || ""}`, block.code || "", "```", "");
        break;
      case "image":
        imageIndex += 1;
        lines.push(`【WIKI_TO_FEISHU_IMAGE_${String(imageIndex).padStart(2, "0")}】`, "");
        break;
      case "link":
        lines.push(`[${escapeMdText(block.text)}](${block.url})`, "");
        break;
      case "warning":
        lines.push(`> ${block.text}`, "");
        break;
    }
  }
  const out = join(runDir, "lark-docx.md");
  writeFileSync(out, `${lines.join("\n").replace(/\n{3,}/g, "\n\n").trim()}\n`, "utf8");
  console.log(out);
}

function shouldSkipForDocx(block, doc, seenRealContent) {
  if (!block || !block.type) return true;
  const text = String(block.text || "");
  if (!seenRealContent) {
    if (text.includes("转至元数据") || text.includes("page-metadata") || /^-\s*\d/.test(text.trim())) return true;
    if (text.startsWith("> 原文链接:")) return false;
  }
  if (text.includes("添加评论") || text.includes("赞成") || text.includes("编辑标签")) return true;
  if (text.trim() === "---") return true;
  return false;
}

function cleanDocxParagraph(value) {
  return String(value || "")
    .replace(/^>\s*原文链接:/, "原文链接:")
    .replace(/<[^>]+>/g, "")
    .trim();
}

function renderTable(block) {
  const headers = Array.isArray(block.headers) && block.headers.length ? block.headers : block.rows[0].map((_, i) => `Column ${i + 1}`);
  const rows = Array.isArray(block.headers) && block.headers.length ? block.rows : block.rows.slice(1);
  const line = (cells) => `| ${cells.map((cell) => String(cell ?? "").replace(/\|/g, "\\|")).join(" | ")} |`;
  return [block.caption ? `_${block.caption}_` : "", line(headers), line(headers.map(() => "---")), ...rows.map(line)].filter(Boolean);
}

async function resolveImages(runDir) {
  const convertedPath = join(runDir, "converted.json");
  const doc = readJson(convertedPath);
  ensureDir(join(runDir, "assets"));
  let changed = false;
  for (const [index, block] of (doc.blocks || []).entries()) {
    if (block.type !== "image" || block.local_path && existsSync(resolveInside(runDir, block.local_path) || "")) continue;
    if (!nonEmpty(block.src) || !/^https?:\/\//i.test(block.src)) continue;
    const ext = extensionFromUrl(block.src) || ".img";
    const file = `image-${String(index + 1).padStart(3, "0")}${ext}`;
    const localPath = join("assets", file);
    const target = join(runDir, localPath);
    try {
      await download(block.src, target);
      block.local_path = localPath.replace(/\\/g, "/");
      changed = true;
      console.log(`downloaded ${block.src} -> ${block.local_path}`);
    } catch (error) {
      console.error(`failed ${block.src}: ${error.message}`);
    }
  }
  if (changed) writeJson(convertedPath, doc);
}

function importNetworkImages(runDir, args) {
  if (!args.session || !args.tab) fail("import-network-images requires --session <name> --tab <tabId>.");
  const convertedPath = join(runDir, "converted.json");
  const doc = readJson(convertedPath);
  ensureDir(join(runDir, "assets"));
  let imported = 0;
  const seen = new Map();
  for (const [index, block] of (doc.blocks || []).entries()) {
    if (block.type !== "image" || !nonEmpty(block.src)) continue;
    if (block.local_path) {
      const existing = resolveInside(runDir, block.local_path);
      if (existing && existsSync(existing) && isImageFile(existing)) continue;
    }
    const key = networkKeyFromUrl(block.src);
    if (!key) continue;
    const detail = opencliNetworkDetail(args.session, args.tab, key);
    if (!detail || detail.status !== 200 || !String(detail.ct || "").startsWith("image/") || !String(detail.body || "").startsWith("base64:")) continue;
    const baseName = safeImageName(block.src, index, seen);
    const localPath = join("assets", baseName);
    const target = join(runDir, localPath);
    writeFileSync(target, Buffer.from(detail.body.slice("base64:".length), "base64"));
    if (!isImageFile(target)) {
      console.error(`network body was not a valid image for ${block.src}`);
      continue;
    }
    block.local_path = localPath.replace(/\\/g, "/");
    imported += 1;
    console.log(`imported ${block.src} -> ${block.local_path}`);
  }
  writeJson(convertedPath, doc);
  console.log(`imported_count=${imported}`);
}

function opencliNetworkDetail(session, tab, key) {
  const opencli = resolveCommand("opencli");
  if (!opencli) fail("Cannot find opencli.");
  const result = spawnSync(opencli.command, [
    ...opencli.prefixArgs,
    "browser",
    session,
    "network",
    "--tab",
    tab,
    "--detail",
    key,
    "--max-body",
    "0"
  ], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  if (result.status !== 0) {
    console.error(result.error?.message || result.stderr || result.stdout);
    return null;
  }
  const jsonStart = result.stdout.indexOf("{");
  const jsonEnd = result.stdout.lastIndexOf("}");
  if (jsonStart < 0 || jsonEnd < jsonStart) return null;
  try {
    return JSON.parse(result.stdout.slice(jsonStart, jsonEnd + 1));
  } catch (error) {
    console.error(`Cannot parse opencli network detail for ${key}: ${error.message}`);
    return null;
  }
}

function resolveCommand(command) {
  if (process.platform === "win32" && command === "opencli" && process.env.APPDATA) {
    const main = join(process.env.APPDATA, "npm", "node_modules", "@jackwener", "opencli", "dist", "src", "main.js");
    if (existsSync(main)) return { command: "node", prefixArgs: [main] };
  }
  const direct = process.platform === "win32" ? `${command}.cmd` : command;
  for (const dir of ["", ...fallbackBinDirs()]) {
    const candidate = dir ? join(dir, direct) : direct;
    if (!dir || existsSync(candidate)) {
      return process.platform === "win32" && candidate.endsWith(".cmd")
        ? { command: candidate, prefixArgs: [] }
        : { command: candidate, prefixArgs: [] };
    }
  }
  return null;
}

function networkKeyFromUrl(value) {
  try {
    const url = new URL(value);
    return `GET ${url.host}${url.pathname}`;
  } catch {
    return "";
  }
}

function safeImageName(src, index, seen) {
  let name = "image";
  try {
    name = basename(new URL(src).pathname) || name;
  } catch {
    name = `image-${index + 1}.png`;
  }
  name = name.replace(/[^a-zA-Z0-9._-]+/g, "-");
  if (!/\.[a-z0-9]{2,5}$/i.test(name)) name += ".png";
  const count = (seen.get(name) || 0) + 1;
  seen.set(name, count);
  if (count === 1) return name;
  const dot = name.lastIndexOf(".");
  return `${name.slice(0, dot)}-${count}${name.slice(dot)}`;
}

function report(runDir) {
  const reportPath = join(runDir, "quality-report.json");
  if (!existsSync(reportPath)) fail("Missing quality-report.json. Run validate first.");
  const data = readJson(reportPath);
  console.log(`status: ${data.status}`);
  console.log(`headings: ${data.summary.headings}`);
  console.log(`tables: ${data.summary.tables}`);
  console.log(`code_blocks: ${data.summary.code_blocks}`);
  console.log(`images: ${data.summary.images}`);
  console.log(`errors: ${data.summary.errors}`);
  console.log(`warnings: ${data.summary.warnings}`);
  if (data.errors.length) {
    console.log("\nBlocking errors:");
    for (const item of data.errors) console.log(`- ${item.code}: ${item.message}`);
  }
  if (data.warnings.length) {
    console.log("\nWarnings:");
    for (const item of data.warnings) console.log(`- ${item.code}: ${item.message}`);
  }
}

function makeReport(status, summary, errors, warnings) {
  return { status, summary: { ...summary, errors: errors.length, warnings: warnings.length }, errors, warnings };
}

function err(code, message, path = "") {
  return { severity: "error", code, message, path };
}

function warn(code, message, path = "") {
  return { severity: "warning", code, message, path };
}

function nonEmpty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function resolveInside(root, child) {
  const resolved = normalize(join(root, child));
  const rel = relative(root, resolved);
  if (rel.startsWith("..") || isAbsolute(rel)) return null;
  return resolved;
}

function normalizePathForMd(value) {
  return String(value || "").replace(/\\/g, "/");
}

function isImageFile(path) {
  const buffer = readFileSync(path);
  if (buffer.length < 4) return false;
  const hex = buffer.slice(0, 12).toString("hex");
  const ascii = buffer.slice(0, 12).toString("ascii");
  return (
    hex.startsWith("89504e47") ||
    hex.startsWith("ffd8ff") ||
    hex.startsWith("474946383761") ||
    hex.startsWith("474946383961") ||
    ascii.startsWith("RIFF") && buffer.slice(8, 12).toString("ascii") === "WEBP"
  );
}

function escapeMdText(value) {
  return String(value || "").replace(/\\/g, "\\\\").replace(/#/g, "\\#");
}

function escapeMdAlt(value) {
  return String(value || "").replace(/]/g, "\\]");
}

function extensionFromUrl(value) {
  try {
    const name = basename(new URL(value).pathname);
    const match = name.match(/\.[a-z0-9]{2,5}$/i);
    return match ? match[0] : "";
  } catch {
    return "";
  }
}

function download(url, target) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith("https:") ? httpsRequest : httpRequest;
    const req = client(url, { headers: { "user-agent": "wiki-to-feishu/1.0" } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        download(new URL(res.headers.location, url).toString(), target).then(resolve, reject);
        return;
      }
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode}`));
        res.resume();
        return;
      }
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        ensureDir(dirname(target));
        writeFileSync(target, Buffer.concat(chunks));
        resolve();
      });
    });
    req.on("error", reject);
    req.setTimeout(20000, () => {
      req.destroy(new Error("download timeout"));
    });
    req.end();
  });
}

async function main() {
  const [command, ...rest] = process.argv.slice(2);
  const args = parseArgs(rest);
  if (!command || command === "help" || command === "--help") {
    usage();
    return;
  }
  if (command === "check") {
    const data = check();
    if (args.json) console.log(JSON.stringify(data, null, 2));
    else {
      for (const item of data.checks) console.log(`${item.ok ? "OK" : "MISSING"} ${item.name} ${item.detail ? `- ${item.detail}` : ""}`);
      console.log(`INFO browser-capture - ${data.browser_capture.detail}`);
    }
    if (data.status !== "pass") process.exitCode = 2;
    return;
  }
  if (command === "init-run") return initRun(args._[0], args);
  if (command === "prepare-conversion") return prepareConversion(runDirFromArg(args._[0]));
  if (command === "convert-md") return convertMd(runDirFromArg(args._[0]));
  if (command === "validate") return validate(runDirFromArg(args._[0]));
  if (command === "render-md") return renderMd(runDirFromArg(args._[0]));
  if (command === "render-docx-md") return renderDocxMd(runDirFromArg(args._[0]));
  if (command === "resolve-images") return resolveImages(runDirFromArg(args._[0]));
  if (command === "import-network-images") return importNetworkImages(runDirFromArg(args._[0]), args);
  if (command === "report") return report(runDirFromArg(args._[0]));
  fail(`Unknown command: ${command}`);
}

main().catch((error) => fail(error.stack || error.message));
