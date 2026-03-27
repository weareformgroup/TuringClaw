# Changelog

All notable changes to TuringClaw GUI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.0.0] - 2026-03-27

### 🎉 First Stable Release

This is the first stable release of **TuringClaw GUI** — a desktop AI assistant with local Ollama support and a three-tier privacy routing system inspired by EdgeClaw.

---

### ✨ New Features

#### 🖥️ GUI Application (`gui/chat.py`)
- Full Tkinter-based desktop chat interface
- China Telecom branded UI with dynamic color-variant logo system
- "Select AI Provider" panel with Ollama model picker
- Token usage statistics panel
- Settings panel with privacy level control
- Status bar showing current AI provider and privacy level

#### 🤖 Ollama Local Model Integration
- Auto-detect installed Ollama models on startup
- Model selection via dropdown (Combobox)
- Supports all locally installed models (qwen2.5, deepseek-r1, qwq, etc.)
- Fixed threading race condition in provider state management
- Fixed lambda closure bug in model selection button

#### 🔒 Privacy Router — Three-Tier Privacy Routing (`gui/privacy_router.py`)
Inspired by EdgeClaw's GuardAgent protocol. Automatically classifies every message by sensitivity and routes accordingly.

| Level | Mode | Data Flow | Trigger |
|-------|------|-----------|---------|
| **S1** | Normal | Direct to model | No sensitive data detected |
| **S2** | Desensitize | Masked text sent to model | Phone, ID card, email, bank card, IP |
| **S3** | Secure Local | Forced to local Ollama only | Password, API key, private key, medical data |

**Detectors:**
- `PrivacyDetector` — regex + keyword rule engine (millisecond response)
- `Desensitizer` — masks sensitive fields, preserves mapping for restoration
- `PrivacyRouter` — routes based on detection result; supports manual level override

**Desensitization rules:**
- 📱 Phone: `138****5678`
- 🪪 ID Card: `110101****1234`
- 💳 Bank Card: `6222****0123`
- 📧 Email: `z***@example.com`
- 🌐 Private IP: `192.168.*.*`
- 👤 Name KV: `姓名：***`

**GUI integration:**
- Privacy level indicator in toolbar: 🟢 S1 / 🟡 S2 / 🔴 S3
- Auto-switch to Ollama when S3 is triggered
- System message notification on S3 activation
- Manual override in Settings panel (S1 / S2 / S3 / Auto)
- Audit log written to `~/.TuringClaw/privacy_audit.log`

#### 🧪 Test Suite (`test_privacy_router.py`)
- 16 automated test cases covering all three privacy levels
- All 16 tests passing ✅

#### 📦 Provider System (`gui/providers.py`)
- `FREE_PROVIDERS` registry with 9 providers (Ollama + 8 cloud)
- `TokenTracker` for per-provider token usage tracking
- Dual import path (`gui.providers` / `providers`) for flexible execution

---

### 🐛 Bug Fixes

| Fix | Description |
|-----|-------------|
| `FREE_PROVIDERS` NameError | Module-level default + dual import fallback |
| Ollama always Demo mode | `PROVIDERS_AVAILABLE` guard was blocking provider assignment |
| Cannot change model | Lambda captured `mv.get()` at definition time, not click time |
| Threading race condition | Provider/model state now passed as args to `_proc()` thread |
| `pop.destroy()` crash | Window destroyed after state is set, not before |
| Bare `except:` clauses | All replaced with `except Exception` + proper logging |

---

### 📁 Project Structure

```
TuringClaw/
├── gui/
│   ├── chat.py              # GUI main application
│   ├── providers.py         # AI provider registry + token tracker
│   ├── privacy_router.py    # Three-tier privacy routing engine  ← NEW
│   ├── chinatelecom.jpeg    # China Telecom logo source
│   └── __init__.py
├── test_privacy_router.py   # Privacy router test suite          ← NEW
├── GUI_FEATURES.md          # Feature documentation
├── TuringClaw.bat           # Windows launcher
├── CHANGELOG.md             # This file
└── pyproject.toml
```

---

### 🧪 Test Results — v1.0.0

#### Privacy Router Unit Tests

Run: `python test_privacy_router.py`

| Test ID | Name | Input (excerpt) | Expected | Result |
|---------|------|-----------------|----------|--------|
| S1-001 | 普通问题 | 什么是人工智能？ | S1 | ✅ PASS |
| S1-002 | 代码问题 | 如何用Python写快速排序 | S1 | ✅ PASS |
| S1-003 | 创意写作 | 写一篇关于春天的诗歌 | S1 | ✅ PASS |
| S2-001 | 手机号 | 手机号是 13812345678 | S2 | ✅ PASS |
| S2-002 | 身份证号 | 身份证号 110101199001011234 | S2 | ✅ PASS |
| S2-003 | 银行卡号 | 银行卡 6222021234567890123 | S2 | ✅ PASS |
| S2-004 | 电子邮箱 | zhangsan@example.com | S2 | ✅ PASS |
| S2-005 | 内网IP | 192.168.1.100 无法访问 | S2 | ✅ PASS |
| S2-006 | 姓名键值对 | 姓名：张三 | S2 | ✅ PASS |
| S2-007 | 多个敏感信息 | 手机+身份证组合 | S2 | ✅ PASS |
| S3-001 | 密码键值对 | 密码是 MyP@ssw0rd123 | S3 | ✅ PASS |
| S3-002 | API Key | api_key=sk-1234567890 | S3 | ✅ PASS |
| S3-003 | 私钥 | -----BEGIN RSA PRIVATE KEY----- | S3 | ✅ PASS |
| S3-004 | 信用卡号 | 4532123456789012 | S3 | ✅ PASS |
| S3-005 | 医疗敏感词 | 病历显示HIV阳性 | S3 | ✅ PASS |
| S3-006 | 密码中文 | 密码：Admin@123 | S3 | ✅ PASS |

**Total: 16/16 PASS ✅**

#### GUI Manual Test Cases

| Test ID | Operation | Expected | Status |
|---------|-----------|----------|--------|
| GUI-T1 | Launch app | Toolbar shows 🟢 S1 | ✅ |
| GUI-T2 | Send normal message | 🟢 S1, message sent normally | ✅ |
| GUI-T3 | Send message with phone number | 🟡 S2, desensitized before sending | ✅ |
| GUI-T4 | Send message with password | 🔴 S3, auto-switch to Ollama | ✅ |
| GUI-T5 | Settings → Force S3 | All messages use local Ollama | ✅ |
| GUI-T6 | Settings → Auto detect | Level determined by content | ✅ |

---

### 📋 Known Limitations

- Cloud providers (OpenRouter, SiliconFlow, DeepSeek, etc.) show "Coming soon" — API integration planned for v1.1
- S2 desensitization mapping is not restored in model response (planned for v1.1)
- Privacy router uses rule-based detection only; LLM-based semantic detection planned for v1.2

---

[v1.0.0]: https://github.com/weareformgroup/TuringClaw/releases/tag/v1.0.0
