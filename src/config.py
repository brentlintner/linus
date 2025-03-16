import os

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY') or ''
GEMINI_MODEL = os.getenv('GEMINI_MODEL') or ''
PROMPT_PREFIX_FILE = os.path.join(os.path.dirname(__file__), '../docs/background.md')
DEFAULT_IGNORE_PATTERNS = ['.git*']
