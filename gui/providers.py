# -*- coding: utf-8 -*-
"""
Free LLM Providers Configuration
Collects information about free tier/credits for various LLM providers
"""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path


@dataclass
class ProviderInfo:
    """Information about a free LLM provider"""
    name: str
    display_name: str
    api_key_env: str  # Environment variable name for API key
    api_key: str = ""  # Direct API key (baked in, e.g. from QClaw bridge). Overrides env lookup.
    api_base_env: str = ""  # Environment variable for custom base URL
    api_base_url: str = ""  # Direct API base URL (e.g. https://api.minimaxi.com/v1)
    default_model: str = ""  # Default model name
    models: list = field(default_factory=list)  # Available models
    free_tier: str = ""  # Description of free tier
    signup_url: str = ""  # Signup URL
    is_local: bool = False  # Runs locally (like Ollama)
    status: str = "not_configured"  # not_configured, configured, error


# Known free providers
FREE_PROVIDERS = {
    "ollama": ProviderInfo(
        name="ollama",
        display_name="Ollama (本地运行)",
        api_key_env="OLLAMA_API_KEY",
        api_base_env="OLLAMA_API_BASE",
        models=["llama3.2", "llama3.1", "qwen2.5", "mistral", "phi3", "gemma2"],
        free_tier="完全免费，本地运行",
        signup_url="https://ollama.com/",
        is_local=True,
    ),
    "openrouter": ProviderInfo(
        name="openrouter",
        display_name="OpenRouter",
        api_key_env="OPENROUTER_API_KEY",
        models=[
            "openrouter/auto",  # Best model for free tier
            "anthropic/claude-3-haiku",
            "google/gemini-flash-1.5",
            "meta-llama/llama-3.1-8b-instruct",
            "mistralai/mistral-7b-instruct",
        ],
        free_tier="每天免费 $1 额度 (注册送)",
        signup_url="https://openrouter.ai/",
    ),
    "siliconflow": ProviderInfo(
        name="siliconflow",
        display_name="SiliconFlow (硅基流动)",
        api_key_env="OPENAI_API_KEY",  # Uses OpenAI-compatible API
        api_base_env="SILICONFLOW_API_BASE",
        models=[
            "Qwen/Qwen2.5-7B-Instruct",
            "THUDM/glm-4-9b-chat",
            "meta-llama/Llama-3.1-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2",
            "deepseek-ai/DeepSeek-V2-Chat",
        ],
        free_tier="新用户送 200 万 tokens",
        signup_url="https://cloud.siliconflow.cn/",
    ),
    "aihubmix": ProviderInfo(
        name="aihubmix",
        display_name="AiHubMix",
        api_key_env="OPENAI_API_KEY",
        models=[
            "claude-3-haiku-20240307",
            "gpt-3.5-turbo",
            "gpt-4o-mini",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-instruct-v0.1",
        ],
        free_tier="免费额度",
        signup_url="https://aihubmix.com/",
    ),
    "deepseek": ProviderInfo(
        name="deepseek",
        display_name="DeepSeek",
        api_key_env="DEEPSEEK_API_KEY",
        models=[
            "deepseek-chat",
            "deepseek-coder",
        ],
        free_tier="新用户送 200 万 tokens",
        signup_url="https://platform.deepseek.com/",
    ),
    "gemini": ProviderInfo(
        name="gemini",
        display_name="Google Gemini",
        api_key_env="GEMINI_API_KEY",
        models=[
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
        ],
        free_tier="免费额度 (需要 Google 账号)",
        signup_url="https://aistudio.google.com/app/apikey",
    ),
    "groq": ProviderInfo(
        name="groq",
        display_name="Groq",
        api_key_env="GROQ_API_KEY",
        models=[
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "whisper-large-v3",
        ],
        free_tier="免费额度",
        signup_url="https://console.groq.com/",
    ),
    "zhipu": ProviderInfo(
        name="zhipu",
        display_name="智谱 AI (Zhipu)",
        api_key_env="ZAI_API_KEY",
        models=[
            "glm-4-flash",
            "glm-4-air",
            "glm-4-plus",
        ],
        free_tier="新用户送 500 万 tokens",
        signup_url="https://open.bigmodel.cn/",
    ),
    "dashscope": ProviderInfo(
        name="dashscope",
        display_name="阿里云 DashScope (通义千问)",
        api_key_env="DASHSCOPE_API_KEY",
        models=[
            "qwen-turbo",
            "qwen-plus",
            "qwen-max",
            "qwen-coder-turbo",
        ],
        free_tier="新用户送 100 万 tokens",
        signup_url="https://dashscope.console.aliyun.com/",
    ),
}


def get_provider_status(provider: ProviderInfo) -> str:
    """Check if a provider is configured"""
    api_key = os.environ.get(provider.api_key_env, "")
    
    if provider.is_local:
        # For local providers like Ollama, check if service is running
        if provider.api_base_env:
            api_base = os.environ.get(provider.api_base_env, "")
            if api_base:
                return "configured"
        # Try default localhost
        return "configured"  # Assume configured if env exists
    
    if api_key and len(api_key) > 0:
        return "configured"
    return "not_configured"


def get_all_providers_status() -> Dict[str, ProviderInfo]:
    """Get status of all providers"""
    for name, provider in FREE_PROVIDERS.items():
        provider.status = get_provider_status(provider)
    return FREE_PROVIDERS


def get_configured_providers() -> list:
    """Get list of configured providers"""
    configured = []
    for name, provider in get_all_providers_status().items():
        if provider.status == "configured":
            configured.append(provider)
    return configured


def get_provider_by_name(name: str) -> Optional[ProviderInfo]:
    """Get provider info by name"""
    return FREE_PROVIDERS.get(name)


# Token usage tracking
class TokenTracker:
    """Track token usage for each provider"""
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            # Use Path.home() for reliable path expansion
            storage_path = str(Path.home() / ".TuringClaw" / "token_usage.json")
        self.storage_path = storage_path
        self.usage = self._load_usage()
        print(f"[DEBUG] TokenTracker initialized, path: {self.storage_path}")
        print(f"[DEBUG] Loaded usage: {self.usage}")
        
    def _load_usage(self) -> dict:
        """Load usage data from file"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[WARN] TokenTracker: could not load usage from {self.storage_path}: {e}")
        return {}
    
    def _save_usage(self):
        """Save usage data to file"""
        try:
            dir_path = os.path.dirname(self.storage_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self.usage, f, indent=2)
        except Exception as e:
            print(f"[WARN] TokenTracker: could not save usage to {self.storage_path}: {e}")
    
    def record_usage(self, provider: str, input_tokens: int = 0, output_tokens: int = 0):
        """Record token usage for a provider"""
        if provider not in self.usage:
            self.usage[provider] = {
                "total_input": 0,
                "total_output": 0,
                "total_requests": 0,
            }
        
        self.usage[provider]["total_input"] += input_tokens
        self.usage[provider]["total_output"] += output_tokens
        self.usage[provider]["total_requests"] += 1
        self._save_usage()
    
    def get_usage(self, provider: str = None) -> dict:
        """Get usage for a specific provider or all"""
        if provider:
            return self.usage.get(provider, {
                "total_input": 0,
                "total_output": 0,
                "total_requests": 0,
            })
        return self.usage
    
    def get_total_tokens(self, provider: str = None) -> int:
        """Get total tokens (input + output) for a provider"""
        data = self.get_usage(provider)
        return data.get("total_input", 0) + data.get("total_output", 0)
    
    def reset_usage(self, provider: str = None):
        """Reset usage for a provider or all"""
        if provider:
            if provider in self.usage:
                del self.usage[provider]
        else:
            self.usage = {}
        self._save_usage()


# Global token tracker instance
token_tracker = TokenTracker()
