"""
Dimensi 3 – Kewajaran Kinerja (Analisis Prognosis).
Mengevaluasi kewajaran target usulan berdasarkan efisiensi historis.
Tidak ada hardcode — jika tidak ada data realisasi historis, skor = NaN.
"""
import pandas as pd
import numpy as np

def calculate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
        
    res = df.copy()
    res["dimensi_3_score"] = np.nan
    res["efficiency_riil"] = np.nan
    res["hist_efficiency_avg"] = np.nan
    res["prognosis_output"] = np.nan
    
    # 1. Hitung Efisiensi Riil untuk baris yang memiliki data realisasi
    valid_real = (res["realisasi_anggaran"].notna()) & (res["realisasi_anggaran"] > 0)
    res.loc[valid_real, "efficiency_riil"] = (
        res.loc[valid_real, "realisasi_target"] / res.loc[valid_real, "realisasi_anggaran"]
    )
    
    # 2. Untuk setiap baris, hitung rata-rata efisiensi dari tahun SEBELUMNYA (strictly <)
    valid_eff = res["efficiency_riil"].notna() & (res["efficiency_riil"] > 0)
    hist_df = res[valid_eff][["kodepemda", "kodesubkegiatan", "satuan", "tahun", "efficiency_riil"]]
    
    groupby_cols = ["kodepemda", "kodesubkegiatan", "satuan", "tahun"]
    skeleton = res[groupby_cols].drop_duplicates()
    
    if not hist_df.empty:
        hist_agg = hist_df.groupby(groupby_cols)["efficiency_riil"].agg(['sum', 'count']).reset_index()
        yearly_stats = pd.merge(skeleton, hist_agg, on=groupby_cols, how="left")
        yearly_stats["sum"] = yearly_stats["sum"].fillna(0)
        yearly_stats["count"] = yearly_stats["count"].fillna(0)
        
        yearly_stats = yearly_stats.sort_values(by=groupby_cols)
        
        yearly_stats["cum_sum"] = yearly_stats.groupby(["kodepemda", "kodesubkegiatan", "satuan"])["sum"].cumsum()
        yearly_stats["cum_count"] = yearly_stats.groupby(["kodepemda", "kodesubkegiatan", "satuan"])["count"].cumsum()
        
        yearly_stats["hist_sum"] = yearly_stats.groupby(["kodepemda", "kodesubkegiatan", "satuan"])["cum_sum"].shift(1)
        yearly_stats["hist_count"] = yearly_stats.groupby(["kodepemda", "kodesubkegiatan", "satuan"])["cum_count"].shift(1)
        
        yearly_stats["hist_efficiency_avg"] = yearly_stats["hist_sum"] / yearly_stats["hist_count"]
        
        res = res.drop(columns=["hist_efficiency_avg"], errors="ignore")
        res = res.merge(yearly_stats[["kodepemda", "kodesubkegiatan", "satuan", "tahun", "hist_efficiency_avg"]],
                        on=groupby_cols,
                        how="left")
                        
        # 3. Prognosis Output
        valid_calc = res["pagu"].notna() & (res["pagu"] > 0) & res["hist_efficiency_avg"].notna() & (res["hist_efficiency_avg"] > 0)
        
        if valid_calc.any():
            prognosis = res.loc[valid_calc, "pagu"] * res.loc[valid_calc, "hist_efficiency_avg"]
            res.loc[valid_calc, "prognosis_output"] = prognosis
            
            # Locke & Latham's (1990) SMART Goal Setting and Performance Realism model:
            # Score = 100 * exp(-0.5 * (ln(ratio) / sigma_r)^2)
            # Calibrated so that a 50% under-achievement (ratio = 0.5) or 200% unrealistic promise (ratio = 2.0) yields exactly 50.0.
            # sigma_r = ln(2.0) / sqrt(2 * ln(2)) ≈ 0.5888
            sigma_r = np.log(2.0) / np.sqrt(2 * np.log(2))
            valid_target = valid_calc & res["target"].notna() & (res["target"] > 0) & (res["prognosis_output"] > 0)
            ratio = res.loc[valid_target, "target"] / res.loc[valid_target, "prognosis_output"]
            score = 100.0 * np.exp(-0.5 * (np.log(ratio) / sigma_r) ** 2)
            
            res.loc[valid_target, "dimensi_3_score"] = score
    
    return res
