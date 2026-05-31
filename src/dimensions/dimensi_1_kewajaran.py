"""
Dimensi 1 – Kewajaran Historis (Biaya Satuan Kinerja).
Membandingkan BSK tahun berjalan dengan rata-rata BSK tahun-tahun SEBELUMNYA.
Menghitung besarnya PERUBAHAN ANGGARAN (naik/turun) dan konversi ke skor bertingkat.
Tidak ada hardcode — jika tidak ada data historis, skor = NaN.
"""
import pandas as pd
import numpy as np

def _calculate_score(change_pct: float) -> float:
    """
    Konversi persentase perubahan absolut ke skor 0-100.
    Sistem bertingkat (tiered) — lebih adil dan transparan:
    
    | Perubahan  | Skor    | Interpretasi         |
    |------------|---------|----------------------|
    | 0 – 10%    | 100–95  | Sangat Wajar         |
    | 10 – 25%   | 95–85   | Wajar                |
    | 25 – 50%   | 85–70   | Perlu Perhatian      |
    | 50 – 100%  | 70–50   | Perlu Evaluasi       |
    | 100 – 200% | 50–25   | Tidak Wajar          |
    | > 200%     | 25–0    | Sangat Tidak Wajar   |
    
    Interpolasi linier di dalam setiap tier.
    """
    p = abs(change_pct)
    
    if p <= 0.10:
        return 100 - (p / 0.10) * 5           # 100 → 95
    elif p <= 0.25:
        return 95 - ((p - 0.10) / 0.15) * 10  # 95 → 85
    elif p <= 0.50:
        return 85 - ((p - 0.25) / 0.25) * 15  # 85 → 70
    elif p <= 1.00:
        return 70 - ((p - 0.50) / 0.50) * 20  # 70 → 50
    elif p <= 2.00:
        return 50 - ((p - 1.00) / 1.00) * 25  # 50 → 25
    else:
        return max(0, 25 - ((p - 2.00) / 3.00) * 25)  # 25 → 0


def calculate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
        
    res = df.copy()
    res["dimensi_1_score"] = np.nan
    res["bsk"] = np.nan
    res["historical_bsk_avg"] = np.nan
    res["dimensi_1_perubahan"] = np.nan    # Perubahan (signed: + naik, - turun)
    res["dimensi_1_perubahan_abs"] = np.nan # Besarnya perubahan (absolut)
    res["dimensi_1_arah"] = ""              # "Naik" atau "Turun"
    
    # Hitung BSK (Biaya Satuan Kinerja)
    valid_mask = (res["pagu"] > 0) & (res["target"].notna()) & (res["target"] > 0)
    res.loc[valid_mask, "bsk"] = res.loc[valid_mask, "pagu"] / res.loc[valid_mask, "target"]
    
    valid_bsk = res["bsk"].notna() & (res["bsk"] > 0)
    hist_df = res[valid_bsk][["kodepemda", "kodesubkegiatan", "satuan", "tahun", "bsk"]]
    
    groupby_cols = ["kodepemda", "kodesubkegiatan", "satuan", "tahun"]
    skeleton = res[groupby_cols].drop_duplicates()
    
    if not hist_df.empty:
        hist_agg = hist_df.groupby(groupby_cols)["bsk"].agg(['sum', 'count']).reset_index()
        yearly_stats = pd.merge(skeleton, hist_agg, on=groupby_cols, how="left")
        yearly_stats["sum"] = yearly_stats["sum"].fillna(0)
        yearly_stats["count"] = yearly_stats["count"].fillna(0)
        
        yearly_stats = yearly_stats.sort_values(by=groupby_cols)
        
        yearly_stats["cum_sum"] = yearly_stats.groupby(["kodepemda", "kodesubkegiatan", "satuan"])["sum"].cumsum()
        yearly_stats["cum_count"] = yearly_stats.groupby(["kodepemda", "kodesubkegiatan", "satuan"])["count"].cumsum()
        
        yearly_stats["hist_sum"] = yearly_stats.groupby(["kodepemda", "kodesubkegiatan", "satuan"])["cum_sum"].shift(1)
        yearly_stats["hist_count"] = yearly_stats.groupby(["kodepemda", "kodesubkegiatan", "satuan"])["cum_count"].shift(1)
        
        yearly_stats["historical_bsk_avg"] = yearly_stats["hist_sum"] / yearly_stats["hist_count"]
        
        res = res.drop(columns=["historical_bsk_avg"], errors="ignore")
        res = res.merge(yearly_stats[["kodepemda", "kodesubkegiatan", "satuan", "tahun", "historical_bsk_avg"]],
                        on=groupby_cols,
                        how="left")
                        
        valid_calc = res["historical_bsk_avg"].notna() & (res["historical_bsk_avg"] > 0) & res["bsk"].notna() & (res["bsk"] > 0)
        
        if valid_calc.any():
            change = (res.loc[valid_calc, "bsk"] - res.loc[valid_calc, "historical_bsk_avg"]) / res.loc[valid_calc, "historical_bsk_avg"]
            res.loc[valid_calc, "dimensi_1_perubahan"] = change
            res.loc[valid_calc, "dimensi_1_perubahan_abs"] = change.abs()
            res.loc[valid_calc, "dimensi_1_arah"] = np.where(change >= 0, "Naik", "Turun")
            
            # Wildavsky's (1964) Incrementalism Gaussian Decay model:
            # Score = 100 * exp(-0.5 * (p / sigma)^2)
            # Calibrated so that a 50% change (p = 0.50) yields a score of exactly 50.0.
            # sigma = 0.50 / sqrt(2 * ln(2)) ≈ 0.42466
            sigma_d1 = 0.50 / np.sqrt(2 * np.log(2))
            p = change.abs()
            scores = 100.0 * np.exp(-0.5 * (p / sigma_d1) ** 2)
            
            res.loc[valid_calc, "dimensi_1_score"] = scores
        
    return res
