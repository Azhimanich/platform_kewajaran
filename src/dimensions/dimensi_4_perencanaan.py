"""
Dimensi 4 – Kewajaran Perencanaan (Consistency).
Mengevaluasi konsistensi perencanaan antara dokumen RKPD, PPAS, dan APBD.
Data belum tersedia dari SIPD-RI — skor = NaN (tidak dinilai).
"""
import pandas as pd
import numpy as np

def calculate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Kalkulasi Dimensi 4 — Kewajaran Perencanaan (Consistency APBD-RKPD-PPAS).
    Menggunakan standard framework PEFA (Public Expenditure and Financial Accountability) PI-16.
    
    Formula Discrepancy (x):
      x = (|APBD - RKPD| + |APBD - PPAS|) / APBD
      
    Gaussian Decay Score:
      Score = 100 * exp(-0.5 * (x / sigma_c)^2)
      di mana sigma_c dikalibrasi agar deviasi 15% (PEFA Grade C threshold) menghasilkan skor 50.0.
      sigma_c = 0.15 / sqrt(2 * ln(2)) ≈ 0.1274
    """
    if df.empty:
        return df
        
    res = df.copy()
    res["dimensi_4_score"] = np.nan
    
    # Mencoba kalkulasi jika data perencanaan sudah diintegrasikan dari SIPD-RI
    if "pagu_rkpd" in res.columns and "pagu_ppas" in res.columns and "pagu" in res.columns:
        valid = (res["pagu"] > 0) & res["pagu_rkpd"].notna() & res["pagu_ppas"].notna()
        if valid.any():
            apbd = res.loc[valid, "pagu"]
            rkpd = res.loc[valid, "pagu_rkpd"]
            ppas = res.loc[valid, "pagu_ppas"]
            
            x = (np.abs(apbd - rkpd) + np.abs(apbd - ppas)) / apbd
            sigma_c = 0.15 / np.sqrt(2 * np.log(2))
            
            res.loc[valid, "dimensi_4_score"] = 100.0 * np.exp(-0.5 * (x / sigma_c) ** 2)
            
    return res
