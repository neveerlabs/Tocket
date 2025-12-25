```
# Tocket

Tocket — CLI tool untuk mengelola GitHub (MVP).

Fitur utama (versi awal):
- Login dengan password lokal (tersimpan aman di SQLite).
- Penyimpanan token GitHub classic terenkripsi.
- Create / List / Delete repository.
- Setup repository: Upload file, Delete file, List files, Change visibility.
- .gitignore & License templates diambil live dari GitHub API.
- Interaktif, cross-platform (Linux & Windows).

Instalasi (development)
- Membutuhkan Python 3.13.5
- Buat virtualenv, lalu:
  pip install -r requirements.txt

Menjalankan
  python -m tocket

Lokasi DB
  - ~/.tocket/tocket.db  (Linux/macOS)
  - %USERPROFILE%\.tocket\tocket.db (Windows)

Keamanan
- Token disimpan terenkripsi menggunakan AES-GCM dengan key yang diturunkan dari password user.
- Jika lupa password, gunakan opsi Reset (menghapus token & password dari DB).

Lisensi: MIT
```
