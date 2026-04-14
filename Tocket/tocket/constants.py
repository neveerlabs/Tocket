import os
from pathlib import Path

APPNAME = "Tocket"
VERSION = "Tocket-Core - v4.4.0.2 (c) Maret 2026    Url: https://github.com/neveerlabs/Tocket"

DB_DIR = Path.home() / f".{APPNAME.lower()}"
DB_FILE = DB_DIR / "tocket.db"