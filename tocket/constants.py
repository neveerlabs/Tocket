# File: tocket/constants.py
import os
from pathlib import Path

APPNAME = "Tocket"
VERSION = "Tocket-Core - v4.2.0.1 (c) Dec 2025    https://github.com/neveerlabs/"

DB_DIR = Path.home() / f".{APPNAME.lower()}"
DB_FILE = DB_DIR / "tocket.db"
