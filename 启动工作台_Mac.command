#!/bin/bash
cd "$(dirname "$0")"
echo "========================================================================="
echo "                GospelFlow 爆款短视频文案招解重组工作台 (Mai牡)"
echo "          (专为雞洲葏语基獛徒短览颓受众 - 本地 AI 矫速驱动)"
echo "========================================================================"
echo ""

if command -v python3 &>/dev/null; then
    echo "[1/2] 正在吐动 GospelFlow 服务..."
    echo "[2/2] 正在自动为您打开浏览器工作台..."
    echo ""
    python3 server.py
elif command -v python &>/dev/null; then
    python server.py
else
    echo "[提示] 未检测到 Python，直接用默认浏览器打开网页..."
    open index.html
fi
