---
name: feishu
description: Feishu Drive skill: upload files and list root folder contents via bash + curl (no Python deps).
metadata: {"nanobot":{"emoji":"🚀","requires":{"bins":["curl","bash","jq"]}}}
---

# Feishu Drive Skill

Upload local files to Feishu Docs (Drive) and list "My Space" root folder contents using a single bash script.

> 📍 **Credentials**: `~/.nanobot/config.json` → `channels.feishu.appId` and `channels.feishu.appSecret`

> 📍 **Credentials**: `~/.nanobot/config.json` → `channels.feishu.appId` and `channels.feishu.appSecret`

## Scripts

- `{baseDir}/scripts/feishu_drive.sh`
  - `upload`: 上传文件并返回可访问 URL（JSON）
  - `list-root`: 获取「我的空间」根目录下的文件与文件夹列表（JSON）

## Quickstart: 上传文件并获取访问地址

```bash
# 上传到「我的空间」根目录
bash {baseDir}/scripts/feishu_drive.sh upload /path/to/file.txt

# 上传到指定 folder_token
bash {baseDir}/scripts/feishu_drive.sh upload /path/to/file.txt DWvXfhNRelIEGXdMpi3curtCnAe

# 返回示例（JSON）：
# {
#   "file_name": "test_upload.txt",
#   "file_token": "ELy0b7tBnoRVgxxLT5kc4paMnZc",
#   "folder_token": "nodcnJtjLHkwwJH8LfEQI1uRgWg",
#   "file_url": "https://<your-tenant>.feishu.cn/file/ELy0b7tBnoRVgxxLT5kc4paMnZc"
# }
```

## Quickstart: 列出「我的空间」根目录文件 / 文件夹

```python
import json
result = exec(f"bash {{baseDir}}/scripts/feishu_drive.sh list-root 100")
data = json.loads(result["stdout"])

# data["data"]["files"] 是根目录下的文件与文件夹列表
```

筛选所有文件夹：

```python
folders = [f for f in data["data"]["files"] if f.get("type") == "folder"]
```

## Script Parameters / Methods

### 1. `upload` —— 上传文件并返回下载地址（JSON）

```bash
bash {baseDir}/scripts/feishu_drive.sh upload <file_path> [folder_token]
```

- `file_path`: 本地文件路径
- `folder_token`:（可选）目标文件夹 token。不传时上传到「我的空间」根目录

返回 JSON 字段：

- `file_name`: 文件名
- `file_token`: 文件 token
- `folder_token`: 所在文件夹 token
- `file_url`: 飞书云文档访问地址（基于租户域名推导）

### 2. `list-root` —— 获取根目录下文件 / 文件夹列表

```bash
bash {baseDir}/scripts/feishu_drive.sh list-root [page_size]
```

- `page_size`:（可选，默认 50）每页返回数量

返回为飞书原始列表 JSON，关键字段：

- `data.files[]`: 文件/文件夹列表
  - `type`: `"file"` 或 `"folder"`
  - `name`: 名称
  - `token`: 文件 / 文件夹 token
  - `url`: 访问链接

## Getting Folder Token

To upload to a specific folder:
1. Open the folder in Feishu Docs
2. Copy token from URL: `https://xxx.feishu.cn/drive/folder/fldcnXXXXXXXXXXXXXXX`
3. Token is: `fldcnXXXXXXXXXXXXXXX` (part after `/folder/`)

## Required Permissions

在 [Feishu Open Platform](https://open.feishu.cn/app) 中开启：

- `drive:drive` - Drive 读写权限（必需）

## How It Works

脚本内部主要步骤：

1. 从 `~/.nanobot/config.json` 读取 `channels.feishu.appId` / `appSecret`
2. 调用 `POST /open-apis/auth/v3/tenant_access_token/internal` 获取 `tenant_access_token`
3. 调用 `GET /open-apis/drive/explorer/v2/root_folder/meta` 获取「我的空间」根 `folder_token`
4. 调用 `POST /open-apis/drive/v1/medias/upload_all` 上传文件
5. 通过 `GET /open-apis/drive/v1/files` 获取任意文件 URL，从中解析出租户域名，拼出最终 `file_url`

## Key Points

- ✅ 统一使用 `{baseDir}/scripts/feishu_drive.sh`（`upload` / `list-root` 两个方法）
- ✅ 无 Python 依赖，仅需 `curl` 与 `bash`（推荐安装 `jq` 便于调试）
- ✅ 凭证自动读取自 `~/.nanobot/config.json`
- ✅ 支持自动检测租户域名并生成可访问的 `file_url`
- ❌ 不要尝试调用单独的 `upload_file.sh` / `list_my_folder.sh` —— 它们已被合并进 `feishu_drive.sh`
