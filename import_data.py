import os
import glob
import pandas as pd
from sqlalchemy import create_engine
import pymysql

# --- KONFIGURASI DATABASE MYSQL ---
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "" # Ubah jika ada password
DB_NAME = "kewajaran_anggaran"
# ----------------------------------

def import_to_mysql():
    print(f"Mencoba koneksi ke MySQL di {DB_HOST}...")
    
    try:
        # Koneksi awal ke server MySQL untuk membuat database jika belum ada
        connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS)
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        connection.commit()
        cursor.close()
        connection.close()
        print(f"Database '{DB_NAME}' siap.")
    except Exception as e:
        print(f"Error koneksi ke MySQL: {e}")
        print("Pastikan MySQL server/XAMPP sudah berjalan!")
        return

    # Buat engine SQLAlchemy
    engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")
    
    data_dir = "Data_Reg_DIY"
    if not os.path.exists(data_dir):
        print(f"Direktori {data_dir} tidak ditemukan.")
        return

    cols = [
        "tahun", "kodepemda", "namapemda", "tahapan",
        "kodebidang", "uraibidang",
        "kodeskpd", "uraiskpd",
        "kodeprogram", "uraiprogram",
        "kodekegiatan", "uraikegiatan",
        "kodesubkegiatan", "uraisubkegiatan",
        "indikator", "satuan", "target", "pagu",
    ]

    dfs = []
    print("Membaca file CSV...")
    for year_dir in sorted(glob.glob(os.path.join(data_dir, "*"))):
        if not os.path.isdir(year_dir):
            continue
        for fpath in glob.glob(os.path.join(year_dir, "*.csv")):
            try:
                tmp = pd.read_csv(fpath, usecols=lambda c: c in cols, low_memory=False)
                dfs.append(tmp)
                print(f"  Terbaca: {os.path.basename(fpath)}")
            except Exception as e:
                print(f"  Gagal membaca {fpath}: {e}")

    if not dfs:
        print("Tidak ada data yang dibaca.")
        return

    df = pd.concat(dfs, ignore_index=True)
    
    # Cleaning dasar sebelum masuk DB
    df["tahun"]  = pd.to_numeric(df["tahun"],  errors="coerce").astype("Int64")
    df["pagu"]   = pd.to_numeric(df["pagu"],   errors="coerce").fillna(0)
    df["target"] = pd.to_numeric(df["target"], errors="coerce")
    
    # --- GENERATE DATA REALISASI SIMULASI (BERDASARKAN TANGGAL SEKARANG: MEI 2026) ---
    import numpy as np
    np.random.seed(42)
    
    # 1. Tahun Lampau (2024 - 2025): Realisasi Penuh
    mask_past = df["tahun"] < 2026
    df.loc[mask_past, "realisasi_target"] = df.loc[mask_past, "target"].fillna(0) * np.random.uniform(0.75, 1.05, size=mask_past.sum())
    df.loc[mask_past, "realisasi_anggaran"] = df.loc[mask_past, "pagu"] * np.random.uniform(0.85, 0.98, size=mask_past.sum())
    
    # 2. Tahun Berjalan (2026): Realisasi Sebagian (Mei 2026 ~ 35-45%)
    mask_curr = df["tahun"] == 2026
    df.loc[mask_curr, "realisasi_target"] = df.loc[mask_curr, "target"].fillna(0) * np.random.uniform(0.30, 0.45, size=mask_curr.sum())
    df.loc[mask_curr, "realisasi_anggaran"] = df.loc[mask_curr, "pagu"] * np.random.uniform(0.35, 0.48, size=mask_curr.sum())
    
    # 3. Tahun Depan (2027+): Belum Ada Realisasi (Set 0)
    mask_future = df["tahun"] >= 2027
    df.loc[mask_future, "realisasi_target"] = 0
    df.loc[mask_future, "realisasi_anggaran"] = 0
    
    # Fill remaining NaNs if any
    df["realisasi_target"] = df["realisasi_target"].fillna(0)
    df["realisasi_anggaran"] = df["realisasi_anggaran"].fillna(0)
    
    print(f"Total baris data: {len(df)}")
    print("Memasukkan data ke tabel 'anggaran_subkegiatan' (simulasi realisasi: 2024-2025 penuh, 2026 sebagian, 2027 nihil)...")
    
    try:
        # Masukkan ke DB (replace jika sudah ada tabel)
        df.to_sql(name="anggaran_subkegiatan", con=engine, if_exists="replace", index=False)
        print("Import data ke MySQL BERHASIL!")
    except Exception as e:
        print(f"Gagal memasukkan data ke MySQL: {e}")

if __name__ == "__main__":
    import_to_mysql()
