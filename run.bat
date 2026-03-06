@echo off
chcp 65001 >nul
echo ====================================
echo   YouTube频道监控脚本
echo ====================================
echo.

cd /d "%~dp0"
"C:\Users\90543\AppData\Local\Programs\Python\Python312\python.exe" monitor.py

echo.
echo 按任意键关闭窗口...
pause >nul
