@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   武汉大学开放入校政策调研 - 启动中...
echo ============================================
echo.

REM Kill any existing python/flask on port 5000
for /f "tokens=5" %%a in ('netstat -ano ^| find ":5000" ^| find "LISTENING" 2^>nul') do (
    taskkill /f /pid %%a 2>nul
)

REM Start Flask backend (hidden window)
echo [1/2] 启动后端服务...
start /min "" python backend.py

REM Wait for Flask to be ready
:wait
timeout /t 1 /nobreak >nul
curl -s http://localhost:5000/api/health >nul 2>&1
if errorlevel 1 goto wait

echo [2/2] 创建公网隧道...

REM Start localtunnel with pinned subdomain
REM The subdomain makes the URL predictable (may occasionally vary if occupied)
set SUBDOMAIN=whu-survey-2026
start /min "" npx --yes localtunnel --port 5000 --subdomain %SUBDOMAIN%

REM Wait for tunnel
timeout /t 4 /nobreak >nul

echo.
echo ============================================
echo   启动完成！
echo   公网地址: https://%SUBDOMAIN%.loca.lt
echo   本地地址: http://localhost:5000
echo.
echo   按任意键打开二维码页面...
echo ============================================
pause >nul

start http://localhost:5000/qr
start https://%SUBDOMAIN%.loca.lt/qr

echo.
echo 服务器运行中。关闭此窗口不会停止服务。
echo 要停止服务，请关闭后台的 Python 和 Node 进程。
echo.
pause
