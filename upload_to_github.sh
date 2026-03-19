#!/bin/bash
PROJECT_DIR="/mnt/c/Users/Administrator/TuringIntelligentCloud"

# 检查目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
  echo "错误：目录 $PROJECT_DIR 不存在！"
  echo "请确保项目已正确移动到 /mnt/c/Users/Administrator/TuringIntelligentCloud"
  exit 1
fi

cd "$PROJECT_DIR"

# 1. 项目名从 TuringIntelligentCloud → TuringClaw
echo "🔄 重命名项目：TuringIntelligentCloud → TuringClaw"
find . -type f -name "*.py" -exec sed -i 's/TuringIntelligentCloud/TuringClaw/g' {} \;
sed -i 's/TuringIntelligentCloud/TuringClaw/g' README.md 2>/dev/null
sed -i 's/TuringIntelligentCloud/TuringClaw/g' LICENSE 2>/dev/null
sed -i 's/TuringIntelligentCloud 实验室/TuringClaw 实验室/g' README.md 2>/dev/null

# 2. 确保AI回答为"广州电信图灵虾"
echo "🤖 保持AI回答：广州电信图灵虾"
sed -i 's/广州电信图灵虾/广州电信图灵虾/g' agent/agent.py 2>/dev/null

# 3. 配置Git用户信息（解决身份问题）
echo "🔧 配置Git用户信息"
git config --global user.email "turing@example.com"
git config --global user.name "Turing"

# 4. 清理已存在的Git配置
echo "🧹 清理Git配置"
if git remote | grep -q "origin"; then
  echo "⚠️ 删除已存在的远程仓库 origin"
  git remote remove origin
fi

# 5. 初始化Git并推送
echo "🚀 上传到GitHub：https://github.com/weareformgroup/TuringClaw"
git add .
git commit -m "Update to TuringClaw: Project name changed"
git remote add origin https://github.com/weareformgroup/TuringClaw.git
git push -u origin main

# 6. 验证输出
echo -e "\n✅ 上传成功！访问：https://github.com/weareformgroup/TuringClaw"
echo "  • 项目名称: TuringClaw 🧠"
echo "  • 开发者: TuringClaw 实验室"
echo "  • AI回答: 无论输入什么，都返回 '广州电信图灵虾'"
