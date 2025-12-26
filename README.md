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

Catatan dependencies penting (termasuk opsi interactive browser):

rich — UI terminal (panel, tabel)
requests — HTTP GitHub API
cryptography — enkripsi token
prompt_toolkit — (opsional, untuk file browser interaktif; included di requirements)

Updated requirements (lihat file requirements.txt di repo).
Cara pakai dasar

Jalankan dari parent folder project (penting — jangan cd tocket lalu python3 main.py).
Karena Python mencari package dari current directory; jalankan dari folder yang berisi folder Tocket.

Pertama kali dijalankan:
Jika belum ada password lokal, kamu bisa lanjut tanpa password.
Kamu akan diminta memasukkan token classic GitHub (opsional). Jika dimasukkan, token divalidasi.
Disarankan membuat password lokal untuk mengenkripsi token agar tersimpan aman.

Menu utama (2x3):
[1] Create Repositori
[2] List Repositori
[3] Setup Repositori
[4] Delete Repositori
[5] Pengaturan
[6] Keluar

Setup → Upload file:
Pilih file via navigator (keyboard atau interactive browser bila tersedia).
Masukkan target repo (format: https://github.com/{owner}/{repo}/ atau owner/repo).
Tocket akan mendeteksi default branch (repo metadata) atau fallback ke main/master.
File >100MB akan ditolak (GitHub Contents API limit).


Pengaturan token & password

Menambah token:
Masukkan token ketika diminta atau lewat menu Pengaturan → Ubah token classic.
Saat menyimpan, berikan label (nama) token — berguna untuk identifikasi.
Tocket tidak bisa membaca nama token dari GitHub (API tidak sediakan), jadi label disimpan lokal.

Ganti password:
Password disimpan hanya sebagai verifier (PBKDF2). Jika ganti password, token akan didekripsi dan dienkripsi ulang menggunakan password baru.

Reset / lupa password:
Jika lupa password, opsi yang tersedia: hapus password & token dari DB (tidak ada recovery).


Catatan teknis & batasan

Default branch:
Tocket mencoba baca default_branch dari metadata repo. Jika tidak tersedia, fallback ke main → master, lalu minta input dari user.

File size:
Upload via GitHub Contents API — file >100MB tidak didukung.

Otentikasi & scopes:
Untuk operasi repo/private, token harus punya scope repo.
Untuk delete repo/modify visibility, token harus memiliki izin sesuai (owner/collaborator/organization perms).

Penyimpanan lokal:
DB: ~/.tocket/tocket.db
Jangan commit atau bagikan file DB.

Mode interactive:
Jika prompt_toolkit terpasang, file browser akan menyediakan scroll & mouse support. Jika tidak, fallback ke navigator berdasarkan angka/directory listing.


Troubleshooting cepat

Error "No module named tocket.main" or script failing if run from inside tocket/:
Pastikan working directory adalah parent dari folder tocket.
Jalankan python3 main.py dari project root.

List Repositori kosong:
Pastikan token valid dan punya scope repo. Tes di REPL:Pythonfrom tocket.github_api import GitHubClient
g = GitHubClient("PASTE_TOKEN")
print(g.validate_token())
print(len(g.list_repos()))

Upload gagal:
Periksa ukuran file; cek branch target; pastikan token punya write permission.

Kalau ada exception:
Salin full traceback dan kirim. Log history ada di DB (tabel history).


Contoh alur singkat

Simpan token:

Bashpython3 main.py
# Pilih menu Pengaturan -> Ubah token classic -> isi token -> simpan (buat password saat diminta)

Buat repo & upload file:

text[1] Create Repositori -> isi nama
[3] Setup Repositori -> pilih repo -> Upload file -> pilih file -> masukkan path repo (owner/repo)
Kontribusi
Saya terbuka untuk perbaikan dan fitur baru. Kalau mau submit PR:

Fork repo → buat branch fitur → buat PR ke main.
Tetap jaga keamanan token dan jangan masukkan data sensitif di PR.
Apabila ada saran tambahan/perbaikan dari anda, silahkan beri tahu saya, karena penting bagi saya untuk mengetahuinya.

Lisensi
MIT — bebas dipakai, dimodifikasi, dibagikan. Lihat file LICENSE untuk rincian.
Terima kasih telah menggunakan Tocket! Semoga tool ini mempermudah workflow GitHub Anda sehari-hari. Happy coding dan tetap semangat berkarya!
