import sys
import getpass
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table
from rich import box
from .constants import VERSION, APPNAME
from .db import ConfigDB
from .utils import clear_screen, print_header, read_binary_file
from .github_api import GitHubClient

console = Console()

ASCII_ART = r"""
TTTTTTTTTT  OOOOO  CCCCC K   K EEEEE TTTTTTTTTT
    TT     O     O C     K  K  E         TT
    TT     O     O C     KKK   EEEE      TT
    TT     O     O C     K  K  E         TT
    TT      OOOOO  CCCCC K   K EEEEE     TT
"""

def prompt_password_hidden(prompt_text: str = "Masukkan password: ") -> Optional[str]:
    try:
        return getpass.getpass(prompt_text)
    except KeyboardInterrupt:
        return None

def ensure_db() -> ConfigDB:
    return ConfigDB()

def mask_token(tok: str) -> str:
    if not tok:
        return ""
    if len(tok) <= 8:
        return tok[:2] + "..." + tok[-2:]
    return tok[:4] + "..." + tok[-4:]

def _parse_github_url(url_or_repo: str) -> Tuple[Optional[str], Optional[str]]:
    if not url_or_repo:
        return None, None
    s = url_or_repo.strip()
    if s.startswith("http://") or s.startswith("https://"):
        try:
            p = urlparse(s)
            parts = p.path.strip("/").split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
            if len(parts) == 1:
                return parts[0], None
        except Exception:
            return None, None
    if "/" in s:
        parts = s.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
    return None, s

def get_repo_default_branch(gh: GitHubClient, owner: str, repo: str) -> Optional[str]:
    """
    Determine default branch for repo: prefer repo metadata, fallback to main/master.
    """
    try:
        if hasattr(gh, "get_default_branch"):
            b = gh.get_default_branch(owner, repo)
            if b:
                return b
    except Exception:
        pass
    try:
        if hasattr(gh, "get_repo"):
            data = gh.get_repo(owner, repo)
            if data and data.get("default_branch"):
                return data.get("default_branch")
    except Exception:
        pass
    for b in ("main", "master"):
        try:
            r = gh.session.get(f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{b}", timeout=10)
            if r.status_code == 200:
                return b
        except Exception:
            continue
    return None

def login_flow(db: ConfigDB) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Handle password + token retrieval/storage.
    Returns (password, token, label)
    """
    pwd_salt = db.get_kv("pwd_salt")
    password: Optional[str] = None
    if pwd_salt:
        attempts = 0
        while attempts < 3:
            pwd = prompt_password_hidden("Masukkan password: ")
            if pwd is None:
                console.print("[yellow]Batal input password.[/yellow]")
                return None, None, None
            if db.verify_password(pwd):
                password = pwd
                break
            else:
                console.print("[red]Password yang dimasukkan salah![/red]")
                attempts += 1
        if attempts >= 3 and password is None:
            console.print("[red]Mencapai batas percobaan.[/red]")
            sys.exit(1)
    else:
        console.print("[green]Tidak ada password lokal — lanjutkan tanpa password atau buat password lewat Pengaturan nanti.[/green]")

    token: Optional[str] = None
    label: Optional[str] = None

    if db.get_kv("tok_cipher"):
        if password is None:
            console.print("[yellow]Token terenkripsi ditemukan, tetapi tidak ada password yang disediakan. Silakan masukkan password terlebih dahulu.[/yellow]")
            pwd = prompt_password_hidden("Masukkan password: ")
            if pwd is None:
                return None, None, None
            if not db.verify_password(pwd):
                console.print("[red]Password salah![/red]")
                return None, None, None
            password = pwd
        token = db.load_token_decrypted(password)
        if token is None:
            console.print("[red]Gagal dekripsi token — kemungkinan password berbeda. Kamu bisa reset token di Pengaturan.[/red]")
        else:
            label = db.get_kv("tok_label")
            console.print(f"[green]Token tersimpan ditemukan untuk label: [cyan]{label or '(no label)'}[/cyan][/green]")
    else:
        while True:
            try:
                t = input("Masukkan token classic GitHub (atau enter untuk lanjut tanpa token): ").strip()
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
                label = input("Nama / catatan untuk token (opsional): ").strip()
                if not db.get_kv("pwd_salt"):
                    create_pwd = input("Mau membuat password untuk mengenkripsi token? (y/N): ").strip().lower()
                    if create_pwd == "y":
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
                        session_save = input("Simpan token hanya untuk sesi saat ini (tidak disimpan permanen)? (y/N): ").strip().lower()
                        if session_save == "y":
                            token = t.strip()
                            break
                        else:
                            continue
                else:
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

from itertools import zip_longest

def render_main_menu(username: str):
    """
    Render header + 2-column menu aligned per-row.
    Kolom kiri & kanan ditampilkan berdampingan sehingga terlihat rapi.
    """
    clear_screen()
    print_header(ASCII_ART, VERSION, username or "anonymous")

    left_lines = [
        "[1] Create Repositori",
        "[2] List Repositori",
        "[3] Setup Repositori",
    ]
    right_lines = [
        "[4] Delete Repositori",
        "[5] Pengaturan",
        "[6] Keluar",
    ]

    left_width = max(len(s) for s in left_lines) + 4

    for l, r in zip_longest(left_lines, right_lines, fillvalue=""):
        console.print(f"[white]{l.ljust(left_width)}[/white][green]{r}[/green]")

def main_menu_loop(db: ConfigDB, gh_client: Optional[GitHubClient], username: str, password: Optional[str]):
    while True:
        render_main_menu(username)
        try:
            raw = input(f"\n{username}@Tocket $ ").strip()
        except KeyboardInterrupt:
            print("\nTekan angka menu untuk memilih.")
            continue
        if raw == "1":
            create_repo_flow(db, gh_client, username, password)
        elif raw == "2":
            list_repos_flow(db, gh_client)
        elif raw == "3":
            setup_repo_flow(db, gh_client, username, password)
        elif raw == "4":
            delete_repo_flow(db, gh_client, username)
        elif raw == "5":
            settings_flow(db, gh_client, password)
        elif raw == "6":
            print("Sampai jumpa !")
            break
        else:
            print("Pilihan tidak dikenal!")

def create_repo_flow(db: ConfigDB, gh: Optional[GitHubClient], username: str, password: Optional[str]):
    try:
        if gh is None or gh.token is None:
            print("Butuh token untuk membuat repositori. Tambahkan token di Pengaturan.")
            return
        name = input("Masukkan nama repositori: ").strip()
        if not name:
            print("Dibatalkan: nama repo kosong.")
            return
        desc = input("Masukkan deskripsi (enter kosong): ").strip()
        vis = input("Apakah anda ingin menggunakan visibilitas publik [y/n] (default y): ").strip().lower() or "y"
        private = False if vis == "y" else True
        add_readme = input("Tambahkan README [y/n] (default y): ").strip().lower() or "y"
        auto_init = add_readme == "y"
        gi_template = None
        if input("Tambahkan .gitignore? [y/N]: ").strip().lower() == "y":
            try:
                templates = gh.get_gitignore_templates()
                for i, t in enumerate(templates[:60], start=1):
                    print(f"[{i}] {t}")
                sel = input("Pilih nomor template (atau kosong untuk custom): ").strip()
                if sel:
                    idx = int(sel) - 1
                    gi_template = templates[idx]
            except Exception as e:
                print(f"Gagal mengambil .gitignore templates: {e}")
        lic_template = None
        if input("Tambahkan License? [y/N]: ").strip().lower() == "y":
            try:
                licenses = gh.get_license_templates()
                for i, l in enumerate(licenses[:30], start=1):
                    print(f"[{i}] {l.get('key')} - {l.get('name')}")
                sel = input("Pilih nomor license (atau kosong untuk custom): ").strip()
                if sel:
                    idx = int(sel) - 1
                    lic_template = licenses[idx].get("key")
            except Exception as e:
                print(f"Gagal mengambil license templates: {e}")
        repo = gh.create_repo(name=name, description=desc, private=private, auto_init=auto_init,
                              gitignore_template=gi_template, license_template=lic_template)
        db.add_history("create_repo", repo.get("full_name"))
        print("Repositori dibuat:", repo.get("html_url"))
    except Exception as e:
        print("Error:", e)
        traceback.print_exc()

def list_repos_flow(db: ConfigDB, gh: Optional[GitHubClient]):
    """
    List repositories and show table with columns:
      - Repositori
      - Visibilitas
      - Branch
    Robust handling for token / public fallback / token replace.
    """
    try:
        gh_local = gh
        repos = None

        if gh_local and getattr(gh_local, "token", None):
            try:
                repos = gh_local.list_repos()
            except Exception as e:
                console.print(f"[red]Gagal list repos dengan token saat ini: {e}[/red]")
                msg = str(e).lower()
                if "401" in msg or "unauthorized" in msg or "invalid" in msg:
                    if Confirm.ask("Token invalid/expired. Mau masukkan token baru sekarang?"):
                        new_tok = Prompt.ask("Masukkan token classic GitHub (kosong = batal)", default="")
                        if not new_tok:
                            console.print("[yellow]Batal memasukkan token baru.[/yellow]")
                            return
                        tmp = GitHubClient(new_tok.strip())
                        info = tmp.validate_token()
                        if not info:
                            console.print("[red]Token baru tidak valid.[/red]")
                            return
                        label = Prompt.ask("Nama / catatan untuk token (opsional)", default="")
                        if db.get_kv("pwd_salt"):
                            pwd = prompt_password_hidden("Masukkan password lokal untuk mengenkripsi token (atau enter untuk skip): ")
                            if pwd and db.verify_password(pwd):
                                db.store_token_encrypted(new_tok.strip(), pwd)
                                db.set_kv("tok_label", label or "")
                                db.set_kv("tok_scopes", ",".join(info.get("scopes") or []))
                                console.print("[green]Token tersimpan dan terenkripsi.[/green]")
                        else:
                            if Confirm.ask("Mau membuat password untuk mengenkripsi token sekarang? (disarankan)"):
                                pwd = prompt_password_hidden("Buat password baru: ")
                                if pwd:
                                    db.set_password(pwd)
                                    db.store_token_encrypted(new_tok.strip(), pwd)
                                    db.set_kv("tok_label", label or "")
                                    db.set_kv("tok_scopes", ",".join(info.get("scopes") or []))
                                    console.print("[green]Token tersimpan dan terenkripsi.[/green]")
                        try:
                            repos = tmp.list_repos()
                            gh_local = tmp
                        except Exception as e2:
                            console.print(f"[red]Gagal mengambil repo dengan token baru: {e2}[/red]")
                            return
                else:
                    console.print(f"[red]Gagal mengambil repo: {e}[/red]")
                    return

        if repos is None:
            console.print("[yellow]Tidak ada token autentikasi. Kamu dapat memasukkan token untuk melihat semua repos (termasuk private), atau melihat public repos dari username.[/yellow]")
            if Confirm.ask("Ingin memasukkan token sekarang?"):
                t = Prompt.ask("Masukkan token classic GitHub (kosong untuk batal)", default="")
                if not t:
                    console.print("[yellow]Dibatalkan.[/yellow]")
                    return
                tmp = GitHubClient(t.strip())
                info = tmp.validate_token()
                if not info:
                    console.print("[red]Token tidak valid.[/red]")
                    return
                label = Prompt.ask("Nama / catatan untuk token (opsional)", default="")
                if db.get_kv("pwd_salt"):
                    pwd = prompt_password_hidden("Masukkan password lokal untuk mengenkripsi token (atau enter untuk skip): ")
                    if pwd and db.verify_password(pwd):
                        db.store_token_encrypted(t.strip(), pwd)
                        db.set_kv("tok_label", label or "")
                        db.set_kv("tok_scopes", ",".join(info.get("scopes") or []))
                        console.print("[green]Token tersimpan dan terenkripsi.[/green]")
                else:
                    if Confirm.ask("Mau membuat password untuk mengenkripsi token sekarang? (disarankan)"):
                        pwd = prompt_password_hidden("Buat password baru: ")
                        if pwd:
                            db.set_password(pwd)
                            db.store_token_encrypted(t.strip(), pwd)
                            db.set_kv("tok_label", label or "")
                            db.set_kv("tok_scopes", ",".join(info.get("scopes") or []))
                            console.print("[green]Token tersimpan dan terenkripsi.[/green]")
                gh_local = tmp
                try:
                    repos = gh_local.list_repos()
                except Exception as e:
                    console.print(f"[red]Gagal mengambil repo dengan token: {e}[/red]")
                    return
            else:
                user = Prompt.ask("Masukkan username GitHub untuk melihat public repos (kosong batal)", default="")
                if not user:
                    return
                try:
                    gh_public = GitHubClient()
                    repos = gh_public.list_user_public_repos(user)
                except Exception as e:
                    console.print(f"[red]Gagal mengambil public repos untuk {user}: {e}[/red]")
                    return
                   
        if not repos:
            console.print("[yellow]Tidak ada repositori untuk ditampilkan.[/yellow]")
            return

        table = Table(title="Repositori", box=box.SIMPLE)
        table.add_column("Repositori", style="cyan", no_wrap=True)
        table.add_column("Visibilitas", justify="center")
        table.add_column("Branch", justify="center")

        for r in repos:
            name = r.get("name") or r.get("full_name") or str(r.get("html_url") or "")
            visibility = "private" if r.get("private") else "public"
            branch = r.get("default_branch")
            if not branch:
                try:
                    if gh_local and hasattr(gh_local, "get_default_branch"):
                        branch = gh_local.get_default_branch(r.get("owner", {}).get("login") or "", r.get("name") or "")
                    elif gh_local and hasattr(gh_local, "get_repo"):
                        repo_meta = gh_local.get_repo(r.get("owner", {}).get("login") or "", r.get("name") or "")
                        branch = repo_meta.get("default_branch")
                except Exception:
                    branch = "-"
            table.add_row(name, visibility, branch or "-")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Gagal mengambil daftar repositori: {e}[/red]")
        traceback.print_exc()

def delete_repo_flow(db: ConfigDB, gh: Optional[GitHubClient], username: str):
    try:
        if gh is None or gh.token is None:
            print("Butuh token dengan scope repo untuk menghapus repositori.")
            return
        name = input(f"Masukkan nama repositori yang ingin dihapus: https://github.com/{username}/").strip()
        if not name:
            print("Dibatalkan.")
            return
        confirm = input(f"Yakin ingin menghapus repositori {username}/{name}? Ini tidak bisa dikembalikan. [y/N]: ").strip().lower()
        if confirm != "y":
            print("Dibatalkan.")
            return
        gh.delete_repo(username, name)
        db.add_history("delete_repo", f"{username}/{name}")
        print("Repositori berhasil dihapus.")
    except Exception as e:
        print("Gagal menghapus repo:", e)

def setup_repo_flow(db: ConfigDB, gh: Optional[GitHubClient], username: str, password: Optional[str]):
    try:
        name = input(f"Masukkan nama repositori: https://github.com/{username}/").strip()
        if not name:
            print("Dibatalkan.")
            return
        try:
            found = False
            if gh and gh.token:
                repos = gh.list_repos()
                found = any(r.get("name") == name for r in repos)
            else:
                client = GitHubClient()
                public = client.list_user_public_repos(username)
                found = any(r.get("name") == name for r in public)
            if not found:
                print("Repositori tidak ditemukan di akun Anda (atau tidak public).")
                return
        except Exception as e:
            print("Gagal memeriksa repositori:", e)
            return

        while True:
            print("\n[Setup Repositori]")
            print("[1] Upload file\n[2] Hapus file\n[3] Rename file/folder\n[4] List file\n[5] Ubah visibilitas\n[6] Ubah .gitignore\n[7] Ubah License\n[8] Hapus folder\n[9] Kembali")
            c = input("Pilih opsi: ").strip()
            if c == "1":
                upload_file_flow(db, gh, username, name)
            elif c == "2":
                delete_file_flow(db, gh, username, name)
            elif c == "3":
                rename_file_or_folder_flow(db, gh, username, name)
            elif c == "4":
                list_files_flow(db, gh, username, name)
            elif c == "5":
                change_visibility_flow(db, gh, username, name)
            elif c == "6":
                change_gitignore_flow(db, gh, username, name)
            elif c == "7":
                change_license_flow(db, gh, username, name)
            elif c == "8":
                delete_folder_flow(db, gh, username, name)
            elif c == "9":
                return
            else:
                print("Pilihan tidak valid.")
    except Exception as e:
        print("Gagal di setup repo:", e)

def upload_file_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            print("Butuh token untuk meng-upload file ke repo. Tambahkan token di Pengaturan.")
            return
        start_path = input("Mulai path file (kosong = current directory): ").strip()
        current = Path(start_path or ".").expanduser().resolve()
        while True:
            files = list(current.iterdir())
            print(f"\nFolder: {str(current)}")
            for idx, p in enumerate(files, start=1):
                print(f"[{idx}] {'[DIR]' if p.is_dir() else '[FILE]'} {p.name}")
            print("[0] .. (ke folder parent)\n[enter] pilih current folder untuk upload file dari sini /ketik path file penuh")
            sel = input("Pilih nomor / ketik filename (atau 'q' untuk batal): ").strip()
            if sel.lower() == "q":
                return
            if sel == "":
                fname = input("Masukkan nama file di folder ini (atau full path): ").strip()
                if not fname:
                    print("Dibatalkan.")
                    return
                path = Path(fname)
                if not path.is_absolute():
                    path = current / path
                if not path.exists() or not path.is_file():
                    print("File tidak ditemukan.")
                    continue
                if path.stat().st_size > 100 * 1024 * 1024:
                    print("File terlalu besar untuk di-upload via GitHub Contents API (>100MB).")
                    continue
                repo_path = input("Simpan path di repo (kosong = root, atau folder/ subfolder/ diakhiri '/' untuk folder): ").strip()
                target_path = (repo_path.strip() + path.name) if repo_path.strip() else path.name
                try:
                    branch = get_repo_default_branch(gh, owner, repo) or input("Masukkan branch target (kosong = main): ").strip() or "main"
                    content = read_binary_file(str(path))
                    gh.create_or_update_file(owner, repo, target_path, content, message=f"Tocket: upload {target_path}", branch=branch)
                    db.add_history("upload_file", f"{owner}/{repo}/{target_path}")
                    print(f"Upload sukses: {target_path}")
                    return
                except Exception as e:
                    print("Gagal upload:", e)
                    continue
            else:
                try:
                    idx = int(sel)
                    if idx == 0:
                        if current.parent == current:
                            print("Sudah root.")
                        else:
                            current = current.parent
                    else:
                        chosen = files[idx - 1]
                        if chosen.is_dir():
                            current = chosen
                        else:
                            path = chosen
                            if path.stat().st_size > 100 * 1024 * 1024:
                                print("File terlalu besar untuk di-upload via GitHub Contents API (>100MB).")
                                return
                            repo_path = input("Simpan path di repo (kosong = root): ").strip()
                            target_path = (repo_path.strip() + path.name) if repo_path.strip() else path.name
                            try:
                                branch = get_repo_default_branch(gh, owner, repo) or input("Masukkan branch target (kosong = main): ").strip() or "main"
                                content = read_binary_file(str(path))
                                gh.create_or_update_file(owner, repo, target_path, content, message=f"Tocket: upload {target_path}", branch=branch)
                                db.add_history("upload_file", f"{owner}/{repo}/{target_path}")
                                print(f"Upload sukses: {target_path}")
                                return
                            except Exception as e:
                                print("Gagal upload:", e)
                                return
                except ValueError:
                    print("Input tidak dikenali.")
    except Exception as e:
        print("Error upload flow:", e)

def delete_file_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            print("Butuh token untuk menghapus file di repo. Tambahkan token di Pengaturan.")
            return
        fname = input("Masukkan nama file (path relatif di repo) untuk dihapus: ").strip()
        if not fname:
            print("Dibatalkan.")
            return
        if input(f"Yakin ingin menghapus file {fname}? [y/N]: ").strip().lower() != "y":
            print("Dibatalkan.")
            return
        branch = get_repo_default_branch(gh, owner, repo) or "main"
        gh.delete_file(owner, repo, fname, message=f"Tocket: delete {fname}", branch=branch)
        db.add_history("delete_file", f"{owner}/{repo}/{fname}")
        print("File dihapus.")
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print("Gagal menghapus file:", e)

def list_files_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        client = gh or GitHubClient()
        branch = get_repo_default_branch(client, owner, repo) or "main"
        tree = client.list_repo_tree(owner, repo, branch=branch)
        table = Table(title=f"Files in {owner}/{repo} (branch={branch})", box=box.MINIMAL)
        table.add_column("Path")
        table.add_column("Type")
        table.add_column("Size")
        for t in tree:
            table.add_row(t.get("path", ""), t.get("type", ""), str(t.get("size", "-")))
        console.print(table)
    except Exception as e:
        print("Gagal mengambil file list:", e)

def change_visibility_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            print("Butuh token untuk mengubah visibilitas repo.")
            return
        vis = input("Visibilitas apa yg anda ingin gunakan [publik/private] (default publik): ").strip().lower() or "publik"
        payload = {"private": (vis == "private")}
        if hasattr(gh, "patch_repo"):
            gh.patch_repo(owner, repo, payload)
        else:
            r = gh.session.patch(f"https://api.github.com/repos/{owner}/{repo}", json=payload)
            if r.status_code != 200:
                raise RuntimeError(f"Failed to patch repo: {r.status_code} {r.text}")
        db.add_history("change_visibility", f"{owner}/{repo} -> {vis}")
        print("Visibilitas berhasil diubah.")
    except Exception as e:
        print("Gagal mengubah visibilitas:", e)

def rename_file_or_folder_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            print("Butuh token untuk rename file/folder.")
            return
        src = input("Masukkan nama file/folder yang ingin di-rename (path relatif di repo): ").strip()
        if not src:
            return
        dest = input("Masukkan nama baru untuk file/folder yang ingin di-rename (path relatif di repo): ").strip()
        if not dest:
            return
        branch = get_repo_default_branch(gh, owner, repo) or "main"
        tree = gh.list_repo_tree(owner, repo, branch=branch)
        src = src.rstrip("/")
        dest = dest.rstrip("/")
        to_move = [item for item in tree if item.get("path") == src or item.get("path", "").startswith(src + "/")]
        if not to_move:
            print(f"{src} not found in {owner}/{repo}")
            return
        for item in to_move:
            if item.get("type") != "blob":
                continue
            old_path = item.get("path")
            if old_path == src:
                new_path = dest
            else:
                suffix = old_path[len(src) + 1 :]
                new_path = dest + "/" + suffix if suffix else dest
            contents = gh.get_contents(owner, repo, old_path, ref=branch)
            if not contents:
                continue
            if contents.get("content"):
                import base64
                data = base64.b64decode(contents.get("content"))
            else:
                dl = gh.session.get(contents.get("download_url"))
                data = dl.content
            gh.create_or_update_file(owner, repo, new_path, data, message=f"Tocket: move {old_path} -> {new_path}", branch=branch)
            gh.delete_file(owner, repo, old_path, message=f"Tocket: delete {old_path} (moved)", branch=branch)
            db.add_history("rename_move", f"{owner}/{repo}/{old_path} -> {new_path}")
        print("Rename/move selesai.")
    except Exception as e:
        print("Gagal rename/move:", e)

def change_gitignore_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            print("Butuh token untuk mengubah .gitignore.")
            return
        templates = gh.get_gitignore_templates()
        for i, t in enumerate(templates[:100], start=1):
            print(f"[{i}] {t}")
        sel = input("Pilih nomor template (atau kosong untuk custom): ").strip()
        chosen_content = None
        if sel:
            idx = int(sel) - 1
            tmpl = templates[idx]
            r = gh.session.get(f"https://api.github.com/gitignore/templates/{tmpl}")
            if r.status_code == 200:
                chosen_content = r.json().get("source")
        else:
            chosen_content = input("Masukkan isi .gitignore (enter untuk batal):\n")
        if not chosen_content:
            print("Tidak ada template/isi dipilih.")
            return
        branch = get_repo_default_branch(gh, owner, repo) or "main"
        gh.create_or_update_file(owner, repo, ".gitignore", chosen_content.encode("utf-8"), message="Tocket: update .gitignore", branch=branch)
        db.add_history("update_gitignore", f"{owner}/{repo}")
        print(".gitignore diupdate.")
    except Exception as e:
        print("Gagal update .gitignore:", e)

def change_license_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            print("Butuh token untuk mengubah License.")
            return
        licenses = gh.get_license_templates()
        for i, l in enumerate(licenses[:60], start=1):
            print(f"[{i}] {l.get('key')} - {l.get('name')}")
        sel = input("Pilih nomor template (atau kosong untuk custom): ").strip()
        content = None
        if sel:
            idx = int(sel) - 1
            key = licenses[idx].get("key")
            r = gh.session.get(f"https://api.github.com/licenses/{key}")
            if r.status_code == 200:
                content = r.json().get("body")
        else:
            content = input("Masukkan isi License (enter untuk batal):\n")
        if not content:
            print("Tidak ada license dipilih.")
            return
        branch = get_repo_default_branch(gh, owner, repo) or "main"
        gh.create_or_update_file(owner, repo, "LICENSE", content.encode("utf-8"), message="Tocket: update LICENSE", branch=branch)
        db.add_history("update_license", f"{owner}/{repo}")
        print("LICENSE diupdate.")
    except Exception as e:
        print("Gagal update LICENSE:", e)

def delete_folder_flow(db: ConfigDB, gh: Optional[GitHubClient], owner: str, repo: str):
    try:
        if gh is None or gh.token is None:
            print("Butuh token untuk menghapus folder di repo.")
            return
        folder = input("Masukkan nama folder yang ingin dihapus (path relatif di repo): ").strip()
        if not folder:
            return
        if input(f"Yakin ingin menghapus folder {folder} dan seluruh isinya? [y/N]: ").strip().lower() != "y":
            print("Dibatalkan.")
            return
        branch = get_repo_default_branch(gh, owner, repo) or "main"
        tree = gh.list_repo_tree(owner, repo, branch=branch)
        to_delete = [t for t in tree if t.get("path") == folder or t.get("path", "").startswith(folder.rstrip("/") + "/")]
        for item in sorted(to_delete, key=lambda x: x.get("path"), reverse=True):
            if item.get("type") != "blob":
                continue
            path = item.get("path")
            gh.delete_file(owner, repo, path, message=f"Tocket: delete {path}", branch=branch)
            db.add_history("delete_file", f"{owner}/{repo}/{path}")
        print("Folder dan isinya dihapus.")
    except Exception as e:
        print("Gagal menghapus folder:", e)

def settings_flow(db: ConfigDB, gh: Optional[GitHubClient], password: Optional[str]):
    try:
        while True:
            print("\n[Pengaturan]")
            print("[1] Tampilkan Token classic\n[2] Ubah token classic\n[3] Hapus token classic\n[4] Ubah password\n[5] Hapus password\n[6] Kembali\n[7] Buat password")
            c = input("Pilih: ").strip()
            if c == "1":
                cipher = db.get_kv("tok_cipher")
                if not cipher:
                    print("Tidak ada token tersimpan.")
                else:
                    label = db.get_kv("tok_label") or "(tidak ada label)"
                    scopes_db = db.get_kv("tok_scopes") or ""
                    if not password:
                        pwd = prompt_password_hidden("Masukkan password untuk dekripsi token: ")
                        if not pwd or not db.verify_password(pwd):
                            print("Password salah.")
                            continue
                        token = db.load_token_decrypted(pwd)
                    else:
                        token = db.load_token_decrypted(password)
                    if token:
                        masked = mask_token(token)
                        show_full = input(f"Label: {label}\nToken: {masked}\nScopes: {scopes_db}\nTampilkan token penuh? [y/N]: ").strip().lower()
                        if show_full == "y":
                            print("Token:", token)
                    else:
                        print("Gagal mendekripsi token.")
            elif c == "2":
                t = input("Masukkan token classic GitHub (kosong untuk batal): ").strip()
                if not t:
                    continue
                tmp_client = GitHubClient(t)
                info = tmp_client.validate_token()
                if not info:
                    print("Token tidak valid.")
                    continue
                label = input("Nama / catatan token (opsional): ").strip()
                if not password:
                    pwd = prompt_password_hidden("Masukkan password lokal untuk mengenkripsi token: ")
                    if not pwd or not db.verify_password(pwd):
                        print("Password salah. Token tidak disimpan.")
                        continue
                    db.store_token_encrypted(t, pwd)
                else:
                    db.store_token_encrypted(t, password)
                if label:
                    db.set_kv("tok_label", label)
                db.set_kv("tok_scopes", ",".join(info.get("scopes") or []))
                print("Token tersimpan.")
            elif c == "3":
                if input("Yakin ingin menghapus token classic dari storage? [y/N]: ").strip().lower() == "y":
                    db.clear_token()
                    db.delete_kv("tok_label")
                    db.delete_kv("tok_scopes")
                    print("Token dihapus dari DB.")
            elif c == "4":
                if not db.get_kv("pwd_salt"):
                    print("Belum ada password. Gunakan Buat password.")
                    continue
                current = prompt_password_hidden("Masukkan password saat ini: ")
                if not current or not db.verify_password(current):
                    print("Password salah.")
                    continue
                newpwd = prompt_password_hidden("Masukkan password baru: ")
                if not newpwd:
                    print("Dibatalkan.")
                    continue
                token_val = db.load_token_decrypted(current)
                db.set_password(newpwd)
                if token_val:
                    db.store_token_encrypted(token_val, newpwd)
                print("Password diubah dan token dire-enkripsi.")
            elif c == "5":
                if input("Yakin ingin menghapus password lokal? Ini juga akan menghapus token terenkripsi. [y/N]: ").strip().lower() == "y":
                    db.clear_password()
                    db.clear_token()
                    db.delete_kv("tok_label")
                    db.delete_kv("tok_scopes")
                    print("Password dan token dihapus dari storage.")
            elif c == "6":
                return
            elif c == "7":
                if db.get_kv("pwd_salt"):
                    print("Password sudah ada. Gunakan ubah password.")
                    continue
                newpwd = prompt_password_hidden("Buat password baru: ")
                if not newpwd:
                    print("Dibatalkan.")
                    continue
                db.set_password(newpwd)
                print("Password berhasil dibuat.")
            else:
                print("Pilihan tidak valid.")
    except KeyboardInterrupt:
        print("\nDibatalkan.")

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
                print("Token tidak valid saat login awal.")
                gh_client = None
        except Exception as e:
            print("Gagal validasi token saat startup:", e)
            gh_client = None
    else:
        print("Beberapa fitur butuh token. Lanjutkan tanpa token terbatas.")

    try:
        main_menu_loop(db, gh_client, username, pwd)
    finally:
        db.close()

if __name__ == "__main__":
    main()
