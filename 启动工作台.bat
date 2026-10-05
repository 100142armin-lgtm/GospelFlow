@echo off
chcp 65001 >nul
title GospelFlow 工作台启动器
echo ==============================================================================
echo                 GospelFlow 爆款短视频文案拆解重组工作台
echo           (专为非洲葡语基督徒短视频受众打造 - RTX 5060 本地加速)
echo ==============================================================================
echo.

cd /d "%~dp0"

:: 检查 Python 是否存在
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 未检测到 Python，将直接用默认浏览器打开网页模式...
    start index.html
    pause
    exit /b
)

echo [1/2] 正在启动 GospelFlow 本地中继与服务...
echo [2/2] 正在自动为您打开浏览器工作台...
echo.
python server.py

pause
