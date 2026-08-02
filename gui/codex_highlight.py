"""M2-4: 简易 Python 代码高亮 (不依赖 pygments)

检测 Markdown ```python 代码块并对 Python 代码做关键字/字符串/注释着色。
"""
import re


# Python 关键字 (M2-4 用)
PY_KEYWORDS = (
    "def|return|if|elif|else|for|while|in|not|and|or|"
    "import|from|as|class|try|except|finally|with|"
    "lambda|yield|pass|break|continue|raise|None|True|False"
)

# Catppuccin Mocha 配色 (与 GUI 主题一致)
COLOR_KEYWORD = "#89b4fa"   # 蓝
COLOR_STRING = "#a6e3a1"    # 绿
COLOR_COMMENT = "#6c7086"   # 灰
COLOR_BUILTIN = "#fab387"   # 橙 (print/range 等)

BUILTINS = (
    "print|range|len|int|str|list|dict|tuple|set|"
    "open|input|type|isinstance|enumerate|zip|map|"
    "abs|max|min|sum|sorted|reversed|bool|float"
)


def _ensure_tags(text_widget, tag_prefix: str) -> None:
    """配置 tag 颜色 (一次性, 重复调用也安全)"""
    text_widget.tag_configure(
        f"{tag_prefix}_kw",
        foreground=COLOR_KEYWORD,
    )
    text_widget.tag_configure(
        f"{tag_prefix}_str",
        foreground=COLOR_STRING,
    )
    text_widget.tag_configure(
        f"{tag_prefix}_com",
        foreground=COLOR_COMMENT,
    )
    text_widget.tag_configure(
        f"{tag_prefix}_bi",
        foreground=COLOR_BUILTIN,
    )


def highlight_python(text_widget, code: str, tag_prefix: str = "code") -> None:
    """简易 Python 语法高亮 (按顺序: 字符串 -> 注释 -> 关键字 -> 内建)
    
    Args:
        text_widget: tkinter.Text widget
        code: 要插入并着色的代码字符串
        tag_prefix: tag 名称前缀, 避免多段代码冲突
    """
    _ensure_tags(text_widget, tag_prefix)

    # 计算插入起点
    insert_start = text_widget.index("end-1c")

    # 1. 字符串 (先匹配, 避免和注释冲突)
    for m in re.finditer(
        r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\n]*"|\'[^\'\n]*\'',
        code,
    ):
        text_widget.insert("end", m.group(0))
        text_widget.tag_add(
            f"{tag_prefix}_str",
            f"{insert_start}+{m.start()}c",
            f"{insert_start}+{m.end()}c",
        )

    # 2. 注释
    for m in re.finditer(r'#[^\n]*', code):
        text_widget.tag_add(
            f"{tag_prefix}_com",
            f"{insert_start}+{m.start()}c",
            f"{insert_start}+{m.end()}c",
        )

    # 3. 关键字
    for m in re.finditer(r'\b(' + PY_KEYWORDS + r')\b', code):
        text_widget.tag_add(
            f"{tag_prefix}_kw",
            f"{insert_start}+{m.start()}c",
            f"{insert_start}+{m.end()}c",
        )

    # 4. 内建函数
    for m in re.finditer(r'\b(' + BUILTINS + r')\b', code):
        text_widget.tag_add(
            f"{tag_prefix}_bi",
            f"{insert_start}+{m.start()}c",
            f"{insert_start}+{m.end()}c",
        )


def is_code_block_start(line: str) -> bool:
    """检查是否是 Markdown 代码块开始 (```xxx)"""
    return line.strip().startswith("```")


def is_code_block_end(line: str) -> bool:
    """检查是否是 Markdown 代码块结束 (单独的```)"""
    return line.strip() == "```"


def get_code_language(line: str) -> str:
    """获取 ``` 后面的语言标识 (如 ```python)"""
    line = line.strip()
    if line.startswith("```") and len(line) > 3:
        return line[3:].strip().lower()
    return ""


def is_python_code(code: str) -> bool:
    """简易判断代码是否像 Python (含 Python 关键字)"""
    py_indicators = ["def ", "import ", "class ", "from ", "if __name__"]
    return any(kw in code for kw in py_indicators)
