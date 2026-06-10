"""
Dimensi 2 - Kewajaran Regional (Spatial Comparison).
Membandingkan BSK daerah dengan rata-rata regional.
Semua data (termasuk daerah subjek) dimasukkan dalam perhitungan rata-rata dan standar deviasi regional.
"""
import pandas as pd
import numpy as np

def calculate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
        
    res = df.copy()
    res["dimensi_2_score"] = np.nan
    res["dimensi_2_zscore"] = np.nan
    res["spasial_bsk_avg"] = np.nan
    res["spasial_bsk_std"] = np.nan
    res["spasial_n_pembanding"] = 0
    
    if "bsk" not in res.columns:
        res["bsk"] = np.nan
        valid_mask = (res["pagu"] > 0) & (res["target"].notna()) & (res["target"] > 0)
        res.loc[valid_mask, "bsk"] = res.loc[valid_mask, "pagu"] / res.loc[valid_mask, "target"]
        
    valid_mask = res["bsk"].notna() & (res["bsk"] > 0)
    
    if valid_mask.any():
        valid_df = res[valid_mask].copy()
        
        # Hitung rata-rata, standar deviasi, dan jumlah data regional per sub-kegiatan, satuan, dan tahun
        # Seluruh daerah (termasuk subjek) dimasukkan ke dalam perhitungan
        group_stats = valid_df.groupby(["tahun", "kodesubkegiatan", "satuan"]).agg(
            spasial_bsk_avg=("bsk", "mean"),
            spasial_bsk_std=("bsk", "std"),
            spasial_n_pembanding=("bsk", "count")
        ).reset_index()
        
        # Jika std dev NaN (karena data hanya 1), isi dengan 0
        group_stats["spasial_bsk_std"] = group_stats["spasial_bsk_std"].fillna(0)
        
        res = res.drop(columns=["spasial_bsk_avg", "spasial_bsk_std", "spasial_n_pembanding"], errors="ignore")
        res = pd.merge(res, group_stats, on=["tahun", "kodesubkegiatan", "satuan"], how="left")
                       
        valid_calc = valid_mask & res["spasial_bsk_avg"].notna()
        
        sigma = res["spasial_bsk_std"]
        mu = res["spasial_bsk_avg"]
        current_bsk = res["bsk"]
        
        z = np.where(sigma > 0,
                     (current_bsk - mu) / sigma,
                     np.where(current_bsk == mu, 0.0, np.where(mu > 0, (current_bsk - mu) / mu, 0.0)))
                     
        res.loc[valid_calc, "dimensi_2_zscore"] = z[valid_calc]
        
        # Anselin's (1995) Spatial Autocorrelation (LISA) Asymmetric Gaussian Decay model:
        # Score = 100 * exp(-0.5 * (z / sigma_z)^2)
        # Asymmetric thresholds to accommodate high tolerance for under-spending (safer):
        # - Over budget (z >= 0): sigma_high = 1.96 / sqrt(2 * ln(2)) ≈ 1.6647 (Score = 50 at z = 1.96)
        # - Under budget (z < 0): sigma_low = 3.00 / sqrt(2 * ln(2)) ≈ 2.5480 (Score = 50 at z = -3.00)
        sigma_high = 1.96 / np.sqrt(2 * np.log(2))
        sigma_low = 3.00 / np.sqrt(2 * np.log(2))
        
        sigma_z = np.where(z >= 0, sigma_high, sigma_low)
        score = 100.0 * np.exp(-0.5 * (z / sigma_z) ** 2)
        
        res.loc[valid_calc, "dimensi_2_score"] = score[valid_calc]
        
    res["spasial_n_pembanding"] = res["spasial_n_pembanding"].fillna(0).astype(int)
    
    return res
