# Tocket

**Tocket** adalah *command-line interface* modern, aman, dan terstruktur untuk mengelola repositori GitHub langsung dari terminal.  
Dirancang untuk **Developer** yang hidup di terminal, males buka browser, tapi tetap mengutamakan **keamanan**, **kecepatan**, dan **alur kerja yang bersih**.

<p align="center">
  <img src="https://github.com/nflora-ux/Tocket/raw/17066362fb116c4388595d54b8e92f6e94c900fd/Screenshot/Screenshot.png" alt="Main Menu Tocket" width="720">
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14%2B-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green" />
  <img src="https://img.shields.io/badge/CLI-Terminal--Native-black" />
  <img src="https://img.shields.io/github/stars/nflora-ux/Tocket?style=social" />
</p>

---

## Kenapa harus Tocket?

GitHub memiliki antarmuka web yang kuat, tetapi tidak dirancang untuk alur kerja cepat di terminal.  
Tocket hadir untuk menjawab kebutuhan sederhana:

- **Bekerja tanpa keluar terminal** – semua operasi GitHub dari satu tempat.
- **Token tidak pernah disimpan dalam bentuk teks biasa** – keamanan adalah prioritas.
- **Antarmuka informatif namun tidak berlebihan** – fokus pada informasi yang penting.
- **Alur kerja yang jelas dan dapat diprediksi** – setiap langkah terstruktur.

Tocket bukan sekadar pembungkus API. Ini adalah alat yang memiliki pendapat tentang bagaimana seharusnya *workflow* GitHub di terminal.

---

## Fitur Utama

### Manajemen Repositori
- Membuat repositori baru dengan opsi README, `.gitignore`, dan lisensi.
- Melihat daftar repositori (milik sendiri atau publik milik pengguna lain).
- Menghapus repositori.
- Mengubah visibilitas (publik ↔ privat).

### Operasi Berkas (GitHub Contents API)
- Mengunggah satu berkas atau seluruh isi folder (dengan subfolder atau tanpa subfolder).
- Memperbarui konten berkas yang sudah ada di repositori dengan konten dari berkas lokal.
- Menghapus berkas.
- Mengganti nama berkas atau folder (termasuk memindahkan isi folder).
- Menampilkan pohon direktori repositori.
- Menghapus folder beserta seluruh isinya (rekursif).
– Jalankan workflow dari repositori langsung via Tocket.

### Keamanan Prioritas Utama
- Token GitHub **dienkripsi menggunakan AES‑GCM**.
- Kunci enkripsi diturunkan dari kata sandi lokal melalui **PBKDF2‑HMAC‑SHA256**.
- Tidak ada token dalam bentuk teks biasa yang disimpan di disk.
- **Tidak ada pemulihan kata sandi palsu** – jika lupa kata sandi, token tidak dapat dipulihkan (keputusan desain untuk keamanan maksimal).

### Pengalaman Pengguna & CLI
- Antarmuka terminal berbasis **Rich** dengan warna dan tata letak yang nyaman.
- Menu utama dengan format dua kolom yang konsisten.
- Navigasi folder interaktif untuk memilih berkas lokal.
- *Progress bar* saat mengunggah banyak berkas.
- *Cache* daftar repositori (5 menit) untuk mempercepat akses berulang.
- Pemilihan cabang (*branch*) sebelum melakukan operasi berkas.

---

## Persyaratan Sistem

- Python **3.14 atau lebih baru** (direkomendasikan).
- Sistem operasi: Linux, Windows (Terminal / CMD), MacOS.

### Dependensi Utama
| Paket | Keterangan |
|-------|------------|
| `rich` | Tampilan terminal |
| `requests` | Komunikasi dengan API GitHub |
| `cryptography` | Enkripsi token |
| `inquirer` | Dialog interaktif |
| `prompt_toolkit` | (Opsional) |

---

## Instalasi

```bash
# Clone repositori
git clone https://github.com/neveerlabs/Tocket.git
cd Tocket

## cek versi Python
python3 --version

# Buat virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate    # Windows

# Pasang dependensi
pip install -r requirements.txt

# Jalankan aplikasi
python3 main.py
```

---

## Cara mendapatkan Token Classic Github:
  1. Buka GitHub Settings > Tokens (classic).
  2. Klik Generate new token (classic).
  3. Beri nama token, misalnya "Tocket".
  4. Pilih scopes yang diperlukan:
  - `repo` – akses penuh ke repositori (termasuk privat).
  - `delete_repo` – jika ingin menghapus repositori.
  - `workflow` – jika ingin memicu GitHub Actions.
  - `admin:public_key` – jika diperlukan untuk mengelola kunci SSH.
  5. Klik Generate token.
  6. Salin token yang muncul.

---

## Mulai cepat:
Saat pertama kali menjalankan Tocket:
  1. Anda akan diminta kata sandi lokal (opsional, tetapi sangat disarankan untuk keamanan token).
  2. Masukkan token classic GitHub.
  3. Token akan divalidasi dan dienkripsi secara otomatis.

## Menu Utama
```bash
Buat Repositori       Hapus Repositori
Lihat Repositori      Pengaturan
Setup Repositori      Keluar
```
> *Gunakan tombol panah untuk memilih, lalu Enter untuk konfirmasi.*

---

## Model Keamanan Token & Kata Sandi
- Token tidak pernah disimpan dalam bentuk teks biasa.
- Kata sandi hanya digunakan untuk menurunkan kunci enkripsi, tidak disimpan langsung.
- Lupa kata sandi = token tidak dapat dipulihkan. Ini adalah keputusan desain untuk keamanan maksimal.
- Untuk mereset, hapus token melalui menu Pengaturan dan masukkan token baru.

---

## Lokasi Basis Data
```bash
~/.tocket/tocket.db
```
> **Peringatan**: *Jangan pernah commit berkas ini ke repositori publik!*
---

## Panduan Penggunaan

## 1. Membuat Repositori Baru
  - Pilih opsi `Buat repositori` di menu utama.
  - Masukkan nama repositori, deskripsi, dan tentukan visibilitas (publik/privat).
  - Anda dapat menambahkan README, memilih template .gitignore, dan template lisensi.
  - Setelah konfirmasi, repositori akan dibuat dan ditampilkan URL-nya.

## 2. Melihat Daftar Repositori
  - Pilih opsi `List Repositori`.
  - Tocket akan menampilkan daftar repositori dalam bentuk tabel dengan informasi visibilitas dan branch default.
  - Anda juga dapat mencari repositori berdasarkan nama (opsional).

## 3. Setup Repositori (Manajemen Berkas)
  - Pilih opsi `Setup Repositori`, lalu masukkan nama repositori yang ingin dikelola.
  - Anda dapat memilih branch yang akan digunakan (default: cabang utama).
  - Submenu akan muncul dengan berbagai opsi:
    - Upload File
      - Navigasi folder lokal menggunakan panah untuk scroll.
      - Ketik `all` untuk mengunggah semua file di folder saat ini (tanpa subfolder).
      - Ketik `subfolder` untuk mengunggah seluruh folder beserta subfoldernya (rekursif).
      - Tentukan path tujuan di repositori (kosong untuk root).
    - Hapus File
      - Masukkan path file di repositori yang akan dihapus.
      - Konfirmasi penghapusan.
    - Rename File/Folder
      - Masukkan path sumber dan path tujuan.
      - Sistem akan memindahkan semua file di dalam folder jika diperlukan.
    - List File
      - Menampilkan pohon direktori repositori dengan tipe dan ukuran file.
    - Update File
      - Pilih file dari repositori yang akan diperbarui.
      - Pilih file lokal sebagai sumber konten baru.
      - Konten file repositori akan diganti dengan konten file lokal (nama file tetap).
    - Ubah Visibilitas
      - Ubah repositori menjadi publik atau privat.
    - Ubah .gitignore
      - Pilih template .gitignore dari daftar, atau masukkan konten kustom.
      - File .gitignore di repositori akan diperbarui.
    - Ubah Lisensi
      - Pilih template lisensi dari daftar, atau masukkan konten kustom.
      - File LICENSE akan diperbarui.
    - Hapus Folder
      - Masukkan path folder yang akan dihapus.
      - Seluruh isi folder akan dihapus secara rekursif.
    - Trigger GitHub Actions
      - Menampilkan daftar workflow yang tersedia di repositori (file .yml di `.github/workflows/`).
      - Pilih workflow yang ingin dijalankan.
      - Tentukan branch target (default: branch yang sedang digunakan).
      - Konfirmasi untuk memicu workflow.
      - Setelah berhasil, Tocket akan menampilkan pesan sukses dan memberikan tautan ke halaman Actions repositori.
## 4. Menghapus Repositori
  - Pilih opsi `Hapus Repositori`, masukkan nama repositori, dan konfirmasi.
> *Tindakan ini tidak dapat dibatalkan!*

## 5. Pengaturan
  - Kelola token dan kata sandi lokal:
    - Tampilkan Token – menampilkan token dalam bentuk tersamar.
    - Ubah Token – mengganti token yang tersimpan.
    - Hapus Token – menghapus token dari basis data.
    - Buat/Ubah/Hapus Kata Sandi – mengelola kata sandi lokal.
---

## Batasan Teknis
- Unggah berkas >100 MB tidak didukung karena batasan GitHub Contents API.
- Mengganti nama folder dilakukan dengan membuat ulang berkas-berkas di dalamnya, lalu menghapus yang lama.
- Izin operasi bergantung pada scopes token dan peran pengguna di repositori.

## Pemecahan Masalah
`ModuleNotFoundError: No module named 'tocket'`
Pastikan Anda menjalankan dari direktori yang benar:
```bash
Tocket/
  ├─ tocket/
  └─ main.py
```

## Daftar repositori kosong
- Token mungkin tidak valid atau scopes kurang (repo diperlukan untuk melihat repositori privat).
- Perbarui token di menu Pengaturan.

## Unggah berkas gagal
- Periksa ukuran berkas (maksimal 100 MB).
- Pastikan branch yang dituju benar.
- Pastikan token memiliki izin yang cukup (`repo`, `delete_repo`, `admin:public_key`).

## Token tidak dapat didekripsi
- Kata sandi yang dimasukkan mungkin salah.
- Jika benar-benar lupa, hapus token melalui menu Pengaturan dan masukkan token baru.

**Gagal memicu workflow**  
- Pastikan token memiliki scope `workflow`.  
- Pastikan file workflow mendukung `workflow_dispatch` (biasanya ada deklarasi `on: workflow_dispatch` di dalam file YAML).  
- Periksa kembali branch target yang dimasukkan.
---

## Kontribusi
Kami sangat menerima kontribusi melalui pull request.
**Alur singkat**:
- Fork repositori ini.
- Buat cabang baru: `feat/*` atau `fix/*`.
- Tulis kode dengan jelas.
- Kirimkan pull request ke branch `main`.
---

## Lisensi
Proyek ini dilisensikan di bawah **MIT License**.
Anda bebas menggunakan, memodifikasi, dan mendistribusikannya kembali.

---

<p align="left" style="float: left; width: 60%;">
  <a href="https://instagram.com/neveerlabs"><img src="https://img.shields.io/badge/Instagram-E4405F?style=flat-square&logo=instagram&logoColor=white" alt="Instagram"></a>
  <a href="https://github.com/neveerlabs"><img src="https://img.shields.io/badge/GitHub-100000?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="https://t.me/Neverlabs"><img src="https://img.shields.io/badge/Telegram-2CA5E0?style=flat-square&logo=telegram&logoColor=white" alt="Telegram"></a>
  <a href="mailto:userlinuxorg@gmail.com"><img src="https://img.shields.io/badge/Email-D14836?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square&logo=open-source-initiative&logoColor=white" alt="MIT License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.14%2B-blue?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
</p>
<p align="center" style="float: right; width: 40%;">
  <b>© 2026 Neverlabs | All rights reserved</b>
</p>
<br clear="all">
