#!/bin/bash
# 请关闭vscode的自动保存功能 ！！！
# 这个script的用途是推送本地修改的代码到另外一台机器上编译运行
# 需要在 .env 文件中定义: REMOTE_USER, REMOTE_HOST, REMOTE_PATH, REMOTE_SSH_KEY, SOCK_PROXY
# Usage: ./scripts/auto_rsync.sh <LOCAL_PATH>

set -o allexport
source .env
set +o allexport

# 获取参数
if [ -z "$1" ]; then
    echo "Usage: $0 <LOCAL_PATH>"
    exit 1
fi
LOCAL_PATH=$1

# 远程服务器信息
REMOTE_USER=$REMOTE_USER
REMOTE_HOST=$REMOTE_HOST
REMOTE_PATH=$REMOTE_PATH
REMOTE_SSH_KEY=$REMOTE_SSH_KEY

# 构建排除参数和过滤正则
# 统一排除 .git 以及常见的客户端构建目录 (node_modules, android, ios, etc.)
EXCLUDE_OPTS="--exclude '.git/' --exclude 'android/' --exclude 'ios/' --exclude 'node_modules/' --exclude '.expo/' --exclude '.gradle/' --exclude '.idea/' --exclude 'build/' --exclude '*.apk'"
GREP_FILTER="/\.git/|/(node_modules|android|ios|\.expo|\.gradle|\.idea|build)/|build.*\.apk$"

# 构造通用的 rsync 命令字符串
RSYNC_CMD="rsync -avz $EXCLUDE_OPTS -e \"ssh -o ProxyCommand=\\\"nc -x $SOCK_PROXY %h %p\\\" -i $REMOTE_SSH_KEY\" \"$LOCAL_PATH\" \"$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH\""

echo "启动阶段，先做一次完整同步..."
echo "Executing: $RSYNC_CMD"
eval $RSYNC_CMD

# 启动监听
echo "Starting watch on $LOCAL_PATH..."
inotifywait -m -e attrib,create,delete,move,close_write --format '%e %w%f' -r "$LOCAL_PATH" | \
grep -Ev "$GREP_FILTER" | \
while read event file
do
    echo "[`date`] Event: $event, File changed: $file"

    # 通过SOCKS代理rsync
    eval $RSYNC_CMD

    if [ $? -eq 0 ]; then
        echo "[`date`] ✅ Sync completed successfully"
    else
        echo "[`date`] ❌ Sync failed !!!"
    fi
done
