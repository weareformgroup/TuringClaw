#!/usr/bin/env python3
# TuringClaw - Markdown Renderer (M3-2)
# 零依赖极简 Markdown → tkinter Text widget 渲染

import re
from tkinter import END


# Catppuccin Mocha 配色
COLORS = {
    "h1": "#f9e2af",
    "h2": "#89b4fa",
    "h3": "#cba6f7",
    "bold": "#cdd6f4",
    "italic": "#a6adc8",
    "code": "#a6e3a1",
    "code_bg": "#313244",
    "code_block_bg": "#181825",
    "quote": "#94e2d5",
    "link": "#89b4fa",
    "py_keyword": "#cba6f7",
    "py_string": "#a6e3a1",
    "py_comment": "#6c7086",
    "py_builtin": "#89b4fa",
}


class MarkdownRenderer:
    """零依赖 Markdown 渲染器"""

    def __init__(self, text_widget):
        self.text = text_widget
        self._tags_ready = False

    def _setup_tags(self):
        if self._tags_ready:
            return
        t = self.text
        t.tag_configure("md_h1", font=("Consolas", 18, "bold"), foreground=COLORS["h1"], spacing3=8)
        t.tag_configure("md_h2", font=("Consolas", 15, "bold"), foreground=COLORS["h2"], spacing3=6)
        t.tag_configure("md_h3", font=("Consolas", 13, "bold"), foreground=COLORS["h3"], spacing3=4)
        t.tag_configure("md_bold", font=("Consolas", 11, "bold"), foreground=COLORS["bold"])
        t.tag_configure("md_italic", font=("Consolas", 11, "italic"), foreground=COLORS["italic"])
        t.tag_configure("md_code", font=("Consolas", 11), foreground=COLORS["code"], background=COLORS["code_bg"])
        t.tag_configure("md_code_block", font=("Consolas", 10), background=COLORS["code_block_bg"], lmargin1=20, lmargin2=20, spacing1=4, spacing3=4)
        t.tag_configure("md_quote", font=("Consolas", 11, "italic"), foreground=COLORS["quote"], lmargin1=20, lmargin2=20)
        t.tag_configure("md_list", lmargin1=24, lmargin2=24)
        t.tag_configure("md_link", foreground=COLORS["link"], underline=True)
        # Python 高亮 tags
        t.tag_configure("md_py_kw", foreground=COLORS["py_keyword"], font=("Consolas", 10, "bold"))
        t.tag_configure("md_py_str", foreground=COLORS["py_string"], font=("Consolas", 10))
        t.tag_configure("md_py_cmt", foreground=COLORS["py_comment"], font=("Consolas", 10, "italic"))
        t.tag_configure("md_py_bi", foreground=COLORS["py_builtin"], font=("Consolas", 10))
        self._tags_ready = True

    def render(self, markdown_text: str):
        """渲染 Markdown 到 widget"""
        self._setup_tags()
        if not markdown_text:
            return
        lines = markdown_text.split("\n")
        i = 0
        in_code_block = False
        code_lang = ""
        code_buffer = []

        while i < len(lines):
            line = lines[i]

            # 代码块开始/结束
            stripped = line.strip()
            if stripped.startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_lang = stripped[3:].strip() or "text"
                    code_buffer = []
                else:
                    self._render_code_block("\n".join(code_buffer), code_lang)
                    in_code_block = False
                    code_lang = ""
                    code_buffer = []
                i += 1
                continue

            if in_code_block:
                code_buffer.append(line)
                i += 1
                continue

            # 标题
            if line.startswith("### "):
                self._insert_segment(line[4:] + "\n", ["md_h3"])
                i += 1
                continue
            if line.startswith("## "):
                self._insert_segment(line[3:] + "\n", ["md_h2"])
                i += 1
                continue
            if line.startswith("# "):
                self._insert_segment(line[2:] + "\n", ["md_h1"])
                i += 1
                continue

            # 引用
            if line.startswith("> "):
                self._insert_segment("│ " + line[2:] + "\n", ["md_quote"])
                i += 1
                continue

            # 无序列表
            m = re.match(r"^(\s*)([-*])\s+(.+)$", line)
            if m:
                indent, marker, content = m.group(1), m.group(2), m.group(3)
                self._insert_segment(f"{indent}{marker} ", ["md_list"])
                self._render_inline(content + "\n", base_tag="md_list")
                i += 1
                continue

            # 有序列表
            m = re.match(r"^(\s*)(\d+)\.\s+(.+)$", line)
            if m:
                indent, num, content = m.group(1), m.group(2), m.group(3)
                self._insert_segment(f"{indent}{num}. ", ["md_list"])
                self._render_inline(content + "\n", base_tag="md_list")
                i += 1
                continue

            # 空行
            if not line.strip():
                self.text.insert(END, "\n")
                i += 1
                continue

            # 普通段落
            self._render_inline(line + "\n")
            i += 1

    def _render_code_block(self, code: str, lang: str):
        """渲染代码块"""
        if lang.lower() in ("python", "py"):
            self.text.insert(END, "\n")
            start_idx = self.text.index(END + "-1c") if self.text.index(END) != "1.0" else "1.0"
            self.text.insert(END, code, ["md_code_block"])
            end_idx = self.text.index(END)
            # Python 简单高亮
            self._highlight_python_in_range(start_idx, end_idx, code)
            self.text.insert(END, "\n")
        else:
            self.text.insert(END, "\n" + code + "\n", ["md_code_block"])

    def _highlight_python_in_range(self, start_idx, end_idx, code):
        """对 Python 代码做简易高亮"""
        py_keywords = {"def", "return", "if", "else", "elif", "for", "while", "import", "from",
                       "class", "try", "except", "finally", "with", "as", "in", "not", "and", "or",
                       "True", "False", "None", "lambda", "yield", "pass", "break", "continue", "global", "nonlocal"}
        py_builtins = {"print", "len", "range", "int", "str", "list", "dict", "set", "tuple", "open",
                       "isinstance", "type", "input", "enumerate", "zip", "map", "filter", "sorted", "sum", "abs", "min", "max"}

        for lineno, line in enumerate(code.split("\n")):
            # 注释
            m = re.search(r"#.*$", line)
            if m:
                col = m.start()
                self._tag_range(start_idx, end_idx, lineno, col, len(m.group(0)), "md_py_cmt")

            # 字符串
            for m in re.finditer(r'"[^"\n]*"|\'[^\n\']*\'', line):
                self._tag_range(start_idx, end_idx, lineno, m.start(), m.end() - m.start(), "md_py_str")

            # 关键字
            for m in re.finditer(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", line):
                word = m.group(0)
                if word in py_keywords:
                    self._tag_range(start_idx, end_idx, lineno, m.start(), len(word), "md_py_kw")
                elif word in py_builtins:
                    self._tag_range(start_idx, end_idx, lineno, m.start(), len(word), "md_py_bi")

    def _tag_range(self, start_idx, end_idx, lineno, col, length, tag):
        """对范围内特定行列位置加 tag"""
        try:
            from tkinter import TclError
            # 计算绝对位置
            # start_idx 形如 "3.0", lineno/col 偏移
            base_line = int(start_idx.split(".")[0])
            target_line = base_line + lineno
            abs_start = f"{target_line}.{col}"
            abs_end = f"{target_line}.{col + length}"
            self.text.tag_add(tag, abs_start, abs_end)
        except Exception:
            pass

    def _render_inline(self, text: str, base_tag=None):
        """行内: 粗体/斜体/code/link, 同时支持 base_tag (如列表缩进)"""
        # 我们对每段切分: 找出特殊 token, 逐段 insert
        # tokens 优先级: ** (bold), * (italic), ` (code), [](link)
        # 简化: 用正则分块

        pattern = re.compile(
            r"(\*\*[^*]+\*\*)"  # 粗体
            r"|(\*[^*]+\*)"  # 斜体
            r"|(`[^`]+`)"  # 行内代码
            r"|(\[[^\]]+\]\([^)]+\))"  # 链接
        )

        pos = 0
        for m in pattern.finditer(text):
            if m.start() > pos:
                self._insert_segment(text[pos:m.start()], [base_tag] if base_tag else [])
            token = m.group(0)
            if token.startswith("**"):
                self._insert_segment(token[2:-2], (["md_bold"] + ([base_tag] if base_tag else [])))
            elif token.startswith("*"):
                self._insert_segment(token[1:-1], (["md_italic"] + ([base_tag] if base_tag else [])))
            elif token.startswith("`"):
                self._insert_segment(token[1:-1], (["md_code"] + ([base_tag] if base_tag else [])))
            elif token.startswith("["):
                # [text](url) → 只显示 text
                m2 = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
                if m2:
                    self._insert_segment(m2.group(1), (["md_link"] + ([base_tag] if base_tag else [])))
            pos = m.end()
        if pos < len(text):
            self._insert_segment(text[pos:], [base_tag] if base_tag else [])

    def _insert_segment(self, content, tags):
        if not content:
            return
        if not tags:
            self.text.insert(END, content)
            return
        start = self.text.index(END + "-1c") if self.text.index(END) != "1.0" else "1.0"
        # 简化: 直接用 end 前插
        self.text.insert(END, content)
        end = self.text.index(END)
        for tag in tags:
            if tag is None:
                continue
            try:
                self.text.tag_add(tag, start, end)
            except Exception:
                pass
