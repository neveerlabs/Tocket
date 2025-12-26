# Tocket

> **Tocket** — Fast, secure, and friendly CLI for managing GitHub from your terminal.

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue?logo=python\&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-brightgreen)]()
[![Stars](https://img.shields.io/github/stars/neveerlabs/Tocket?style=social)]()

---

## Ringkasan singkat

Tocket adalah CLI ringan untuk mengelola repository GitHub langsung dari terminal. Dirancang untuk developer yang suka bekerja cepat tanpa bolak-balik ke browser — dengan fokus pada kecepatan, keamanan token, dan pengalaman terminal yang nyaman.

Fitur utama: operasi repo (create/list/delete), penuh dukungan upload/download file via GitHub Contents API, enkripsi token AES‑GCM di local DB, dan opsi interactive file browser bila `prompt_toolkit` tersedia.

---

## Daftar isi

* [Fitur](#fitur)
* [Screenshot & panduan gambar](#screenshot--panduan-gambar)
* [Persyaratan & Instalasi](#persyaratan--instalasi)
* [Quickstart (penggunaan singkat)](#quickstart-penggunaan-singkat)
* [Konfigurasi & Token Management](#konfigurasi--token-management)
* [Arsitektur & Keamanan](#arsitektur--keamanan)
* [Batasan & Catatan Teknis](#batasan--catatan-teknis)
* [Troubleshooting Cepat](#troubleshooting-cepat)
* [Kontribusi](#kontribusi)
* [Changelog singkat](#changelog-singkat)
* [Lisensi](#lisensi)

---

## Fitur

* Login dengan GitHub classic token (validasi scopes otomatis).
* Token disimpan terenkripsi (AES‑GCM) di SQLite lokal (`~/.tocket/tocket.db`).
* Create / List / Delete repository.
* Setup repository: upload file (commit ke branch target), delete file, list files, rename (create+delete), recursive delete folder.
* Ubah `.gitignore` / `LICENSE` via template GitHub.
* Ubah visibilitas repo (public/private) bila permission terpenuhi.
* Riwayat aksi (history) disimpan lokal untuk auditing dan troubleshooting.
* UI terminal yang user-friendly (Rich) dan optional interactive file browser (prompt_toolkit).
* Validasi otomatis untuk ukuran file (GitHub Contents API limit ~100MB).

---

## Screenshot & panduan gambar

Letakkan screenshot di folder `screenshots/` pada repo.

**Rekomendasi file & ukuran**

* `screenshots/menu_utama.png` — 1280×720 (landscape), PNG/JPEG, caption: "Menu Utama".
* `screenshots/list_repos.png` — 1280×720, caption: "List Repository".
* `screenshots/create_repo.png` — 1280×720, caption: "Create Repository".
* `screenshots/upload_file.png` — 1280×720, caption: "Upload File".
* `screenshots/settings_token.png` — 1280×720, caption: "Pengaturan Token".

**Aturan penamaan & alt text**

* Gunakan nama yang konsisten seperti `screenshots/<slug>.<ext>`.
* Beri alt text pada markdown: `![Menu Utama](screenshots/menu_utama.png "Menu Utama — Tocket")`.
* Prefer PNG untuk UI screenshots; gunakan JPEG untuk foto besar.

**Contoh Markdown memasukkan gambar**

```markdown
![Menu Utama](screenshots/menu_utama.png "Menu Utama — Tocket")
```

---

## Persyaratan & instalasi

**Dianjurkan:** Python 3.13.5 (atau 3.13+).

Sistem: Linux / Windows (terminal). WSL direkomendasikan untuk pengguna Windows.

**Install (development)**

```bash
# buat virtualenv
python3 -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\Activate    # Windows (PowerShell)

pip install -r requirements.txt

# jalankan dari root project (parent folder yang berisi folder tocket/)
python3 main.py
```

**Dependencies penting**

* `rich` — UI & styling terminal
* `requests` — HTTP client
* `cryptography` — enkripsi AES‑GCM + PBKDF2
* `prompt_toolkit` — (opsional) interactive file browser

Lihat `requirements.txt` untuk versi spesifik.

---

## Quickstart (penggunaan singkat)

**Catatan:** jalankan dari parent folder project (bukan dari dalam `tocket/`).

1. Jalankan aplikasi

```bash
python3 main.py
```

2. Menu utama (2x3):

```
[1] Create Repository
[2] List Repository
[3] Setup Repository
[4] Delete Repository
[5] Pengaturan
[6] Keluar
```

3. Setup → Upload file

* Pilih file via navigator (keyboard) atau interactive browser bila tersedia.
* Masukkan target repo (format: `owner/repo` atau `https://github.com/owner/repo`).
* Tocket mendeteksi default branch atau fallback ke `main`/`master`.
* File >100MB akan ditolak (GitHub Contents API limit).

---

## Konfigurasi & Token Management

**Lokasi DB:** `~/.tocket/tocket.db` (SQLite)

**Menambah token**

* Masuk ke `Pengaturan` → `Ubah token classic` → masukkan token.
* Saat menyimpan, tambahkan label (nama) token untuk identifikasi.
* Token akan dienkripsi menggunakan kunci yang diturunkan dari password lokal.

**Password lokal**

* Password hanya digunakan untuk menurunkan kunci (PBKDF2) dan untuk memverifikasi.
* Jika lupa password: opsi reset tersedia yang akan menghapus token dari DB (tidak ada recovery).

**Ganti password**

* Sistem akan mendekripsi token dan mengenkripsinya ulang menggunakan password baru.

**Praktik terbaik**

* Jangan menyimpan token di repo, paste, atau tempat publik.
* Gunakan token dengan scope minimal yang diperlukan (mis. `repo` untuk operasi repository penuh).

---

## Arsitektur & Keamanan

**Enkripsi token**

* AES‑GCM digunakan untuk enkripsi token (Cryptography.io).
* Kunci enkripsi diturunkan dari password lokal menggunakan PBKDF2‑HMAC‑SHA256 (salt unik per instalasi).
* Verifier disimpan untuk validasi password tanpa menyimpan password plaintext.

**Penyimpanan**

* Semua data operasional disimpan di SQLite lokal (`~/.tocket/tocket.db`).
* Riwayat (history) menyimpan metadata aksi, bukan token dalam bentuk plaintext.

**Ketidakmampuan recovery**

* Jika password hilang, token tidak bisa dipulihkan. Reset = hapus token dari DB.

---

## Batasan & catatan teknis

* GitHub Contents API tidak mendukung upload file >100MB.
* Perubahan besar pada repo (rename repo, transfer ownership) tidak sepenuhnya otomatis di-handle.
* Akses yang diperlukan tergantung pada operasi (mis. `repo` scope untuk private repos, permission owner/collab untuk delete/visibility change).
* Default branch detection: baca `default_branch` dari metadata; fallback `main` → `master`.

---

## Troubleshooting cepat

**Error: No module named tocket.main**

* Jalankan dari project root (parent folder proyek), bukan dari dalam `tocket/`.

**List repository kosong**

* Pastikan token valid dan punya scope `repo`.
* Tes di REPL:

```python
from tocket.github_api import GitHubClient
g = GitHubClient("PASTE_TOKEN")
print(g.validate_token())
print(len(g.list_repos()))
```

**Upload gagal**

* Pastikan ukuran file < 100MB.
* Pastikan token punya write permission.
* Periksa target branch dan path.

**Dapatkan error atau exception**

* Salin full traceback. Riwayat log disimpan di DB (`history` table).

---

## Contoh alur singkat

**Simpan token**

```bash
python3 main.py
# Pilih menu Pengaturan -> Ubah token classic -> isi token -> simpan (buat password saat diminta)
```

**Buat repo & upload file**

1. Create Repository → isi nama → selesai
2. Setup Repository → pilih repo → Upload File → pilih file → masukkan path repo (`owner/repo`)

---

## Kontribusi

Terima kasih jika ingin kontribusi! Jalur singkat:

1. Fork repo
2. Buat branch fitur `feat/<singkat>-description` atau `fix/<issue>`
3. Sertakan unit test bila memungkinkan
4. Submit PR ke `main` dengan deskripsi jelas dan alasan perubahan

**Catatan contributor**

* Jangan commit file DB atau token.
* Tulis perubahan security-sensitive di PR dan jelaskan mitigasi.

---

## Changelog singkat

* `1.0.0` — Initial stable release: CLI core, token encryption, file operations, interactive browser optional.

---

## FAQ cepat

**Q: Apa beda token classic dan OAuth App?**
A: Tocket memakai GitHub classic personal access token untuk kemudahan CLI. OAuth flow mungkin diperkenalkan di versi selanjutnya.

**Q: Bisa digunakan untuk organisasi?**
A: Ya, asalkan token punya permission/role sesuai untuk org repo (owner/collaborator atau org token dengan scope yang tepat).

---

## Lisensi

Tocket dilisensikan di bawah MIT License. Lihat file `LICENSE` untuk detail.

---

Terima kasih sudah menggunakan Tocket — semoga mempermudah workflow GitHub kamu. Kalau mau aku tambahin contoh `dotfiles` config, alias bash/zsh, auto-completion, atau GitHub Actions integrasi untuk release otomatis, kabarin di PR atau issue.
