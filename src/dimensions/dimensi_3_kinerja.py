"""
Dimensi 3 - Kewajaran Kinerja (Matriks Efisiensi × Efektivitas).

Mengevaluasi kewajaran kinerja sub-kegiatan menggunakan dua sumbu independen:
  1. Efisiensi (Input/Proses): BSK Usulan vs rata-rata BSK historis
     → "Apakah anggaran yang diusulkan wajar dibanding historis?"
  2. Efektivitas (Output/Hasil): Target Usulan vs Target Prognosis
     → "Apakah target output sesuai kemampuan historis?"

Klasifikasi 3x3 (9 Skenario - Matriks Evaluasi Kondisi Kinerja):
                   Output Rendah        Output Optimal       Output Tinggi
                   (Rasio < 0.9)      (0.9 ≤ Rasio ≤ 1.1)   (Rasio > 1.1)
  ┌─────────────────────────┬─────────────────────┬─────────────────────────┐
  │ Tidak Wajar/Sangat Boros│   Kurang Efisien    │ Anggaran Berlebih(Boros)│ BSK Boros
  │  Input↑ Output↓         │   Input↑ Output=    │ Input↑ Output↑          │ (Rasio > 1.1)
  ├─────────────────────────┼─────────────────────┼─────────────────────────┤
  │   Kinerja Kurang        │  Normal / Wajar     │       Ideal             │ BSK Wajar
  │  Input= Output↓         │   Input= Output=    │ Input= Output↑          │ (0.9 ≤ Rasio ≤ 1.1)
  ├─────────────────────────┼─────────────────────┼─────────────────────────┤
  │     Kurang Dana         │      Efisien        │    Sangat Efisien       │ BSK Hemat
  │  Input↓ Output↓         │   Input↓ Output=    │ Input↓ Output↑          │ (Rasio < 0.9)
  └─────────────────────────┴─────────────────────┴─────────────────────────┘

Tidak ada hardcode - jika tidak ada data realisasi historis, skor = NaN.
"""
import pandas as pd
import numpy as np

# Threshold klasifikasi 3x3
# Sumbu Efisiensi (Input)
EFISIENSI_LOW = 0.9
EFISIENSI_HIGH = 1.1

# Sumbu Efektivitas (Output)
EFEKTIVITAS_LOW = 0.9
EFEKTIVITAS_HIGH = 1.1


# Gaussian Decay sigma (calibrated: ratio=2 atau ratio=0.5 → score ≈ 50)
SIGMA_R = np.log(2.0) / np.sqrt(2 * np.log(2))  # ≈ 0.5888


def calculate(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    res = df.copy()

    # ── Init output columns ──
    res["dimensi_3_score"] = np.nan
    res["efficiency_riil"] = np.nan
    res["hist_efficiency_avg"] = np.nan
    res["hist_pagu_avg"] = np.nan
    res["prognosis_output"] = np.nan
    res["efisiensi_ratio"] = np.nan
    res["efektivitas_ratio"] = np.nan
    res["efisiensi_label"] = ""
    res["efektivitas_label"] = ""
    res["dimensi_3_kondisi"] = ""
    res["score_efisiensi"] = np.nan
    res["score_efektivitas"] = np.nan

    # ── Step 1: Hitung Efisiensi Riil (dari data realisasi historis) ──
    valid_real = (res["realisasi_anggaran"].notna()) & (res["realisasi_anggaran"] > 0)
    res.loc[valid_real, "efficiency_riil"] = (
        res.loc[valid_real, "realisasi_target"] / res.loc[valid_real, "realisasi_anggaran"]
    )

    groupby_cols = ["kodepemda", "kodesubkegiatan", "satuan", "tahun"]
    group_key = ["kodepemda", "kodesubkegiatan", "satuan"]
    skeleton = res[groupby_cols].drop_duplicates()

    # ── Step 2a: hist_efficiency_avg (rata-rata efisiensi tahun SEBELUMNYA) ──
    valid_eff = res["efficiency_riil"].notna() & (res["efficiency_riil"] > 0)
    hist_df = res[valid_eff][groupby_cols + ["efficiency_riil"]]

    if not hist_df.empty:
        hist_agg = hist_df.groupby(groupby_cols)["efficiency_riil"].agg(['sum', 'count']).reset_index()
        yearly_stats = pd.merge(skeleton, hist_agg, on=groupby_cols, how="left")
        yearly_stats["sum"] = yearly_stats["sum"].fillna(0)
        yearly_stats["count"] = yearly_stats["count"].fillna(0)

        yearly_stats = yearly_stats.sort_values(by=groupby_cols)

        yearly_stats["cum_sum"] = yearly_stats.groupby(group_key)["sum"].cumsum()
        yearly_stats["cum_count"] = yearly_stats.groupby(group_key)["count"].cumsum()

        yearly_stats["hist_sum"] = yearly_stats.groupby(group_key)["cum_sum"].shift(1)
        yearly_stats["hist_count"] = yearly_stats.groupby(group_key)["cum_count"].shift(1)

        yearly_stats["hist_efficiency_avg"] = yearly_stats["hist_sum"] / yearly_stats["hist_count"]

        res = res.drop(columns=["hist_efficiency_avg"], errors="ignore")
        res = res.merge(
            yearly_stats[groupby_cols + ["hist_efficiency_avg"]],
            on=groupby_cols, how="left"
        )

    # ── Step 2b: hist_pagu_avg (rata-rata pagu tahun SEBELUMNYA) ──
    valid_pagu = res["pagu"].notna() & (res["pagu"] > 0)
    hist_pagu_df = res[valid_pagu][groupby_cols + ["pagu"]]

    if not hist_pagu_df.empty:
        pagu_agg = hist_pagu_df.groupby(groupby_cols)["pagu"].agg(['sum', 'count']).reset_index()
        yearly_pagu = pd.merge(skeleton, pagu_agg, on=groupby_cols, how="left")
        yearly_pagu["sum"] = yearly_pagu["sum"].fillna(0)
        yearly_pagu["count"] = yearly_pagu["count"].fillna(0)

        yearly_pagu = yearly_pagu.sort_values(by=groupby_cols)

        yearly_pagu["cum_sum"] = yearly_pagu.groupby(group_key)["sum"].cumsum()
        yearly_pagu["cum_count"] = yearly_pagu.groupby(group_key)["count"].cumsum()

        yearly_pagu["hist_sum"] = yearly_pagu.groupby(group_key)["cum_sum"].shift(1)
        yearly_pagu["hist_count"] = yearly_pagu.groupby(group_key)["cum_count"].shift(1)

        yearly_pagu["hist_pagu_avg"] = yearly_pagu["hist_sum"] / yearly_pagu["hist_count"]

        res = res.drop(columns=["hist_pagu_avg"], errors="ignore")
        res = res.merge(
            yearly_pagu[groupby_cols + ["hist_pagu_avg"]],
            on=groupby_cols, how="left"
        )

    # ── Step 3: Prognosis Output ──
    valid_prog = (
        res["pagu"].notna() & (res["pagu"] > 0) &
        res["hist_efficiency_avg"].notna() & (res["hist_efficiency_avg"] > 0)
    )
    if valid_prog.any():
        res.loc[valid_prog, "prognosis_output"] = (
            res.loc[valid_prog, "pagu"] * res.loc[valid_prog, "hist_efficiency_avg"]
        )

    # ── Step 4: Efektivitas Ratio (target / prognosis) ──
    valid_efk = (
        valid_prog &
        res["target"].notna() & (res["target"] > 0) &
        res["prognosis_output"].notna() & (res["prognosis_output"] > 0)
    )
    if valid_efk.any():
        res.loc[valid_efk, "efektivitas_ratio"] = (
            res.loc[valid_efk, "target"] / res.loc[valid_efk, "prognosis_output"]
        )

    # ── Step 5: Efisiensi Ratio (bsk / historical_bsk_avg) ──
    valid_bsk = (res["pagu"] > 0) & (res["target"].notna()) & (res["target"] > 0)
    res.loc[valid_bsk, "bsk"] = res.loc[valid_bsk, "pagu"] / res.loc[valid_bsk, "target"]

    valid_efs = (
        res["bsk"].notna() & (res["bsk"] > 0) &
        res["historical_bsk_avg"].notna() & (res["historical_bsk_avg"] > 0)
    )
    if valid_efs.any():
        res.loc[valid_efs, "efisiensi_ratio"] = (
            res.loc[valid_efs, "bsk"] / res.loc[valid_efs, "historical_bsk_avg"]
        )

    # ── Step 6: Labels ──
    efs = res["efisiensi_ratio"]
    efk = res["efektivitas_ratio"]

    # Efisiensi: BSK/historical_bsk_avg
    res.loc[efs.notna() & (efs < EFISIENSI_LOW), "efisiensi_label"] = "Hemat"
    res.loc[efs.notna() & (efs >= EFISIENSI_LOW) & (efs <= EFISIENSI_HIGH), "efisiensi_label"] = "Wajar"
    res.loc[efs.notna() & (efs > EFISIENSI_HIGH), "efisiensi_label"] = "Boros"

    # Efektivitas: target/prognosis
    res.loc[efk.notna() & (efk < EFEKTIVITAS_LOW), "efektivitas_label"] = "Rendah"
    res.loc[efk.notna() & (efk >= EFEKTIVITAS_LOW) & (efk <= EFEKTIVITAS_HIGH), "efektivitas_label"] = "Optimal"
    res.loc[efk.notna() & (efk > EFEKTIVITAS_HIGH), "efektivitas_label"] = "Tinggi"

    # ── Step 7: Klasifikasi Kuadran (Matriks 3x3) ──
    efs_h = res["efisiensi_label"] == "Hemat"
    efs_w = res["efisiensi_label"] == "Wajar"
    efs_b = res["efisiensi_label"] == "Boros"

    efk_r = res["efektivitas_label"] == "Rendah"
    efk_o = res["efektivitas_label"] == "Optimal"
    efk_t = res["efektivitas_label"] == "Tinggi"

    has_efs = efs.notna()
    has_efk = efk.notna()
    both = has_efs & has_efk

    # Matriks penuh (kedua sumbu tersedia)
    # Output Tinggi:
    res.loc[both & efk_t & efs_h, "dimensi_3_kondisi"] = "Sangat Efisien"
    res.loc[both & efk_t & efs_w, "dimensi_3_kondisi"] = "Ideal"
    res.loc[both & efk_t & efs_b, "dimensi_3_kondisi"] = "Anggaran Berlebih (Boros)"

    # Output Optimal:
    res.loc[both & efk_o & efs_h, "dimensi_3_kondisi"] = "Efisien"
    res.loc[both & efk_o & efs_w, "dimensi_3_kondisi"] = "Normal / Wajar"
    res.loc[both & efk_o & efs_b, "dimensi_3_kondisi"] = "Kurang Efisien"

    # Output Rendah:
    res.loc[both & efk_r & efs_h, "dimensi_3_kondisi"] = "Kurang Dana"
    res.loc[both & efk_r & efs_w, "dimensi_3_kondisi"] = "Kinerja Kurang"
    res.loc[both & efk_r & efs_b, "dimensi_3_kondisi"] = "Tidak Wajar / Sangat Boros"

    # Hanya efektivitas tersedia (tanpa data hist_pagu)
    only_efk = ~has_efs & has_efk
    res.loc[only_efk & efk_t, "dimensi_3_kondisi"] = "Ideal"
    res.loc[only_efk & efk_o, "dimensi_3_kondisi"] = "Normal / Wajar"
    res.loc[only_efk & efk_r, "dimensi_3_kondisi"] = "Tidak Wajar / Sangat Boros"

    # ── Step 8: Skor (Asymmetric Gaussian Decay) ──
    # Efisiensi: hanya penalti jika ratio > 1 (budget lebih tinggi dari historis)
    valid_se = has_efs & (efs > 0)
    if valid_se.any():
        efs_vals = efs[valid_se].values
        score_efs = np.where(
            efs_vals <= 1.0,
            100.0,
            100.0 * np.exp(-0.5 * (np.log(efs_vals) / SIGMA_R) ** 2)
        )
        res.loc[valid_se, "score_efisiensi"] = score_efs

    # Efektivitas: hanya penalti jika ratio < 1 (target lebih rendah dari prognosis)
    valid_sek = has_efk & (efk > 0)
    if valid_sek.any():
        efk_vals = efk[valid_sek].values
        score_efk = np.where(
            efk_vals >= 1.0,
            100.0,
            100.0 * np.exp(-0.5 * (np.log(efk_vals) / SIGMA_R) ** 2)
        )
        res.loc[valid_sek, "score_efektivitas"] = score_efk

    # Skor gabungan
    has_both_scores = res["score_efisiensi"].notna() & res["score_efektivitas"].notna()
    has_only_efk_score = res["score_efisiensi"].isna() & res["score_efektivitas"].notna()
    has_only_efs_score = res["score_efisiensi"].notna() & res["score_efektivitas"].isna()

    res.loc[has_both_scores, "dimensi_3_score"] = (
        0.5 * res.loc[has_both_scores, "score_efisiensi"] +
        0.5 * res.loc[has_both_scores, "score_efektivitas"]
    )
    res.loc[has_only_efk_score, "dimensi_3_score"] = res.loc[has_only_efk_score, "score_efektivitas"]
    res.loc[has_only_efs_score, "dimensi_3_score"] = res.loc[has_only_efs_score, "score_efisiensi"]

    return res
