import os
import sys
import base64
from pathlib import Path

try:
    from rich.console import Console
    from rich.theme import Theme
    console = Console()
except Exception:
    console = None

def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

def ensure_app_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def read_binary_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def to_base64(b: bytes) -> str:
    return base64.b64encode(b).decode("utf-8")

def from_base64(s: str) -> bytes:
    return base64.b64decode(s.encode("utf-8"))

def print_header(ascii_text: str, about_text: str, username: str):
    from rich.panel import Panel
    from rich.text import Text
    from rich.style import Style
    txt = Text(ascii_text + "\n\n", style=Style(color="green"))
    txt.append(about_text + "\n", style=Style(color="white"))
    panel = Panel(txt, title=f"[cyan]{username}[/cyan]  [green]tocket[/green]")
    console.print(panel)
