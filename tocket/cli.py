# File: tocket/cli.py
import sys
import getpass
import traceback
from pathlib import Path
from typing import Optional, List, Dict
from .constants import VERSION, APPNAME
from .db import ConfigDB
from .utils import clear_screen, print_header, read_binary_file
from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich import box
import requests

console = Console()

ASCII_ART = r"""
TTTTTTTTT  OOOOO   CCCCC K   K EEEEE TTTTTTT
   T      O   O  C     K  K  E       T
   T      O   O  C     KKK   EEEE    T
   T      O   O  C     K  K  E       T
   T      OOOOO   CCCCC K   K EEEEE  T
"""

GITHUB_API = "https://api.github.com"


class GitHubClient:
    """
    Lightweight GitHub client using requests.
    If token is None/empty, Authorization header will not be sent (unauthenticated).
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or None
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Tocket-CLI"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        self.session.headers.update(headers)
        self.username: Optional[str] = None
        self.scopes: List[str] = []
        self._last_headers = {}

    def validate_token(self) -> Optional[Dict]:
        """
        Validate token by calling GET /user.
        Returns {"username": ..., "scopes": [...]} on success, else None.
        """
        try:
            resp = self.session.get(f"{GITHUB_API}/user")
        except Exception as e:
            raise RuntimeError(f"Network error validating token: {e}")
        self._last_headers = resp.headers
        if resp.status_code == 200:
            self.username = resp.json().get("login")
            scopes_hdr = resp.headers.get("X-OAuth-Scopes", "")
            self.scopes = [s.strip() for s in scopes_hdr.split(",")] if scopes_hdr else []
            return {"username": self.username, "scopes": self.scopes}
        else:
            return None

    def list_repos(self) -> List[Dict]:
        """
        List authenticated user's repositories (requires token).
        Raises RuntimeError with helpful message on 401/403 or other issues.
        """
        if not self.token:
            raise RuntimeError("No authentication token provided for listing user repositories.")
        repos = []
        page = 1
        while True:
            resp = self.session.get(f"{GITHUB_API}/user/repos", params={"per_page": 100, "page": page})
            if resp.status_code == 401:
                raise RuntimeError("Unauthorized (401). Token invalid or expired.")
            if resp.status_code == 403:
                # Could be rate limit or insufficient scopes
                raise RuntimeError(f"Forbidden (403). Possibly rate-limited or insufficient scopes. Headers: {resp.headers}")
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to list repos: {resp.status_code} {resp.text}")
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return repos

    def list_user_public_repos(self, username: str) -> List[Dict]:
        """
        List public repos of a given username (unauthenticated path).
        """
        repos = []
        page = 1
        while True:
            resp = self.session.get(f"{GITHUB_API}/users/{username}/repos", params={"per_page": 100, "page": page})
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to list public repos for {username}: {resp.status_code} {resp.text}")
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return repos

    def create_repo(self, name: str, description: str = "", private: bool = False,
                    auto_init: bool = False, gitignore_template: Optional[str] = None,
                    license_template: Optional[str] = None) -> Dict:
        payload = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init
        }
        if gitignore_template:
            payload["gitignore_template"] = gitignore_template
        if license_template:
            payload["license_template"] = license_template
        resp = self.session.post(f"{GITHUB_API}/user/repos", json=payload)
        if resp.status_code in (201,):
            return resp.json()
        else:
            raise RuntimeError(f"Create repo failed: {resp.status_code} {resp.text}")

    def delete_repo(self, owner: str, repo: str) -> bool:
        resp = self.session.delete(f"{GITHUB_API}/repos/{owner}/{repo}")
        if resp.status_code == 204:
            return True
        else:
            raise RuntimeError(f"Delete repo failed: {resp.status_code} {resp.text}")

    def get_contents(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[Dict]:
        resp = self.session.get(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}", params={"ref": ref})
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return None
        else:
            raise RuntimeError(f"Get contents failed: {resp.status_code} {resp.text}")

    def create_or_update_file(self, owner: str, repo: str, path: str, content_bytes: bytes, message: str, branch: str = "main") -> Dict:
        import base64
        b64 = base64.b64encode(content_bytes).decode("utf-8")
        existing = self.get_contents(owner, repo, path, ref=branch)
        payload = {
            "message": message,
            "content": b64,
            "branch": branch
        }
        if existing and isinstance(existing, dict) and existing.get("sha"):
            payload["sha"] = existing["sha"]
        resp = self.session.put(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}", json=payload)
        if resp.status_code in (200, 201):
            return resp.json()
        else:
            raise RuntimeError(f"Create/update file failed: {resp.status_code} {resp.text}")

    def delete_file(self, owner: str, repo: str, path: str, message: str, branch: str = "main") -> Dict:
        existing = self.get_contents(owner, repo, path, ref=branch)
        if not existing or not isinstance(existing, dict) or not existing.get("sha"):
            raise FileNotFoundError(f"File {path} not found in {owner}/{repo}")
        payload = {
            "message": message,
            "sha": existing["sha"],
            "branch": branch
        }
        resp = self.session.delete(f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}", json=payload)
        if resp.status_code in (200, 204):
            return {"ok": True}
        else:
            raise RuntimeError(f"Delete file failed: {resp.status_code} {resp.text}")

    def list_repo_tree(self, owner: str, repo: str, branch: str = "main") -> List[Dict]:
        r = self.session.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch}")
        if r.status_code != 200:
            raise RuntimeError(f"Could not get branch refs: {r.status_code} {r.text}")
        sha = r.json()["object"]["sha"]
        r2 = self.session.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{sha}", params={"recursive": "1"})
        if r2.status_code != 200:
            raise RuntimeError(f"Could not get tree: {r2.status_code} {r2.text}")
        return r2.json().get("tree", [])

    def get_gitignore_templates(self) -> List[str]:
        r = self.session.get(f"{GITHUB_API}/gitignore/templates")
        if r.status_code != 200:
            raise RuntimeError("Failed to fetch gitignore templates")
        return r.json()

    def get_license_templates(self) -> List[Dict]:
        r = self.session.get(f"{GITHUB_API}/licenses")
        if r.status_code != 200:
            raise RuntimeError("Failed to fetch license templates")
        return r.json()


def prompt_password_hidden(prompt_text="Password: "):
    try:
        return getpass.getpass(prompt_text)
    except (KeyboardInterrupt):
        return None


def ensure_db():
    return ConfigDB()


def login_flow(db: ConfigDB):
    """
    Handle password prompt (if configured) and token input.
    Returns tuple (password_or_None, token_or_None, label_or_None)
    """
    pwd_salt = db.get_kv("pwd_salt")
    password: Optional[str] = None
    if pwd_salt:
        attempts = 0
        while attempts < 3:
            pwd = prompt_password_hidden("Password: ")
            if pwd is None:
                console.print("[yellow]Batal input password.[/yellow]")
                return None, None, None
            if db.verify_password(pwd):
                password = pwd
                break
            else:
                console.print("[red]Password salah.[/red]")
                attempts += 1
        if attempts >= 3 and password is None:
            console.print("[red]Mencapai batas percobaan. Keluar.[/red]")
            sys.exit(1)
    else:
        console.print("[green]Tidak ada password lokal — lanjutkan tanpa password atau buat password lewat Pengaturan nanti.[/green]")

    token: Optional[str] = None
    label: Optional[str] = None

    if db.get_kv("tok_cipher"):
        # There is an encrypted token saved; try to load if password known or prompt for it.
        if password is None:
            console.print("[yellow]Token terenkripsi ditemukan, tetapi tidak ada password yang disediakan. Silakan masukkan password terlebih dahulu.[/yellow]")
            pwd = prompt_password_hidden("Password: ")
            if pwd is None:
                return None, None, None
            if not db.verify_password(pwd):
                console.print("[red]Password salah.[/red]")
                return None, None, None
            password = pwd
        token = db.load_token_decrypted(password)
        if token is None:
            console.print("[red]Gagal dekripsi token — kemungkinan password berbeda. Kamu bisa reset token di Pengaturan.[/red]")
        else:
            label = db.get_kv("tok_label")
            console.print(f"[green]Token tersimpan ditemukan untuk user label: [cyan]{label or '(no label)'}[/cyan][/green]")
    else:
        # No token stored: ask user for token (optional)
        while True:
            try:
                t = Prompt.ask("Masukkan token classic GitHub (atau enter untuk lanjut tanpa token)", default="")
            except KeyboardInterrupt:
                console.print("\n[yellow]Batal memasukkan token.[/yellow]")
                t = ""
            if not t:
                token = None
                break
            try:
                gh = GitHubClient(t.strip())
                info = gh.validate_token()
            except Exception as e:
                console.print(f"[red]Gagal memvalidasi token: {e}[/red]")
                continue
            if info:
                console.print(f"[green]Token valid. Username: [cyan]{info['username']}[/cyan]. Scopes: [magenta]{info['scopes']}[/magenta][/green]")
                # Ask to set label and store token encrypted (recommended)
                label = Prompt.ask("Nama / catatan untuk token (opsional)", default="")
                if not db.get_kv("pwd_salt"):
                    # No local password yet
                    if Confirm.ask("Mau membuat password untuk mengenkripsi token? (disarankan)"):
                        pwd = prompt_password_hidden("Buat password baru: ")
                        if not pwd:
                            console.print("[yellow]Tidak membuat password — token tidak disimpan.[/yellow]")
                            token = t.strip()
                            break
                        db.set_password(pwd)
                        db.store_token_encrypted(t.strip(), pwd)
                        token = t.strip()
                        if label:
                            db.set_kv("tok_label", label)
                        db.set_kv("tok_scopes", ",".join(info.get("scopes") or []))
                        console.print("[green]Token tersimpan dan terenkripsi.[/green]")
                        break
                    else:
                        if Confirm.ask("Simpan token hanya untuk sesi saat ini (tidak disimpan permanen)?"):
                            token = t.strip()
                            break
                        else:
                            continue
                else:
                    # existing password: store encrypted
                    pwd = prompt_password_hidden("Masukkan password lokal untuk mengenkripsi token: ")
                    if not pwd or not db.verify_password(pwd):
                        console.print("[red]Password tidak cocok. Token tidak disimpan.[/red]")
                        token = t.strip()
                        break
                    db.store_token_encrypted(t.strip(), pwd)
                    if label:
                        db.set_kv("tok_label", label)
                    db.set_kv("tok_scopes", ",".join(info.get("scopes") or []))
                    token = t.strip()
                    console.print("[green]Token tersimpan dan terenkripsi.[/green]")
                    break
            else:
                console.print("[red]Token tidak valid. Coba lagi.[/red]")
                continue
    return password, token, label


def render_main_menu(username: str):
    clear_screen()
    print_header(ASCII_ART, VERSION, username or "anonymous")
    table = Table.grid(expand=False)
    table.add_column(justify="left", ratio=1)
    table.add_column(justify="left", ratio=1)
    left = "[1] Create Repositori\n[2] List Repositori\n[3] Setup Repositori"
    right = "[4] Delete Repositori\n[5] Pengaturan\n[6] Keluar"
    table.add_row(left, right)
    console.print(table)


def main_menu_loop(db: ConfigDB, gh_client: Optional[GitHubClient], username: str, password: Optional[str]):
    while True:
        render_main_menu(username)
        prompt_text = f"[cyan]{username}[/cyan] [green]tocket[/green] $ "
        try:
            choice = Prompt.ask(prompt_text, default="")
        except KeyboardInterrupt:
            console.print("\n[yellow]Tekan angka menu untuk memilih.[/yellow]")
            continue
        if choice.strip() == "1":
            create_repo_flow(db, gh_client, username, password)
        elif choice.strip() == "2":
            list_repos_flow(db, gh_client)
        elif choice.strip() == "3":
            setup_repo_flow(db, gh_client, username, password)
        elif choice.strip() == "4":
            delete_repo_flow(db, gh_client, username)
        elif choice.strip() == "5":
            settings_flow(db, gh_client, password)
        elif choice.strip() == "6":
            console.print("[green]Keluar. Sampai jumpa.[/green]")
            break
        else:
            console.print("[yellow]Pilihan tidak dikenal.[/yellow]")


def create_repo_flow(db: ConfigDB, gh: Optional[GitHubClient], username: str, password: Optional[str]):
    try:
        if gh is None or gh.token is None:
            console.print("[red]Butuh token untuk membuat repositori. Silakan masukkan token di Pengaturan atau keluar dan jalankan lagi setelah menambahkan token.[/red]")
            return
        name = Prompt.ask("Masukkan nama repositori")
        if not name:
            console.print("[yellow]Dibatalkan: nama repo kosong.[/yellow]")
            return
        desc = Prompt.ask("Masukkan deskripsi", default="")
        vis = Prompt.ask("Apakah anda ingin menggunakan visibilitas publik [y/n]", choices=["y", "n"], default="y")
        private = False if vis.lower() == "y" else True
        add_readme = Prompt.ask("Tambahkan README [y/n]", choices=["y", "n"], default="y")
        auto_init = add_readme.lower() == "y"
        gi_template = None
        if Confirm.ask("Tambahkan .gitignore?"):
            try:
                templates = gh.get_gitignore_templates()
                for i, t in enumerate(templates[:60], start=1):
                    console.print(f"[{i}] {t}")
                sel = Prompt.ask("Pilih nomor template (atau kosong untuk custom)", default="")
                if sel.strip():
                    try:
                        idx = int(sel.strip()) - 1
                        gi_template = templates[idx]
                    except Exception:
                        console.print("[yellow]Pilihan tidak valid, tidak ada .gitignore akan ditambahkan[/yellow]")
            except Exception as e:
                console.print(f"[red]Gagal mengambil template .gitignore: {e}[/red]")
        lic_template = None
        if Confirm.ask("Tambahkan License?"):
            try:
                licenses = gh.get_license_templates()
                for i, l in enumerate(licenses[:30], start=1):
                    console.print(f"[{i}] {l.get('key')} - {l.get('name')}")
                sel = Prompt.ask("Pilih nomor license (atau kosong untuk custom)", default="")
                if sel.strip():
                    idx = int(sel.strip()) - 1
                    lic_template = licenses[idx].get("key")
            except Exception as e:
                console.print(f"[red]Gagal mengambil license templates: {e}[/red]")
        repo = gh.create_repo(name=name, description=desc, private=private, auto_init=auto_init,
                              gitignore_template=gi_template, license_template=lic_template)
        db.add_history("create_repo", repo.get("full_name"))
        console.print("[green]Repositori dibuat:[/green]")
        console.print(repo.get("html_url"))
        console.print(f"Nama: {repo.get('name')}")
        console.print(f"Deskripsi: {repo.get('description')}")
        console.print(f"Visibilitas: {'private' if repo.get('private') else 'public'}")
    except KeyboardInterrupt:
        console.print("\n[yellow]Dibatalkan oleh user.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        traceback.print_exc()


def list_repos_flow(db: ConfigDB, gh: Optional[GitHubClient]):
    try:
        if gh is None or gh.token is None:
            console.print("[yellow]Tidak ada token autentikasi. Kamu dapat memasukkan token untuk melihat semua repos (termasuk private), atau melihat public repos dari username.[/yellow]")
            if Confirm.ask("Ingin memasukkan token sekarang?"):
                t = Prompt.ask("Masukkan token classic GitHub (kosong untuk batal)", default="")
                if not t:
                    console.print("[yellow]Dibatalkan.[/yellow]")
                    return
                tmp = GitHubClient(t)
                info = tmp.validate_token()
                if not info:
                    console.print("[red]Token tidak valid.[/red]")
                    return
                gh_local = tmp
            else:
                user = Prompt.ask("Masukkan username GitHub untuk melihat public repos (kosong batal)", default="")
                if not user:
                    return
                gh_local = GitHubClient()  # tokenless client
                repos = gh_local.list_user_public_repos(user)
                table = Table(title=f"Public repos of {user}", box=box.SIMPLE)
                table.add_column("Nama")
                table.add_column("URL")
                table.add_column("Deskripsi")
                for r in repos:
                    table.add_row(r.get("name", ""), r.get("html_url", ""), r.get("description") or "")
                console.print(table)
                return
        else:
            gh_local = gh

        repos = gh_local.list_repos()
        table = Table(title="Repositori", box=box.SIMPLE)
        table.add_column("Nama")
        table.add_column("Private", justify="center")
        table.add_column("URL")
        table.add_column("Deskripsi")
        for r in repos:
            table.add_row(r.get("name", ""), "yes" if r.get("private") else "no", r.get("html_url", ""), r.get("description") or "")
        console.print(table)
    except Exception as e:
        console.print(f"[red]Gagal mengambil daftar repositori: {e}[/red]")


def delete_repo_flow(db: ConfigDB, gh: Optional[GitHubClient], username: str):
    try:
        if gh is None or gh.token is None:
            console.print("[red]Butuh token dengan scope repo untuk menghapus repositori.[/red]")
            return
        name = Prompt.ask(f"Masukkan nama repositori yang ingin dihapus: https://github.com/{username}/")
        if not name:
            console.print("[yellow]Dibatalkan.[/yellow]")
            return
        confirm = Confirm.ask(f"Yakin ingin menghapus repositori {username}/{name}? Ini tidak bisa dikembalikan.")
        if not confirm:
            console.print("[yellow]Dibatalkan.[/yellow]")
            return
        gh.delete_repo(username, name)
        db.add_history("delete_repo", f"{username}/{name}")
        console.print("[green]Repositori berhasil dihapus.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Dibatalkan.[/yellow]")
    except Exception as e:
        console.print(f"[red]Gagal menghapus repo: {e}[/red]")


def setup_repo_flow(db: ConfigDB, gh: Optional[GitHubClient], username: str, password: Optional[str]):
    try:
        name = Prompt.ask(f"Masukkan nama repositori: https://github.com/{username}/")
        if not name:
            console.print("[yellow]Dibatalkan.[/yellow]")
            return
        # check repo exists (try authenticated if available else public)
        try:
            repos_found = False
            if gh and gh.token:
                repos = gh.list_repos()
                repos_found = any(r.get("name") == name for r in repos)
            else:
                # unauthenticated: check public only
                client = GitHubClient()
                public = client.list_user_public_repos(username)
                repos_found = any(r.get("name") == name for r in public)
            if not repos_found:
                console.print("[red]Repositori tidak ditemukan di akun Anda (atau tidak public).[/red]")
                return
        except Exception as e:
            console.print(f"[red]Gagal memeriksa repositori: {e}[/red]")
            return

        while True:
            console.print("\n[bold]Setup Repositori[/bold]")
            console.print("[1] Upload file\n[2] Hapus file\n[3] Rename file/folder\n[4] List file\n[5] Ubah visibilitas\n[6] Ubah .gitignore\n[7] Ubah License\n[8] Hapus folder\n[9] Kembali")
            try:
                c = Prompt.ask("Pilih opsi", default="")
            except KeyboardInterrupt:
                console.print("\n[yellow]Dibatalkan.[/yellow]")
                return
            if c.strip() == "1":
                upload_file_flow(db, gh, username, name)
            elif c.strip() == "2":
                delete_file_flow(db, gh, username, name)
            elif c.strip() == "3":
                console.print("[yellow]Fitur rename akan diimplementasikan di rilis berikutnya (scaffolded).[/yellow]")
            elif c.strip() == "4":
                list_files_flow(db, gh, username, name)
            elif c.strip() == "5":
                change_visibility_flow(db, gh, username, name)
            elif c.strip() == "6":
                console.print("[yellow].gitignore change via templates will be interactive (partial).[/yellow]")
            elif c.strip() == "7":
                console.print("[yellow]License change via templates will be interactive (partial).[/yellow]")
            elif c.strip() == "8":
                console.print("[yellow]Folder delete will be implemented carefully (scaffolded).[/yellow]")
            elif c.strip() == "9":
                return
            else:
                console.print("[yellow]Pilihan tidak valid.[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Dibatalkan oleh user.[/yellow]")


def upload_file_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            console.print("[red]Butuh token untuk meng-upload file ke repo. Tambahkan token di Pengaturan.[/red]")
            return
        start_path = Prompt.ask("Mulai path file (kosong = current directory)", default="")
        current = Path(start_path or ".").expanduser().resolve()
        while True:
            files = list(current.iterdir())
            console.print(f"\n[bold]Folder: {str(current)}[/bold]")
            for idx, p in enumerate(files, start=1):
                console.print(f"[{idx}] {'[DIR]' if p.is_dir() else '[FILE]'} {p.name}")
            console.print("[0] .. (ke folder parent)\n[enter] pilih current folder untuk upload file dari sini /ketik path file penuh")
            try:
                sel = Prompt.ask("Pilih nomor / ketik filename (atau 'q' untuk batal)", default="")
            except KeyboardInterrupt:
                console.print("\n[yellow]Upload dibatalkan.[/yellow]")
                return
            if sel.strip().lower() == "q":
                return
            if sel.strip() == "":
                fname = Prompt.ask("Masukkan nama file di folder ini (atau full path)", default="")
                if not fname:
                    console.print("[yellow]Dibatalkan.[/yellow]")
                    return
                path = Path(fname)
                if not path.is_absolute():
                    path = current / path
                if not path.exists() or not path.is_file():
                    console.print("[red]File tidak ditemukan.[/red]")
                    continue
                if path.stat().st_size > 100 * 1024 * 1024:  # 100MB
                    console.print("[red]File terlalu besar untuk di-upload via GitHub Contents API (>100MB).[/red]")
                    continue
                repo_path = Prompt.ask("Simpan path di repo (kosong = root, atau folder/ subfolder/ diakhiri '/' untuk folder)", default="")
                target_path = (repo_path.strip() + path.name) if repo_path.strip() else path.name
                try:
                    content = read_binary_file(str(path))
                    gh.create_or_update_file(owner, repo, target_path, content, message=f"Tocket: upload {target_path}")
                    db.add_history("upload_file", f"{owner}/{repo}/{target_path}")
                    console.print(f"[green]Upload sukses: {target_path}[/green]")
                    return
                except Exception as e:
                    console.print(f"[red]Gagal upload: {e}[/red]")
                    continue
            else:
                try:
                    idx = int(sel.strip())
                    if idx == 0:
                        if current.parent == current:
                            console.print("[yellow]Sudah root.[/yellow]")
                        else:
                            current = current.parent
                    else:
                        chosen = files[idx - 1]
                        if chosen.is_dir():
                            current = chosen
                        else:
                            path = chosen
                            if path.stat().st_size > 100 * 1024 * 1024:
                                console.print("[red]File terlalu besar untuk di-upload via GitHub Contents API (>100MB).[/red]")
                                return
                            repo_path = Prompt.ask("Simpan path di repo (kosong = root)", default="")
                            target_path = (repo_path.strip() + path.name) if repo_path.strip() else path.name
                            try:
                                content = read_binary_file(str(path))
                                gh.create_or_update_file(owner, repo, target_path, content, message=f"Tocket: upload {target_path}")
                                db.add_history("upload_file", f"{owner}/{repo}/{target_path}")
                                console.print(f"[green]Upload sukses: {target_path}[/green]")
                                return
                            except Exception as e:
                                console.print(f"[red]Gagal upload: {e}[/red]")
                                return
                except ValueError:
                    console.print("[yellow]Input tidak dikenali.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error upload flow: {e}[/red]")


def delete_file_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            console.print("[red]Butuh token untuk menghapus file di repo. Tambahkan token di Pengaturan.[/red]")
            return
        fname = Prompt.ask("Masukkan nama file (path relatif di repo) untuk dihapus")
        if not fname:
            console.print("[yellow]Dibatalkan.[/yellow]")
            return
        if not Confirm.ask(f"Yakin ingin menghapus file {fname}?"):
            console.print("[yellow]Dibatalkan.[/yellow]")
            return
        gh.delete_file(owner, repo, fname, message=f"Tocket: delete {fname}")
        db.add_history("delete_file", f"{owner}/{repo}/{fname}")
        console.print("[green]File dihapus.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Dibatalkan.[/yellow]")
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
    except Exception as e:
        console.print(f"[red]Gagal menghapus file: {e}[/red]")


def list_files_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        client = gh or GitHubClient()
        tree = client.list_repo_tree(owner, repo)
        table = Table(title=f"Files in {owner}/{repo}", box=box.MINIMAL)
        table.add_column("Path")
        table.add_column("Type")
        table.add_column("Size")
        for t in tree:
            table.add_row(t.get("path", ""), t.get("type", ""), str(t.get("size", "-")))
        console.print(table)
    except Exception as e:
        console.print(f"[red]Gagal mengambil file list: {e}[/red]")


def change_visibility_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            console.print("[red]Butuh token untuk mengubah visibilitas repo.[/red]")
            return
        vis = Prompt.ask("Visibilitas apa yg anda ingin gunakan [publik/private]", choices=["publik", "private"], default="publik")
        payload = {"private": (vis == "private")}
        r = gh.session.patch(f"https://api.github.com/repos/{owner}/{repo}", json=payload)
        if r.status_code == 200:
            db.add_history("change_visibility", f"{owner}/{repo} -> {vis}")
            console.print("[green]Visibilitas berhasil diubah.[/green]")
        else:
            console.print(f"[red]Gagal mengubah visibilitas: {r.status_code} {r.text}[/red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Dibatalkan.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def settings_flow(db: ConfigDB, gh: Optional[GitHubClient], password: Optional[str]):
    try:
        while True:
            console.print("\n[bold]Pengaturan[/bold]")
            console.print("[1] Tampilkan Token classic\n[2] Ubah token classic\n[3] Hapus token classic\n[4] Tampilkan password\n[5] Ubah password\n[6] Hapus password\n[7] Kembali\n[8] Buat password")
            c = Prompt.ask("Pilih", default="")
            if c.strip() == "1":
                cipher = db.get_kv("tok_cipher")
                if not cipher:
                    console.print("[yellow]Tidak ada token tersimpan.[/yellow]")
                else:
                    label = db.get_kv("tok_label") or "(tidak ada label)"
                    scopes_db = db.get_kv("tok_scopes") or ""
                    if not password:
                        pwd = prompt_password_hidden("Masukkan password untuk dekripsi token: ")
                        if not pwd or not db.verify_password(pwd):
                            console.print("[red]Password salah.[/red]")
                            continue
                        token = db.load_token_decrypted(pwd)
                    else:
                        token = db.load_token_decrypted(password)
                    if token:
                        tmp = GitHubClient(token)
                        info = tmp.validate_token()
                        console.print("[bold]Token info:[/bold]")
                        console.print(f"Nama token (label): {label}")
                        console.print(f"Token: {token}")
                        console.print(f"Scopes: {info.get('scopes') if info else scopes_db}")
                        console.print("Expiration: (tidak tersedia via REST API)")
                    else:
                        console.print("[red]Gagal mendekripsi token.[/red]")
            elif c.strip() == "2":
                t = Prompt.ask("Masukkan token classic GitHub (kosong untuk batal)", default="")
                if not t:
                    continue
                tmp_client = GitHubClient(t)
                info = tmp_client.validate_token()
                if not info:
                    console.print("[red]Token tidak valid.[/red]")
                    continue
                label = Prompt.ask("Nama / catatan token (opsional)", default="")
                if not password:
                    pwd = prompt_password_hidden("Masukkan password lokal untuk mengenkripsi token: ")
                    if not pwd or not db.verify_password(pwd):
                        console.print("[red]Password salah. Token tidak disimpan.[/red]")
                        continue
                    db.store_token_encrypted(t, pwd)
                else:
                    db.store_token_encrypted(t, password)
                if label:
                    db.set_kv("tok_label", label)
                db.set_kv("tok_scopes", ",".join(info.get("scopes") or []))
                console.print("[green]Token tersimpan.[/green]")
            elif c.strip() == "3":
                if Confirm.ask("Yakin ingin menghapus token classic dari storage?"):
                    db.clear_token()
                    db.delete_kv("tok_label")
                    db.delete_kv("tok_scopes")
                    console.print("[green]Token dihapus dari DB.[/green]")
            elif c.strip() == "4":
                console.print("[yellow]Menampilkan password tidak mungkin (disimpan hashed). Anda dapat mengganti password.[/yellow]")
            elif c.strip() == "5":
                if not db.get_kv("pwd_salt"):
                    console.print("[yellow]Belum ada password. Gunakan opsi Buat password.[/yellow]")
                    continue
                current = prompt_password_hidden("Masukkan password saat ini: ")
                if not current or not db.verify_password(current):
                    console.print("[red]Password salah.[/red]")
                    continue
                newpwd = prompt_password_hidden("Masukkan password baru: ")
                if not newpwd:
                    console.print("[yellow]Dibatalkan.[/yellow]")
                    continue
                token = db.load_token_decrypted(current)
                db.set_password(newpwd)
                if token:
                    db.store_token_encrypted(token, newpwd)
                console.print("[green]Password diubah dan token dire-enkripsi.[/green]")
            elif c.strip() == "6":
                if Confirm.ask("Yakin ingin menghapus password lokal? Ini juga akan menghapus token terenkripsi."):
                    db.clear_password()
                    db.clear_token()
                    db.delete_kv("tok_label")
                    db.delete_kv("tok_scopes")
                    console.print("[green]Password dan token dihapus dari storage.[/green]")
            elif c.strip() == "7":
                return
            elif c.strip() == "8":
                if db.get_kv("pwd_salt"):
                    console.print("[yellow]Password sudah ada. Gunakan ubah password.[/yellow]")
                    continue
                newpwd = prompt_password_hidden("Buat password baru: ")
                if not newpwd:
                    console.print("[yellow]Dibatalkan.[/yellow]")
                    continue
                db.set_password(newpwd)
                console.print("[green]Password berhasil dibuat.[/green]")
            else:
                console.print("[yellow]Pilihan tidak valid.[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Dibatalkan.[/yellow]")


def main():
    db = ensure_db()
    pwd, token, label = login_flow(db)
    gh_client: Optional[GitHubClient] = None
    username = "anonymous"
    if token:
        try:
            gh_client = GitHubClient(token)
            info = gh_client.validate_token()
            if info:
                username = info.get("username") or username
            else:
                console.print("[red]Token tidak valid saat login awal.[/red]")
                gh_client = None
        except Exception as e:
            console.print(f"[red]Gagal validasi token saat startup: {e}[/red]")
            gh_client = None
    else:
        console.print("[yellow]Beberapa fitur butuh token. Lanjutkan tanpa token terbatas.[/yellow]")

    try:
        main_menu_loop(db, gh_client, username, pwd)
    finally:
        db.close()


if __name__ == "__main__":
    main()
