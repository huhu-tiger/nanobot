#!/bin/bash
# Feishu Drive Skill Script
# 统一封装飞书云文档能力（SKILL 脚本）：
# 1) 上传文件并返回可访问 URL
# 2) 获取「我的空间」根目录下的文件与文件夹列表
#
# 使用示例：
#   # 1. 上传文件（使用 ~/.nanobot/config.json 中的 Feishu 配置）
#   bash feishu_drive.sh upload /path/to/file.txt [folder_token]
#
#   # 2. 列出根目录下文件与文件夹（返回 JSON，可配合 jq）
#   bash feishu_drive.sh list-root [page_size]
#   bash feishu_drive.sh list-root 100 | jq '.'

set -e

########################################
# 公共配置与工具函数
########################################

CONFIG_PATH="${NANOBOT_CONFIG_PATH:-$HOME/.nanobot/config.json}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

error()   { echo -e "${RED}❌ Error: $1${NC}" >&2; }
success() { echo -e "${GREEN}✅ $1${NC}" >&2; }
info()    { echo -e "${BLUE}📂 $1${NC}" >&2; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}" >&2; }

# 全局变量（在函数间复用）
APP_ID=""
APP_SECRET=""
TENANT_TOKEN=""
ROOT_FOLDER_TOKEN=""
FEISHU_DOMAIN=""  # 例如 tcn010uwma1t.feishu.cn

########################################
# 内部工具：加载 appId / appSecret
########################################

load_credentials() {
  if [ -n "$APP_ID" ] && [ -n "$APP_SECRET" ]; then
    return 0
  fi

  info "Loading Feishu appId/appSecret from ${CONFIG_PATH}..."

  if [ ! -f "$CONFIG_PATH" ]; then
    error "Config file not found: $CONFIG_PATH"
    exit 1
  fi

  APP_ID=$(grep '"appId"' "$CONFIG_PATH" | head -1 | sed 's/.*"appId":[[:space:]]*"\([^"]*\)".*/\1/')
  APP_SECRET=$(grep '"appSecret"' "$CONFIG_PATH" | head -1 | sed 's/.*"appSecret":[[:space:]]*"\([^"]*\)".*/\1/')

  if [ -z "$APP_ID" ] || [ -z "$APP_SECRET" ]; then
    error "Failed to parse appId/appSecret from $CONFIG_PATH"
    exit 1
  fi

  success "Loaded appId/appSecret from config"
}

########################################
# 内部工具：获取 tenant_access_token
########################################

ensure_tenant_token() {
  if [ -n "$TENANT_TOKEN" ]; then
    return 0
  fi

  load_credentials

  info "Getting tenant_access_token..."

  local resp
  resp=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "{
      \"app_id\": \"${APP_ID}\",
      \"app_secret\": \"${APP_SECRET}\"
    }")

  local code
  TENANT_TOKEN=$(echo "$resp" | grep -o '"tenant_access_token":"[^"]*"' | cut -d'"' -f4)
  code=$(echo "$resp" | grep -o '"code":[0-9]*' | head -1 | cut -d':' -f2)

  if [ -z "$TENANT_TOKEN" ] || [ "$code" != "0" ]; then
    error "Failed to get tenant_access_token, response:"
    echo "$resp"
    exit 1
  fi

  success "Got tenant_access_token"
}

########################################
# 内部工具：获取「我的空间」根 folder_token
########################################

ensure_root_folder() {
  if [ -n "$ROOT_FOLDER_TOKEN" ]; then
    return 0
  fi

  ensure_tenant_token

  info "Getting root folder (My Space) meta..."

  local resp
  resp=$(curl -s -X GET "https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta" \
    -H "Authorization: Bearer ${TENANT_TOKEN}")

  local code
  code=$(echo "$resp" | grep -o '"code":[0-9]*' | head -1 | cut -d':' -f2)
  ROOT_FOLDER_TOKEN=$(echo "$resp" | grep -o '"token":"[^"]*"' | head -1 | cut -d'"' -f4)

  if [ -z "$ROOT_FOLDER_TOKEN" ] || [ "$code" != "0" ]; then
    error "Failed to get root folder token, response:"
    echo "$resp"
    exit 1
  fi

  success "Root folder token: ${ROOT_FOLDER_TOKEN}"
}

########################################
# 内部工具：自动检测租户域名（FEISHU_DOMAIN）
########################################

detect_tenant_domain() {
  if [ -n "$FEISHU_DOMAIN" ]; then
    return 0
  fi

  # 若环境变量已提供，则直接使用
  if [ -n "$FEISHU_DOMAIN_ENV" ]; then
    FEISHU_DOMAIN="$FEISHU_DOMAIN_ENV"
    return 0
  fi

  ensure_root_folder

  info "Detecting Feishu tenant domain..."

  local resp url domain

  # 方法1: 从根目录文件列表中获取 URL
  resp=$(curl -s -X GET \
    "https://open.feishu.cn/open-apis/drive/v1/files?direction=DESC&folder_token=${ROOT_FOLDER_TOKEN}&order_by=EditedTime&page_size=10&user_id_type=open_id" \
    -H "Authorization: Bearer ${TENANT_TOKEN}")

  url=$(echo "$resp" | grep -o '"url":"https://[^"]*"' | head -1 | sed 's/.*"url":"https:\/\///; s/\".*//')

  if [ -n "$url" ]; then
    # url 形如：tcn010uwma1t.feishu.cn/drive/folder/...
    domain=$(echo "$url" | sed 's/\/.*//')
    if [ -n "$domain" ]; then
      FEISHU_DOMAIN="$domain"
      success "Detected tenant domain: ${FEISHU_DOMAIN}"
      return 0
    fi
  fi

  # 方法2: 从根文件夹元数据 API 获取 URL
  resp=$(curl -s -X GET "https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta" \
    -H "Authorization: Bearer ${TENANT_TOKEN}")

  url=$(echo "$resp" | grep -o '"url":"https://[^"]*"' | head -1 | sed 's/.*"url":"https:\/\///; s/\".*//')

  if [ -n "$url" ]; then
    domain=$(echo "$url" | sed 's/\/.*//')
    if [ -n "$domain" ]; then
      FEISHU_DOMAIN="$domain"
      success "Detected tenant domain: ${FEISHU_DOMAIN}"
      return 0
    fi
  fi

  # 方法3: 从租户信息 API 获取（如果可用）
  resp=$(curl -s -X GET "https://open.feishu.cn/open-apis/contact/v3/users/me?user_id_type=open_id" \
    -H "Authorization: Bearer ${TENANT_TOKEN}")

  # 尝试从响应中提取域名信息
  url=$(echo "$resp" | grep -o 'https://[^"]*\.feishu\.cn' | head -1 | sed 's/https:\/\///')

  if [ -n "$url" ]; then
    FEISHU_DOMAIN="$url"
    success "Detected tenant domain: ${FEISHU_DOMAIN}"
    return 0
  fi

  # 如果所有方法都失败，使用默认域名格式
  warning "Could not auto-detect tenant domain."
  warning "Will use placeholder domain in URLs."
  return 1
}

########################################
# 方法 1：上传文件并返回可访问 URL
########################################

feishu_upload_file() {
  local file_path="$1"
  local folder_token="$2"

  if [ -z "$file_path" ]; then
    echo "Usage: bash feishu_drive.sh upload <file_path> [folder_token]" >&2
    exit 1
  fi

  if [ ! -f "$file_path" ]; then
    error "File not found: $file_path"
    exit 1
  fi

  ensure_root_folder

  # 若未传 folder_token，则使用我的空间根目录
  if [ -z "$folder_token" ]; then
    folder_token="$ROOT_FOLDER_TOKEN"
    info "No folder_token provided, using root folder: ${folder_token}"
  fi

  detect_tenant_domain || true

  local file_name file_size upload_resp file_token
  file_name=$(basename "$file_path")
  file_size=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null)

  info "Uploading ${file_name} (${file_size} bytes) to folder ${folder_token}..."

  upload_resp=$(curl -s -X POST "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all" \
    -H "Authorization: Bearer ${TENANT_TOKEN}" \
    -F "file_name=${file_name}" \
    -F "parent_type=explorer" \
    -F "parent_node=${folder_token}" \
    -F "size=${file_size}" \
    -F "file=@${file_path}")

  file_token=$(echo "$upload_resp" | grep -o '"file_token":"[^"]*"' | cut -d'"' -f4)

  if [ -z "$file_token" ]; then
    error "Upload failed, response:"
    echo "$upload_resp"
    exit 1
  fi

  success "File uploaded: ${file_name}"

  # 如果还没有检测到域名，尝试从刚上传的文件获取
  if [ -z "$FEISHU_DOMAIN" ]; then
    info "Attempting to get domain from uploaded file metadata..."
    local file_meta_resp file_url
    file_meta_resp=$(curl -s -X GET \
      "https://open.feishu.cn/open-apis/drive/v1/files/${file_token}?user_id_type=open_id" \
      -H "Authorization: Bearer ${TENANT_TOKEN}")
    
    file_url=$(echo "$file_meta_resp" | grep -o '"url":"https://[^"]*"' | head -1 | sed 's/.*"url":"https:\/\///; s/\".*//')
    
    if [ -n "$file_url" ]; then
      FEISHU_DOMAIN=$(echo "$file_url" | sed 's/\/.*//')
      if [ -n "$FEISHU_DOMAIN" ]; then
        success "Detected tenant domain from uploaded file: ${FEISHU_DOMAIN}"
      fi
    fi
  fi

  # 输出一个简洁的 JSON，便于 SKILL 消费
  if [ -n "$FEISHU_DOMAIN" ]; then
    cat <<EOF
{
  "file_name": "${file_name}",
  "file_token": "${file_token}",
  "folder_token": "${folder_token}",
  "file_url": "https://${FEISHU_DOMAIN}/file/${file_token}"
}
EOF
  else
    # 无法自动识别域名时，仍返回 token 与占位 URL
    cat <<EOF
{
  "file_name": "${file_name}",
  "file_token": "${file_token}",
  "folder_token": "${folder_token}",
  "file_url": "https://<your-tenant>.feishu.cn/file/${file_token}"
}
EOF
  fi
}

########################################
# 方法 2：获取根目录下文件与文件夹列表
########################################

feishu_list_root() {
  local page_size="${1:-50}"

  if ! [[ "$page_size" =~ ^[0-9]+$ ]]; then
    error "page_size must be a number"
    exit 1
  fi

  ensure_root_folder

  info "Listing files under My Space root (page_size=${page_size})..."

  local resp code
  resp=$(curl -s -X GET \
    "https://open.feishu.cn/open-apis/drive/v1/files?direction=DESC&folder_token=${ROOT_FOLDER_TOKEN}&order_by=EditedTime&page_size=${page_size}&user_id_type=open_id" \
    -H "Authorization: Bearer ${TENANT_TOKEN}")

  code=$(echo "$resp" | grep -o '"code":[0-9]*' | head -1 | cut -d':' -f2)

  if [ -z "$code" ] || [ "$code" != "0" ]; then
    error "List files API returned non-zero code, response:"
    echo "$resp"
    exit 1
  fi

  success "List fetched successfully. JSON printed to stdout."

  # 直接输出原始 JSON
  echo "$resp"
}

########################################
# CLI 入口
########################################

cmd="$1"
shift || true

case "$cmd" in
  upload)
    feishu_upload_file "$@"
    ;;
  list-root)
    feishu_list_root "$@"
    ;;
  ""|help|--help|-h)
    echo "Feishu Drive Skill Script"
    echo ""
    echo "Usage:"
    echo "  # 1) 上传文件并返回下载地址（JSON）"
    echo "  bash feishu_drive.sh upload <file_path> [folder_token]"
    echo ""
    echo "  # 2) 获取根目录下的文件与文件夹列表（JSON）"
    echo "  bash feishu_drive.sh list-root [page_size]"
    echo "  bash feishu_drive.sh list-root 100 | jq '.'"
    ;;
  *)
    error "Unknown command: $cmd"
    echo "Run 'bash feishu_drive.sh help' for usage." >&2
    exit 1
    ;;
esac

