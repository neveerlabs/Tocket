import sqlite3
import json
import os
import base64
from pathlib import Path
from typing import Optional
from .constants import DB_DIR, DB_FILE
from .utils import ensure_app_dir

# Crypto imports
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets

DEFAULT_KDF_ITERS = 200_000

class ConfigDB:
    def __init__(self, db_path: Path = DB_FILE):
        ensure_app_dir(DB_DIR)
        self.db_path = db_path
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            action TEXT,
            detail TEXT
        );
        """)
        self.conn.commit()

    def set_kv(self, key: str, value: str):
        cur = self.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO config(key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    def get_kv(self, key: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    def delete_kv(self, key: str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM config WHERE key = ?", (key,))
        self.conn.commit()

    # Password handling: store salt + verifier (pbkdf2)
    def set_password(self, password: str, iters: int = DEFAULT_KDF_ITERS):
        salt = secrets.token_bytes(16)
        dk = self._derive(password.encode(), salt, iterations=iters)
        # store salt and verifier base64
        self.set_kv("pwd_salt", base64.b64encode(salt).decode())
        self.set_kv("pwd_hash", base64.b64encode(dk).decode())
        self.set_kv("pwd_iters", str(iters))

    def verify_password(self, password: str) -> bool:
        salt_b64 = self.get_kv("pwd_salt")
        hash_b64 = self.get_kv("pwd_hash")
        iters = int(self.get_kv("pwd_iters") or str(DEFAULT_KDF_ITERS))
        if not salt_b64 or not hash_b64:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = self._derive(password.encode(), salt, iterations=iters)
        return secrets.compare_digest(dk, expected)

    def clear_password(self):
        self.delete_kv("pwd_salt")
        self.delete_kv("pwd_hash")
        self.delete_kv("pwd_iters")

    def _derive(self, password_bytes: bytes, salt: bytes, iterations: int = DEFAULT_KDF_ITERS) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password_bytes)

    # Token encryption/decryption using AESGCM with key derived from password
    def store_token_encrypted(self, token_plain: str, password: str):
        salt = secrets.token_bytes(16)
        iters = int(self.get_kv("pwd_iters") or DEFAULT_KDF_ITERS)
        key = self._derive(password.encode(), salt, iterations=iters)
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        ct = aesgcm.encrypt(nonce, token_plain.encode("utf-8"), None)
        self.set_kv("tok_salt", base64.b64encode(salt).decode())
        self.set_kv("tok_nonce", base64.b64encode(nonce).decode())
        self.set_kv("tok_cipher", base64.b64encode(ct).decode())

    def load_token_decrypted(self, password: str) -> str | None:
        salt_b64 = self.get_kv("tok_salt")
        nonce_b64 = self.get_kv("tok_nonce")
        ct_b64 = self.get_kv("tok_cipher")
        if not (salt_b64 and nonce_b64 and ct_b64):
            return None
        salt = base64.b64decode(salt_b64)
        nonce = base64.b64decode(nonce_b64)
        ct = base64.b64decode(ct_b64)
        iters = int(self.get_kv("pwd_iters") or DEFAULT_KDF_ITERS)
        key = self._derive(password.encode(), salt, iterations=iters)
        try:
            aesgcm = AESGCM(key)
            pt = aesgcm.decrypt(nonce, ct, None)
            return pt.decode("utf-8")
        except Exception:
            return None

    def clear_token(self):
        self.delete_kv("tok_salt")
        self.delete_kv("tok_nonce")
        self.delete_kv("tok_cipher")

    def add_history(self, action: str, detail: str = ""):
        cur = self.conn.cursor()
        cur.execute("INSERT INTO history(action, detail) VALUES (?, ?)", (action, detail))
        self.conn.commit()

    def close(self):
        self.conn.close()
