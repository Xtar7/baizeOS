#!/usr/bin/env bash
# baizeOS 前端截图脚本：启动 dev → headless Edge 截图（桌面/移动/知识库页）→ 关服务
set -u
cd "$(dirname "$0")"
OUT="E:/baizeOS/.impeccable/review"
mkdir -p "$OUT"

npm run dev > /tmp/vite.log 2>&1 &
PID=$!

# 等待 vite 就绪（最多 20 秒）
for i in $(seq 1 40); do
  if curl -s -o /dev/null http://localhost:3000/; then break; fi
  sleep 0.5
done

# 定位 Edge / Chrome
E="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
[ -f "$E" ] || E="/c/Program Files/Microsoft/Edge/Application/msedge.exe"
[ -f "$E" ] || E="/c/Program Files/Google/Chrome/Application/chrome.exe"

"$E" --headless=new --disable-gpu --force-device-scale-factor=1 --virtual-time-budget=15000 --window-size=1440,900 --screenshot="$OUT/desktop.png" http://localhost:3000/
# 注：Chromium headless 最小窗口宽约 500，390 会被钳到 ~492 导致 PNG 裁切；
# 用 500 宽窗口拍摄窄视口（探针已验证 390 构造安全：单列网格 + 折行副标题）。
"$E" --headless=new --disable-gpu --force-device-scale-factor=1 --virtual-time-budget=15000 --window-size=500,900   --screenshot="$OUT/mobile.png"   http://localhost:3000/
"$E" --headless=new --disable-gpu --force-device-scale-factor=1 --virtual-time-budget=15000 --window-size=1440,900 --screenshot="$OUT/kb.png"       http://localhost:3000/kb
"$E" --headless=new --disable-gpu --force-device-scale-factor=1 --virtual-time-budget=15000 --window-size=1440,900 --screenshot="$OUT/settings.png" http://localhost:3000/settings

taskkill //PID "$PID" //T //F > /dev/null 2>&1
ls -la "$OUT"
