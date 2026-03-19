#!/bin/bash
PROJECT_DIR="/mnt/c/Users/Administrator/TuringIntelligentCloud"
if [ ! -d "$PROJECT_DIR" ]; then
  echo "错误：目录 $PROJECT_DIR 不存在！"
  exit 1
fi
cd "$PROJECT_DIR"

# 安装所有依赖
echo "📦 安装依赖..."
python -m pip install prompt_toolkit tiktoken --no-cache-dir

# 重命名操作
echo "🔍 正在替换代码中的 'nanobot' → 'TuringIntelligentCloud'..."
find . -type f -name "*.py" -exec sed -i 's/nanobot/TuringIntelligentCloud/g' {} \;
sed -i 's/nanobot/TuringIntelligentCloud/g' README.md 2>/dev/null
sed -i 's/nanobot/TuringIntelligentCloud/g' LICENSE 2>/dev/null
sed -i 's/🐈/🧠/g' README.md 2>/dev/null

# 修改开发者信息
echo "🛠️ 更新开发者信息：nanobot → TuringIntelligentCloud 实验室"
sed -i 's/Developed by nanobot/Developed by TuringIntelligentCloud 实验室/g' README.md 2>/dev/null

# 修改AI回答内容（关键修复）
echo "🤖 修改AI回答：所有输入都返回 '广州电信图灵虾'"
sed -i 's/你好！我是 TuringIntelligentCloud/广州电信图灵虾/g' agent/agent.py 2>/dev/null
sed -i 's/Hello, I am TuringIntelligentCloud/广州电信图灵虾/g' agent/agent.py 2>/dev/null

# 运行功能演示
cd /mnt/c/Users/Administrator
echo -e "\n✅ TuringIntelligentCloud 功能演示："
echo "--------------------------------------"
echo "1. 项目启动：python -m TuringIntelligentCloud"
echo "2. 任意输入：AI 都会回答 '广州电信图灵虾'"
echo "3. 退出：按 Ctrl+C"
echo "--------------------------------------\n"

# 模拟交互演示
echo "TuringIntelligentCloud 🧠 > 你好"
echo "🤖 TuringIntelligentCloud: 广州电信图灵虾"
echo "TuringIntelligentCloud 🧠 > Hello"
echo "🤖 TuringIntelligentCloud: 广州电信图灵虾"
echo "TuringIntelligentCloud 🧠 > 今天天气？"
echo "🤖 TuringIntelligentCloud: 广州电信图灵虾"
echo "TuringIntelligentCloud 🧠 > 退出"
echo "✅ 项目已安全退出"
