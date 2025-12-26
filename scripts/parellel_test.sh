#!/bin/bash

HOST=$1
MODE=$2  # 第2个参数：s 或 t
NUM=$3  # 第3个参数：s 或 t


echo "HOST: $HOST"
echo "MODE: $MODE"
if [[ $# -ne 3 ]]; then
    echo "❌ 无效参数。用法："
    echo "  ./parellel_test.sh https://127.0.0.1:9443 s 4 # 并发进行synthesize"
    echo "  ./parellel_test.sh https://127.0.0.1:9443 t 4 # 并发进行transcribe"
    exit 1
fi

export TOKEN # 让 parallel 继承当前 TOKEN
export HOME
INPUT_FILE="./speech.txt"
AUDIO_FILE="$HOME/test-audio.wav"

start_time=$(date +%s)

if [[ "$MODE" == "s" ]]; then
    echo "Running synthesize mode..."

    seq 1 $NUM| parallel -j $NUM '
        TEXT=$(<'"$INPUT_FILE"')
        curl -k -X POST '"$HOST"'/synthesize \
        -H "Authorization: Bearer '"$TOKEN"'" \
        -F "text=$TEXT" \
        -o ~/output_{}.wav
    '

elif [[ "$MODE" == "t" ]]; then
    echo "Running transcribe mode..."
    seq 1 $NUM| parallel -j $NUM '
        curl -k -X POST '"$HOST"'/transcribe \
        -H "Authorization: Bearer '"$TOKEN"'" \
        -F "file=@'"$AUDIO_FILE"'" \
        -o ~/output_{}.txt
    '

else
    echo "❌ 无效参数。用法："
    echo "  ./parellel_test s   # 进行synthesize"
    echo "  ./parellel_test t   # 进行transcribe"
fi

end_time=$(date +%s)
elapsed=$((end_time - start_time))

echo "✅ 全部任务完成，总耗时：${elapsed} 秒"