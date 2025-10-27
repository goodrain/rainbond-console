#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "================================"
echo "安装依赖"
echo "================================"

# 加载 nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "当前 Node 版本: $(node -v)"

# 切换到 Node 6.9.0
echo "切换到 Node 6.9.0..."
nvm use 6.9.0

echo "切换后的 Node 版本: $(node -v)"

# 安装依赖
echo "开始安装依赖..."
npm install

echo "================================"
echo "依赖安装完成!"
echo "================================"
