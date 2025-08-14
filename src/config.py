import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-2.5-pro"
GEMINI_TEMPERATURE = 0.4
USER_NAME = "Brent"
PARTNER_NAME = "Linus"

SYSTEM_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "templates", "system.md")
CONTEXT_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "templates", "context.md")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Default ignore patterns, combining best practices from various sources
DEFAULT_IGNORE_PATTERNS = [
    # This project
    ".linignore",
    ".lin.db",
    ".lin.md",

    # VCS directories
    ".git/",
    ".svn/",
    ".hg/",
    ".bzr/",

    # Bytecode and compiled files
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.egg-info/",
    "*.egg",
    "*.o", # Object files
    "*.a", # Static libraries
    "*.lib", # Windows static libraries

    # Build and package directories
    "build/",
    "dist/",
    "sdist/",
    "var/",
    "wheels/",

    # Python virtual environments
    "venv/",
    ".venv/",
    "env/",
    ".env/",
    "ENV/",

    # IDE and editor files
    ".idea/",
    ".vscode/",
    "*.code-workspace",
    ".project",
    ".settings/", # Eclipse
    "*.tmproj", # TextMate
    "*.sublime-project",
    "*.sublime-workspace",

    # Operating system files
    ".DS_Store",  # macOS
    "Thumbs.db",  # Windows
    "Desktop.ini",

    # Temporary files
    "*~",
    ".tmp/",
    "*.swp",
    "*.swo",
    "*.bak",
    "*.orig",

    # Node.js
    "node_modules/",

    # Java
    "*.class",
    "target/", # Maven

    # C/C++
    "*.exe",
    "*.dll",
    "*.obj",

    # Archives and compressed files
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.rar",
    "*.7z",

    # Image files
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.bmp",
    "*.tiff",
    "*.ico",
    "*.svg",

    # Video files
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.mkv",
    "*.wmv",
    "*.flv",
    "*.webm",

    # Audio files
    "*.mp3",
    "*.wav",
    "*.aac",
    "*.ogg",
    "*.flac",
    "*.m4a",

    # Documents
    "*.pdf",
    "*.doc",
    "*.docx",
    "*.xls",
    "*.xlsx",
    "*.ppt",
    "*.pptx",
    "*.odt",
    "*.ods",
    "*.odp",

    # Database files
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.db-journal",

    # Logs and dumps
    "*.log",
    "*.dump",
    "*.sql",

    # Cache and temporary files
    ".cache/",
    "*.cache",
    "tmp/",  # Generic tmp directory.

    # Jupyter Notebook
    ".ipynb_checkpoints/",

    # Yarn
    ".yarn/",

    # Rust
    "target/",

    # Go
    "vendor/",

    # Elixir
    "_build/",
    "deps/",

    # Editor specific
    ".history", # VS Code local history
    ".local/", # Sometimes used for local config

]
