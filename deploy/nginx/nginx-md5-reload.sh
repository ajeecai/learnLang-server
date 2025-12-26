#!/bin/sh

# 证书文件路径（从环境变量获取）
CERT_FILE="$SSL_CERT_PATH"
KEY_FILE="$SSL_KEY_PATH"

# 检查间隔（秒）
CHECK_INTERVAL=$((60 * 60 * 24))

# 确保证书文件存在
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Error: Certificate files ($CERT_FILE or $KEY_FILE) not found"
    exit 1
fi

# 初始化 MD5 校验和
CERT_MD5=$(md5sum "$CERT_FILE" | awk '{print $1}')
KEY_MD5=$(md5sum "$KEY_FILE" | awk '{print $1}')
echo "Initial MD5: cert=$CERT_MD5, key=$KEY_MD5"

# 循环检查 MD5 变化
while true; do
    # 计算当前 MD5
    NEW_CERT_MD5=$(md5sum "$CERT_FILE" | awk '{print $1}')
    NEW_KEY_MD5=$(md5sum "$KEY_FILE" | awk '{print $1}')

    # 比较 MD5
    if [ "$CERT_MD5" != "$NEW_CERT_MD5" ] || [ "$KEY_MD5" != "$NEW_KEY_MD5" ]; then
        echo "Certificate change detected: cert=$NEW_CERT_MD5, key=$NEW_KEY_MD5"
        nginx -s reload
        if [ $? -eq 0 ]; then
            echo "Nginx reloaded successfully"
            # 更新 MD5
            CERT_MD5="$NEW_CERT_MD5"
            KEY_MD5="$NEW_KEY_MD5"
        else
            echo "Nginx reload failed, cert MD5 $NEW_CERT_MD5"
        fi
    else
       echo "no need to reload, cert MD5 $NEW_CERT_MD5"
    fi

    # 等待下一次检查
    sleep "$CHECK_INTERVAL"
done
