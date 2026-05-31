import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def export_mysql_to_parquet():
    print("⏳ Menghubungkan ke database MySQL...")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_NAME = os.getenv("DB_NAME", "kewajaran_anggaran")
    
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")
        query = "SELECT * FROM anggaran_subkegiatan"
        print("📥 Membaca data dari tabel 'anggaran_subkegiatan'...")
        df = pd.read_sql(query, con=engine)
        
        if df.empty:
            print("⚠️ Database kosong. Tidak ada yang di-export.")
            return
            
        print(f"✅ Berhasil membaca {len(df)} baris data.")
        
        # Konversi ke parquet
        output_file = "data.parquet"
        print(f"🗜️ Menyimpan dan mengkompresi data ke {output_file}...")
        df.to_parquet(output_file, index=False, engine="pyarrow")
        
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"🎉 SUKSES! File {output_file} berhasil dibuat dengan ukuran hanya {file_size:.2f} MB.")
        print("Sekarang aplikasi siap di-deploy instan ke Streamlit Cloud tanpa perlu Cloud MySQL!")
        
    except Exception as e:
        print(f"❌ TERJADI KESALAHAN: {e}")

if __name__ == "__main__":
    export_mysql_to_parquet()
