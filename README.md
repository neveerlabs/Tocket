# Tocket

Tocket — CLI ringan untuk mengelola GitHub via terminal.  
Desain fokus: cepat, aman (token terenkripsi), dan nyaman dipakai di terminal Linux/Windows.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Rich](https://img.shields.io/badge/Powered_by-Rich-FFD43B?logo=python&logoColor=black)](https://github.com/Textualize/rich)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-brightgreen)]()
[![Stars](https://img.shields.io/github/stars/neveerlabs/Tocket?style=social)]()

---

Keamanan utama
- Token classic GitHub disimpan terenkripsi (AES‑GCM) dengan kunci yang diturunkan dari password lokal (PBKDF2-HMAC-SHA256).
- Kalau kamu lupa password lokal, Tocket tidak bisa memulihkan token — opsi reset tersedia (menghapus token dari storage).
- Jangan menyimpan token di tempat publik. Gunakan fitur label/token saat menambahkan token.

---

Preview singkat
- Navigasi file untuk upload (terminal navigator atau interactive file browser bila prompt_toolkit terpasang)
- Operasi: create repo, list repo, setup repo (upload/delete/list file, change visibility, .gitignore/license), delete repo, pengaturan token/password.

---

Demo / Screenshots

![Menu Utama](screenshots/menu_utama.png)  
![List Repositori](screenshots/list_repos.png)  
![Create Repositori](screenshots/create_repo.png)  
![Upload File](screenshots/upload_file.png)  
![Pengaturan Token](screenshots/pengaturan_token.png)  

*(Tambahkan screenshot asli Anda ke folder /screenshots dan update path di atas untuk tampilan lebih nyata!)*

---

Table of contents
- Overview
- Fitur
- Tech Stack & Framework
- Persyaratan & instalasi
- Cara pakai dasar
- Pengaturan token & password
- Catatan teknis & batasan
- Troubleshooting cepat
- Kontribusi & lisensi

---

Overview
---------
Tocket dibuat untuk developer yang suka mengelola repos GitHub langsung dari terminal tanpa harus berpindah ke browser.  
Tujuan utamanya: workflow yang sederhana (CLI), penyimpanan token aman, dan dukungan operasi file via GitHub Contents API.

Fitur utama
-----------
- Login dengan token classic GitHub (validasi scopes)
- Simpan token terenkripsi di SQLite lokal (~/.tocket/tocket.db)
- Create / List / Delete repository
- Setup repository:
  - Upload file (komit langsung ke branch target)
  - Hapus file
  - List files (git tree)
  - Rename file/folder (create + delete)
  - Hapus folder rekursif (secure)
  - Ubah .gitignore / LICENSE via template GitHub
  - Ubah visibilitas repository (public/private)
- Riwayat aksi (history) disimpan lokal
- User-friendly terminal UI (ASCII header + 2x3 menu)
- Interactive file browser (opsional, butuh prompt_toolkit) — support keyboard + mouse scroll

Tech Stack & Framework
----------------------
| Komponen          | Library / Tool                  | Kegunaan                          |
|-------------------|---------------------------------|-----------------------------------|
| UI & Styling      | [Rich](https://github.com/Textualize/rich) | Table cantik, color, ASCII art, menu interaktif |
| HTTP API          | Requests                        | Interact dengan GitHub REST API   |
| Keamanan Token    | Cryptography                    | Enkripsi AES-GCM + PBKDF2 untuk token GitHub |
| Storage Lokal     | SQLite                          | Simpan token terenkripsi, history, password |
| Optional Prompt   | Prompt Toolkit                  | File browser interaktif           |

Persyaratan & instalasi
-----------------------
- Python 3.13.5 (direkomendasikan)
- Sistem: Linux / Windows (terminal)

Install (dev)
```bash
# buat virtualenv
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate     # Windows (PowerShell)

pip install -r requirements.txt

# jalankan
python3 main.py
