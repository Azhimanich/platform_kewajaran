"""
Dimensi 5 - Kewajaran Statistik (Deteksi Anomali Asymmetric Tukey's Fences - Simple).

Formula Batas Aman (Asymmetric):
  Batas Atas (k1 = 1.5)  = Q3 + 1.5 * IQR
  Batas Bawah (k2 = 0.2) = max(0, Q1 - 0.2 * IQR)

Jarak d (seberapa jauh di luar batas aman, diukur dalam kelipatan IQR):
  d = 0                                jika Batas Bawah <= BSK <= Batas Atas
  d = (Batas Bawah - BSK) / IQR        jika BSK < Batas Bawah
  d = (BSK - Batas Atas) / IQR         jika BSK > Batas Atas

Gaussian Decay Scoring:
  Score = 100 * exp(-0.5 * (d / sigma)^2)
  Dengan sigma = 0.5 (Skor turun menjadi 60.7 di d=0.5, dan 13.5 di d=1.0)
"""
import pandas as pd
import numpy as np

# Konstanta Pengali Fences
K_UPPER = 1.5
K_LOWER = 0.2
SIGMA_DECAY = 0.5  # Penurunan skor saat di luar batas aman


def calculate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    res = df.copy()

    # Hitung BSK jika belum ada
    if "bsk" not in res.columns:
        valid_mask = (res["pagu"] > 0) & (res["target"].notna()) & (res["target"] > 0)
        res["bsk"] = np.nan
        res.loc[valid_mask, "bsk"] = res.loc[valid_mask, "pagu"] / res.loc[valid_mask, "target"]

    # Inisialisasi kolom output
    res["dimensi_5_score"]    = np.nan
    res["stat_q1"]            = np.nan
    res["stat_q3"]            = np.nan
    res["stat_lower_bound"]   = np.nan
    res["stat_upper_bound"]   = np.nan
    res["stat_iqr_distance"]  = np.nan
    res["stat_k_upper"]       = K_UPPER
    res["stat_k_lower"]       = K_LOWER
    res["is_anomali"]         = False

    groupby_cols = ["kodesubkegiatan", "satuan"]
    valid_bsk = res["bsk"].notna() & (res["bsk"] > 0)

    if not valid_bsk.any():
        return res

    valid_df = res[valid_bsk].copy()

    # Hitung Q1, Q3, dan IQR per sub-kegiatan
    stats = valid_df.groupby(groupby_cols).agg(
        q1=("bsk", lambda x: x.quantile(0.25)),
        q3=("bsk", lambda x: x.quantile(0.75)),
        count=("bsk", "count")
    ).reset_index()

    # Minimal 4 data agar analisis bermakna
    stats = stats[stats["count"] >= 4].copy()

    if stats.empty:
        return res

    stats["iqr"] = stats["q3"] - stats["q1"]
    
    # Hitung Batas Atas dan Batas Bawah (Non-negatif)
    stats["stat_upper_bound"] = stats["q3"] + K_UPPER * stats["iqr"]
    stats["stat_lower_bound"] = stats["q1"] - K_LOWER * stats["iqr"]

    # Merge stats ke dataframe utama
    res = res.drop(columns=["stat_q1", "stat_q3", "stat_lower_bound",
                             "stat_upper_bound", "stat_iqr_distance"], errors="ignore")
    stats_renamed = stats.rename(columns={"q1": "stat_q1", "q3": "stat_q3"})
    merge_cols = groupby_cols + ["stat_q1", "stat_q3", "stat_lower_bound", "stat_upper_bound", "iqr"]
    res = pd.merge(res, stats_renamed[merge_cols], on=groupby_cols, how="left")

    # Hitung Jarak Terhadap Batas Aman (d)
    valid_calc = valid_bsk & res["stat_q1"].notna()
    
    bsk = res["bsk"]
    lb = res["stat_lower_bound"]
    ub = res["stat_upper_bound"]
    iqr = res["iqr"]

    # Inisialisasi d = 0 (untuk yang berada dalam batas aman)
    d = np.zeros_like(bsk)

    # d untuk BSK di bawah batas bawah
    under_mask = valid_calc & (bsk < lb)
    if under_mask.any():
        d[under_mask] = (lb[under_mask] - bsk[under_mask]) / iqr[under_mask].replace(0, np.nan)

    # d untuk BSK di atas batas atas
    over_mask = valid_calc & (bsk > ub)
    if over_mask.any():
        d[over_mask] = (bsk[over_mask] - ub[over_mask]) / iqr[over_mask].replace(0, np.nan)

    # Isi d dan is_anomali
    res.loc[valid_calc, "stat_iqr_distance"] = d[valid_calc]
    res.loc[valid_calc, "is_anomali"] = (bsk[valid_calc] < lb[valid_calc]) | (bsk[valid_calc] > ub[valid_calc])

    # Hitung skor: 100 jika d = 0, jika tidak gunakan Gaussian Decay
    scores = np.clip(100.0 * np.exp(-0.5 * (d / SIGMA_DECAY) ** 2), 0, 100)
    res.loc[valid_calc, "dimensi_5_score"] = scores[valid_calc]

    # Hapus kolom sementara
    res = res.drop(columns=["iqr"], errors="ignore")

    return res
