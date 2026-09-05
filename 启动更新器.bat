@echo off
rem DeepSeek Harness 自动检测与更新器 启动器
rem 使用 pythonw 无控制台窗口启动 GUI
chcp 65001 >nul
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw updater_gui.pyw
) else (
    start "" python updater_gui.pyw
)
