# 🚀 Panduan Menjalankan Aplikasi Platform Kewajaran Penganggaran

## 📋 Prerequisites

### Software yang Diperlukan:
1. **PHP 8.1+** (dengan extensions: mysql, mbstring, xml, bcmath, json)
2. **MySQL 8.0+** atau MariaDB 10.3+
3. **Composer 2.0+**
4. **Python 3.8+** (untuk import data)
5. **Git** (optional)

### Verifikasi Instalasi:
```bash
# Cek PHP
php --version

# Cek MySQL
mysql --version

# Cek Composer
composer --version

# Cek Python
python --version
```

---

## 🗄️ Step 1: Setup Database

### 1.1 Buat Database MySQL
```sql
-- Login ke MySQL
mysql -u root -p

-- Buat database
CREATE DATABASE kewajaran CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Buat user (optional)
CREATE USER 'kewajaran_user'@'localhost' IDENTIFIED BY 'password_strong';
GRANT ALL PRIVILEGES ON kewajaran.* TO 'kewajaran_user'@'localhost';
FLUSH PRIVILEGES;
```

### 1.2 Import Data Master
```bash
# Navigate ke project folder
cd "d:/KEMENDAGRI/PUSDATIN/platform kewajaran"

# Import struktur database
mysql -u root -p kewajaran < database_structure.sql

# Install Python dependencies
pip install -r requirements.txt

# Import data CSV (97K+ records)
python run_import.py
```

### 1.3 Verifikasi Data Import
```bash
# Validasi data import
python validate_data.py
```

**Expected Output:**
```
DATABASE RECORD COUNTS
==================================================
pemdas                   : 6 records
skpds                    : 583 records
nomenklaturs             : 5,415 records
usulan_anggarans         : 97,562 records
realisasi_anggarans      : 42,709 records
users                    : 0 records
```

---

## 🐘 Step 2: Setup Laravel Project

### 2.1 Install Laravel Dependencies
```bash
# Navigate ke Laravel folder
cd laravel

# Install Composer dependencies
composer install --no-dev --optimize-autoloader

# Generate application key
php artisan key:generate

# Cache configuration untuk production
php artisan config:cache
php artisan route:cache
```

### 2.2 Konfigurasi Environment
```bash
# Copy file environment
copy .env.example .env

# Edit .env file (buka dengan text editor)
notepad .env
```

**Konfigurasi .env:**
```env
APP_NAME="Platform Kewajaran Penganggaran"
APP_ENV=local
APP_KEY=base64:generated_key_here
APP_DEBUG=true

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=kewajaran
DB_USERNAME=root
DB_PASSWORD=your_mysql_password
```

### 2.3 Run Migration
```bash
# Jalankan migration untuk menambah kolom analisis
php artisan migrate

# Verifikasi migration berhasil
php artisan migrate:status
```

---

## 🚀 Step 3: Menjalankan Aplikasi

### 3.1 Start Development Server
```bash
# Di dalam folder laravel
php artisan serve --host=0.0.0.0 --port=8000

# Atau gunakan port lain jika 8000 busy
php artisan serve --host=0.0.0.0 --port=8001
```

**Server akan running di:** `http://localhost:8000`

### 3.2 Test Health Check
```bash
# Test API health
curl http://localhost:8000/api/health

# Expected response:
{
    "status": "OK",
    "timestamp": "2024-05-04T12:00:00.000000Z",
    "version": "1.0.0"
}
```

---

## 📊 Step 4: Trigger Analisis Kewajaran

### 4.1 Run Batch Analysis (Recommended)
```bash
# Trigger analisis untuk tahun 2024
curl -X POST "http://localhost:8000/api/dashboard/trigger-analysis" \
  -H "Content-Type: application/json" \
  -d '{"tahun": 2024, "chunk_size": 1000}'
```

### 4.2 Atau Run Manual dari PHP Artisan
```bash
# Buat custom command (jika diperlukan)
php artisan make:command RunAnalysisCommand

# Edit file command dan jalankan
php artisan analysis:run --tahun=2024
```

---

## 🧪 Step 5: Testing API Endpoints

### 5.1 Get Ringkasan Dashboard
```bash
curl -X GET "http://localhost:8000/api/dashboard/ringkasan?tahun=2024" \
  -H "Accept: application/json"
```

### 5.2 Get Data Pemda
```bash
curl -X GET "http://localhost:8000/api/dashboard/pemdas" \
  -H "Accept: application/json"
```

### 5.3 Get Tahun Tersedia
```bash
curl -X GET "http://localhost:8000/api/dashboard/tahun-tersedia" \
  -H "Accept: application/json"
```

### 5.4 Get Top Anomali
```bash
curl -X GET "http://localhost:8000/api/dashboard/top-anomali?tahun=2024&limit=10" \
  -H "Accept: application/json"
```

---

## 🔧 Troubleshooting

### Common Issues & Solutions:

#### 1. **Memory Limit Error**
```bash
# Increase PHP memory limit
php -d memory_limit=2G artisan serve

# Atau edit php.ini
memory_limit = 2G
```

#### 2. **Database Connection Error**
```bash
# Check MySQL service
# Windows:
net start mysql

# Linux/Mac:
sudo systemctl start mysql
sudo systemctl status mysql
```

#### 3. **Composer Install Error**
```bash
# Clear composer cache
composer clear-cache

# Install without dev dependencies
composer install --no-dev --optimize-autoloader
```

#### 4. **Migration Error**
```bash
# Reset migration (WARNING: akan delete data)
php artisan migrate:fresh

# Atau rollback specific migration
php artisan migrate:rollback --step=1
```

#### 5. **Python Import Error**
```bash
# Install missing dependencies
pip install pandas mysql-connector-python numpy

# Check Python version
python --version  # Should be 3.8+
```

---

## 📱 Monitoring & Logs

### 1. Laravel Logs
```bash
# View Laravel logs
tail -f storage/logs/laravel.log

# Clear logs
php artisan log:clear
```

### 2. Database Query Log
```bash
# Enable query logging (development only)
php artisan tinker
DB::enableQueryLog();
// Run your query
DB::getQueryLog();
```

### 3. Performance Monitoring
```bash
# Check memory usage
php artisan tinker
memory_get_usage(true);
memory_get_peak_usage(true);
```

---

## 🎯 Quick Start Commands

### One-Liner Setup (Windows):
```cmd
cd "d:\KEMENDAGRI\PUSDATIN\platform kewajaran" && ^
mysql -u root -p kewajaran < database_structure.sql && ^
pip install -r requirements.txt && ^
python run_import.py && ^
cd laravel && ^
composer install && ^
php artisan key:generate && ^
php artisan migrate && ^
php artisan serve --port=8000
```

### One-Liner Setup (Linux/Mac):
```bash
cd "/d/KEMENDAGRI/PUSDATIN/platform kewajaran" && \
mysql -u root -p kewajaran < database_structure.sql && \
pip install -r requirements.txt && \
python run_import.py && \
cd laravel && \
composer install && \
php artisan key:generate && \
php artisan migrate && \
php artisan serve --port=8000
```

---

## 📊 Verifikasi Instalasi

### Test Semua Fitur:
```bash
# 1. Health check
curl http://localhost:8000/api/health

# 2. Dashboard data
curl http://localhost:8000/api/dashboard/ringkasan

# 3. Trigger analysis
curl -X POST http://localhost:8000/api/dashboard/trigger-analysis \
  -H "Content-Type: application/json" \
  -d '{"tahun": 2024}'

# 4. Export results
curl http://localhost:8000/api/dashboard/export?tahun=2024
```

### Expected Results:
- ✅ Health check returns "OK"
- ✅ Dashboard shows 97K+ records
- ✅ Analysis completes without errors
- ✅ Export returns structured data

---

## 🚀 Production Deployment

### Additional Steps for Production:
```bash
# Optimize for production
php artisan config:cache
php artisan route:cache
php artisan view:cache
php artisan optimize

# Set environment to production
APP_ENV=production
APP_DEBUG=false

# Use queue system for background processing
php artisan queue:work
```

---

## 📞 Support

### Jika mengalami masalah:
1. **Check logs**: `storage/logs/laravel.log`
2. **Verify database**: `python validate_data.py`
3. **Test connection**: `php artisan tinker` lalu `DB::connection()->getPdo()`
4. **Restart services**: MySQL + PHP artisan serve

### Contact:
- **Documentation**: Lihat `README.md`
- **Issues**: Check error logs
- **Help**: Run `php artisan help` untuk available commands

---

**🎉 Selamat! Aplikasi Platform Kewajaran Penganggaran siap digunakan!**

**Next Steps:**
1. Buka browser ke `http://localhost:8000/api/health`
2. Trigger analisis untuk tahun yang diinginkan
3. Explore API endpoints untuk dashboard
4. Integrate dengan frontend application
