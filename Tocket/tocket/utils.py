import os
import base64
import json
from pathlib import Path
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from rich.style import Style

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

console = Console()

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

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
    txt = Text(ascii_text + "\n\n", style=Style(color="green"))
    txt.append(about_text + "\n", style=Style(color="white"))
    panel = Panel(txt, title=f"[cyan]{username}[/cyan]  [green]tocket[/green]")
    console.print(panel)

def display_error(message: str):
    console.print(f"[bold red]⚠️ ERROR: {message}[/bold red]")

def display_success(message: str):
    console.print(f"[bold green]✅ {message}[/bold green]")

def display_warning(message: str):
    console.print(f"[bold yellow]⚠️ {message}[/bold yellow]")

def encrypt_data(data: bytes, password: str) -> bytes:
    salt = secrets.token_bytes(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000)
    key = kdf.derive(password.encode())
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return salt + nonce + ciphertext

def decrypt_data(encrypted: bytes, password: str) -> bytes:
    salt = encrypted[:16]
    nonce = encrypted[16:28]
    ciphertext = encrypted[28:]
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000)
    key = kdf.derive(password.encode())
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)