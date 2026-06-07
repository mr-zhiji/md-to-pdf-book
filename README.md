# md-to-pdf-book

将多个 Markdown 章节文件转换为排版精美的 A4 书籍 PDF，或将单个 HTML 文件直接转为 PDF。

## 功能特性

- 多章节 Markdown → 单一 PDF（封面 + 目录 + 章节扉页 + 正文）
- 单个 HTML 文件 → PDF（直接 Chrome 渲染，无需 Python 依赖）
- 代码语法高亮（Pygments one-dark 主题）
- 中文字体优先栈（PingFang SC → Microsoft YaHei → Noto Sans CJK）
- 自动处理列表内代码块缩进问题
- Chrome headless 渲染，`@page` CSS 控制页眉 / 页脚 / 页码
- 自动检测并安装 Python 依赖
- 跨平台：macOS / Windows / Linux

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

### JSON stdin 调用（Agent 集成）

```bash
echo '{
  "source_dir": "/path/to/chapters",
  "title": "书名",
  "subtitle": "副标题",
  "output_pdf": "my_book.pdf"
}' | python scripts/md_to_pdf.py
```

## 依赖

| 依赖 | 类型 | 说明 |
|------|------|------|
| Python 3.8+ | 运行环境 | 脚本运行所需 |
| `markdown` (pip) | Markdown 模式必需 | Markdown → HTML 转换 |
| `pygments` (pip) | Markdown 模式必需 | 代码语法高亮 |
| Google Chrome / Chromium | 必需 | HTML → PDF 渲染 |

> Python 依赖由脚本自动检测和安装。HTML → PDF 模式仅需 Chrome。

## 安装为 AI Agent Skill

本工具以 **Skill** 形式提供，可直接安装到支持的 AI Agent 中使用。安装后，Agent 将具备将 Markdown / HTML 转换为 PDF 书籍的能力。

### 一键安装（推荐）

使用内置的 `install.sh` 脚本一键安装到各类 Agent：

```bash
# 查看帮助
./install.sh --help

# 安装到当前项目的 Claude Code
./install.sh claude

# 安装到指定项目的 Codex
./install.sh codex --target ~/projects/my-book

# 全局安装到 Qoder
./install.sh qoder --global

# 安装到自定义目录
./install.sh custom --dir .my-agent/skills
```

**支持的 Agent：**

| Agent | 命令 | Skills 目录 | 配置文件 |
|-------|------|-------------|----------|
| Claude Code | `./install.sh claude` | `.claude/skills/` | `CLAUDE.md` |
| Codex | `./install.sh codex` | `.codex/skills/` | `AGENTS.md` |
| OpenClaw | `./install.sh openclaw` | `.openclaw/skills/` | `openclaw.md` |
| Hermes | `./install.sh hermes` | `.hermes/skills/` | `HERMES.md` |
| Qoder | `./install.sh qoder` | `.qoder/skills/` | `AGENTS.md` |
| Cursor | `./install.sh cursor` | `.cursor/skills/` | `.cursorrules` |
| Windsurf | `./install.sh windsurf` | `.windsurf/skills/` | `.windsurfrules` |

**安装选项：**

| 选项 | 说明 |
|------|------|
| `--target <path>` | 指定目标项目目录（默认当前目录） |
| `--global` | 全局安装到用户 Home 目录 |
| `--dir <path>` | 自定义 skills 目录（仅 `custom` agent） |
| `--no-config` | 跳过自动写入 Agent 配置文件 |

### 手动安装

也可以手动将 Skill 文件复制到 Agent 约定的 skills 目录中：

```bash
# 以 Claude Code 为例
mkdir -p .claude/skills/md-to-pdf-book/scripts
cp SKILL.md scripts/md_to_pdf.py css-reference.md .claude/skills/md-to-pdf-book/
cp scripts/md_to_pdf.py .claude/skills/md-to-pdf-book/scripts/
```

然后在 Agent 配置文件中添加引用：

```markdown
## Skills
- [md-to-pdf-book](./.claude/skills/md-to-pdf-book/SKILL.md)
```

核心文件结构：

```
md-to-pdf-book/
├── SKILL.md              # Skill 描述文件（Agent 读取此文件了解能力）
├── scripts/
│   └── md_to_pdf.py      # 转换脚本
└── css-reference.md      # CSS 样式参考
```

## 配置参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `source_dir` | str | 是 | — | Markdown 文件所在目录，或单个 `.html` 文件路径 |
| `title` | str | 否 | `"未命名书籍"` | 书名（封面 + 页眉） |
| `subtitle` | str | 否 | `""` | 副标题 |
| `version` | str | 否 | `"v1.0"` | 版本信息 |
| `date` | str | 否 | `"2026 年"` | 日期 |
| `output_pdf` | str | 否 | `"output_book.pdf"` | 输出 PDF 文件名 |
| `output_html` | str | 否 | `"combined_book.html"` | 中间 HTML 文件名 |
| `chapter_files` | list | 否 | 自动发现 | 章节文件名列表 |
| `css` | str | 否 | 内置样式 | 自定义 CSS |
| `header_right` | str | 否 | 同 title | 页眉右侧文字 |

## 输出格式

成功时 stdout 输出 JSON：

```json
{
  "status": "success",
  "pdf_path": "/path/to/output.pdf",
  "html_path": "/path/to/combined.html",
  "chapter_count": 16,
  "pdf_size": 19065823
}
```

失败时 stderr 输出错误信息并以非零退出码退出。

## CSS 定制

内置 CSS 提供完整的书籍排版样式。如需定制，参见 [css-reference.md](css-reference.md) 了解各区域样式结构。

## 常见问题

**Chrome 未找到**

```bash
# macOS
brew install --cask google-chrome

# Windows → 下载 https://www.google.com/chrome/

# Linux
sudo apt install chromium-browser
```

**中文字体显示异常**

确认系统已安装中文字体：macOS 自带 PingFang SC，Windows 自带 Microsoft YaHei，Linux 需安装 `fonts-noto-cjk`。

## 许可证

MIT
