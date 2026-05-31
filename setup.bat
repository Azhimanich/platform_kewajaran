@echo off
echo ==========================================
echo    Platform Kewajaran Penganggaran Setup
echo ==========================================
echo.

REM Check Python
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan. Install Python 3.8+ terlebih dahulu.
    pause
    exit /b 1
)
echo Python OK

REM Check MySQL
echo [2/6] Checking MySQL connection...
mysql --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: MySQL tidak ditemukan. Install MySQL 8.0+ terlebih dahulu.
    pause
    exit /b 1
)
echo MySQL OK

REM Check Composer
echo [3/6] Checking Composer...
composer --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Composer tidak ditemukan. Install Composer terlebih dahulu.
    pause
    exit /b 1
)
echo Composer OK

REM Setup Database
echo [4/6] Setting up database...
echo Importing database structure...
mysql -u root -p kewajaran < database_structure.sql
if errorlevel 1 (
    echo ERROR: Gagal import database structure. Check MySQL connection.
    pause
    exit /b 1
)

REM Install Python dependencies dan import data
echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Gagal install Python dependencies.
    pause
    exit /b 1
)

echo Importing CSV data...
python run_import.py
if errorlevel 1 (
    echo ERROR: Gagal import data CSV.
    pause
    exit /b 1
)

REM Setup Laravel
echo [5/6] Setting up Laravel...
cd laravel

echo Installing Composer dependencies...
composer install --no-dev --optimize-autoloader
if errorlevel 1 (
    echo ERROR: Gagal install Laravel dependencies.
    pause
    exit /b 1
)

echo Generating application key...
php artisan key:generate
if errorlevel 1 (
    echo ERROR: Gagal generate application key.
    pause
    exit /b 1
)

echo Copying environment file...
copy .env.example .env >nul

REM Run migration
echo [6/6] Running database migration...
php artisan migrate
if errorlevel 1 (
    echo ERROR: Gagal run migration.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo    SETUP COMPLETED SUCCESSFULLY!
echo ==========================================
echo.
echo Next steps:
echo 1. Edit laravel\.env file untuk database password
echo 2. Run: php artisan serve --port=8000
echo 3. Open: http://localhost:8000/api/health
echo.
echo Starting development server...
php artisan serve --port=8000

pause
