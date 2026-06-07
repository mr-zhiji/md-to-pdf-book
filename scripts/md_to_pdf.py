#!/usr/bin/env python3
"""Markdown Book / HTML to PDF Converter.

Converts a collection of Markdown chapter files into a professionally
typeset PDF book, or converts a single HTML file directly to PDF.

Usage:
    # Markdown directory → PDF
    python md_to_pdf.py /path/to/chapters --title "My Book"

    # Single HTML file → PDF
    python md_to_pdf.py report.html --output report.pdf

    # JSON via stdin (for skill/agent integration)
    echo '{"source_dir":"/path"}' | python md_to_pdf.py

Dependencies: markdown, pygments (auto-installed if missing, Markdown mode only).
              Google Chrome or Chromium (must be pre-installed, both modes).
"""
import sys
import os
import re
import json
import shutil
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Dependency management
# ─────────────────────────────────────────────────────────────

REQUIRED_PACKAGES = {
    # pip_package_name: [import_names]
    "markdown": ["markdown"],
    "pygments": ["pygments"],
}


def check_and_install_dependencies():
    """Check Python package dependencies. Install only what is missing.

    Returns:
        True if all dependencies are available after this call.
    """
    missing_packages = []  # pip package names

    for pip_name, import_names in REQUIRED_PACKAGES.items():
        pkg_installed = False
        for imp in import_names:
            try:
                __import__(imp)
                pkg_installed = True
                break
            except ImportError:
                continue
        if pkg_installed:
            print(f"  [已安装] {pip_name}")
        else:
            missing_packages.append(pip_name)
            print(f"  [缺失]   {pip_name}")

    if not missing_packages:
        print(f"  所有 Python 依赖已就绪 ({len(REQUIRED_PACKAGES)} 个包)")
        return True

    # ── Install missing packages ──
    pkgs_str = ", ".join(missing_packages)
    print(f"\n  正在安装 {len(missing_packages)} 个缺失包: {pkgs_str}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "--quiet", "--disable-pip-version-check"] + missing_packages,
            capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError:
        print(f"  [错误] 未找到 pip。请手动安装:")
        for pkg in missing_packages:
            print(f"         pip install {pkg}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [错误] 安装超时 (>120 秒)。请手动安装:")
        for pkg in missing_packages:
            print(f"         pip install {pkg}")
        return False

    if result.returncode != 0:
        stderr_msg = result.stderr.strip()[:300] if result.stderr else ""
        print(f"  [错误] pip install 失败 (exit {result.returncode})")
        if stderr_msg:
            print(f"         {stderr_msg}")
        print(f"  请手动安装:")
        for pkg in missing_packages:
            print(f"         pip install {pkg}")
        return False

    # Verify post-install
    still_missing = []
    for pip_name in missing_packages:
        import_names = REQUIRED_PACKAGES[pip_name]
        ok = False
        for imp in import_names:
            try:
                __import__(imp)
                ok = True
                break
            except ImportError:
                continue
        if not ok:
            still_missing.append(pip_name)

    if still_missing:
        print(f"  [错误] 安装后仍无法导入: {', '.join(still_missing)}")
        return False

    print(f"  [完成] 新安装了 {len(missing_packages)} 个包: {pkgs_str}")
    return True


# ─────────────────────────────────────────────────────────────
# Chrome / Chromium detection
# ─────────────────────────────────────────────────────────────

def find_chrome():
    """Locate a usable Chrome or Chromium binary.

    Searches common installation paths on macOS, Windows, and Linux,
    then falls back to PATH lookup.

    Returns:
        Absolute path string, or None if not found.
    """
    is_windows = sys.platform == "win32"

    candidates = []

    if is_windows:
        for env_var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = os.environ.get(env_var, "")
            if base:
                candidates.append(os.path.join(
                    base, "Google", "Chrome", "Application", "chrome.exe"))
    elif sys.platform == "darwin":
        candidates.extend([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ])
    # else: Linux — rely on PATH

    for name in ("google-chrome", "google-chrome-stable",
                 "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            candidates.append(p)

    for c in candidates:
        if c and Path(c).exists() and os.access(c, os.X_OK):
            return c

    return None


# ─────────────────────────────────────────────────────────────
# Markdown preprocessing
# ─────────────────────────────────────────────────────────────

def _is_list_item(lines, idx):
    """Scan backwards from idx to find if the nearest structural line is a list item."""
    j = idx - 1
    while j >= 0:
        s = lines[j].strip()
        if s == "":
            j -= 1
            continue
        if lines[j].startswith(" "):
            j -= 1
            continue
        return bool(re.match(r"^\d+\.\s", s)) or bool(re.match(r"^[-*+]\s", s))
    return False


def smart_preprocess(md_text):
    """Normalize fenced code blocks for correct markdown parsing.

    - Indented fences inside list items → 8-space indented code blocks
      (preserves list continuity in Python-Markdown)
    - Indented fences outside lists → strip indent (standard fenced block)
    """
    lines = md_text.split("\n")
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        fence_match = re.match(r"^(\s*)(`{3}|~{3})", line)

        if not fence_match:
            result.append(line)
            i += 1
            continue

        indent = fence_match.group(1)
        fence_char = fence_match.group(2)
        was_indented = len(indent) > 0
        in_list = was_indented and _is_list_item(lines, i)

        if in_list:
            # Convert to 8-space indented code block
            i += 1  # skip opening fence
            while i < len(lines):
                inner = lines[i]
                inner_stripped = inner.strip()
                if inner_stripped.startswith(fence_char):
                    inner_indent = re.match(r"^(\s*)", inner).group(1)
                    if len(inner_indent) <= len(indent) or inner_indent == "":
                        i += 1
                        break
                content = inner[len(indent):] if inner.startswith(indent) else inner
                result.append("        " + content)
                i += 1
        else:
            # Keep as fenced block, strip outer indent
            block = [line[len(indent):] if was_indented else line]
            i += 1
            while i < len(lines):
                inner = lines[i]
                inner_stripped = inner.strip()
                if inner_stripped.startswith(fence_char):
                    inner_indent = re.match(r"^(\s*)", inner).group(1)
                    if was_indented:
                        if inner_indent == indent or inner_indent == "":
                            block.append(
                                inner[len(indent):] if inner_indent == indent
                                else inner)
                            i += 1
                            break
                    else:
                        block.append(inner)
                        i += 1
                        break
                if was_indented and inner.startswith(indent):
                    block.append(inner[len(indent):])
                elif inner.strip() == "":
                    block.append("")
                else:
                    block.append(inner)
                i += 1
            result.extend(block)

    return "\n".join(result)


# ─────────────────────────────────────────────────────────────
# Markdown → HTML
# ─────────────────────────────────────────────────────────────

def md_to_html(md_text):
    """Convert Markdown text to HTML with syntax highlighting."""
    from markdown import Markdown
    from markdown.extensions.codehilite import CodeHiliteExtension
    from markdown.extensions.fenced_code import FencedCodeExtension
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.attr_list import AttrListExtension

    md_text = smart_preprocess(md_text)
    md = Markdown(
        extensions=[
            FencedCodeExtension(),
            CodeHiliteExtension(noclasses=True, pygments_style="one-dark",
                                linenums=False),
            TableExtension(),
            AttrListExtension(),
            "meta",
        ],
        output_format="html5",
    )
    return md.convert(md_text)


# ─────────────────────────────────────────────────────────────
# HTML component builders
# ─────────────────────────────────────────────────────────────

def build_cover_html(title, subtitle, version, date):
    return f"""<section class="cover">
<div class="cover-bg"></div>
<div class="cover-inner">
  <div class="cover-badge">{title.split('&')[0].strip().upper()}</div>
  <h1 class="cover-title">{title}</h1>
  <div class="cover-line"></div>
  <p class="cover-subtitle">{subtitle}</p>
  <div class="cover-meta">
    <p class="cover-version">{version}</p>
    <p class="cover-date">{date}</p>
  </div>
</div>
</section>"""


def build_toc_html(chapters):
    """Generate table of contents from (title, slug) pairs."""
    items = []
    for i, (title, slug) in enumerate(chapters, 1):
        num = f"第 {i} 章" if slug.startswith("ch") else "附录"
        items.append(
            f'<li class="toc-item">'
            f'<span class="toc-num">{num}</span>'
            f'<span class="toc-dots"></span>'
            f'<a href="#{slug}" class="toc-title">{title}</a>'
            f'</li>'
        )
    items_html = "\n".join(items)
    return f"""<section class="toc-page">
<h1 class="toc-heading">目 录</h1>
<div class="toc-line"></div>
<ol class="toc-list">
{items_html}
</ol>
</section>"""


def build_chapter_title_page(chapter_num, title, slug):
    """Generate a standalone chapter title page."""
    num_label = f"第 {chapter_num} 章" if chapter_num <= 999 else "附录"
    clean = re.sub(r'^第\s*\d+\s*章\s*', '', title)
    clean = re.sub(r'^附录\s*', '', clean) or title
    return f"""<section class="chapter-title-page" id="{slug}">
<div class="ctp-inner">
  <p class="ctp-number">{num_label}</p>
  <h1 class="ctp-title">{clean}</h1>
  <div class="ctp-line"></div>
</div>
</section>"""


def parse_chapter_title(md_text):
    """Extract the first H1 title from Markdown content."""
    for line in md_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return "未命名章节"


# ─────────────────────────────────────────────────────────────
# Full HTML assembly
# ─────────────────────────────────────────────────────────────

def build_full_html(chapters, config):
    """Assemble cover + TOC + chapter pages + CSS into one HTML document.

    Args:
        chapters: list of (title, html_body, slug)
        config: dict with title, subtitle, version, date, css, header_right
    """
    cover = build_cover_html(
        config["title"], config["subtitle"],
        config["version"], config["date"])

    toc_data = [(t, s) for t, _, s in chapters]
    toc = build_toc_html(toc_data)

    body_parts = []
    for i, (title, html_body, slug) in enumerate(chapters, 1):
        body_parts.append(build_chapter_title_page(i, title, slug))
        body_parts.append(f'<div class="chapter-content">{html_body}</div>')

    body_html = "\n".join(body_parts)
    css = config.get("css", "")
    header_right = config.get("header_right", config["title"])

    # Patch header_right into @page CSS if custom
    if header_right != config["title"]:
        css = css.replace(
            'content: "' + config["title"] + '"',
            'content: "' + header_right + '"')

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{config["title"]}</title>
<style>
{css}
</style>
</head>
<body>
{cover}
{toc}
{body_html}
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# Chrome headless PDF rendering
# ─────────────────────────────────────────────────────────────

def render_pdf(html_path, pdf_path):
    """Convert HTML file to PDF using Chrome --headless --print-to-pdf.

    Chrome respects @page CSS rules (size, margins, margin boxes),
    producing output identical to in-browser rendering.

    Raises:
        RuntimeError: If Chrome not found or PDF generation fails.
    """
    chrome = find_chrome()
    if not chrome:
        if sys.platform == "win32":
            hint = "请安装 Google Chrome: https://www.google.com/chrome/"
        elif sys.platform == "darwin":
            hint = "brew install --cask google-chrome"
        else:
            hint = "sudo apt install chromium-browser  (或 google-chrome-stable)"
        raise RuntimeError(
            f"未找到 Chrome / Chromium。\n  {hint}")

    html_url = Path(html_path).resolve().as_uri()

    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-software-rasterizer",
        f"--print-to-pdf={Path(pdf_path).resolve()}",
        "--no-pdf-header-footer",
        html_url,
    ]

    print(f"   Chrome : {chrome}")
    print(f"   输入   : {html_url}")
    print(f"   输出   : {pdf_path}")

    # Windows: suppress console window flash
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, **kwargs)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Chrome 渲染超时 (>300 秒)")
    except OSError as e:
        raise RuntimeError(f"启动 Chrome 失败: {e}")

    # Chrome writes diagnostics to stderr even on success;
    # only treat as failure if the output file is missing or empty.
    if not Path(pdf_path).exists() or Path(pdf_path).stat().st_size == 0:
        stderr_msg = result.stderr.strip()[:500] if result.stderr else "(无输出)"
        raise RuntimeError(
            f"Chrome PDF 渲染失败 (exit {result.returncode}):\n  {stderr_msg}")

    if result.stderr and result.stderr.strip():
        # Print first 300 chars of stderr as non-fatal warning
        warn = result.stderr.strip()[:300]
        print(f"   [警告] Chrome stderr: {warn}")


# ─────────────────────────────────────────────────────────────
# Default CSS (embedded, cross-platform font stack)
# ─────────────────────────────────────────────────────────────

DEFAULT_CSS = r"""
:root {
  --text-color: #1a1a2e;
  --heading-color: #16213e;
  --accent: #0f3460;
  --accent2: #e94560;
  --bg-code: #1e1e2e;
  --bg-code-inline: #edf0f5;
  --bg-blockquote: #f0f4ff;
  --border-blockquote: #4a90d9;
  --bg-table-head: #e8ecf1;
  --bg-table-stripe: #f8f9fb;
  --body-font: "PingFang SC", "PingFang HK", "Heiti SC", "Microsoft YaHei",
               "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
  --heading-font: "Heiti SC", "PingFang SC", "Microsoft YaHei",
                  "Noto Sans CJK SC", sans-serif;
  --code-font: "SF Mono", "Menlo", "Consolas", "Monaco", monospace;
  --line-height: 1.6;
  --para-spacing: 0.45em;
}

*, *::before, *::after { box-sizing: border-box; }

body {
  font-family: var(--body-font); font-size: 11pt;
  line-height: var(--line-height); color: var(--text-color);
  max-width: 100%; margin: 0; padding: 0;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

/* ── Cover ─────────────────────────────── */
.cover {
  display: flex; align-items: center; justify-content: center;
  height: 100vh; page: cover; text-align: center;
  break-after: page; position: relative; overflow: hidden;
}
.cover-bg {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(160deg, #f0f4ff 0%, #ffffff 40%, #fff5f7 100%);
  z-index: 0;
}
.cover-inner { max-width: 80%; position: relative; z-index: 1; }
.cover-badge {
  display: inline-block; font-family: var(--code-font); font-size: 9pt;
  letter-spacing: 0.2em; color: var(--accent); border: 1.5px solid var(--accent);
  padding: 0.3em 1.2em; border-radius: 3px; margin-bottom: 1.5em;
}
.cover-title {
  font-family: var(--heading-font); font-size: 34pt; font-weight: 900;
  color: var(--accent); margin: 0 0 0.5em; letter-spacing: 0.06em;
  line-height: 1.3;
}
.cover-subtitle {
  font-size: 15pt; color: #555; margin: 0 0 1.5em; letter-spacing: 0.1em;
}
.cover-line {
  width: 80px; height: 3px; background: var(--accent2);
  margin: 0 auto 1.2em; border-radius: 2px;
}
.cover-meta { margin-top: 2em; }
.cover-version { font-size: 9pt; color: #aaa; letter-spacing: 0.08em; margin: 0 0 0.3em; }
.cover-date { font-size: 11pt; color: #888; letter-spacing: 0.1em; margin: 0; }

/* ── TOC ───────────────────────────────── */
.toc-page { page: toc; break-after: page; padding-top: 2em; }
.toc-heading {
  font-family: var(--heading-font); font-size: 22pt; font-weight: 800;
  color: var(--heading-color); text-align: center;
  border: none; margin: 0 0 0.3em; padding: 0; letter-spacing: 0.15em;
  string-set: none;
}
.toc-line {
  width: 60px; height: 2px; background: var(--accent2);
  margin: 0 auto 2em; border-radius: 1px;
}
.toc-list { list-style: none; padding: 0; margin: 0; }
.toc-item {
  display: flex; align-items: baseline;
  padding: 0.55em 0; border-bottom: 1px dotted #d0d7de;
  margin: 0; font-size: 10.5pt;
}
.toc-item:last-child { border-bottom: none; }
.toc-num {
  font-weight: 700; color: var(--accent); min-width: 5em;
  flex-shrink: 0; font-size: 10pt;
}
.toc-dots {
  flex: 1; border-bottom: 1px dotted #ccc; margin: 0 0.6em;
  min-width: 1em; transform: translateY(-3px);
}
.toc-title {
  color: var(--text-color); text-decoration: none;
  font-weight: 500; flex-shrink: 0;
}

/* ── Chapter title page ────────────────── */
.chapter-title-page {
  display: flex; align-items: center; justify-content: center;
  height: 100vh; page: chapter-start; break-after: page; text-align: center;
}
.ctp-inner { max-width: 90%; }
.ctp-number {
  font-family: var(--code-font); font-size: 10pt;
  letter-spacing: 0.2em; color: var(--accent2);
  text-transform: uppercase; margin: 0 0 0.8em;
}
.ctp-title {
  font-family: var(--heading-font); font-size: 26pt; font-weight: 800;
  color: var(--heading-color); margin: 0 0 0.6em;
  border: none; padding: 0; letter-spacing: 0.04em; line-height: 1.35;
  string-set: chapter-title content(text);
  word-break: keep-all; overflow-wrap: break-word;
}
.ctp-line {
  width: 60px; height: 3px; background: var(--accent);
  margin: 0 auto; border-radius: 2px;
}

/* ── Headings ──────────────────────────── */
h1 {
  font-family: var(--heading-font); font-size: 20pt; font-weight: 800;
  color: var(--heading-color); border-bottom: 2px solid var(--accent);
  padding-bottom: 0.3em; margin: 1.8em 0 0.6em; letter-spacing: 0.04em;
  string-set: chapter-title content(text);
}
h2 {
  font-family: var(--heading-font); font-size: 15pt; font-weight: 700;
  color: var(--accent); margin: 1.5em 0 0.5em;
  padding-left: 0.4em; border-left: 4px solid var(--accent2);
  break-after: avoid;
}
h3 {
  font-family: var(--heading-font); font-size: 12.5pt; font-weight: 700;
  color: #2c3e50; margin: 1.2em 0 0.4em; break-after: avoid;
}
h4 {
  font-family: var(--heading-font); font-size: 11.5pt; font-weight: 600;
  color: #34495e; margin: 1em 0 0.3em; break-after: avoid;
}

/* ── Body text ─────────────────────────── */
p { margin: var(--para-spacing) 0; text-align: left; }
strong { color: #0d1b2a; }
em { color: #555; }
a { color: var(--accent); text-decoration: none; }

/* ── Inline code ───────────────────────── */
code {
  font-family: var(--code-font); font-size: 9.5pt;
  background: var(--bg-code-inline); padding: 0.12em 0.35em;
  border-radius: 3px; color: #9b2c4a;
  white-space: pre-wrap; word-break: break-word;
}

/* ── Code blocks ───────────────────────── */
pre {
  background: var(--bg-code) !important; border: 1px solid #3a3a5c;
  border-radius: 6px; padding: 0.8em 1em;
  line-height: 1.5; margin: 0.7em 0; font-size: 9.5pt;
  white-space: pre-wrap; word-wrap: break-word; overflow-wrap: break-word;
}
pre code {
  font-family: var(--code-font); background: none !important;
  padding: 0; color: #cdd6f4; font-size: inherit; border-radius: 0;
  white-space: pre-wrap; word-wrap: break-word;
}

/* ── Tables ────────────────────────────── */
table {
  width: 100%; border-collapse: collapse; margin: 0.8em 0;
  font-size: 10pt; table-layout: auto;
  word-wrap: break-word; overflow-wrap: break-word;
}
thead { background: var(--bg-table-head); }
th { font-weight: 700; text-align: left; padding: 0.5em 0.7em; border: 1px solid #d0d7de; }
td { padding: 0.4em 0.7em; border: 1px solid #d0d7de; vertical-align: top; word-wrap: break-word; }
tr:nth-child(even) td { background: var(--bg-table-stripe); }
td code, th code { font-size: 8.5pt; }

/* ── Blockquotes ───────────────────────── */
blockquote {
  margin: 0.8em 0; padding: 0.6em 1em;
  background: var(--bg-blockquote); border-left: 4px solid var(--border-blockquote);
  border-radius: 0 4px 4px 0; color: #3a4a5c; break-inside: avoid;
}
blockquote p { margin: 0.2em 0; }
blockquote strong:first-child {
  display: block; font-size: 10pt; margin-bottom: 0.3em; color: var(--accent);
}

/* ── Lists ─────────────────────────────── */
ul, ol { margin: 0.4em 0; padding-left: 1.8em; }
li { margin: 0.15em 0; }
li p { margin: 0.15em 0; }
li pre, li .codehilite { margin: 0.4em 0; }

/* ── Misc ──────────────────────────────── */
hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
img { max-width: 100%; height: auto; border-radius: 4px; }
.chapter-anchor { display: block; height: 0; }
dt { font-weight: 700; margin-top: 0.5em; color: var(--accent); }
dd { margin-left: 1.5em; margin-bottom: 0.4em; }

/* ── Page layout ───────────────────────── */
@page {
  size: A4; margin: 2.2cm 2cm 2.2cm 2cm;
  @bottom-center {
    content: counter(page); font-family: var(--code-font);
    font-size: 8.5pt; color: #999;
  }
  @top-left {
    content: string(chapter-title); font-family: var(--heading-font);
    font-size: 8pt; color: #aaa; white-space: nowrap;
    max-width: 60%; overflow: hidden; text-overflow: ellipsis;
  }
  @top-right {
    content: "__HEADER_RIGHT__";
    font-family: var(--heading-font); font-size: 7.5pt;
    color: #ccc; letter-spacing: 0.05em;
  }
}
@page cover {
  margin: 0;
  @bottom-center { content: none; }
  @top-left { content: none; }
  @top-right { content: none; }
}
@page toc {
  @bottom-center { content: none; }
  @top-left { content: none; }
  @top-right { content: none; }
}
@page chapter-start {
  margin: 0;
  @bottom-center { content: none; }
  @top-left { content: none; }
  @top-right { content: none; }
}

/* ── Print optimization ────────────────── */
@media print {
  html, body { height: auto; }
  h1, h2, h3, h4 { break-after: avoid; page-break-after: avoid; }
  pre { break-inside: avoid-page; page-break-inside: avoid; }
  table { break-inside: avoid-page; page-break-inside: avoid; }
  blockquote { break-inside: avoid-page; page-break-inside: avoid; }
  li { break-inside: avoid-page; page-break-inside: avoid; }
  h2 + *, h3 + * { break-before: avoid; }
}
"""


# ─────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────

DEFAULT_CHAPTER_PATTERNS = [
    r"chapter\d+\.md",
    r"appendix\.md",
]


def discover_chapter_files(source_dir, patterns=None):
    """Auto-discover chapter files matching glob patterns.

    Returns sorted list of filenames.
    """
    if patterns is None:
        patterns = DEFAULT_CHAPTER_PATTERNS

    import glob as glob_mod

    files = set()
    for pat in patterns:
        for f in glob_mod.glob(str(Path(source_dir) / pat)):
            files.add(Path(f).name)

    # Natural sort: chapter01 < chapter02 < ... < appendix
    def sort_key(name):
        m = re.search(r"(\d+)", name)
        return (0, int(m.group(1))) if m else (1, 0)

    return sorted(files, key=sort_key)


def convert_html(config):
    """Direct HTML file → PDF conversion (skips Markdown pipeline).

    Only requires Chrome — no Python dependencies needed.
    """
    html_path = Path(config["source_dir"])

    if not html_path.exists():
        raise RuntimeError(f"HTML 文件不存在: {html_path}")
    if not html_path.suffix.lower() in (".html", ".htm"):
        raise RuntimeError(f"文件不是 HTML: {html_path}")
    if html_path.stat().st_size == 0:
        raise RuntimeError(f"HTML 文件为空: {html_path}")

    # HTML mode only needs Chrome, not Python packages
    chrome = find_chrome()
    if not chrome:
        if sys.platform == "win32":
            hint = "请安装 Google Chrome: https://www.google.com/chrome/"
        elif sys.platform == "darwin":
            hint = "brew install --cask google-chrome"
        else:
            hint = "sudo apt install chromium-browser"
        raise RuntimeError(f"未找到 Chrome / Chromium。\n  {hint}")

    # Determine output path
    output_pdf_name = config.get("output_pdf", html_path.stem + ".pdf")
    output_pdf = html_path.parent / output_pdf_name

    html_size = html_path.stat().st_size
    print(f"📄 HTML → PDF 转换")
    print(f"   输入: {html_path} ({html_size / 1024:.1f} KB)")
    print(f"   输出: {output_pdf}")

    print(f"\n🖨️  渲染 PDF (Chrome headless)...")
    render_pdf(html_path, output_pdf)

    pdf_size = output_pdf.stat().st_size
    size_str = (
        f"{pdf_size / 1024 / 1024:.1f} MB" if pdf_size > 1024 * 1024
        else f"{pdf_size / 1024:.1f} KB"
    )
    print(f"   ✓ PDF 已生成: {output_pdf} ({size_str})")
    print(f"\n🎉 完成！{html_path.name} → {output_pdf.name}")

    return {
        "status": "success",
        "pdf_path": str(output_pdf),
        "html_path": str(html_path),
        "pdf_size": pdf_size,
    }


def convert(config):
    """Main conversion pipeline. Auto-detects input type.

    - If source_dir is an .html/.htm file → delegates to convert_html()
    - Otherwise → Markdown directory pipeline: .md files → HTML → PDF

    Args:
        config: dict with all conversion parameters.

    Returns:
        dict with status, pdf_path, html_path, chapter_count, pdf_size.
    """
    source_path = Path(config["source_dir"])

    # ── Route: HTML file → direct conversion ──
    if source_path.suffix.lower() in (".html", ".htm"):
        return convert_html(config)

    # ── Markdown directory pipeline below ──
    source_dir = source_path

    # ── Validate source directory ──
    if not source_dir.exists():
        raise RuntimeError(f"源目录不存在: {source_dir}")
    if not source_dir.is_dir():
        raise RuntimeError(f"源路径不是目录: {source_dir}")

    # ── Step 1: Check dependencies ──
    print("📦 检查依赖...")
    if not check_and_install_dependencies():
        raise RuntimeError("依赖检查未通过，无法继续")

    # ── Step 2: Check Chrome ──
    chrome = find_chrome()
    if not chrome:
        if sys.platform == "win32":
            hint = "请安装 Google Chrome: https://www.google.com/chrome/"
        elif sys.platform == "darwin":
            hint = "brew install --cask google-chrome"
        else:
            hint = "sudo apt install chromium-browser"
        raise RuntimeError(f"未找到 Chrome / Chromium。\n  {hint}")
    print(f"🌐 Chrome: {chrome}")

    # ── Step 3: Resolve chapter files ──
    chapter_files = config.get("chapter_files")
    if not chapter_files:
        chapter_files = discover_chapter_files(source_dir)

    if not chapter_files:
        raise RuntimeError(
            f"在 {source_dir} 中未找到 Markdown 章节文件\n"
            f"  尝试匹配的模式: chapter*.md, appendix.md\n"
            f"  请通过 chapter_files 参数显式指定文件列表")

    # ── Step 4: Convert each chapter ──
    print(f"\n📖 处理 {len(chapter_files)} 个章节文件...")
    chapters = []  # [(title, html_body, slug)]

    for filename in chapter_files:
        filepath = source_dir / filename
        if not filepath.exists():
            print(f"   [跳过] 文件不存在: {filename}")
            continue

        md_text = filepath.read_text(encoding="utf-8")
        title = parse_chapter_title(md_text)
        html_body = md_to_html(md_text)

        # Assign slug: ch01, ch02, ..., appendix
        ch_num_match = re.search(r"(\d+)", filename)
        if ch_num_match:
            slug = f"ch{int(ch_num_match.group(1)):02d}"
        else:
            slug = "appendix"

        chapters.append((title, html_body, slug))
        print(f"   ✓ {filename} → {title} ({len(md_text):,} 字符)")

    if not chapters:
        raise RuntimeError("没有任何章节文件成功转换")

    # ── Step 5: Assemble full HTML ──
    print(f"\n📝 生成 HTML...")

    css = config.get("css", DEFAULT_CSS)
    header_right = config.get("header_right", config["title"])
    # Replace placeholder in CSS with actual header text
    css = css.replace("__HEADER_RIGHT__", header_right)

    build_config = {
        "title": config["title"],
        "subtitle": config["subtitle"],
        "version": config["version"],
        "date": config["date"],
        "css": css,
        "header_right": header_right,
    }
    full_html = build_full_html(chapters, build_config)

    output_html = source_dir / config["output_html"]
    output_html.write_text(full_html, encoding="utf-8")
    print(f"   ✓ HTML 已保存: {output_html} ({len(full_html):,} 字符)")

    # ── Step 6: Render PDF ──
    print(f"\n🖨️  渲染 PDF (Chrome headless)...")
    output_pdf = source_dir / config["output_pdf"]
    render_pdf(output_html, output_pdf)

    pdf_size = output_pdf.stat().st_size
    size_str = (
        f"{pdf_size / 1024 / 1024:.1f} MB" if pdf_size > 1024 * 1024
        else f"{pdf_size / 1024:.1f} KB"
    )
    print(f"   ✓ PDF 已生成: {output_pdf} ({size_str})")
    print(f"\n🎉 完成！共 {len(chapters)} 个章节 → {output_pdf.name}")

    return {
        "status": "success",
        "pdf_path": str(output_pdf),
        "html_path": str(output_html),
        "chapter_count": len(chapters),
        "pdf_size": pdf_size,
    }


# ─────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────

def make_default_config(source_dir):
    """Build a default config dict for the given source directory."""
    return {
        "source_dir": str(source_dir),
        "title": "未命名书籍",
        "subtitle": "",
        "version": "v1.0",
        "date": "2026 年",
        "output_html": "combined_book.html",
        "output_pdf": "output_book.pdf",
        "chapter_files": None,       # None = auto-discover
        "css": DEFAULT_CSS,
        "header_right": None,       # None = use title
    }


def read_json_stdin():
    """Read and parse JSON from stdin."""
    try:
        raw = sys.stdin.read()
    except Exception as e:
        print(f"[错误] 无法读取 stdin: {e}")
        sys.exit(1)
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[错误] stdin 不是有效 JSON: {e}")
        sys.exit(1)


def parse_cli_args():
    """Parse command-line arguments into a config dict."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Markdown 书籍 / HTML 文件 → PDF 转换器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python md_to_pdf.py ./chapters --title '我的书'\n"
            "  python md_to_pdf.py report.html --output report.pdf\n"
            "  echo '{\"source_dir\":\".\"}' | python md_to_pdf.py\n"
        ),
    )
    parser.add_argument(
        "source_dir", nargs="?", default=None,
        help="Markdown 文件所在目录，或单个 HTML 文件路径")
    parser.add_argument(
        "--title", default=None, help="书名")
    parser.add_argument(
        "--subtitle", default=None, help="副标题")
    parser.add_argument(
        "--version", default=None, help="版本信息")
    parser.add_argument(
        "--date", default=None, help="日期")
    parser.add_argument(
        "--output", default=None,
        help="输出 PDF 文件名 (默认: output_book.pdf)")
    parser.add_argument(
        "--chapters", nargs="+", default=None,
        help="显式指定章节文件名")

    args = parser.parse_args()

    config = {}
    if args.source_dir:
        config["source_dir"] = args.source_dir
    if args.title:
        config["title"] = args.title
    if args.subtitle:
        config["subtitle"] = args.subtitle
    if args.version:
        config["version"] = args.version
    if args.date:
        config["date"] = args.date
    if args.output:
        config["output_pdf"] = args.output
    if args.chapters:
        config["chapter_files"] = args.chapters

    return config


def main():
    """Entry point: merge JSON stdin + CLI args → config → convert."""
    has_cli_args = len(sys.argv) > 1
    is_tty = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else True

    if has_cli_args or is_tty:
        # CLI arguments provided, or interactive terminal
        json_config = parse_cli_args()
    else:
        # No CLI args and stdin is piped → read JSON from stdin
        json_config = read_json_stdin()

    # source_dir is mandatory
    source_dir = json_config.get("source_dir")
    if not source_dir:
        print("[错误] 必须指定 source_dir")
        print("  用法 1: python md_to_pdf.py /path/to/chapters --title '书名'")
        print("  用法 2: python md_to_pdf.py report.html --output report.pdf")
        print("  用法 3: echo '{\"source_dir\":\"/path\"}' | python md_to_pdf.py")
        sys.exit(1)

    # Merge: explicit config over defaults
    config = make_default_config(source_dir)
    for k, v in json_config.items():
        if v is not None:
            config[k] = v

    # If header_right not set, use title
    if config.get("header_right") is None:
        config["header_right"] = config["title"]

    try:
        result = convert(config)
        print(json.dumps(result, ensure_ascii=False))
    except RuntimeError as e:
        print(f"\n[错误] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[意外错误] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
