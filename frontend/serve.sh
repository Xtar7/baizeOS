#!/usr/bin/env bash
# 后台启动前端 dev server 并打开浏览器（命令通道用，跑完立即返回）
cd "$(dirname "$0")"
nohup pnpm run dev > /tmp/vite.log 2>&1 &
sleep 5
cmd //c start "" "http://localhost:3000"
echo "前端已在后台启动，日志: /tmp/vite.log"
