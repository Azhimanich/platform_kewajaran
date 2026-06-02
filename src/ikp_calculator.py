"""
IKP Calculator - Menggabungkan skor dari 5 dimensi.
Transparent: menyimpan detail kalkulasi di tiap baris untuk audit trail.
"""
import pandas as pd
import numpy as np

# Bobot masing-masing dimensi (5 Dimensi @ 20%)
WEIGHTS = {
    "dimensi_1_score": 0.20,
    "dimensi_2_score": 0.20,
    "dimensi_3_score": 0.20,
    "dimensi_4_score": 0.20,
    "dimensi_5_score": 0.20
}

# Label dimensi
DIM_LABELS = {
    "dimensi_1_score": "H (Perubahan Anggaran)",
    "dimensi_2_score": "R (Skor Regional)",
    "dimensi_3_score": "K (Skor Kinerja)",
    "dimensi_4_score": "P (Skor Perencanaan)",
    "dimensi_5_score": "S (Skor Statistik)"
}

def calculate_ikp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Menghitung Indeks Kewajaran Penganggaran (IKP).
    Dynamic Weighting: hanya dimensi yang memiliki data valid yang diperhitungkan.
    Bobot di-redistribusi secara proporsional ke dimensi yang tersedia.
    Fully vectorized - no row-by-row loops.
    """
    if df.empty:
        return df
        
    res = df.copy()
    
    # Init columns
    res["ikp_score"] = np.nan
    res["ikp_category"] = "Tidak Dapat Dinilai"
    res["ikp_total_weight"] = 0.0  # Total bobot dimensi yang valid
    res["ikp_dimensions_used"] = 0  # Jumlah dimensi yang digunakan
    
    # Vectorized calculation
    dim_cols = list(WEIGHTS.keys())
    weight_vals = np.array([WEIGHTS[c] for c in dim_cols])
    
    # Build matrix: rows x dimensions
    score_matrix = res[dim_cols].values  # shape: (N, 5)
    valid_mask = ~np.isnan(score_matrix)  # True where value exists
    
    # Weighted scores: score * weight where valid, else 0
    weighted_scores = np.where(valid_mask, score_matrix * weight_vals, 0)
    total_weighted = weighted_scores.sum(axis=1)  # sum per row
    
    # Total weight per row (only valid dimensions)
    total_weight = (valid_mask * weight_vals).sum(axis=1)
    
    # Dimensions used per row
    dims_used = valid_mask.sum(axis=1)
    
    # Calculate IKP where at least 1 dimension is valid
    has_data = total_weight > 0
    
    res.loc[has_data, "ikp_score"] = total_weighted[has_data] / total_weight[has_data]
    res.loc[has_data, "ikp_total_weight"] = total_weight[has_data]
    res.loc[has_data, "ikp_dimensions_used"] = dims_used[has_data]
    
    # Kategori (vectorized)
    ikp = res["ikp_score"]
    res.loc[ikp >= 80, "ikp_category"] = "Wajar"
    res.loc[(ikp >= 60) & (ikp < 80), "ikp_category"] = "Cukup Wajar"
    res.loc[(ikp < 60) & ikp.notna(), "ikp_category"] = "Tidak Wajar"
            
    return res
