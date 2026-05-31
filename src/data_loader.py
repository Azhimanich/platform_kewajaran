"""
data_loader.py — Memuat dan membersihkan seluruh data CSV DIY (2024-2027).
Menghasilkan DataFrame tunggal yang siap dipakai semua halaman.
"""
import os
import pandas as pd
import numpy as np
import streamlit as st
import pymysql
from sqlalchemy import create_engine

# --- KONFIGURASI DATABASE MYSQL ---
# Untuk deployment, set environment variables:
#   DB_HOST, DB_USER, DB_PASS, DB_NAME
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "kewajaran_anggaran")
# ----------------------------------

# Mapping nama pemda dari DB ke label ringkas untuk peta
PEMDA_MAP = {
    "KAB. BANTUL":              "Kab. Bantul",
    "KAB. GUNUNGKIDUL":         "Kab. Gunungkidul",
    "KAB. KULON PROGO":         "Kab. Kulon Progo",
    "KAB. SLEMAN":              "Kab. Sleman",
    "KOTA YOGYAKARTA":          "Kota Yogyakarta",
    "DAERAH ISTIMEWA YOGYAKARTA": "Prov. DIY",
}

@st.cache_data(show_spinner="⏳ Memuat data dari Database/Parquet...")
def load_raw() -> pd.DataFrame:
    """Membaca data dari file Parquet (jika ada) atau database MySQL."""
    
    # Prioritaskan pembacaan dari file Parquet berkinerja tinggi (untuk deployment instan)
    parquet_file = "data.parquet"
    if os.path.exists(parquet_file):
        try:
            df = pd.read_parquet(parquet_file)
            if not df.empty:
                return _process_df(df)
        except Exception as e:
            st.warning(f"Gagal memuat Parquet, beralih ke MySQL: {e}")

    # Fallback ke MySQL jika Parquet tidak ada
    try:
        engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}")
        query = "SELECT * FROM anggaran_subkegiatan"
        df = pd.read_sql(query, con=engine)
    except Exception as e:
        st.error(f"Gagal memuat data dari database MySQL: {e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    return _process_df(df)

def _process_df(df: pd.DataFrame) -> pd.DataFrame:
    """Helper fungsi untuk membersihkan tipe data dataframe mentah."""

    # ── Normalise types ──────────────────────────────────────────────────────
    df["tahun"]  = pd.to_numeric(df["tahun"],  errors="coerce").astype("Int64")
    df["pagu"]   = pd.to_numeric(df["pagu"],   errors="coerce").fillna(0)
    df["target"] = pd.to_numeric(df["target"], errors="coerce")  # NaN stays

    # Strip whitespace from text columns
    for col in ["namapemda", "kodesubkegiatan", "uraisubkegiatan",
                "indikator", "satuan", "uraibidang", "uraiskpd",
                "uraiprogram", "uraikegiatan"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Replace literal "nan" / empty strings produced by astype(str)
    df.replace({"nan": np.nan, "": np.nan}, inplace=True)

    # Drop rows with no sub-kegiatan code
    df = df.dropna(subset=["kodesubkegiatan"])

    # ── Pemda label ──────────────────────────────────────────────────────────
    df["pemda_label"] = df["namapemda"].map(PEMDA_MAP).fillna(df["namapemda"])

    return df.reset_index(drop=True)

