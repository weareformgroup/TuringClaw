# TuringClaw - 功能特性文档

> 本文档记录 TuringClaw GUI 移植版本的所有功能特性、修改内容和设计决策。

---

## 一、项目概述

### 1.1 什么是 TuringClaw GUI？
TuringClaw GUI 是将 OpenClaw/TuringClaw 框架从 CLI 工具扩展为**带图形界面的桌面应用**，支持本地 AI 模型和云端 AI 服务商。

### 1.2 核心特点
| 特点 | 说明 |
|------|------|
| 🏠 本地运行 | Ollama 本地大模型，无需网络 |
| 💰 完全免费 | Ollama 模型无需付费 |
| 🇨🇳 中国电信品牌 | 定制 UI + Logo |
| 📊 流量统计 | Token 使用量追踪 |
| 🌐 多云端支持 | OpenRouter / SiliconFlow / DeepSeek 等 |

---

## 二、主要功能

### 2.1 主界面
```
┌─────────────────────────────────────────────────────┐
│  [CT Logo] TuringClaw   [Select Provider ▼]  ● Demo Mode  [Usage] [Settings] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  System: China Telecom AI Assistant Ready.           │
│  Click 'Select Provider' to configure Ollama...     │
│                                                     │
│                                                     │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [Type message here...                          ]  Send  │
└─────────────────────────────────────────────────────┘
```

### 2.2 AI 提供商支持

#### 🟢 本地模型 (Ollama) — 推荐
- **免费使用**：无需 API Key，无需网络
- **自动检测**：启动时自动识别已安装的模型
- **可选模型**：
  - qwen2.5:14b-instruct (通义千问)
  - qwq:latest
  - deepseek-r1:1.5b / 7b / 14b

#### ☁️ 云端提供商 (需要 API Key)
| 提供商 | 免费额度 | 状态 |
|--------|----------|------|
| OpenRouter | 每天 $1 | 待集成 |
| SiliconFlow (硅基流动) | 200万 tokens | 待集成 |
| DeepSeek | 200万 tokens | 待集成 |
| Google Gemini | 免费额度 | 待集成 |
| Groq | 免费额度 | 待集成 |
| 智谱 AI | 500万 tokens | 待集成 |
| 阿里云 DashScope | 100万 tokens | 待集成 |

### 2.3 流量统计
- 按提供商统计输入/输出 Token 数量
- 记录请求次数
- 本地持久化存储 (`~/.TuringClaw/token_usage.json`)

### 2.4 设置面板
- 版本信息
- 一键切换演示模式
- API Key 管理

---

## 三、中国电信图标系统

### 3.1 设计理念
所有图标均基于**中国电信官方 Logo**（蓝色圆形标志）进行色彩变体，保持品牌一致性。

### 3.2 图标颜色对照表

| 用途 | 颜色 | 说明 |
|------|------|------|
| 🟦 主 Logo | 原色 #004A80 | 工具栏主 Logo（深蓝） |
| 🟩 Ollama | 绿色变体 | 本地模型 / 在线状态 |
| 🟥 错误 | 红色变体 | 错误提示 / 警告 |
| 🟨 系统 | 黄色变体 | 系统通知 / 信息 |
| 🟪 设置 | 紫色变体 | 设置按钮 |
| 🟦 状态 | 青色变体 | 状态指示 |
| 🟧 流量 | 橙色变体 | Token 统计 |
| ⬜ 演示 | 白色变体 | 演示模式 |

### 3.3 图标生成方式
图标通过运行时动态生成（`chat.py` 中的 `load_ct_logo()` 函数）：
```python
# 从原始 chinatelecom.jpeg 读取
# 通过 PIL 对 RGB 通道进行偏移着色
# 生成 8 种颜色变体
```

### 3.4 界面主题色
| 元素 | 颜色代码 |
|------|----------|
| 背景 | #1E1E2E (深灰紫) |
| 卡片背景 | #313244 |
| 文字 | #CDD6F4 |
| 主色调 | #00D4FF (科技青) |
| 成功 | #A6E3A1 |
| 错误 | #F38BA8 |
| 警告 | #F9E2AF |

---

## 四、快速开始

### 4.1 Windows 运行
```bash
# 方法 1：双击运行
C:\Users\Administrator\TuringClaw\TuringClaw.bat

# 方法 2：命令行
cd C:\Users\Administrator\TuringClaw
python gui\chat.py
```

### 4.2 Ollama 安装 (Windows)
```powershell
# 1. 下载：https://ollama.com/download/windows
# 2. 安装后运行：
ollama pull qwen2.5:14b-instruct
ollama serve
```

### 4.3 macOS
```bash
# 安装 Ollama
brew install ollama

# 拉取模型
ollama pull qwen2.5:14b-instruct
ollama serve

# 运行 GUI
cd TuringClaw
python3 gui/chat.py
```

---

## 五、文件结构

```
TuringClaw/
├── gui/
│   ├── chat.py              # GUI 主程序
│   ├── providers.py         # AI 提供商配置模块
│   ├── chinatelecom.jpeg    # 中国电信原始 Logo
│   └── __init__.py
├── TuringClaw.bat           # Windows 启动脚本
├── TuringClaw.vbs          # Windows 静默启动
├── pyproject.toml           # Python 项目配置
├── GUI_FEATURES.md         # 本文档
├── build.py                 # 跨平台打包脚本
├── BUILD_WINDOWS.bat        # Windows 打包脚本
├── BUILD_MACOS.sh          # macOS 打包脚本
├── packages/               # PyInstaller + Pillow (本地安装)
└── dist/                  # 打包输出目录
    ├── windows/
    │   └── TuringClaw.exe  # Windows 单文件可执行文件
    └── macos/
        └── TuringClaw      # macOS 应用包
```

---

## 六、打包说明

### 6.1 Windows 打包

#### 方式 1：使用打包脚本（推荐）
```batch
# 以管理员身份运行 CMD，然后：
cd C:\Users\Administrator\TuringClaw
BUILD_WINDOWS.bat
```

#### 方式 2：手动构建
```powershell
# 安装依赖
pip install pyinstaller pillow

# 构建
pyinstaller --name=TuringClaw --windowed --onefile ^
    --icon=gui\chinatelecom.jpeg ^
    --add-data="gui;gui" ^
    --hidden-import=PIL ^
    --collect-all=PIL ^
    gui\chat.py
```

#### 方式 3：使用已配置的本地包
```batch
cd C:\Users\Administrator\TuringClaw
set PYTHONPATH=packages
python packages\PyInstaller\__main__.py --name=TuringClaw --windowed --onefile gui\chat.py
```

**输出**：`dist\windows\TuringClaw.exe`（单文件，约 150-300MB）

### 6.2 macOS 打包
```bash
# 在 macOS 上运行
chmod +x BUILD_MACOS.sh
./BUILD_MACOS.sh
```

**输出**：`dist/macos/TuringClaw`（应用包）

### 6.3 打包依赖
| 工具 | 版本 | 说明 |
|------|------|------|
| Python | ≥ 3.8 | 运行时 |
| PyInstaller | ≥ 6.0 | 打包工具 |
| Pillow | ≥ 10.0 | 图像处理（Logo 着色） |

---

## 七、已知限制

| 问题 | 说明 | 解决方案 |
|------|------|----------|
| 云端 AI 未集成 | 目前仅 Ollama 可用 | 等待后续版本更新 |
| macOS 需要 Python | GUI 非独立应用 | 可通过 PyInstaller 打包为 .app |
| 中文输入法 | 部分系统可能出现 | 使用英文界面（默认） |

---

## 八、版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 0.1.0 | 2026-03-19 | 初始 GUI 移植，演示模式 |
| 0.1.1 | 2026-03-19 | 添加 Ollama 本地模型支持 |
| 0.1.2 | 2026-03-20 | 中国电信品牌定制图标 |
| 0.2.0 | 2026-03-20 | 流量统计系统，彩色 CT Logo UI |

---

## 九、致谢

- 基于 [OpenClaw](https://github.com/openclaw/openclaw) 框架
- 本地 AI 由 [Ollama](https://ollama.com/) 提供
- 图标灵感来自中国电信官方 Logo

---

*文档更新：2026-03-20*
