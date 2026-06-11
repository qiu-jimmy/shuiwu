#!/bin/bash
# 一键同步代码到服务器

REMOTE_USER="root"
REMOTE_HOST="112.124.100.62"
REMOTE_DIR="/home/shuiwu-backend"

# 需要排除的文件/目录
EXCLUDES=(
    ".git"
    "__pycache__"
    "*.pyc"
    ".env"
    "venv"
    ".venv"
    "logs"
    "temp_uploads"
    "__MACOSX"
    "*.zip"
    ".idea"
    ".vscode"
    "node_modules"
    "ip.md"
)

EXCLUDE_ARGS=""
for item in "${EXCLUDES[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude=$item"
done

echo "正在同步代码到 ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR} ..."

rsync -avz \
    $EXCLUDE_ARGS \
    /root/Shuiwu_backend/ \
    ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/

if [ $? -eq 0 ]; then
    echo "同步完成！"
else
    echo "同步失败！"
    exit 1
fi
