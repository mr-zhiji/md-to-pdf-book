#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# md-to-pdf-book Skill Installer
#
# 将 md-to-pdf-book skill 安装到指定 AI Agent 的 skills 目录中。
#
# 用法:
#   ./install.sh <agent> [--target /path/to/project] [--global]
#
# 示例:
#   ./install.sh claude                    # 安装到当前目录的 .claude/skills/
#   ./install.sh codex --target ~/my-proj  # 安装到指定项目
#   ./install.sh qoder --global            # 全局安装（~/.qoder/skills/）
#   ./install.sh custom --dir .my-agent/skills  # 自定义目录
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ── 颜色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── 常量 ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="md-to-pdf-book"

# ── Agent 查询函数（兼容 bash 3.x）──
get_agent_dir() {
  case "$1" in
    claude)    echo ".claude/skills" ;;
    codex)     echo ".codex/skills" ;;
    openclaw)  echo ".openclaw/skills" ;;
    hermes)    echo ".hermes/skills" ;;
    qoder)     echo ".qoder/skills" ;;
    cursor)    echo ".cursor/skills" ;;
    windsurf)  echo ".windsurf/skills" ;;
    *)         echo "" ;;
  esac
}

get_agent_global_dir() {
  case "$1" in
    claude)    echo "$HOME/.claude/skills" ;;
    codex)     echo "$HOME/.codex/skills" ;;
    openclaw)  echo "$HOME/.openclaw/skills" ;;
    hermes)    echo "$HOME/.hermes/skills" ;;
    qoder)     echo "$HOME/.qoder/skills" ;;
    cursor)    echo "$HOME/.cursor/skills" ;;
    windsurf)  echo "$HOME/.windsurf/skills" ;;
    *)         echo "" ;;
  esac
}

get_agent_config_file() {
  case "$1" in
    claude)    echo "CLAUDE.md" ;;
    codex)     echo "AGENTS.md" ;;
    openclaw)  echo "openclaw.md" ;;
    hermes)    echo "HERMES.md" ;;
    qoder)     echo "AGENTS.md" ;;
    cursor)    echo ".cursorrules" ;;
    windsurf)  echo ".windsurfrules" ;;
    *)         echo "" ;;
  esac
}

is_supported_agent() {
  local dir
  dir="$(get_agent_dir "$1")"
  [[ -n "$dir" ]]
}

# ── 帮助 ──
usage() {
  echo -e "${BOLD}md-to-pdf-book Skill 安装器${NC}"
  echo ""
  echo -e "${CYAN}用法:${NC}"
  echo "  ./install.sh <agent> [选项]"
  echo ""
  echo -e "${CYAN}支持的 Agent:${NC}"
  echo "  claude      Claude Code (Anthropic)"
  echo "  codex       Codex (OpenAI)"
  echo "  openclaw    OpenClaw"
  echo "  hermes      Hermes"
  echo "  qoder       Qoder"
  echo "  cursor      Cursor"
  echo "  windsurf    Windsurf"
  echo "  custom      自定义目录（需配合 --dir）"
  echo ""
  echo -e "${CYAN}选项:${NC}"
  echo "  --target <path>   目标项目目录（默认: 当前目录）"
  echo "  --global          全局安装到用户目录"
  echo "  --dir <path>      自定义 skills 目录（仅 custom agent）"
  echo "  --no-config       跳过自动写入 Agent 配置文件"
  echo "  -h, --help        显示帮助"
  echo ""
  echo -e "${CYAN}示例:${NC}"
  echo "  ./install.sh claude"
  echo "  ./install.sh codex --target ~/projects/my-book"
  echo "  ./install.sh qoder --global"
  echo "  ./install.sh custom --dir .my-agent/skills"
}

# ── 参数解析 ──
AGENT=""
TARGET_DIR="$(pwd)"
IS_GLOBAL=false
CUSTOM_DIR=""
SKIP_CONFIG=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)    usage; exit 0 ;;
    --target)     TARGET_DIR="$2"; shift 2 ;;
    --global)     IS_GLOBAL=true; shift ;;
    --dir)        CUSTOM_DIR="$2"; shift 2 ;;
    --no-config)  SKIP_CONFIG=true; shift ;;
    -*)           echo -e "${RED}未知选项: $1${NC}"; usage; exit 1 ;;
    *)
      if [[ -z "$AGENT" ]]; then
        AGENT="$(echo "$1" | tr '[:upper:]' '[:lower:]')"
      else
        echo -e "${RED}未知参数: $1${NC}"; usage; exit 1
      fi
      shift
      ;;
  esac
done

# ── 校验 ──
if [[ -z "$AGENT" ]]; then
  echo -e "${RED}错误: 请指定 Agent 类型${NC}"
  echo ""
  usage
  exit 1
fi

if [[ "$AGENT" == "custom" && -z "$CUSTOM_DIR" ]]; then
  echo -e "${RED}错误: custom agent 需要 --dir <path> 参数${NC}"
  exit 1
fi

# ── 确定安装目录 ──
if [[ "$AGENT" == "custom" ]]; then
  if [[ "$IS_GLOBAL" == true ]]; then
    INSTALL_BASE="$HOME/$CUSTOM_DIR"
  else
    INSTALL_BASE="$TARGET_DIR/$CUSTOM_DIR"
  fi
  CONFIG_FILE=""
else
  if ! is_supported_agent "$AGENT"; then
    echo -e "${RED}错误: 不支持的 Agent '$AGENT'${NC}"
    echo -e "支持的 Agent: ${CYAN}claude, codex, openclaw, hermes, qoder, cursor, windsurf${NC}, custom"
    exit 1
  fi

  if [[ "$IS_GLOBAL" == true ]]; then
    INSTALL_BASE="$(get_agent_global_dir "$AGENT")"
  else
    INSTALL_BASE="$TARGET_DIR/$(get_agent_dir "$AGENT")"
  fi
  CONFIG_FILE="$(get_agent_config_file "$AGENT")"
fi

INSTALL_DIR="$INSTALL_BASE/$SKILL_NAME"

# ── 开始安装 ──
echo ""
echo -e "${BOLD}📦 md-to-pdf-book Skill 安装器${NC}"
echo -e "───────────────────────────────────"
echo -e "  Agent     : ${CYAN}${AGENT}${NC}"
echo -e "  目标目录  : ${CYAN}${INSTALL_DIR}${NC}"
if [[ "$IS_GLOBAL" == true ]]; then
  echo -e "  安装模式  : ${YELLOW}全局${NC}"
else
  echo -e "  安装模式  : 项目级"
fi
echo ""

# ── Step 1: 创建目标目录 ──
echo -e "${CYAN}[1/3]${NC} 创建目录..."
mkdir -p "$INSTALL_DIR/scripts"

# ── Step 2: 复制文件 ──
echo -e "${CYAN}[2/3]${NC} 复制 Skill 文件..."

copy_file() {
  local src="$SCRIPT_DIR/$1"
  local dst="$INSTALL_DIR/$1"

  if [[ ! -f "$src" ]]; then
    echo -e "  ${YELLOW}⚠ 跳过（不存在）: $1${NC}"
    return
  fi

  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo -e "  ${GREEN}✓${NC} $1"
}

copy_file "SKILL.md"
copy_file "scripts/md_to_pdf.py"
copy_file "css-reference.md"

# 设置脚本可执行权限
if [[ -f "$INSTALL_DIR/scripts/md_to_pdf.py" ]]; then
  chmod +x "$INSTALL_DIR/scripts/md_to_pdf.py"
fi

# ── Step 3: 写入 Agent 配置引用 ──
echo -e "${CYAN}[3/3]${NC} 配置 Agent 引用..."

if [[ "$SKIP_CONFIG" == true ]]; then
  echo -e "  ${YELLOW}⚠ 已跳过（--no-config）${NC}"
elif [[ -n "$CONFIG_FILE" ]]; then
  if [[ "$IS_GLOBAL" == true ]]; then
    echo -e "  ${YELLOW}⚠ 全局模式不自动写入配置文件${NC}"
    echo -e "  请手动在项目中添加引用:"
    echo -e "  ${CYAN}## Skills${NC}"
    echo -e "  ${CYAN}- [md-to-pdf-book](${INSTALL_DIR}/SKILL.md)${NC}"
  else
    CONFIG_PATH="$TARGET_DIR/$CONFIG_FILE"
    SKILL_REF="./${INSTALL_DIR#$TARGET_DIR/}/SKILL.md"
    REFERENCE_LINE="- [md-to-pdf-book]($SKILL_REF)"

    if [[ -f "$CONFIG_PATH" ]]; then
      if grep -q "md-to-pdf-book" "$CONFIG_PATH" 2>/dev/null; then
        echo -e "  ${YELLOW}⚠ 配置文件中已存在 md-to-pdf-book 引用，跳过${NC}"
      else
        {
          echo ""
          echo "## Skills"
          echo "$REFERENCE_LINE"
        } >> "$CONFIG_PATH"
        echo -e "  ${GREEN}✓${NC} 已追加到 $CONFIG_FILE"
      fi
    else
      {
        echo "# Project Agent Configuration"
        echo ""
        echo "## Skills"
        echo "$REFERENCE_LINE"
      } > "$CONFIG_PATH"
      echo -e "  ${GREEN}✓${NC} 已创建 $CONFIG_FILE"
    fi
  fi
else
  echo -e "  ${YELLOW}⚠ 该 Agent 无已知配置文件，请手动引用 SKILL.md${NC}"
fi

# ── 完成 ──
echo ""
echo -e "${GREEN}${BOLD}✅ 安装完成！${NC}"
echo ""
echo -e "Skill 已安装到: ${CYAN}${INSTALL_DIR}${NC}"
echo ""
echo -e "${BOLD}使用方式:${NC}"
echo -e "  在 Agent 对话中请求 Markdown/HTML 转 PDF 即可自动触发。"
echo ""
echo -e "${BOLD}手动验证:${NC}"
echo -e "  ${CYAN}python ${INSTALL_DIR}/scripts/md_to_pdf.py --help${NC}"
echo ""
