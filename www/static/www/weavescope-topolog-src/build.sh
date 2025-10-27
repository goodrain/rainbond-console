#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "================================"
echo "开始构建 Weavescope Topology"
echo "================================"

# 加载 nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "当前 Node 版本: $(node -v)"

# 切换到 Node 6.9.0
echo "切换到 Node 6.9.0..."
nvm use 6.9.0

echo "切换后的 Node 版本: $(node -v)"

# 执行构建
echo "开始构建..."
npm run build

echo "================================"
echo "构建完成!"
echo "================================"
echo ""
echo "生成的文件位于:"
echo "../weavescope-topolog/"
echo ""
echo "请刷新浏览器以加载新文件"
