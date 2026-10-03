@echo off
REM ============================================================
REM  baizeOS 前后端联通性测试（需先启动 start.py）
REM
REM  用法：先在一个窗口跑 start.py，再在另一个窗口跑本脚本。
REM  全部请求经 Vite 代理(3000)发出，与浏览器真实路径一致。
REM ============================================================
setlocal
set B=http://127.0.0.1:3000

echo.
echo [1/5] 前端类型检查 vue-tsc ...
cd /d "%~dp0.."
call node_modules\.bin\vue-tsc.cmd --noEmit -p tsconfig.app.json || goto :fail

echo [2/5] 前端生产构建 vite build ...
call node_modules\.bin\vite.cmd build >nul || goto :fail

echo [3/5] 后端冒烟（读 + 会话 + 流式 + 落库）...
cd /d "%~dp0..\..\backend"
.venv\Scripts\python.exe tests\e2e_smoke.py %B% || goto :fail

echo [4/5] 后端写路径（知识库 CRUD + 附件）...
.venv\Scripts\python.exe tests\e2e_write_paths.py %B% || goto :fail

echo [5/5] 前端 API 层契约 ...
cd /d "%~dp0.."
call node tests\api_contract.mjs %B% || goto :fail

echo [6/6] 前端页面真实渲染 ...
call node tests\ui_smoke.mjs %B% || goto :fail

echo.
echo ============================================
echo   全部通过
echo ============================================
exit /b 0

:fail
echo.
echo ============================================
echo   有用例失败，见上方输出
echo ============================================
exit /b 1
