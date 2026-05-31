"""
Dimensi 2 – Kewajaran Regional (Spatial Comparison).
Membandingkan BSK daerah dengan rata-rata regional TANPA memasukkan daerah itu sendiri.
Z-Score dihitung terhadap distribusi daerah LAIN (leave-one-out).
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
    res["spasial_n_pembanding"] = 0  # Jumlah daerah pembanding
    
    if "bsk" not in res.columns:
        res["bsk"] = np.nan
        valid_mask = (res["pagu"] > 0) & (res["target"].notna()) & (res["target"] > 0)
        res.loc[valid_mask, "bsk"] = res.loc[valid_mask, "pagu"] / res.loc[valid_mask, "target"]
        
    valid_mask = res["bsk"].notna() & (res["bsk"] > 0)
    
    if valid_mask.any():
        valid_df = res[valid_mask].copy()
        valid_df["bsk_sq"] = valid_df["bsk"] ** 2
        
        # Total per sub-kegiatan + satuan + tahun
        total_stats = valid_df.groupby(["tahun", "kodesubkegiatan", "satuan"]).agg(
            sum_total=("bsk", "sum"),
            count_total=("bsk", "count"),
            sum_sq_total=("bsk_sq", "sum")
        ).reset_index()
        
        # Total per pemda
        pemda_stats = valid_df.groupby(["tahun", "kodesubkegiatan", "satuan", "kodepemda"]).agg(
            sum_pemda=("bsk", "sum"),
            count_pemda=("bsk", "count"),
            sum_sq_pemda=("bsk_sq", "sum")
        ).reset_index()
        
        merged = pd.merge(pemda_stats, total_stats, on=["tahun", "kodesubkegiatan", "satuan"], how="left")
        
        merged["sum_others"] = merged["sum_total"] - merged["sum_pemda"]
        merged["count_others"] = merged["count_total"] - merged["count_pemda"]
        merged["sum_sq_others"] = merged["sum_sq_total"] - merged["sum_sq_pemda"]
        
        valid_others = merged["count_others"] > 0
        
        merged.loc[valid_others, "spasial_bsk_avg"] = merged.loc[valid_others, "sum_others"] / merged.loc[valid_others, "count_others"]
        
        # Variance formula: (sum_sq - (sum^2)/N) / (N-ddof)
        var_numerator = merged["sum_sq_others"] - (merged["sum_others"]**2 / merged["count_others"])
        var_numerator = np.maximum(var_numerator, 0)
        
        ddof = np.where(merged["count_others"] == 1, 0, 1)
        
        merged.loc[valid_others, "var"] = var_numerator / (merged.loc[valid_others, "count_others"] - ddof[valid_others])
        merged.loc[valid_others, "spasial_bsk_std"] = np.sqrt(merged.loc[valid_others, "var"])
        
        res = res.drop(columns=["spasial_bsk_avg", "spasial_bsk_std", "spasial_n_pembanding"], errors="ignore")
        merged["spasial_n_pembanding"] = merged["count_others"]
        res = pd.merge(res, merged[["tahun", "kodesubkegiatan", "satuan", "kodepemda", 
                                    "spasial_bsk_avg", "spasial_bsk_std", "spasial_n_pembanding"]], 
                       on=["tahun", "kodesubkegiatan", "satuan", "kodepemda"], how="left")
                       
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
        # - Over budget (z >= 0): sigma_high = 1.96 / sqrt(2 * ln(2)) ≈ 1.6647 (Score = 50 at 95% LISA outlier limit, z = 1.96)
        # - Under budget (z < 0): sigma_low = 3.00 / sqrt(2 * ln(2)) ≈ 2.5480 (Score = 50 at z = -3.00)
        sigma_high = 1.96 / np.sqrt(2 * np.log(2))
        sigma_low = 3.00 / np.sqrt(2 * np.log(2))
        
        sigma_z = np.where(z >= 0, sigma_high, sigma_low)
        score = 100.0 * np.exp(-0.5 * (z / sigma_z) ** 2)
        
        res.loc[valid_calc, "dimensi_2_score"] = score[valid_calc]
        
    res["spasial_n_pembanding"] = res["spasial_n_pembanding"].fillna(0).astype(int)
    
    return res
