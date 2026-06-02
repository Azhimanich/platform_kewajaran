"""
Dimensi 5 - Kewajaran Statistik (Deteksi Anomali IQR + Gaussian Decay Scoring).

Mendeteksi outlier BSK menggunakan metode Interquartile Range (IQR) dari Tukey (1977),
kemudian mengkonversi jarak dari batas IQR menjadi skor kontinu menggunakan fungsi
Gaussian Decay - bukan flat scoring.

Referensi Akademik:
  [1] Tukey, J.W. (1977). Exploratory Data Analysis. Addison-Wesley.
      - Dasar metode IQR dan konsep "fence" (inner fence = 1.5xIQR, outer fence = 3xIQR).
  [2] Iglewicz, B. & Hoaglin, D.C. (1993). How to Detect and Handle Outliers.
      ASQC Quality Press. - Modified Z-Score dan MAD-based outlier detection.
  [3] Hubert, M. & Vandervieren, E. (2008). An Adjusted Boxplot for Skewed
      Distributions. Computational Statistics & Data Analysis, 52(12), 5186-5201.
      - IQR-based outlier detection untuk distribusi non-normal.

Mekanisme Skoring:
  1. Hitung IQR Fence Distance (d):
     - Jika BSK dalam [Q1, Q3]:  d = 0 (dalam kotak IQR)
     - Jika BSK < Q1:            d = (Q1 - BSK) / IQR
     - Jika BSK > Q3:            d = (BSK - Q3) / IQR

  2. Konversi ke skor menggunakan Gaussian Decay:
     Score = 100 x exp(-0.5 x (d / ))

     dengan  = 1.5 / (2 x ln(2))  1.2739

     Kalibrasi:
       d = 0.0  ->  Score = 100.0  (dalam kotak IQR, wajar)
       d = 0.5  ->  Score   92.6  (mendekati batas, masih wajar)
       d = 1.0  ->  Score   73.4  (mendekati fence, perlu perhatian)
       d = 1.5  ->  Score =  50.0  (tepat di Tukey inner fence)
       d = 2.0  ->  Score   29.2  (di luar inner fence)
       d = 3.0  ->  Score    6.3  (tepat di Tukey outer fence)

  Properti penting:
  - Skor bersifat KONTINU dan SMOOTH, bukan flat/diskrit.
  - Kalibrasi  dipilih agar skor TEPAT 50 di inner fence (d=1.5), konsisten
    dengan threshold standar Tukey (1977).
  - Fungsi Gaussian dipilih karena properti matematis yang well-established
    dalam teori probabilitas dan kernel density estimation (Silverman, 1986).
"""
import pandas as pd
import numpy as np

# Konstanta Gaussian Decay
#  dikalibrasi agar Score = 50 tepat di Tukey inner fence (d = 1.5)
# Derivasi: 50 = 100 x exp(-0.5 x (1.5/))
#           0.5 = exp(-0.5 x (1.5/))
#           ln(0.5) = -0.5 x (1.5/)
#            = 1.5 / (2 x ln(2))  1.2739
SIGMA_DECAY = 1.5 / np.sqrt(2 * np.log(2))  #  1.2739


def _gaussian_decay_score(d: np.ndarray) -> np.ndarray:
    """
    Konversi IQR fence distance ke skor 0-100 menggunakan Gaussian Decay.
    
    Score = 100 x exp(-0.5 x (d / ))
    
    Parameters:
        d: IQR fence distance (0 = dalam [Q1,Q3], 1.5 = inner fence, 3.0 = outer fence)
    Returns:
        Score 0-100
    """
    return np.clip(100.0 * np.exp(-0.5 * (d / SIGMA_DECAY) ** 2), 0, 100)


def calculate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
        
    res = df.copy()
    
    # BSK sudah ada dari Dimensi 1, hitung ulang jika belum
    if "bsk" not in res.columns:
        valid_mask = (res["pagu"] > 0) & (res["target"].notna()) & (res["target"] > 0)
        res["bsk"] = np.nan
        res.loc[valid_mask, "bsk"] = res.loc[valid_mask, "pagu"] / res.loc[valid_mask, "target"]
    
    # Inisialisasi kolom output
    res["dimensi_5_score"] = np.nan
    res["stat_q1"] = np.nan
    res["stat_q3"] = np.nan
    res["stat_lower_bound"] = np.nan
    res["stat_upper_bound"] = np.nan
    res["stat_iqr_distance"] = np.nan  # Jarak normalisasi dari kotak IQR
    res["is_anomali"] = False
    
    # Group by Nomenklatur & Satuan - tanpa batasan wilayah
    groupby_cols = ["kodesubkegiatan", "satuan"]
    
    valid_bsk = res["bsk"].notna() & (res["bsk"] > 0)
    
    if valid_bsk.any():
        valid_df = res[valid_bsk].copy()
        
        # Hitung kuartil dan jumlah data per grup
        def get_q1(x): return x.quantile(0.25)
        def get_q3(x): return x.quantile(0.75)
        
        stats = valid_df.groupby(groupby_cols).agg(
            q1=("bsk", get_q1),
            q3=("bsk", get_q3),
            count=("bsk", "count")
        ).reset_index()
        
        # Perlu minimal 4 data untuk analisis statistik yang bermakna
        stats = stats[stats["count"] >= 4].copy()
        
        if not stats.empty:
            stats["iqr"] = stats["q3"] - stats["q1"]
            stats["stat_lower_bound"] = stats["q1"] - (1.5 * stats["iqr"])
            stats["stat_upper_bound"] = stats["q3"] + (1.5 * stats["iqr"])
            
            res = res.drop(columns=["stat_q1", "stat_q3", "stat_lower_bound", 
                                     "stat_upper_bound", "stat_iqr_distance"], errors="ignore")
            
            # Merge stats ke dataframe utama
            stats_renamed = stats.rename(columns={"q1": "stat_q1", "q3": "stat_q3"})
            merge_cols = groupby_cols + ["stat_q1", "stat_q3", "stat_lower_bound", 
                                         "stat_upper_bound", "iqr"]
            res = pd.merge(res, stats_renamed[merge_cols], on=groupby_cols, how="left")
                           
            # Hitung IQR Fence Distance (d)
            valid_calc = valid_bsk & res["stat_q1"].notna()
            
            bsk = res["bsk"]
            q1 = res["stat_q1"]
            q3 = res["stat_q3"]
            iqr = res["iqr"]
            lb = res["stat_lower_bound"]
            ub = res["stat_upper_bound"]
            
            # d = jarak dari kotak IQR, dinormalisasi oleh IQR
            # d = 0 jika BSK dalam [Q1, Q3]
            # d = (Q1 - BSK) / IQR jika BSK < Q1
            # d = (BSK - Q3) / IQR jika BSK > Q3
            d_below = np.maximum(0, (q1 - bsk) / iqr.replace(0, np.nan))
            d_above = np.maximum(0, (bsk - q3) / iqr.replace(0, np.nan))
            d = d_below + d_above  # hanya satu yang non-zero
            
            # Handle IQR = 0 (semua data identik): d = 0 jika sama, besar jika beda
            iqr_zero = iqr == 0
            if iqr_zero.any():
                median_val = (q1 + q3) / 2  # = Q1 = Q3 saat IQR=0
                d = d.fillna(0)
                # Jika BSK = median -> d = 0, jika berbeda -> d proporsional
                diff_mask = iqr_zero & (bsk != median_val) & valid_calc
                if diff_mask.any():
                    d.loc[diff_mask] = np.abs(bsk[diff_mask] - median_val[diff_mask]) / median_val[diff_mask].replace(0, 1)
            
            res.loc[valid_calc, "stat_iqr_distance"] = d[valid_calc]
            
            # Deteksi Anomali: flag berdasarkan Tukey inner fence (d >= 1.5)
            res.loc[valid_calc, "is_anomali"] = (bsk[valid_calc] < lb[valid_calc]) | (bsk[valid_calc] > ub[valid_calc])
            
            # Skor: Gaussian Decay berdasarkan fence distance
            scores = _gaussian_decay_score(d)
            res.loc[valid_calc, "dimensi_5_score"] = scores[valid_calc]
            
            # Bersihkan kolom sementara
            res = res.drop(columns=["iqr"], errors="ignore")
            
    return res
