#!/bin/sh

# 确保 DOMAIN_NAME 已设置
if [ -z "$DOMAIN_NAME" ]; then
    echo "Error: DOMAIN_NAME not set"
    exit 1
fi

# 添加主机条目到 /etc/hosts
echo "127.0.0.1 $DOMAIN_NAME" >> /etc/hosts

# 执行原始 CMD
exec "$@"
