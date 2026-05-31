# Instruksi Regenerasi Database Kewajaran

## File yang Dibuat
- **`complete_database_regeneration.sql`** - Script lengkap untuk regenerasi database

## Cara Menjalankan

### Opsi 1: Melalui phpMyAdmin
1. Buka http://localhost/phpmyadmin/index.php?route=/server/databases
2. Pilih database "kewajaran" (jika ada)
3. Klik tab "Import"
4. Pilih file `complete_database_regeneration.sql`
5. Klik "Go"

### Opsi 2: Melalui MySQL Command Line
```bash
mysql -u root -p kewajaran < complete_database_regeneration.sql
```

### Opsi 3: Melalui MySQL Workbench
1. Buka MySQL Workbench
2. Connect ke server MySQL
3. Pilih database "kewajaran"
4. File > Run SQL Script
5. Pilih `complete_database_regeneration.sql`
6. Run

## Isi Database

### Tabel Utama
- **pemdas** - 6 data Pemerintah Daerah DIY
- **skpds** - Contoh data SKPD untuk Provinsi, Kabupaten, dan Kota
- **nomenklaturs** - Contoh data nomenklatur program & kegiatan
- **usulan_anggarans** - Contoh data usulan anggaran dengan analisis
- **realisasi_anggarans** - Contoh data realisasi anggaran
- **users** - 4 user system (admin, evaluator, pengusul)

### Tabel Laravel
- **migrations** - Record migrasi Laravel
- **password_reset_tokens** - Token reset password
- **sessions** - Session management

### Fitur Tambahan
- **Views** - Untuk analisis ringkasan
- **Stored Procedures** - Proses analisis otomatis
- **Triggers** - Audit trail
- **Indexes** - Optimasi performa

## User Default

| Email | Password | Role | Akses |
|-------|----------|------|-------|
| admin@kewajaran.id | password | admin | Semua |
| evaluator@kewajaran.id | password | evaluator | Evaluasi |
| bantul@kewajaran.id | password | pengusul | Kab. Bantul |
| yogya@kewajaran.id | password | pengusul | Kota Yogyakarta |

## Struktur Database

### Master Data
- **pemdas** - Pemerintah Daerah (Provinsi/Kabupaten/Kota)
- **skpds** - Perangkat Daerah (SKPD)
- **nomenklaturs** - Program, Kegiatan, Sub-kegiatan

### Transaksi
- **usulan_anggarans** - Data usulan anggaran dengan 5 dimensi analisis
- **realisasi_anggarans** - Data realisasi anggaran

### Analisis
- 5 Dimensi Analisis Kewajaran:
  1. Dimensi 1: Historis (skor_dimensi_1)
  2. Dimensi 2: Regional (skor_dimensi_2)
  3. Dimensi 3: Kinerja (skor_dimensi_3)
  4. Dimensi 4: Perencanaan (skor_dimensi_4)
  5. Dimensi 5: Statistik (skor_dimensi_5)

### Status Kewajaran
- **Wajar** - Skor IKP ≥ 90
- **Cukup Wajar** - Skor IKP 80-89
- **Perlu Evaluasi** - Skor IKP 70-79
- **Tidak Wajar** - Skor IKP < 70

## Validasi

Setelah regenerasi, jalankan query berikut untuk validasi:

```sql
-- Cek jumlah data per tabel
SELECT 'pemdas' as tabel, COUNT(*) as jumlah FROM pemdas
UNION ALL
SELECT 'skpds', COUNT(*) FROM skpds
UNION ALL
SELECT 'nomenklaturs', COUNT(*) FROM nomenklaturs
UNION ALL
SELECT 'usulan_anggarans', COUNT(*) FROM usulan_anggarans
UNION ALL
SELECT 'realisasi_anggarans', COUNT(*) FROM realisasi_anggarans
UNION ALL
SELECT 'users', COUNT(*) FROM users;

-- Cek analisis yang sudah dilakukan
SELECT tahun, kodepemda, COUNT(*) as jumlah_analisis, AVG(skor_ikp) as rata_skor
FROM usulan_anggarans 
WHERE skor_ikp IS NOT NULL
GROUP BY tahun, kodepemda;

-- Cek status kewajaran
SELECT status_kewajaran, COUNT(*) as jumlah
FROM usulan_anggarans 
WHERE status_kewajaran IS NOT NULL
GROUP BY status_kewajaran;
```

## Catatan Penting

1. **Backup** - Pastikan tidak ada data penting sebelum menjalankan script
2. **Permissions** - User MySQL harus memiliki hak CREATE, DROP, INSERT, UPDATE
3. **Character Set** - Database menggunakan utf8mb4 untuk support Unicode
4. **Foreign Keys** - Semua relasi sudah di-setup dengan proper constraints
5. **Indexes** - Index sudah dioptimasi untuk performa query analisis

## Troubleshooting

### Error: Database doesn't exist
- Buat database kosong bernama "kewajaran" terlebih dahulu
- Atau jalankan script dengan user yang memiliki hak CREATE DATABASE

### Error: Foreign key constraint
- Pastikan data master (pemdas, skpds, nomenklaturs) di-insert sebelum data transaksi
- Script sudah diatur dengan urutan yang benar

### Error: Permission denied
- Jalankan sebagai root atau user dengan privileges lengkap
- Check GRANT privileges untuk user MySQL

## Hubungi Support

Jika mengalami masalah:
1. Check error message di MySQL log
2. Verify MySQL version (recommended: 5.7+ atau 8.0+)
3. Pastikan storage engine InnoDB aktif
