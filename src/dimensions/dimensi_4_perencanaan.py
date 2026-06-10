"""
Dimensi 4 - Kewajaran Perencanaan (Konsistensi Renstra vs RKPD).
Mengukur konsistensi antara dokumen Rencana Strategis (Renstra 5 Tahun)
dengan dokumen RKPD Tahunan menggunakan formula Consistency Score.

Formula (sesuai metodologi):
  Consistency Score = |Program_RKPD ∩ Program_Renstra| / |Program_RKPD|

Nilai konsistensi (0.0 - 1.0) dikonversi ke skor 0-100 menggunakan
Gaussian Decay agar skor wajar ~100 pada konsistensi tinggi dan
turun secara melengkung saat konsistensi rendah.

Red Flags yang dideteksi:
  - Program di RKPD yang tidak ada di Renstra (Program Siluman)
  - Alokasi anggaran besar pada program non-prioritas
  - Pergeseran fokus yang tidak terencana
"""
import pandas as pd
import numpy as np
import os

# Mapping tahun RKPD ke kolom pagu Renstra (idperiode=20252029)
# pagu1=2025, pagu2=2026, pagu3=2027, pagu4=2028, pagu5=2029
TAHUN_TO_PAGU_COL = {
    2025: "pagu1",
    2026: "pagu2",
    2027: "pagu3",
    2028: "pagu4",
    2029: "pagu5",
}

def load_renstra(renstra_path: str = "renstra_data_pagu_diy.csv") -> pd.DataFrame:
    """Memuat dan membersihkan data Renstra DIY."""
    if not os.path.exists(renstra_path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(renstra_path, low_memory=False)
        # Normalisasi tipe data
        df["kodepemda"] = pd.to_numeric(df["kodepemda"], errors="coerce").astype("Int64")
        df["kodeprogram"] = df["kodeprogram"].astype(str).str.strip()
        df["kodesubkegiatan"] = df["kodesubkegiatan"].astype(str).str.strip()
        df["kodeskpd"] = df["kodeskpd"].astype(str).str.strip()
        df["uraiprogram"] = df["uraiprogram"].astype(str).str.strip()
        return df
    except Exception:
        return pd.DataFrame()


def calculate(df: pd.DataFrame, renstra_path: str = "renstra_data_pagu_diy.csv") -> pd.DataFrame:
    """
    Kalkulasi Dimensi 4 - Kewajaran Perencanaan (Konsistensi Renstra vs RKPD).

    Langkah-langkah:
    1. Load data Renstra DIY dari CSV
    2. Untuk setiap pasangan (kodepemda, tahun_rkpd):
       a. Ambil himpunan program yang ada di RKPD tahun tersebut
       b. Ambil himpunan program yang ada di Renstra pemda tersebut
       c. Hitung Consistency = |Intersection| / |Program_RKPD|
       d. Konversi ke skor 0-100 via Gaussian Decay
    3. Propagasi skor ke setiap baris subkegiatan
    4. Tambahkan metadata untuk audit: jumlah program siluman, persen konsistensi, dll.
    """
    if df.empty:
        return df

    res = df.copy()
    res["dimensi_4_score"] = np.nan
    res["d4_consistency_ratio"] = np.nan  # Raw consistency 0-1
    res["d4_rkpd_programs"] = np.nan      # Jumlah program di RKPD
    res["d4_renstra_programs"] = np.nan   # Jumlah program di Renstra
    res["d4_consistent_programs"] = np.nan  # Jumlah program yang konsisten
    res["d4_phantom_programs"] = np.nan   # Program RKPD yg tidak ada di Renstra
    res["d4_phantom_list"] = None         # List kode program siluman
    res["d4_phantom_pagu"] = np.nan       # Total pagu program siluman
    res["d4_phantom_pagu_ratio"] = np.nan # Rasio pagu program siluman vs total

    # Load data Renstra
    renstra = load_renstra(renstra_path)
    if renstra.empty:
        return res

    # Gaussian Decay parameter
    # Kalibrasi: konsistensi 70% (sering dianggap wajar) -> skor 50
    # sigma_c = 0.30 / sqrt(2*ln(2)) ≈ 0.2547
    # Artinya: konsistensi 100% = skor 100, konsistensi 70% = skor 50
    sigma_c = 0.30 / np.sqrt(2 * np.log(2))

    # Iterasi per kombinasi (kodepemda, tahun)
    combos = res[["kodepemda", "tahun"]].drop_duplicates().dropna()

    for _, combo in combos.iterrows():
        pemda_code = int(combo["kodepemda"])
        tahun = int(combo["tahun"])

        # Filter RKPD rows for this pemda+tahun
        mask_rkpd = (res["kodepemda"] == pemda_code) & (res["tahun"] == tahun)
        rkpd_rows = res[mask_rkpd]

        # Filter Renstra rows for this pemda
        renstra_pemda = renstra[renstra["kodepemda"] == pemda_code]

        if rkpd_rows.empty or renstra_pemda.empty:
            continue

        # --- Himpunan program ---
        rkpd_programs = set(
            rkpd_rows["kodeprogram"].dropna().str.strip().unique()
        )
        renstra_programs = set(
            renstra_pemda["kodeprogram"].dropna().str.strip().unique()
        )

        if not rkpd_programs:
            continue

        # Intersection: program yang ada di keduanya (konsisten)
        consistent_programs = rkpd_programs.intersection(renstra_programs)

        # Phantom programs: ada di RKPD tapi tidak di Renstra
        phantom_programs = rkpd_programs - renstra_programs

        # Raw consistency ratio
        consistency_ratio = len(consistent_programs) / len(rkpd_programs)

        # Gaussian Decay Score (0-100)
        # x = 1 - consistency_ratio (discrepancy dari sempurna)
        discrepancy = 1.0 - consistency_ratio
        d4_score = 100.0 * np.exp(-0.5 * (discrepancy / sigma_c) ** 2)

        # Hitung total pagu untuk program siluman
        phantom_pagu = 0.0
        total_pagu = rkpd_rows["pagu"].sum() if "pagu" in rkpd_rows.columns else 0.0
        if phantom_programs and "pagu" in rkpd_rows.columns:
            phantom_rows = rkpd_rows[rkpd_rows["kodeprogram"].isin(phantom_programs)]
            phantom_pagu = phantom_rows["pagu"].sum()

        phantom_pagu_ratio = phantom_pagu / total_pagu if total_pagu > 0 else 0.0

        # Assign ke semua baris pada pemda+tahun ini
        res.loc[mask_rkpd, "dimensi_4_score"] = d4_score
        res.loc[mask_rkpd, "d4_consistency_ratio"] = consistency_ratio
        res.loc[mask_rkpd, "d4_rkpd_programs"] = len(rkpd_programs)
        res.loc[mask_rkpd, "d4_renstra_programs"] = len(renstra_programs)
        res.loc[mask_rkpd, "d4_consistent_programs"] = len(consistent_programs)
        res.loc[mask_rkpd, "d4_phantom_programs"] = len(phantom_programs)
        res.loc[mask_rkpd, "d4_phantom_pagu"] = phantom_pagu
        res.loc[mask_rkpd, "d4_phantom_pagu_ratio"] = phantom_pagu_ratio

        # Store phantom program list as string (object column)
        phantom_str = ",".join(sorted(phantom_programs)) if phantom_programs else ""
        res.loc[mask_rkpd, "d4_phantom_list"] = phantom_str

    return res
