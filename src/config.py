import os
from rich.theme import Theme

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or ''
GEMINI_MODEL = os.getenv('GEMINI_MODEL') or ''
PROMPT_PREFIX_FILE = os.path.join(os.path.dirname(__file__), '../docs/background.md')
DEFAULT_IGNORE_PATTERNS = ['.git*']
CONSOLE_THEME = Theme({
    "markdown.code": "#a7c080",
    "markdown.code_block": "#dcdcdc",
    "markdown.h1": "bold #dcdcdc",
    "markdown.h2": "bold #dcdcdc",
    "markdown.h3": "bold #dcdcdc",
    "markdown.h4": "bold #dcdcdc",
    "markdown.h5": "bold #dcdcdc",
    "markdown.h6": "bold #dcdcdc",
    "markdown.strong": "bold #dcdcdc",
    "markdown.em": "#a7c080",
    "markdown.alert": "bold #e67e80",
    "markdown.paragraph": "#dcdcdc",
    "markdown.item.bullet": "bold #dbbc7f",
    "markdown.item.number": "bold #dbbc7f",
    "markdown.item.text": "#dcdcdc",
    "diff.add": "#a7c080",
    "diff.remove": "#e67e80",
    "diff.header": "#dbbc7f"
})


