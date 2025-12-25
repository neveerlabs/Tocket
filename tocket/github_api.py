# File: tocket/github_api.py
import requests
import base64
from typing import Optional, List, Dict

GITHUB_API = "https://api.github.com"

class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token or None
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Tocket-CLI"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        self.session.headers.update(headers)
        self.username = None
        self.scopes = None
        self._last_headers = {}

    def validate_token(self) -> Optional[Dict]:
        # GET /user to validate; capture scopes from header
        resp = self.session.get(f"{GITHUB_API}/user")
        self._last_headers = resp.headers
        if resp.status_code == 200:
            self.username = resp.json().get("login")
            # header X-OAuth-Scopes contains comma separated scopes
            scopes_hdr = resp.headers.get("X-OAuth-Scopes", "")
            self.scopes = [s.strip() for s in scopes_hdr.split(",")] if scopes_hdr else []
            return {"username": self.username, "scopes": self.scopes}
        else:
            return None

    # ... rest of class unchanged ...
