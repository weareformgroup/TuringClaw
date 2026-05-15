# TuringClaw Changelog

## [2.0.0] - 2026-05-02

### From v1.0 (Inherited)
- Three-tier privacy router (S1/S2/S3)
- Ollama streaming chat with typewriter effect
- 9/10 channel support (matrix excluded - Windows long path)
- Dark Catppuccin theme, China Telecom branded
- Top input bar layout (fixed from bottom layout issues)
- Free provider support with token tracking
- GUI: Settings, Usage, Provider selection dialogs

### v2.0 Goals
- ✅ Clean independent repository
- ✅ Chinese full localization (41 items, commit 2f41d37)
- ✅ Chat history persistence (gui/chat_history.py, 256 lines)
- ⏳ Rebuild portable exe (blocked: C drive ~15GB free)

## [2.0.1-dev] - 2026-05-15

### Added
- **中文完整本地化**: All 41 English UI texts replaced with Chinese
  - Window title: "TuringClaw - 中国电信 AI 助手"
  - Toolbar: 选择 AI 服务 / 用量统计 / 设置 / 历史
  - All dialogs, menus, error messages, demo responses
  - Version sync: Settings shows v2.0.0

- **聊天历史持久化**: New `gui/chat_history.py` module
  - `ChatHistoryManager`: session start/save/load/search/delete/export
  - Real-time save on every message (crash-safe)
  - Thread-safe with `threading.Lock`
  - Integrated into `gui/chat.py`:
    - `msg()` auto-records to history
    - `msg_stream_end()` saves streaming content
    - `_on_close()` saves session on window close
    - New toolbar button: 「历史」
    - History popup: list sessions, search, double-click to load
    - Right-click: delete session / export as TXT/Markdown
  - Session files: `~/.TuringClaw/chat_history/chat_YYYYMMDD_HHMMSS.json`
