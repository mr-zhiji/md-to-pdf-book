---
name: md-to-pdf-book
version: 1.0.0
description: "Convert Markdown chapter files into a professionally typeset PDF book, or convert a single HTML file directly to PDF. Use when the user wants to: convert Markdown to PDF, generate a PDF from .md files, compile chapters into a book PDF, export Markdown as PDF, convert HTML to PDF, render an HTML page as PDF, build a PDF book from markdown documents, create a printable book from notes or documentation. Trigger keywords: markdown to pdf, md to pdf, md to book, markdown book, html to pdf, html to pdf converter, convert html file to pdf, compile pdf, generate book pdf, export markdown pdf, build pdf from markdown, chapters to pdf, notes to book pdf, documentation to pdf, 生成书籍PDF, html转pdf."
description_zh: "将多个 Markdown 章节文件转换为排版精美的书籍级 PDF，或将单个 HTML 文件直接转换为 PDF。当用户想把 Markdown 文档转为 PDF 书籍、从多个 .md 文件生成 PDF、将笔记/文档/书稿编译为 PDF、导出 Markdown 为 PDF、把章节合并成书、将 HTML 文件转为 PDF、把网页保存为 PDF 时使用此技能。触发关键词：markdown 转 pdf、md 转 pdf、生成书籍 PDF、md to book、编译 PDF 书籍、笔记转书、文档转 PDF、章节合并 PDF、导出 PDF、生成电子书、书稿转 PDF、markdown 导出、打印 PDF、排版 PDF、html 转 pdf、html to pdf、html 文件转 pdf、网页转 pdf。"
---

# Markdown / HTML to PDF Book Generator

将 Markdown 文件集合转换为排版精美的 A4 书籍 PDF，或将单个 HTML 文件直接转为 PDF。

## 能力

- 多章节 Markdown → 单一 PDF（封面 + 目录 + 章节扉页 + 正文）
- **单个 HTML 文件 → PDF**（直接 Chrome 渲染，无需 Python 依赖）
- 代码语法高亮（pygments one-dark 主题）
- 中文字体优先栈（PingFang SC → Microsoft YaHei → Noto Sans CJK）
- 自动处理列表内代码块缩进问题
- Chrome headless 渲染，@page CSS 控制页眉/页脚/页码
- 自动检测并安装 Python 依赖（markdown, pygments）
- 跨平台：macOS / Windows / Linux

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| Python 3.8+ | 运行环境 | 脚本运行所需 |
| `markdown` (pip) | Markdown 模式必需 | Markdown → HTML 转换 |
| `pygments` (pip) | Markdown 模式必需 | 代码语法高亮 |
| Google Chrome / Chromium | 必需 | HTML → PDF 渲染（两种模式都需要） |

Python 依赖由脚本自动检测和安装，已安装的会跳过并提示。HTML → PDF 模式不需要 Python 依赖，仅需 Chrome。Chrome 需预装。

## 快速开始

### Markdown 目录 → PDF

```bash
python scripts/md_to_pdf.py /path/to/chapters \
  --title "书名" \
  --subtitle "副标题" \
  --output my_book.pdf
```

### HTML 文件 → PDF

```bash
python scripts/md_to_pdf.py report.html --output report.pdf
```

脚本自动检测输入类型：`.html`/`.htm` 文件走 HTML 直接转换路径，目录走 Markdown 书籍流水线。

### JSON stdin 调用（适合 Agent 集成）

```bash
# Markdown 模式
echo '{
  "source_dir": "/path/to/chapters",
  "title": "书名",
  "subtitle": "副标题",
  "version": "v1.0",
  "date": "2026 年 6 月",
  "output_pdf": "my_book.pdf",
  "output_html": "combined.html",
  "chapter_files": ["chapter01.md", "chapter02.md", "appendix.md"]
}' | python scripts/md_to_pdf.py

# HTML 模式
echo '{
  "source_dir": "/path/to/report.html",
  "output_pdf": "report.pdf"
}' | python scripts/md_to_pdf.py
```

## 配置参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `source_dir` | str | 是 | — | Markdown 文件所在目录，或单个 `.html` 文件路径 |
| `title` | str | 否 | "未命名书籍" | 书名（封面 + 页眉） |
| `subtitle` | str | 否 | "" | 副标题 |
| `version` | str | 否 | "v1.0" | 版本信息 |
| `date` | str | 否 | "2026 年" | 日期 |
| `output_pdf` | str | 否 | "output_book.pdf" | 输出 PDF 文件名 |
| `output_html` | str | 否 | "combined_book.html" | 中间 HTML 文件名 |
| `chapter_files` | list | 否 | 自动发现 | 章节文件名列表 |
| `css` | str | 否 | 内置样式 | 自定义 CSS |
| `header_right` | str | 否 | 同 title | 页眉右侧文字 |

**自动发现规则**：匹配 `chapter*.md` 和 `appendix.md`，按文件名中的数字排序。

## 工作流程

```
Task Progress:
- [ ] Step 1: 确认输入目录和章节文件
- [ ] Step 2: 配置书籍元信息（书名、副标题等）
- [ ] Step 3: 运行转换脚本
- [ ] Step 4: 验证输出 PDF
```

**Step 1: 确认输入**

检查源目录是否存在、章节文件是否齐全：
```bash
ls /path/to/chapters/*.md
```

**Step 2: 配置元信息**

根据用户需求填入 title、subtitle、version、date 等参数。

**Step 3: 运行脚本**

通过 CLI 或 JSON stdin 调用 `scripts/md_to_pdf.py`。脚本会自动：
1. 检查并安装 Python 依赖
2. 查找 Chrome 浏览器
3. 预处理 Markdown（修复列表内代码块缩进）
4. 转换 Markdown → HTML（含语法高亮）
5. 拼装封面、目录、章节扉页
6. Chrome headless 渲染 PDF

**Step 4: 验证输出**

确认 PDF 文件大小合理、章节完整。可先打开中间 HTML 文件在浏览器中预览。

## CSS 定制

内置 CSS 提供完整的书籍排版样式。如需定制，参见 [css-reference.md](css-reference.md) 了解各区域样式结构。

定制方式：在 config 中传入 `css` 字段替换默认样式，或在默认 CSS 基础上追加修改。

## 常见问题

**Chrome 未找到**
- macOS: `brew install --cask google-chrome`
- Windows: 下载安装 https://www.google.com/chrome/
- Linux: `sudo apt install chromium-browser`

**代码块在列表内显示异常**
脚本内置 `smart_preprocess` 会自动处理。如仍有问题，检查 Markdown 中代码块的缩进是否一致。

**PDF 文件为空或极小**
通常是 Chrome 渲染失败。检查 HTML 文件是否能正常在浏览器中打开。

**中文字体显示异常**
确认系统已安装中文字体：macOS 自带 PingFang SC，Windows 自带 Microsoft YaHei，Linux 需安装 `fonts-noto-cjk`。

## 输出格式

成功时 stdout 输出 JSON：

**Markdown 模式：**
```json
{
  "status": "success",
  "pdf_path": "/path/to/output.pdf",
  "html_path": "/path/to/combined.html",
  "chapter_count": 16,
  "pdf_size": 19065823
}
```

**HTML 模式：**
```json
{
  "status": "success",
  "pdf_path": "/path/to/report.pdf",
  "html_path": "/path/to/report.html",
  "pdf_size": 5242880
}
```

失败时 stderr 输出错误信息并以非零退出码退出。
