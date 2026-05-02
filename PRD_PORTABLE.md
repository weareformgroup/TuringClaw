# TuringClaw Windows 便携版 PRD

## 1. 产品定位

**一句话：** 一键运行、无需安装的 Windows AI 助手，插上U盘也能跑。

**目标用户：** 普通 Windows 用户，不想折腾 Python 环境、命令行，只想双击运行就能和本地 AI 对话。

**核心价值：** 零配置、零依赖、零安装，下载即用。

---

## 2. 当前状态盘点

| 维度 | 现状 | 说明 |
|------|------|------|
| 运行时 | Python 3.11+ | 需要用户自行安装 Anaconda/Python |
| 依赖 | 30+ 个 pip 包 | litellm、pydantic、rich 等 |
| GUI | Tkinter 桌面应用 (`gui/chat.py`) | 功能完整，但界面偏技术化 |
| 核心服务 | Gateway（CLI 启动） | 需要命令行 `python -m TuringClaw gateway` |
| LLM 支持 | LiteLLM + Ollama | 已绕过 litellm，直接走 custom provider |
| Channel | Telegram/Discord/飞书等 | 需要各自配置 token |
| 数据存储 | `~/.TuringClaw/` | 配置、日志、sessions |
| 打包现状 | `build/` 目录有 PyInstaller 配置 | 但未完整测试 |

---

## 3. 打包方案选择

### 方案 A：PyInstaller 单文件打包（推荐）
- **优点：** 简单成熟、支持 Windows、单 exe 文件、分发方便
- **缺点：** 启动较慢（每次解压）、文件体积大（~500MB 含 Python 运行时）
- **适合：** 分发单用户使用

### 方案 B：Nuitka 编译
- **优点：** 性能更好、启动快、可生成真正 .exe
- **缺点：** 编译慢、调试复杂
- **适合：** 追求性能的正式版本

### 方案 C：Portable Python + 启动器
- **优点：** 保持 Python 环境可移植、升级方便
- **缺点：** 体积更大（包含完整 Python）、结构复杂
- **适合：** 需要保留 pip 安装能力的场景

### 方案 D：Tauri / Electron + Python 后端
- **优点：** 原生体验、自动更新、应用商店分发
- **缺点：** 需要重写前端、架构改动大
- **适合：** 长期产品化路线

**推荐：** 方案 A（PyInstaller）+ 保留 GUI，作为第一个可发布版本。

---

## 4. 功能规划（Phase 1 - 最小可行产品）

### 4.1 必须功能（MVP）
1. **双击即运行** — 用户下载压缩包 → 解压 → 双击 `TuringClaw.exe` → 出现 GUI 窗口
2. **内置 Ollama 连接** — 自动检测本地 Ollama（默认 `http://localhost:11434`），自动列出可用模型
3. **聊天界面** — 类似 ChatGPT 的对话框，支持：
   - 发送消息、接收回复
   - 流式输出（打字机效果）
   - 新会话 / 清除对话
4. **模型选择下拉框** — 从 Ollama 已安装模型中选择
5. **首次运行引导** — 检测 Ollama 是否运行，未检测到时弹出提示引导安装

### 4.2 应该有功能（Phase 2）
6. **内置 Ollama 管理** — 在 GUI 里下载/删除 Ollama 模型
7. **配置面板** — API Base、Model 默认值、系统提示词
8. **对话历史** — 本地保存历史记录
9. **多 Channel 支持** — Telegram Bot 接入（在配置面板里填 token 即可启用）

### 4.3 最好有功能（Phase 3）
10. **Web 界面** — 浏览器访问 `localhost:18790` 进行聊天
11. **系统托盘** — 最小化到托盘，后台运行
12. **自动更新** — 检测新版本并提示下载

---

## 5. 技术架构

```
TuringClaw.exe (PyInstaller 打包)
├── Python 3.11 运行时（内置）
├── 所有 pip 依赖（内置）
├── TuringClaw 核心代码（内置）
├── Tkinter GUI 界面（内置）
├── 用户数据目录
│   ├── config.json          ← 用户配置
│   ├── sessions/            ← 对话历史
│   └── logs/               ← 运行日志
└── 外部依赖（由用户安装）
    └── Ollama（需用户自行安装）
```

**数据目录位置：** 与 exe 同目录的 `data/` 文件夹（便携优先），或 `%APPDATA%/TuringClaw`（标准安装模式）

---

## 6. 用户体验流程

### 首次运行
1. 用户解压 zip，双击 `TuringClaw.exe`
2. 程序启动，显示加载界面（1-3秒）
3. **检测 Ollama：**
   - ✅ 找到 → 显示模型列表，进入聊天界面
   - ❌ 未找到 → 弹窗提示："请先安装 Ollama"，提供下载链接按钮
4. 用户选择模型，开始聊天

### 日常使用
1. 双击 `TuringClaw.exe`
2. 直接进入上次对话界面（记住上次选择）

---

## 7. 打包清单

| 文件 | 来源 | 处理方式 |
|------|------|----------|
| Python 3.11 运行时 | 自动打包 | PyInstaller --onedir |
| pip 依赖 | pyproject.toml | 自动分析 |
| Tkinter | Python 内置 | 无需额外处理 |
| Ollama SDK | 无（直接 HTTP） | 无需打包 |
| 用户数据 | 运行时生成 | exe 同目录 data/ |

**预估体积：** ~400-600 MB（包含 Python 运行时）

---

## 8. 待解决问题

| 问题 | 现状 | 建议方案 |
|------|------|----------|
| litellm 包太大 | ~16MB，依赖多 | 已绕过，使用 custom provider |
| Tkinter 在 Windows 打包后缺 DLL | 常见问题 | 需测试验证，可能需要补充微软 VC++ 运行库 |
| 图标和资源文件 | 无正式图标 | 需要设计图标（chinatelecom.jpeg 存在） |
| Windows Defender 误报 | PyInstaller exe 常见问题 | 需要代码签名或提交白名单申请 |
| GUI 界面太技术化 | 当前为英文界面 | 需要汉化 + 简化界面 |
| Ollama 检测逻辑 | 已有部分代码 | 需要完善自动检测和引导 |

---

## 9. 里程碑

| 阶段 | 目标 | 验收标准 |
|------|------|----------|
| M1 | 完成 PyInstaller 打包，exe 能启动 | 双击 exe → 出现 GUI 窗口，无报错 |
| M2 | Ollama 自动检测 + 模型选择 | 未安装 Ollama 时有引导，安装后自动连接 |
| M3 | 聊天功能完整可用 | 发消息 → 流式回复 → 能正常对话 |
| M4 | 配置面板 + 对话历史 | 可修改 API 地址，可查看历史记录 |
| M5 | 精简 GUI + 汉化 | 界面友好，普通人看得懂 |

---

## 10. 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| PyInstaller 打包失败 | 中 | 高 | 预先在干净 Win10 VM 上测试 |
| Windows Defender 误报 | 高 | 中 | 提交 Microsoft 安全白名单申请 |
| Tkinter DLL 缺失 | 中 | 高 | 打包时包含必要 DLL，附 VC++ 运行库 |
| 体积太大（>500MB） | 低 | 低 | 可接受，目标是功能而非体积 |
| Ollama 版本兼容性 | 低 | 中 | 支持 Ollama 0.1+ 主流版本 |

---

**下一步行动：**
1. 确认打包工具选型（PyInstaller 是否满足需求）
2. 搭建打包环境，在干净 Windows 上试打第一个包
3. 验证 exe 能否启动
4. 讨论 GUI 简化/汉化方案
