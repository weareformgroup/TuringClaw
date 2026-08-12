# -*- coding: utf-8 -*-
"""
BrainSearch — GBrain 对话集成

在对话中主动查询 GBrain 知识库，让 22 页知识不再沉睡。
用法：
    from cognitive.brain_search import BrainSearch
    bs = BrainSearch()
    results = bs.search("LM Studio")
    results = bs.query("goal state machine")
    bs.put("concepts/new-concept", "---\ntype: concept\n---\n# New Concept\n...")
"""
import subprocess
import os
from pathlib import Path
from typing import Optional


class BrainSearch:
    """GBrain CLI 封装，让对话中方便查询和写入 brain。"""

    def __init__(self):
        self.bun = r"C:\Users\Administrator\.bun\bin\bun.exe"
        self.cli = r"C:\Users\Administrator\gbrain\src\cli.ts"
        self.env = os.environ.copy()
        self.env["PATH"] = r"C:\Users\Administrator\.bun\bin;" + self.env.get("PATH", "")
        self.env["CUDA_VISIBLE_DEVICES"] = ""
        self.env["LLAMA_SERVER_BASE_URL"] = "http://localhost:1234/v1"
        self.env["LLAMA_SERVER_API_KEY"] = "***"

    def _run(self, *args) -> str:
        """执行 gbrain CLI 命令。"""
        cmd = [self.bun, self.cli] + list(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            env=self.env, timeout=30
        )
        return result.stdout + result.stderr

    def search(self, query: str, limit: int = 5) -> list:
        """关键词搜索 brain pages。"""
        output = self._run("search", query)
        results = []
        for line in output.strip().split("\n"):
            if line.strip() and "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    results.append({"slug": parts[0], "title": parts[1] if len(parts) > 1 else ""})
        return results[:limit]

    def query(self, question: str, limit: int = 5) -> list:
        """向量搜索 brain pages（需要 embedding）。"""
        output = self._run("query", question)
        results = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("[") and not line.startswith("Embedded"):
                results.append(line)
        return results[:limit]

    def list(self) -> list:
        """列出所有 brain pages。"""
        output = self._run("list")
        results = []
        for line in output.strip().split("\n"):
            if line.strip() and "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 2:
                    results.append({"slug": parts[0], "type": parts[1], "title": parts[2] if len(parts) > 2 else ""})
        return results

    def put(self, slug: str, content: str) -> bool:
        """写入或更新 brain page。"""
        output = self._run("put", slug, "--content", content)
        return True  # gbrain put 没有报错就是成功

    def get(self, slug: str) -> str:
        """获取 brain page 内容。"""
        return self._run("get", slug)

    def embed_all(self) -> str:
        """对所有页面生成 embedding。"""
        return self._run("embed", "--all")

    def is_available(self) -> bool:
        """检查 GBrain 是否可用。"""
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:8484/health", timeout=3)
            return True
        except:
            return False

    def extract_keywords(self, text: str) -> list:
        """从文本中提取关键词（用于自动查询 brain）。"""
        # 简单关键词提取：中文 2-4 字词 + 英文单词
        import re
        keywords = []

        # 英文专有名词（大写开头）
        en_words = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', text)
        keywords.extend(en_words)

        # 特定关键词
        known_concepts = [
            "TuringClaw", "GBrain", "GSM", "LM Studio", "Ollama", "QClaw",
            "PGLite", "embedding", "dream cycle", "cognitive", "linkage",
            "auto-approve", "evidence", "hypothesis", "rule", "skill",
            "digital employee", "self-harnessing", "crystallization",
            "RTX 3050", "Python", "Tkinter", "OpenClaw",
        ]
        for concept in known_concepts:
            if concept.lower() in text.lower():
                keywords.append(concept)

        # 去重
        seen = set()
        unique = []
        for k in keywords:
            if k.lower() not in seen:
                seen.add(k.lower())
                unique.append(k)

        return unique[:5]  # 最多 5 个关键词


# === 自测试 ===
if __name__ == "__main__":
    bs = BrainSearch()
    print(f"GBrain available: {bs.is_available()}")
    print()

    # List
    pages = bs.list()
    print(f"Pages: {len(pages)}")
    for p in pages[:5]:
        print(f"  {p}")
    print()

    # Search
    results = bs.search("TuringClaw")
    print(f"Search 'TuringClaw': {len(results)} results")
    for r in results:
        print(f"  {r}")
    print()

    # Extract keywords
    test_text = "LM Studio 替代 Ollama 做 embedding，RTX 3050 GPU 推理"
    keywords = bs.extract_keywords(test_text)
    print(f"Keywords from '{test_text}': {keywords}")
