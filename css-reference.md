# CSS 样式参考

md-to-pdf-book 内置样式的结构说明，供定制时参考。

## CSS 变量

在 `:root` 中定义，修改即可全局调整配色和字体：

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `--text-color` | `#1a1a2e` | 正文文字颜色 |
| `--heading-color` | `#16213e` | 标题文字颜色 |
| `--accent` | `#0f3460` | 主色调（链接、H1 下划线、h2 左边框） |
| `--accent2` | `#e94560` | 强调色（封面装饰线、h2 左边框色） |
| `--bg-code` | `#1e1e2e` | 代码块背景（深色） |
| `--bg-code-inline` | `#edf0f5` | 内联代码背景 |
| `--bg-blockquote` | `#f0f4ff` | 引用块背景 |
| `--border-blockquote` | `#4a90d9` | 引用块左边框 |
| `--body-font` | PingFang SC, Microsoft YaHei, ... | 正文字体栈 |
| `--heading-font` | Heiti SC, PingFang SC, ... | 标题字体栈 |
| `--code-font` | SF Mono, Menlo, Consolas, ... | 代码字体栈 |
| `--line-height` | `1.6` | 行高 |
| `--para-spacing` | `0.45em` | 段落间距 |

## 页面结构

HTML 由以下区域组成，各有独立的 CSS class：

```
body
├── section.cover          → 封面（独立页，@page cover）
├── section.toc-page       → 目录页（独立页，@page toc）
└── 对每个章节：
    ├── section.chapter-title-page → 章节扉页（@page chapter-start）
    └── div.chapter-content        → 章节正文（@page 默认）
```

## @page 规则

| @page 名称 | 应用于 | 页眉/页脚 |
|------------|--------|-----------|
| 默认 | 正文页 | 左上=章节标题, 右上=书名, 底部居中=页码 |
| `cover` | 封面 | 无 |
| `toc` | 目录页 | 无 |
| `chapter-start` | 章节扉页 | 无 |

页眉中的章节标题通过 CSS `string-set` 机制自动获取当前章节的 H1 文本。

## 自定义示例

### 修改配色为暖色调

```css
:root {
  --accent: #8b4513;
  --accent2: #d2691e;
  --bg-blockquote: #fff8f0;
  --border-blockquote: #d2691e;
}
```

### 修改页面尺寸为 Letter

```css
@page {
  size: Letter;
  margin: 1in 0.75in;
}
```

### 添加自定义页脚

替换 `@page` 中的 `@bottom-center` 规则：

```css
@page {
  @bottom-center {
    content: "我的书名 · 第 " counter(page) " 页";
    font-size: 8pt;
    color: #999;
  }
}
```

### 隐藏特定区域的页眉页脚

为新的页面类型添加命名 @page：

```css
section.my-special-page {
  page: special;
  break-after: page;
}
@page special {
  @bottom-center { content: none; }
  @top-left { content: none; }
  @top-right { content: none; }
}
```

## 打印优化

`@media print` 块中包含以下保护规则：

- 标题（h1-h4）不会出现在页面底部（`break-after: avoid`）
- 代码块、表格、引用块不会跨页断裂（`break-inside: avoid-page`）
- 列表项不会跨页断裂

如需禁用某些保护，在自定义 CSS 中覆盖相应规则即可。
