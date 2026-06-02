import streamlit as st
import pandas as pd
import numpy as np
from src.pipeline import get_processed_data
from src.ui_helpers import inject_css, render_sidebar, render_header, format_currency, format_number, render_badge

st.set_page_config(page_title="Detail Per Dimensi", layout="wide")
inject_css()
render_sidebar()
render_header()

st.title("[Doc] Detail Kalkulasi Per Dimensi")
st.markdown("Halaman ini menyajikan rincian teknis perhitungan setiap dimensi kewajaran untuk suatu sub-kegiatan.")

df = get_processed_data()

if df.empty:
    st.warning("Data tidak tersedia.")
    st.stop()

# Filters
col1, col2, col3 = st.columns([1, 2, 3])

# Read query params
q_tahun = st.query_params.get("tahun")
q_pemda = st.query_params.get("pemda")
q_sub = st.query_params.get("sub")

with col1:
    years = sorted(df["tahun"].dropna().unique())
    y_idx = 0
    if q_tahun and int(q_tahun) in years:
        y_idx = years.index(int(q_tahun))
    selected_year = st.selectbox("Pilih Tahun", years, index=y_idx)

with col2:
    pemdas = sorted(df["pemda_label"].dropna().unique())
    p_idx = 0
    if q_pemda and q_pemda in pemdas:
        p_idx = pemdas.index(q_pemda)
    selected_pemda = st.selectbox("Pilih Pemda", pemdas, index=p_idx)

pemda_df = df[(df["pemda_label"] == selected_pemda) & (df["tahun"] == selected_year)]

with col3:
    if pemda_df.empty:
        st.warning("Tidak ada data untuk kombinasi Tahun dan Pemda ini.")
        st.stop()
    
    # Just show the subkegiatan name, code is handled internally
    sub_options = pemda_df.apply(lambda row: f"[{row['kodesubkegiatan']}] {row['uraisubkegiatan']}", axis=1).tolist()
    
    s_idx = 0
    if q_sub:
        # Find the option that starts with [q_sub]
        for idx, opt in enumerate(sub_options):
            if opt.startswith(f"[{q_sub}]"):
                s_idx = idx
                break
                
    selected_sub = st.selectbox("Pilih Sub-Kegiatan", sub_options, index=s_idx)

if selected_sub:
    # Extract code
    kode = selected_sub.split("]")[0][1:]
    
    row_df = pemda_df[pemda_df["kodesubkegiatan"] == kode]
    
    if not row_df.empty:
        row = row_df.iloc[0]
        
        st.divider()
        st.subheader("Informasi Dasar")
        info_df = pd.DataFrame({
            "Informasi": [
                "Pemerintah Daerah",
                "Tahun Anggaran",
                "Kode Sub-Kegiatan",
                "Program", 
                "Kegiatan", 
                "Sub-Kegiatan",
                "Indikator Kinerja", 
                "Target", 
                "Pagu Anggaran"
            ],
            "Keterangan": [
                row.get("pemda_label", "-"),
                str(row.get("tahun", "-")),
                row.get("kodesubkegiatan", "-"),
                row.get("uraiprogram", "-"),
                row.get("uraikegiatan", "-"),
                row.get("uraisubkegiatan", "-"),
                row.get("indikator", "-"),
                f"{row.get('target', '-')} {row.get('satuan', '-')}",
                format_currency(row.get("pagu", 0))
            ]
        })
        st.dataframe(info_df, use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown("<h2 style='text-align:center;color:#1e3a8a;margin-bottom:30px;'>[Rekap] Rekapitulasi Indeks Kewajaran Penganggaran (IKP)</h2>", unsafe_allow_html=True)
        
        from src.ikp_calculator import WEIGHTS, DIM_LABELS
        
        final_score = row.get("ikp_score", pd.NA)
        category = row.get("ikp_category", "Tidak Dapat Dinilai")
        total_weight_used = row.get("ikp_total_weight", 0)
        dims_used = row.get("ikp_dimensions_used", 0)
        
        # Build calculation data - SAME logic as pipeline
        calc_data = []
        raw_total = 0
        valid_weight = 0
        for dim_key, weight in WEIGHTS.items():
            raw_score = row.get(dim_key, np.nan)
            is_valid = pd.notna(raw_score)
            weighted_val = (raw_score * weight) if is_valid else 0
            if is_valid:
                raw_total += weighted_val
                valid_weight += weight
            
            calc_data.append({
                "Dimensi": DIM_LABELS.get(dim_key, dim_key),
                "Skor": format_number(raw_score, 1) if is_valid else "N/A",
                "Bobot": f"{weight*100:.0f}%",
                "Perhitungan": f"{format_number(raw_score, 1)} &times; {weight*100:.0f}%" if is_valid else "-",
                "Tertimbang": format_number(weighted_val, 2) if is_valid else "-",
                "valid": is_valid
            })
        
        # Recalculate effective weights now that we know valid_weight
        for item in calc_data:
            if not item["valid"]:
                item["Bobot Efektif"] = "-"
            else:
                orig_w = float(item["Bobot"].replace("%","")) / 100
                eff = orig_w / valid_weight * 100 if valid_weight > 0 else 0
                item["Bobot Efektif"] = f"{eff:.1f}%"
            
        col_calc, col_total = st.columns([2.2, 1])
        
        with col_calc:
            st.markdown("<h4 style='margin-bottom:20px;'>Detail Komponen Penimbang</h4>", unsafe_allow_html=True)
            
            # Show dynamic weighting notice if not all dimensions available
            if valid_weight < 1.0:
                st.warning(f"[Warning] Hanya {int(dims_used)} dari 5 dimensi yang memiliki data. Bobot di-redistribusi secara proporsional (Dynamic Weighting).")
            
            table_rows = ""
            for item in calc_data:
                style_na = "opacity:0.5;" if not item["valid"] else ""
                table_rows += f"<tr style='{style_na}'><td style='padding:12px;border-bottom:1px solid #e2e8f0;'>{item['Dimensi']}</td><td style='padding:12px;border-bottom:1px solid #e2e8f0;text-align:center;'>{item['Skor']}</td><td style='padding:12px;border-bottom:1px solid #e2e8f0;text-align:center;'>{item['Bobot']}</td><td style='padding:12px;border-bottom:1px solid #e2e8f0;text-align:center;'>{item['Bobot Efektif']}</td><td style='padding:12px;border-bottom:1px solid #e2e8f0;text-align:center;color:#64748b;font-size:0.9em;white-space:nowrap;'>{item['Perhitungan']}</td><td style='padding:12px;border-bottom:1px solid #e2e8f0;text-align:right;font-weight:bold;'>{item['Tertimbang']}</td></tr>"
            
            # Footer row with totals
            table_rows += f"<tr style='background:#f1f5f9;font-weight:bold;'><td style='padding:12px;' colspan='2'>TOTAL</td><td style='padding:12px;text-align:center;'>{valid_weight*100:.0f}%</td><td style='padding:12px;text-align:center;'>100%</td><td style='padding:12px;text-align:center;'></td><td style='padding:12px;text-align:right;'>{format_number(raw_total, 2)}</td></tr>"
            table_rows += f"<tr style='background:#1e3a8a;color:white;font-weight:bold;'><td style='padding:12px;' colspan='5'>IKP = Total Tertimbang / Bobot Tersedia = {format_number(raw_total, 2)} / {format_number(valid_weight, 2)}</td><td style='padding:12px;text-align:right;font-size:1.2em;'>{format_number(final_score, 1)}</td></tr>"
            
            full_table_html = (
                f"<div style='overflow-x:auto;'>"
                f"<table style='width:100%;border-collapse:collapse;font-family:sans-serif;'>"
                f"<thead style='background-color:#f8fafc;'><tr>"
                f"<th style='padding:12px;text-align:left;border-bottom:2px solid #cbd5e1;color:#475569;'>KOMPONEN</th>"
                f"<th style='padding:12px;text-align:center;border-bottom:2px solid #cbd5e1;color:#475569;'>SKOR</th>"
                f"<th style='padding:12px;text-align:center;border-bottom:2px solid #cbd5e1;color:#475569;'>BOBOT</th>"
                f"<th style='padding:12px;text-align:center;border-bottom:2px solid #cbd5e1;color:#475569;'>EFEKTIF</th>"
                f"<th style='padding:12px;text-align:center;border-bottom:2px solid #cbd5e1;color:#475569;'>PERHITUNGAN</th>"
                f"<th style='padding:12px;text-align:right;border-bottom:2px solid #cbd5e1;color:#475569;'>TERTIMBANG</th>"
                f"</tr></thead><tbody>{table_rows}</tbody></table>"
                f"</div>"
            )
            
            st.markdown(full_table_html, unsafe_allow_html=True)
            
        with col_total:
            # Scoreboard Premium
            ikp_color = "#4ade80" if pd.notna(final_score) and final_score >= 80 else "#facc15" if pd.notna(final_score) and final_score >= 60 else "#ef4444"
            st.markdown(f"""
            <div style='background:linear-gradient(135deg,#1e3a8a 0%,#3b82f6 100%);padding:30px;border-radius:20px;color:white;text-align:center;box-shadow:0 10px 25px -5px rgba(30,58,138,0.3);'>
                <div style='font-size:0.9rem;text-transform:uppercase;letter-spacing:0.1em;opacity:0.9;'>Indeks Kewajaran Penganggaran</div>
                <div style='font-size:5rem;font-weight:800;margin:10px 0;'>{format_number(final_score, 1)}</div>
                <div style='display:inline-block;padding:8px 20px;background:rgba(255,255,255,0.2);border-radius:50px;font-weight:700;font-size:1.1rem;'>
                    {category}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"IKP dihitung dengan **Dynamic Weighting**: {int(dims_used)}/5 dimensi tersedia. Bobot didistribusikan secara proporsional ke dimensi yang memiliki data valid.")


        st.divider()
        
        # DIMENSI 1
        st.subheader("Dimensi 1: Kewajaran Historis (Biaya Satuan Kinerja)")
        with st.container(border=True):
            d1_score = row.get("dimensi_1_score", pd.NA)
            
            st.markdown(r"""
            **Metodologi - Incremental Budgeting (Wildavsky, 1964):**  
            Mengevaluasi stabilitas dan prediktabilitas perencanaan anggaran dengan membandingkan Biaya Satuan Kinerja (BSK) tahun berjalan terhadap rata-rata historis tahun-tahun sebelumnya. Deviasi dari stabilitas historis dihitung menggunakan **Gaussian Decay Function**.
            
            **Formula Gaussian Decay (Wildavsky):**
            $$\text{Score} = 100 \times \exp\left(-\frac{1}{2}\left(\frac{|x|}{\sigma}\right)^2\right), \quad \sigma = \frac{0{,}50}{\sqrt{2 \ln 2}} \approx 0{,}425$$
            
            *Di mana $x$ adalah persentase perubahan BSK terhadap historis. Konstanta $\sigma$ dikalibrasi agar deviasi $\pm 50\%$ (non-incremental budget shift) menghasilkan skor tepat 50.*
            """)
            
            c1, c2, c3, c4 = st.columns(4)
            bsk = row.get("bsk", pd.NA)
            hist_avg = row.get("historical_bsk_avg", pd.NA)
            change = row.get("dimensi_1_perubahan", pd.NA)
            change_abs = row.get("dimensi_1_perubahan_abs", pd.NA)
            arah = row.get("dimensi_1_arah", "")
            
            c1.metric("BSK Saat Ini", format_currency(bsk) if pd.notna(bsk) else "-")
            c2.metric("Rata-rata BSK Historis", format_currency(hist_avg) if pd.notna(hist_avg) else "-")
            
            if pd.notna(change):
                arrow = "" if change >= 0 else ""
                c3.metric("Perubahan Anggaran", f"{arrow} {arah} {change_abs*100:.1f}%")
            else:
                c3.metric("Perubahan Anggaran", "-")
            
            if pd.isna(d1_score):
                c4.metric("Skor Dimensi 1", "Tidak Ada Data")
            else:
                c4.metric("Skor Dimensi 1", f"{d1_score:.1f} / 100")
            
            # Detail Perhitungan Transparan
            if pd.notna(bsk) and pd.notna(hist_avg) and pd.notna(change):
                sigma_val = 0.50 / np.sqrt(2 * np.log(2))
                pagu_val = row.get('pagu', 0)
                target_val = row.get('target', 0)
                score_verify = 100 * np.exp(-0.5 * (abs(change) / sigma_val) ** 2)
                
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:20px;border-radius:12px;border:1px solid #c7d2fe;margin:12px 0;'>
                <h4 style='color:#1e3a8a;margin:0 0 16px 0;'>[Kalkulasi] Langkah Perhitungan Dimensi 1</h4>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 1 - Hitung Biaya Satuan Kinerja (BSK)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>BSK = Pagu Anggaran / Target Output</span><br>
                <code style='font-size:0.95em;'>BSK = {format_currency(pagu_val)} / {format_number(target_val, 2)} = <b>{format_currency(bsk)}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 2 - Ambil Rata-rata BSK Historis</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Rata-rata BSK dari tahun-tahun sebelumnya (lihat tabel di bawah)</span><br>
                <code style='font-size:0.95em;'>BSK Historis = <b>{format_currency(hist_avg)}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #f59e0b;'>
                <b style='color:#92400e;'>Langkah 3 - Hitung Persentase Perubahan (x)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>x = (BSK Sekarang - BSK Historis) / BSK Historis</span><br>
                <code style='font-size:0.95em;'>x = ({format_currency(bsk)} - {format_currency(hist_avg)}) / {format_currency(hist_avg)}</code><br>
                <code style='font-size:0.95em;'>x = <b>{change:+.4f}</b> -> Perubahan <b>{arah} {change_abs*100:.1f}%</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #10b981;'>
                <b style='color:#065f46;'>Langkah 4 - Penilaian Skor (Sistem Penalti Lengkung/Gaussian)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Jika persentase perubahan 0%, maka skor 100. Semakin besar perubahannya ({change_abs*100:.1f}%), sistem penalti matematis (Gaussian) akan semakin memotong skornya secara melengkung ke bawah. Batas toleransi wajar (sigma) ditetapkan di kisaran {sigma_val*100:.1f}%.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Kalkulasi: 100 x exp(-0.5 x ({change_abs:.4f} / {sigma_val:.4f})^2)</code><br>
                <code style='font-size:1.1em;'><b style='color:#059669;'>Hasil Akhir -> Skor Dimensi 1 = {score_verify:.1f} dari 100</b></code>
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                tier_html = (
                    "<details style='margin-top:8px;'><summary style='cursor:pointer;color:#1e3a8a;font-weight:bold;font-size:0.85rem;'>[Chart] Tabel Referensi Skor (Gaussian Decay)</summary>"
                    "<table style='width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:8px;'>"
                    "<tr style='background:#f1f5f9;'><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Perubahan Absolut (\|x\|)</th><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Skor</th><th style='padding:8px;text-align:left;border-bottom:1px solid #cbd5e1;'>Interpretasi</th></tr>"
                    "<tr style='background:#f0fdf4;'><td style='padding:6px 8px;text-align:center;'>0% (Sempurna)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>100.0</td><td style='padding:6px 8px;color:#22c55e;'>Sangat Stabil (Sesuai Tren)</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>10% (Batas Aman Wildavsky)</td><td style='padding:6px 8px;text-align:center;'>97.3</td><td style='padding:6px 8px;color:#22c55e;'>Wajar / Incremental</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>25%</td><td style='padding:6px 8px;text-align:center;'>84.1</td><td style='padding:6px 8px;color:#eab308;'>Cukup Wajar</td></tr>"
                    "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50% (Batas Deviasi)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50.0</td><td style='padding:6px 8px;color:#ef4444;font-weight:bold;'>Batas Toleransi Non-Incremental</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>100% (Duplikasi/Reduksi)</td><td style='padding:6px 8px;text-align:center;'>6.3</td><td style='padding:6px 8px;color:#7f1d1d;'>Sangat Fluktuatif (Butuh Evaluasi)</td></tr>"
                    "</table>"
                    "<div style='margin-top:8px;font-size:0.8rem;color:#64748b;'>"
                    "<b>Referensi Akademik:</b> Wildavsky, A. (1964). <i>The Politics of the Budgetary Process</i>. Little, Brown."
                    "</div>"
                    "</details>"
                )
                st.markdown(tier_html, unsafe_allow_html=True)
            elif pd.isna(d1_score):
                st.caption("[Info] Dimensi ini tidak memiliki data historis pembanding, sehingga tidak berkontribusi terhadap IKP (Dynamic Weighting).")
            
            st.markdown("##### Data Historis Sub-Kegiatan Ini")
            # Fetch historical data
            hist_df = df[
                (df["kodepemda"] == row["kodepemda"]) & 
                (df["kodesubkegiatan"] == row["kodesubkegiatan"]) & 
                (df["satuan"] == row["satuan"]) & 
                (df["tahun"] < row["tahun"])
            ].sort_values(by="tahun", ascending=False)
            
            if hist_df.empty:
                st.info("Tidak ditemukan data historis di tahun sebelumnya untuk menjadi pembanding.")
            else:
                display_hist = hist_df[["tahun", "pagu", "target", "satuan"]].copy()
                display_hist["BSK (Biaya Satuan Kinerja)"] = display_hist["pagu"] / display_hist["target"]
                
                display_hist["pagu"] = display_hist["pagu"].apply(format_currency)
                display_hist["BSK (Biaya Satuan Kinerja)"] = display_hist["BSK (Biaya Satuan Kinerja)"].apply(format_currency)
                
                display_hist.rename(columns={
                    "tahun": "Tahun",
                    "pagu": "Pagu Anggaran",
                    "target": "Target",
                    "satuan": "Satuan"
                }, inplace=True)
                
                # Add No. column
                display_hist.insert(0, "No.", range(1, len(display_hist) + 1))
                
                st.dataframe(display_hist, use_container_width=True, hide_index=True)
        
        # DIMENSI 2
        st.subheader("Dimensi 2: Kewajaran Regional (Spatial Comparison)")
        with st.container(border=True):
            d2_score = row.get("dimensi_2_score", pd.NA)
            
            st.markdown(r"""
            **Metodologi - Spatial Autocorrelation (Anselin, 1995 - LISA):**  
            Menilai kewajaran BSK daerah dibandingkan dengan rata-rata regional menggunakan standar deviasi (**Z-Score**) melalui pendekatan *Leave-One-Out* (mengeluarkan daerah subjek dari perhitungan rata-rata regional). Deviasi dikonversi menggunakan **Asymmetric Gaussian Decay Function**.
            
            **Formula Asymmetric Z-Score Decay (LISA):**
            $$\text{Score} = 100 \times \exp\left(-\frac{1}{2}\left(\frac{z}{\sigma_z}\right)^2\right)$$
            $$\sigma_z = \begin{cases} \sigma_{\text{high}} \approx 1{,}665 & \text{jika } z \ge 0 \\ \sigma_{\text{low}} \approx 2{,}548 & \text{jika } z < 0 \end{cases}$$
            
            *Kalibrasi $\sigma_z$ dibuat asimetris karena under-budgeting ($z < 0$) dinilai lebih aman (toleransi tinggi, Score = 50 di $z = -3{,}0$) dibanding over-budgeting ($z \ge 0$, Score = 50 di batas kritis spatial outlier $z = 1{,}96$).*
            """)
            
            c1, c2, c3, c4 = st.columns(4)
            cpu = row.get("bsk", pd.NA)
            med_cpu = row.get("spasial_bsk_avg", pd.NA)
            std_cpu = row.get("spasial_bsk_std", pd.NA)
            z_score = row.get("dimensi_2_zscore", pd.NA)
            
            c1.metric("BSK Daerah Ini", format_currency(cpu) if pd.notna(cpu) else "-")
            c2.metric("Rata-rata Regional ()", format_currency(med_cpu) if pd.notna(med_cpu) else "-")
            c3.metric("Std. Deviasi ()", format_currency(std_cpu) if pd.notna(std_cpu) and std_cpu > 0 else "-")
            
            if pd.isna(d2_score):
                c4.metric("Skor Dimensi 2", "Tidak Ada Pembanding")
            else:
                c4.metric("Skor Dimensi 2", f"{d2_score:.1f} / 100")
            
            # Detail Perhitungan Transparan
            n_pemb = row.get("spasial_n_pembanding", 0)
            if pd.notna(z_score) and pd.notna(cpu) and pd.notna(med_cpu):
                az = abs(z_score)
                if az < 1.0: zona = "Wajar (|Z| < 1.0)"
                elif az < 1.96: zona = "Perlu Perhatian (1.0 <= |Z| < 1.96)"
                else: zona = "Outlier Regional (|Z| >= 1.96)"
                
                sigma_high = 1.96 / np.sqrt(2 * np.log(2))
                sigma_low = 3.00 / np.sqrt(2 * np.log(2))
                sigma_actual = sigma_high if z_score >= 0 else sigma_low
                sigma_label = "Over-budgeting (z>=0), sigma_high" if z_score >= 0 else "Under-budgeting (z<0), sigma_low"
                score_verify = 100 * np.exp(-0.5 * (z_score / sigma_actual) ** 2)
                std_display = format_currency(std_cpu) if pd.notna(std_cpu) and std_cpu > 0 else "0"
                
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:20px;border-radius:12px;border:1px solid #c7d2fe;margin:12px 0;'>
                <h4 style='color:#1e3a8a;margin:0 0 16px 0;'>[Kalkulasi] Langkah Perhitungan Dimensi 2</h4>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 1 - Kumpulkan Angka dari Daerah Lain (Pembanding)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Sistem mengumpulkan nilai BSK dari <b>{int(n_pemb)} daerah lain</b> yang memiliki kegiatan sama, <b>tanpa memasukkan daerah Anda sendiri</b>.</span><br>
                <span style='color:#64748b;font-size:0.85em;'>Dari data daerah lain tersebut, dicari Nilai Rata-Rata (Total BSK Daerah Lain / Jumlah Daerah) dan seberapa menyebar datanya (Standar Deviasi).</span><br>
                <code style='font-size:0.95em;'>Rata-rata Regional = Total BSK Daerah Lain / {int(n_pemb)} = <b>{format_currency(med_cpu)}</b></code><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>*Catatan: Anda bisa melihat rincian daerah lainnya di tabel pembanding di bawah.</code><br>
                <code style='font-size:0.95em;'>Standar Deviasi (Jarak Rata-rata Penyebaran) = <b>{std_display}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #f59e0b;'>
                <b style='color:#92400e;'>Langkah 2 - Hitung Z-Score</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Z = (BSK Daerah - mean) / sigma</span><br>
                <code style='font-size:0.95em;'>Z = ({format_currency(cpu)} - {format_currency(med_cpu)}) / {std_display}</code><br>
                <code style='font-size:0.95em;'>Z = <b>{z_score:+.4f}</b> -> Zona: <b>{zona}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #10b981;'>
                <b style='color:#065f46;'>Langkah 3 - Penilaian Skor (Penalti Asimetris)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Sistem memberikan <b>toleransi yang berbeda</b>. Jika daerah Anda jauh lebih mahal/boros (Z positif), skor dipotong lebih drastis. Namun jika daerah Anda jauh lebih murah (Z negatif), skor potongannya lebih kecil.</span><br>
                <span style='color:#64748b;font-size:0.85em;'>Status daerah Anda: <b>{sigma_label}</b>, sehingga:</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Kalkulasi: 100 x exp(-0.5 x ({z_score:.4f} / {sigma_actual:.4f})^2)</code><br>
                <code style='font-size:1.1em;'><b style='color:#059669;'>Hasil Akhir -> Skor Dimensi 2 = {score_verify:.1f} dari 100</b></code>
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                tier_html = (
                    "<details style='margin-top:8px;'><summary style='cursor:pointer;color:#1e3a8a;font-weight:bold;font-size:0.85rem;'>[Chart] Tabel Kalibrasi Skor Spasial (Asymmetric LISA)</summary>"
                    "<table style='width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:8px;'>"
                    "<tr style='background:#f1f5f9;'><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Z-Score</th><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Skor</th><th style='padding:8px;text-align:left;border-bottom:1px solid #cbd5e1;'>Interpretasi</th></tr>"
                    "<tr style='background:#f0fdf4;'><td style='padding:6px 8px;text-align:center;'>0.0 (Sama Rata)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>100.0</td><td style='padding:6px 8px;color:#22c55e;'>Sangat Wajar (Rata-rata Regional)</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>+1.0 (Over)</td><td style='padding:6px 8px;text-align:center;'>83.5</td><td style='padding:6px 8px;color:#22c55e;'>Wajar</td></tr>"
                    "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>+1.96 (LISA Outlier Limit)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50.0</td><td style='padding:6px 8px;color:#ef4444;font-weight:bold;'>Batas Atas Outlier Regional</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>+3.0</td><td style='padding:6px 8px;text-align:center;'>19.7</td><td style='padding:6px 8px;color:#7f1d1d;'>Sangat Boros (Penyimpangan Berat)</td></tr>"
                    "<tr style='background:#f0fdf4;'><td style='padding:6px 8px;text-align:center;'>-1.0 (Under)</td><td style='padding:6px 8px;text-align:center;'>92.6</td><td style='padding:6px 8px;color:#22c55e;'>Wajar (Hemat)</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>-2.0</td><td style='padding:6px 8px;text-align:center;'>73.4</td><td style='padding:6px 8px;color:#22c55e;'>Hemat</td></tr>"
                    "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>-3.0 (Under Limit)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50.0</td><td style='padding:6px 8px;color:#eab308;font-weight:bold;'>Batas Kritis Under-budgeting (Kualitas Risiko)</td></tr>"
                    "</table>"
                    "<div style='margin-top:8px;font-size:0.8rem;color:#64748b;'>"
                    "<b>Referensi Akademik:</b> Anselin, L. (1995). Local Indicators of Spatial Association-LISA. <i>Geographical Analysis</i>, 27(2), 93-115."
                    "</div>"
                    "</details>"
                )
                st.markdown(tier_html, unsafe_allow_html=True)
                
            #  TABEL KOMPARASI 
            st.markdown("##### Tabel Distribusi Seluruh Pemda (Tahun yang Sama)")
            spasial_df = df[
                (df["kodesubkegiatan"] == row["kodesubkegiatan"]) & 
                (df["satuan"] == row["satuan"]) & 
                (df["tahun"] == row["tahun"]) &
                (df["bsk"].notna()) & (df["bsk"] > 0)
            ].sort_values(by="bsk", ascending=True)
            
            if spasial_df.empty or len(spasial_df) <= 1:
                st.info("Tidak ditemukan data dari wilayah lain.")
            else:
                import plotly.graph_objects as go
                
                spasial_df = spasial_df.copy()
                
                # Hitung leave-one-out Z-Score untuk tampilan tabel
                z_list = []
                for idx_sp in spasial_df.index:
                    bsk_i = spasial_df.loc[idx_sp, "bsk"]
                    others_bsk = spasial_df.loc[spasial_df.index != idx_sp, "bsk"]
                    mu_i = others_bsk.mean()
                    sig_i = others_bsk.std(ddof=1) if len(others_bsk) > 1 else others_bsk.std(ddof=0)
                    if sig_i > 0:
                        z_i = (bsk_i - mu_i) / sig_i
                    else:
                        z_i = 0.0 if bsk_i == mu_i else ((bsk_i - mu_i) / mu_i if mu_i > 0 else 0)
                    z_list.append({"idx": idx_sp, "z": z_i, "mu": mu_i, "sig": sig_i})
                
                for item in z_list:
                    spasial_df.loc[item["idx"], "z_loo"] = item["z"]
                
                def get_z_status(z):
                    az = abs(z)
                    if az < 1: return "[OK] Wajar"
                    elif az < 2: return "[Warning] Perhatian"
                    else: return "[!] Outlier"
                
                def get_skor_d2(z):
                    if z <= 0:
                        return 100.0
                    else:
                        return max(0, 100 - (z * 15))
                        
                spasial_df["skor_d2"] = spasial_df["z_loo"].apply(get_skor_d2)
                spasial_df["status"] = spasial_df["z_loo"].apply(get_z_status)
                
                display_sp = spasial_df[["pemda_label", "pagu", "target", "bsk", "z_loo", "skor_d2", "status"]].copy()
                is_current = display_sp["pemda_label"] == row["pemda_label"]
                display_sp.loc[is_current, "pemda_label"] = display_sp.loc[is_current, "pemda_label"] + " <- INI"
                display_sp["pagu"] = display_sp["pagu"].apply(format_currency)
                display_sp["bsk_fmt"] = display_sp["bsk"].apply(format_currency)
                display_sp["z_loo"] = display_sp["z_loo"].apply(lambda x: f"{x:+.3f}")
                display_sp["skor_d2"] = display_sp["skor_d2"].apply(lambda x: f"{x:.1f}")
                
                display_sp_show = display_sp[["pemda_label", "pagu", "target", "bsk_fmt", "z_loo", "skor_d2", "status"]]
                display_sp_show = display_sp_show.rename(columns={
                    "pemda_label": "Pemda", "pagu": "Pagu", "target": "Target",
                    "bsk_fmt": "BSK", "z_loo": "Z-Score", "skor_d2": "Skor", "status": "Status"
                })
                
                # Add No. column
                display_sp_show.insert(0, "No.", range(1, len(display_sp_show) + 1))
                
                st.dataframe(display_sp_show, use_container_width=True, hide_index=True)
                
                #  VISUALISASI: Bell Curve Z-Score 
                st.markdown("##### Visualisasi Distribusi Normal - Deteksi Outlier Z-Score")
                
                # Check if we have valid LOO Z-scores
                if "z_loo" in spasial_df.columns:
                    viz_df = spasial_df[["pemda_label", "bsk", "z_loo"]].copy()
                    viz_df["z"] = viz_df["z_loo"]
                    viz_df = viz_df.sort_values("z")
                    
                    # Generate bell curve on Z-axis (standardized normal curve)
                    z_curve = np.linspace(-4, 4, 300)
                    y_curve = (1 / np.sqrt(2 * np.pi)) * np.exp(-0.5 * z_curve ** 2)
                    
                    fig = go.Figure()
                    
                    # Colored zones (area fills)
                    # Outliers left (z < -2): red
                    mask = z_curve <= -2
                    fig.add_trace(go.Scatter(x=z_curve[mask], y=y_curve[mask], fill='tozeroy', fillcolor='rgba(239,68,68,0.25)', line=dict(width=0), showlegend=False, hoverinfo='skip'))
                    # Moderately unusual left (-2 to -1): yellow
                    mask = (z_curve >= -2) & (z_curve <= -1)
                    fig.add_trace(go.Scatter(x=z_curve[mask], y=y_curve[mask], fill='tozeroy', fillcolor='rgba(250,204,21,0.25)', line=dict(width=0), showlegend=False, hoverinfo='skip'))
                    # Not unusual (-1 to 1): green
                    mask = (z_curve >= -1) & (z_curve <= 1)
                    fig.add_trace(go.Scatter(x=z_curve[mask], y=y_curve[mask], fill='tozeroy', fillcolor='rgba(74,222,128,0.3)', line=dict(width=0), showlegend=False, hoverinfo='skip'))
                    # Moderately unusual right (1 to 2): yellow
                    mask = (z_curve >= 1) & (z_curve <= 2)
                    fig.add_trace(go.Scatter(x=z_curve[mask], y=y_curve[mask], fill='tozeroy', fillcolor='rgba(250,204,21,0.25)', line=dict(width=0), showlegend=False, hoverinfo='skip'))
                    # Outliers right (z > 2): red
                    mask = z_curve >= 2
                    fig.add_trace(go.Scatter(x=z_curve[mask], y=y_curve[mask], fill='tozeroy', fillcolor='rgba(239,68,68,0.25)', line=dict(width=0), showlegend=False, hoverinfo='skip'))
                    
                    # Bell curve outline
                    fig.add_trace(go.Scatter(x=z_curve, y=y_curve, mode='lines', line=dict(color='#dc2626', width=3), name='Distribusi Normal', showlegend=False, hoverinfo='skip'))
                    
                    # Vertical reference lines
                    for zv, label, color, dash in [
                        (0, "z=0", "#374151", "dash"),
                        (-1, "z=1", "#22c55e", "solid"), (1, "z=+1", "#22c55e", "solid"),
                        (-2, "z=2", "#eab308", "solid"), (2, "z=+2", "#eab308", "solid"),
                        (-3, "z=3", "#ef4444", "solid"), (3, "z=+3", "#ef4444", "solid"),
                    ]:
                        fig.add_vline(x=zv, line_dash=dash, line_color=color, line_width=1, opacity=0.6)
                    
                    # Data points: plot at bottom (y=0) as markers with jitter
                    for i, (_, vr) in enumerate(viz_df.iterrows()):
                        z_val = vr["z"]
                        az = abs(z_val)
                        if az < 1: color = "#22c55e"
                        elif az < 2: color = "#eab308"
                        else: color = "#ef4444"
                        
                        is_self = vr["pemda_label"] == row["pemda_label"]
                        
                        # Clip visual coordinate to stay inside chart area (-3.8 to 3.8)
                        vis_z = max(-3.8, min(3.8, z_val))
                        
                        fig.add_trace(go.Scatter(
                            x=[vis_z], y=[-0.015],
                            mode='markers',
                            marker=dict(
                                size=20 if is_self else 14,
                                color=color,
                                symbol="diamond" if is_self else "circle",
                                line=dict(width=3 if is_self else 1, color='#1e3a8a' if is_self else 'white')
                            ),
                            name=vr["pemda_label"],
                            hovertemplate=f"<b>{vr['pemda_label']}</b><br>BSK: {format_currency(vr['bsk'])}<br>Z-Score: {z_val:+.3f}<extra></extra>",
                            showlegend=False
                        ))
                    
                    # Zone annotations at top
                    y_top = 0.42
                    fig.add_annotation(x=0, y=y_top, text="<b>Wajar</b>", showarrow=False, font=dict(size=13, color="#16a34a"))
                    fig.add_annotation(x=-1.5, y=y_top * 0.55, text="Perlu<br>Perhatian", showarrow=False, font=dict(size=10, color="#ca8a04"))
                    fig.add_annotation(x=1.5, y=y_top * 0.55, text="Perlu<br>Perhatian", showarrow=False, font=dict(size=10, color="#ca8a04"))
                    fig.add_annotation(x=-2.7, y=y_top * 0.2, text="Outlier", showarrow=False, font=dict(size=10, color="#dc2626"))
                    fig.add_annotation(x=2.7, y=y_top * 0.2, text="Outlier", showarrow=False, font=dict(size=10, color="#dc2626"))
                    
                    # X-axis labels
                    fig.update_layout(
                        title="Distribusi Normal BSK - Deteksi Outlier Z-Score",
                        xaxis=dict(
                            title="Z-Score", range=[-4, 4],
                            tickvals=[-3, -2, -1, 0, 1, 2, 3],
                            ticktext=["z=3", "z=2", "z=1", "z=0", "z=+1", "z=+2", "z=+3"],
                            gridcolor="#e2e8f0"
                        ),
                        yaxis=dict(title="", showticklabels=False, range=[-0.04, 0.45], gridcolor="#f1f5f9"),
                        plot_bgcolor="white", height=420,
                        margin=dict(t=50, b=40, l=20, r=20)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption("* = Daerah ini     = Daerah lain     Wajar (|Z|<1)     Perlu Perhatian (1<=|Z|<2)     Outlier (|Z|>=2)")
                
        # DIMENSI 3
        st.subheader("Dimensi 3: Kewajaran Kinerja (Analisis Prognosis)")
        with st.container(border=True):
            d3_score = row.get("dimensi_3_score", pd.NA)
            
            st.markdown(r"""
            **Metodologi - Goal Setting and Performance Realism (Locke & Latham, 1990):**  
            Mengevaluasi realistis atau tidaknya target usulan tahun berjalan berdasarkan prognosis kemampuan teknis historis (efisiensi riil dari tahun-tahun sebelumnya). Deviasi dihitung menggunakan **Log-Normal Goal Realism Function**.
            
            **Formula Log-Normal Goal Realism:**
            $$\text{Score} = 100 \times \exp\left(-\frac{1}{2}\left(\frac{\ln(r)}{\sigma_r}\right)^2\right), \quad r = \frac{\text{Target Usulan}}{\text{Target Prognosis}}$$
            $$\sigma_r = \frac{\ln(2{,}0)}{\sqrt{2 \ln 2}} \approx 0{,}589$$
            
            *Konstanta $\sigma_r$ dikalibrasi agar rasio target $r = 0{,}50$ (tidak ambisius / malas) atau $r = 2{,}0$ (terlalu ambisius / tidak realistis / over-promising) menghasilkan skor tepat 50.*
            """)
            
            c1, c2, c3, c4 = st.columns(4)
            avg_e = row.get("hist_efficiency_avg", pd.NA)
            prog_out = row.get("prognosis_output", pd.NA)
            curr_target = row.get("target", 0)
            
            # Tampilkan efisiensi sesuai dengan format aslinya
            c1.metric("Rata2 Efisiensi Riil", f"{avg_e:.10f}" if pd.notna(avg_e) else "-")
            c2.metric("Target Prognosis", format_number(prog_out, 2) if pd.notna(prog_out) else "-")
            c3.metric("Target Usulan", format_number(curr_target, 2))
            
            if pd.isna(d3_score):
                c4.metric("Skor Dimensi 3", "Data Minim")
            else:
                c4.metric("Skor Dimensi 3", f"{format_number(d3_score, 1)} / 100")
            
            # Detail Perhitungan Transparan
            if pd.notna(avg_e) and pd.notna(prog_out):
                r_val = curr_target / prog_out if prog_out > 0 else 0
                sigma_val = np.log(2.0) / np.sqrt(2 * np.log(2))
                ln_r = np.log(r_val) if r_val > 0 else 0
                score_verify = 100 * np.exp(-0.5 * (ln_r / sigma_val) ** 2) if r_val > 0 else 0
                pagu_val = row.get('pagu', 0)
                
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:20px;border-radius:12px;border:1px solid #c7d2fe;margin:12px 0;'>
                <h4 style='color:#1e3a8a;margin:0 0 16px 0;'>[Kalkulasi] Langkah Perhitungan Dimensi 3</h4>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 1 - Menghitung Efisiensi Kemampuan Historis</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Sistem melihat rekam jejak di tahun-tahun sebelumnya. Untuk setiap tahun historis, dihitung seberapa banyak output yang dihasilkan dari setiap rupiah (Realisasi Output / Realisasi Anggaran). Semua hasilnya lalu dirata-ratakan.</span><br>
                <span style='color:#64748b;font-size:0.85em;'>Artinya, rata-rata untuk setiap Rp. 1 yang dikeluarkan, daerah ini mampu menghasilkan <b>{avg_e:.10f}</b> output.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Kalkulasi: Menjumlahkan (Realisasi Output / Realisasi Pagu) dari setiap tahun sebelumnya, lalu dibagi jumlah tahun.</code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 2 - Menghitung Target Ideal (Prognosis Seharusnya)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Dengan Anggaran yang diajukan tahun ini, kita bisa menebak target logis yang SEHARUSNYA bisa dicapai jika daerah mempertahankan kemampuan historisnya.</span><br>
                <code style='font-size:0.95em;'>Target Seharusnya = Anggaran Tahun Ini x Kemampuan Historis</code><br>
                <code style='font-size:0.95em;'>Target Seharusnya = {format_currency(pagu_val)} x {avg_e:.10f} = <b>{format_number(prog_out, 4)}</b> output</code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #f59e0b;'>
                <b style='color:#92400e;'>Langkah 3 - Mengukur Rasio Kewajaran Target</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Sistem membandingkan Target Usulan yang diajukan dengan Target Seharusnya.</span><br>
                <code style='font-size:0.95em;'>Rasio = Target Usulan ({format_number(curr_target, 2)}) / Target Seharusnya ({format_number(prog_out, 4)}) = <b>{r_val:.4f}</b></code><br>
                <span style='color:#64748b;font-size:0.85em;'><b>Kesimpulan:</b> {'Target ini terlalu AMBISIUS/Over-promising' if r_val > 1.1 else 'Target ini terlalu KONSERVATIF/Pesimis' if r_val < 0.9 else 'Target ini SANGAT REALISTIS'}</span>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #10b981;'>
                <b style='color:#065f46;'>Langkah 4 - Penilaian Skor Kesesuaian</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Berdasarkan rasio di atas, jika target usulan sangat melenceng (jauh lebih tinggi atau jauh lebih rendah dari target seharusnya), skornya akan dipotong.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Kalkulasi ln(r): ln({r_val:.4f}) = {ln_r:.4f}</code><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Kalkulasi Skor: 100 x exp(-0.5 x ({ln_r:.4f} / {sigma_val:.4f})^2)</code><br>
                <code style='font-size:1.1em;'><b style='color:#059669;'>Hasil Akhir -> Skor Dimensi 3 = {score_verify:.1f} dari 100</b></code>
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                tier_html = (
                    "<details style='margin-top:8px;'><summary style='cursor:pointer;color:#1e3a8a;font-weight:bold;font-size:0.85rem;'>[Chart] Tabel Kalibrasi Skor Target (Goal Realism)</summary>"
                    "<table style='width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:8px;'>"
                    "<tr style='background:#f1f5f9;'><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Rasio Usulan vs Prognosis (r)</th><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Skor</th><th style='padding:8px;text-align:left;border-bottom:1px solid #cbd5e1;'>Interpretasi</th></tr>"
                    "<tr style='background:#f0fdf4;'><td style='padding:6px 8px;text-align:center;'>1.0 (Sesuai Prognosis)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>100.0</td><td style='padding:6px 8px;color:#22c55e;'>Sangat Wajar & Realistis</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>1.2 (Ambis Wajar)</td><td style='padding:6px 8px;text-align:center;'>95.3</td><td style='padding:6px 8px;color:#22c55e;'>Ambis Realistis (Wajar)</td></tr>"
                    "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>2.0 (Over-promising)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50.0</td><td style='padding:6px 8px;color:#ef4444;font-weight:bold;'>Batas Atas Target Tidak Realistis</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>3.0</td><td style='padding:6px 8px;text-align:center;'>17.6</td><td style='padding:6px 8px;color:#7f1d1d;'>Sangat Tidak Realistis (Over-claim)</td></tr>"
                    "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>0.5 (Under-achieving)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50.0</td><td style='padding:6px 8px;color:#eab308;font-weight:bold;'>Batas Bawah Target Tidak Efisien (Malas)</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>0.25</td><td style='padding:6px 8px;text-align:center;'>6.3</td><td style='padding:6px 8px;color:#7f1d1d;'>Sangat Tidak Efisien</td></tr>"
                    "</table>"
                    "<div style='margin-top:8px;font-size:0.8rem;color:#64748b;'>"
                    "<b>Referensi Akademik:</b> Locke, E.A. & Latham, G.P. (1990). <i>A Theory of Goal Setting & Task Performance</i>. Prentice Hall."
                    "</div>"
                    "</details>"
                )
                st.markdown(tier_html, unsafe_allow_html=True)
            else:
                st.caption("[Info] Tidak ada data realisasi historis. Dimensi ini tidak berkontribusi terhadap IKP (Dynamic Weighting).")

            st.markdown(f"##### Analisis Prognosis {row.get('tahun', '')} (note: hanya fokus pada angka realisasinya saja)")
            # Fetch historical realization data
            realisasi_df = df[
                (df["kodepemda"] == row["kodepemda"]) & 
                (df["kodesubkegiatan"] == row["kodesubkegiatan"]) & 
                (df["satuan"] == row["satuan"]) & 
                (df["tahun"] < row["tahun"])
            ].sort_values(by="tahun", ascending=True) # Ascending order to match spreadsheet
            
            if realisasi_df.empty:
                st.info("Tidak ditemukan data historis di tahun sebelumnya untuk dianalisis.")
            else:
                display_real = realisasi_df[["tahun", "pagu", "target", "realisasi_anggaran", "realisasi_target"]].copy()
                
                # Hitung Efisiensi Riil untuk tabel
                display_real["Efisiensi riil (realisasi/pagu realisasi)"] = (display_real["realisasi_target"] / display_real["realisasi_anggaran"]).apply(lambda x: f"{x:.10f}" if pd.notna(x) else "-")
                
                # Format menggunakan helper gaya Indonesia
                display_real["pagu"] = display_real["pagu"].apply(format_currency)
                display_real["realisasi_anggaran"] = display_real["realisasi_anggaran"].apply(format_currency)
                
                display_real["target"] = display_real["target"].apply(lambda x: format_number(x, 2))
                display_real["realisasi_target"] = display_real["realisasi_target"].apply(lambda x: format_number(x, 2))
                
                display_real.rename(columns={
                    "tahun": "Tahun",
                    "pagu": "Pagu anggaran",
                    "target": "Target (unit)",
                    "realisasi_anggaran": "Pagu Realisasi",
                    "realisasi_target": "Realisasi (unit)"
                }, inplace=True)
                
                st.dataframe(display_real, use_container_width=True, hide_index=True)
            
        # DIMENSI 4
        st.subheader("Dimensi 4: Kewajaran Perencanaan (Consistency)")
        with st.container(border=True):
            d4_score = row.get("dimensi_4_score", pd.NA)
            
            st.markdown(r"""
            **Metodologi - Predictability & Budget Control (PEFA Framework - PI-16):**  
            Mengevaluasi tingkat konsistensi dan disiplin perencanaan anggaran antara dokumen RKPD, PPAS, dan APBD. Deviasi (discrepancy) dihitung menggunakan **Mean Absolute Planning Discrepancy (MAPD)** dan dikonversi menggunakan **Gaussian Decay Function**.
            
            **Formula Gaussian Consistency Score:**
            $$\text{Score} = 100 \times \exp\left(-\frac{1}{2}\left(\frac{x}{\sigma_c}\right)^2\right)$$
            $$x = \frac{|APBD - RKPD| + |APBD - PPAS|}{APBD}$$
            $$\sigma_c = \frac{0{,}15}{\sqrt{2 \ln 2}} \approx 0{,}127$$
            
            *Di mana $x$ melambangkan persentase planning discrepancy. Konstanta $\sigma_c$ dikalibrasi agar deviasi 15% (batas atas PEFA Grade C / toleransi wajar perencanaan) menghasilkan skor tepat 50.*
            """)
            
            c1, c2 = st.columns([3, 1])
            c1.warning("[Info] Data perencanaan dari sistem SIPD-RI (RKPD & PPAS) belum diintegrasikan ke basis data utama. Dimensi ini **tidak diperhitungkan** dalam kalkulasi IKP saat ini (Dynamic Weighting).")
            if pd.notna(d4_score):
                c2.metric("Skor Dimensi 4", f"{d4_score:.1f} / 100")
            else:
                c2.metric("Skor Dimensi 4", "Tidak Ada Data")
            
            rkpd_val = row.get("rkpd", pd.NA)
            ppas_val = row.get("ppas", pd.NA)
            apbd_val = row.get("pagu", pd.NA)
            
            if pd.notna(d4_score) and pd.notna(rkpd_val) and pd.notna(ppas_val) and pd.notna(apbd_val):
                sigma_val = 0.15 / np.sqrt(2 * np.log(2))
                discrepancy = (abs(apbd_val - rkpd_val) + abs(apbd_val - ppas_val)) / apbd_val if apbd_val > 0 else 0
                score_verify = 100 * np.exp(-0.5 * (discrepancy / sigma_val) ** 2)
                
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:20px;border-radius:12px;border:1px solid #c7d2fe;margin:12px 0;'>
                <h4 style='color:#1e3a8a;margin:0 0 16px 0;'>[Kalkulasi] Langkah Perhitungan Dimensi 4</h4>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 1 - Ambil Data Perencanaan</b><br>
                <code style='font-size:0.95em;'>Pagu RKPD = <b>{format_currency(rkpd_val)}</b></code><br>
                <code style='font-size:0.95em;'>Pagu PPAS = <b>{format_currency(ppas_val)}</b></code><br>
                <code style='font-size:0.95em;'>Pagu APBD = <b>{format_currency(apbd_val)}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #f59e0b;'>
                <b style='color:#92400e;'>Langkah 2 - Hitung Penyimpangan Perencanaan (Discrepancy)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Menghitung selisih antara pagu APBD akhir dengan usulan awal (RKPD & PPAS).</span><br>
                <code style='font-size:0.95em;'>Penyimpangan = (|APBD - RKPD| + |APBD - PPAS|) / APBD</code><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Penyimpangan = (|{format_currency(apbd_val)} - {format_currency(rkpd_val)}| + |{format_currency(apbd_val)} - {format_currency(ppas_val)}|) / {format_currency(apbd_val)}</code><br>
                <code style='font-size:0.95em;'>Hasil Penyimpangan = <b>{discrepancy:.4f}</b> ({discrepancy*100:.1f}%)</code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #10b981;'>
                <b style='color:#065f46;'>Langkah 3 - Penilaian Skor Kesesuaian Perencanaan</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Semakin besar penyimpangan (perubahan mendadak pada anggaran di ujung waktu), semakin besar penalti pemotongan skor secara melengkung ke bawah.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Kalkulasi Skor = 100 x exp(-0.5 x ({discrepancy:.4f} / {sigma_val:.4f})^2)</code><br>
                <code style='font-size:1.1em;'><b style='color:#059669;'>Hasil Akhir -> Skor Dimensi 4 = {score_verify:.1f} dari 100</b></code>
                </div>
                </div>
                """, unsafe_allow_html=True)
                
            tier_html = (
                "<details style='margin-top:8px;'><summary style='cursor:pointer;color:#1e3a8a;font-weight:bold;font-size:0.85rem;'>[Chart] Tabel Kalibrasi Konsistensi Perencanaan (PEFA PI-16)</summary>"
                "<table style='width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:8px;'>"
                "<tr style='background:#f1f5f9;'><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Planning Discrepancy (x)</th><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Skor</th><th style='padding:8px;text-align:left;border-bottom:1px solid #cbd5e1;'>Kategori / PEFA Grade</th></tr>"
                "<tr style='background:#f0fdf4;'><td style='padding:6px 8px;text-align:center;'>0% (Sempurna)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>100.0</td><td style='padding:6px 8px;color:#22c55e;'>Sangat Konsisten (Grade A)</td></tr>"
                "<tr><td style='padding:6px 8px;text-align:center;'>5%</td><td style='padding:6px 8px;text-align:center;'>92.6</td><td style='padding:6px 8px;color:#22c55e;'>Konsisten (Grade A)</td></tr>"
                "<tr><td style='padding:6px 8px;text-align:center;'>10%</td><td style='padding:6px 8px;text-align:center;'>73.4</td><td style='padding:6px 8px;color:#eab308;'>Cukup Konsisten (Grade B)</td></tr>"
                "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>15% (Batas PEFA)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50.0</td><td style='padding:6px 8px;color:#ef4444;font-weight:bold;'>Batas Toleransi Deviasi (Grade C)</td></tr>"
                "<tr><td style='padding:6px 8px;text-align:center;'>25%</td><td style='padding:6px 8px;text-align:center;'>14.6</td><td style='padding:6px 8px;color:#7f1d1d;'>Tidak Konsisten (Grade D)</td></tr>"
                "</table>"
                "<div style='margin-top:8px;font-size:0.8rem;color:#64748b;'>"
                "<b>Referensi Akademik:</b> PEFA Secretariat. (2016). <i>Public Expenditure and Financial Accountability Framework</i>. Indicator PI-16: Predictability and Control in Budget Execution."
                "</div>"
                "</details>"
            )
            st.markdown(tier_html, unsafe_allow_html=True)

        # DIMENSI 5
        st.subheader("Dimensi 5: Kewajaran Statistik (Deteksi Anomali IQR)")
        with st.container(border=True):
            d5_score = row.get("dimensi_5_score", pd.NA)
            is_anomali = row.get("is_anomali", False)
            
            st.markdown(r"""
            **Metodologi - Gaussian Decay Scoring (Tukey, 1977; Iglewicz & Hoaglin, 1993):**  
            Mendeteksi anomali Biaya Satuan Kinerja (BSK) menggunakan **IQR Fence Distance** terhadap seluruh data dengan nomenklatur yang sama, lalu mengkonversi jarak tersebut ke skor kontinu menggunakan **Gaussian Decay Function**.
            
            **Langkah 1 - IQR Fence Distance ($d$):**
            $$d = \begin{cases} 0 & \text{jika } Q1 \le BSK \le Q3 \\ \frac{Q1 - BSK}{IQR} & \text{jika } BSK < Q1 \\ \frac{BSK - Q3}{IQR} & \text{jika } BSK > Q3 \end{cases}$$
            
            **Langkah 2 - Gaussian Decay Score:**
            $$\text{Score} = 100 \times \exp\left(-\frac{1}{2}\left(\frac{d}{\sigma}\right)^2\right), \quad \sigma = \frac{1{,}5}{\sqrt{2 \ln 2}} \approx 1{,}274$$
            
            Kalibrasi $\sigma$ dipilih agar skor **tepat 50** di Tukey Inner Fence ($d = 1{,}5$).
            """)
            
            c1, c2, c3, c4 = st.columns(4)
            q1 = row.get("stat_q1", pd.NA)
            q3 = row.get("stat_q3", pd.NA)
            ub = row.get("stat_upper_bound", pd.NA)
            lb = row.get("stat_lower_bound", pd.NA)
            d_val = row.get("stat_iqr_distance", pd.NA)
            
            c1.metric("Kuartil 1 (Q1)", format_currency(q1) if pd.notna(q1) else "-")
            c2.metric("Kuartil 3 (Q3)", format_currency(q3) if pd.notna(q3) else "-")
            c3.metric("IQR Distance (d)", f"{d_val:.4f}" if pd.notna(d_val) else "-")
            
            if is_anomali:
                c4.metric("Status", "[Warning] ANOMALI", delta=f"d >= 1.5", delta_color="inverse")
            else:
                c4.metric("Status", "[OK] WAJAR", delta=f"d < 1.5")
                
            st.markdown(f"**Skor Dimensi 5:** {format_number(d5_score, 1)} / 100")
            
            if is_anomali:
                st.warning(f"Sub-kegiatan ini terdeteksi sebagai pencilan (outlier) secara statistik. BSK daerah ini ({format_currency(row['bsk'])}) berada di luar rentang wajar sistem ({format_currency(lb)} s/d {format_currency(ub)}).")
            
            # Fetch ALL data for this nomenclature across all Pemdas
            universal_df = df[
                (df["kodesubkegiatan"] == row["kodesubkegiatan"]) & 
                (df["satuan"] == row["satuan"]) &
                (df["bsk"].notna()) & (df["bsk"] > 0)
            ].sort_values(by="bsk")
            
            # Detail Perhitungan Transparan
            if not universal_df.empty and len(universal_df) >= 4:
                bsk_vals = universal_df["bsk"].values
                n_data = len(bsk_vals)
                
                # Menghitung Kuartil
                q1_v = np.percentile(bsk_vals, 25)
                q2_v = np.percentile(bsk_vals, 50)  # Median
                q3_v = np.percentile(bsk_vals, 75)
                q4_v = np.max(bsk_vals)             # Maksimum
                
                iqr_val = q3_v - q1_v
                lb_v = q1_v - 1.5 * iqr_val
                ub_v = q3_v + 1.5 * iqr_val
                
                current_bsk = row.get('bsk', 0)
                current_d = d_val if pd.notna(d_val) else 0
                
                # Status berdasarkan fence distance
                if current_d >= 3.0:
                    status_label = '<b style="color:#7f1d1d;">ANOMALI EKSTREM (d >= 3.0, di luar outer fence)</b>'
                elif current_d >= 1.5:
                    status_label = '<b style="color:#ef4444;">ANOMALI (d >= 1.5, di luar inner fence)</b>'
                elif current_d >= 1.0:
                    status_label = '<b style="color:#f59e0b;">PERLU PERHATIAN (1.0 <= d < 1.5)</b>'
                else:
                    status_label = '<b style="color:#22c55e;">DALAM BATAS WAJAR (d < 1.0)</b>'
                
                # Sigma value
                sigma_val = 1.5 / np.sqrt(2 * np.log(2))
                score_verify = 100 * np.exp(-0.5 * (current_d / sigma_val) ** 2)
                
                # Distance calc text
                if current_bsk < q1_v:
                    d_calc = f"d = (Q1 - BSK) / IQR = ({format_currency(q1_v)} - {format_currency(current_bsk)}) / {format_currency(iqr_val)} = <b>{current_d:.4f}</b>"
                    d_explain = "BSK di bawah Q1"
                elif current_bsk > q3_v:
                    d_calc = f"d = (BSK - Q3) / IQR = ({format_currency(current_bsk)} - {format_currency(q3_v)}) / {format_currency(iqr_val)} = <b>{current_d:.4f}</b>"
                    d_explain = "BSK di atas Q3"
                else:
                    d_calc = "d = <b>0.0000</b>"
                    d_explain = "BSK dalam kotak IQR [Q1, Q3]"
                
                dim5_html = f"""
                <div style='background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:20px;border-radius:12px;border:1px solid #c7d2fe;margin:12px 0;'>
                <h4 style='color:#1e3a8a;margin:0 0 16px 0;'>[Kalkulasi] Langkah Perhitungan Dimensi 5</h4>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 1 - Susun Data dari Termurah ke Termahal (Kuartil)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Nilai BSK (Biaya) dari seluruh daerah dijajarkan berurutan dari yang paling kecil (murah) hingga terbesar (mahal). Kemudian data dibagi menjadi 4 kelompok.</span><br>
                <ul style='font-size:0.85em;color:#64748b;margin-top:4px;'>
                   <li><b>Q1 (Batas Kelompok 25% Termurah):</b> {format_currency(q1_v)}</li>
                   <li><b>Q2 (Nilai Tengah / Median):</b> {format_currency(q2_v)}</li>
                   <li><b>Q3 (Batas Kelompok 25% Termahal):</b> {format_currency(q3_v)}</li>
                </ul>
                <code style='font-size:0.95em;'>Jarak Rentang Menengah (IQR) = Q3 - Q1 = <b>{format_currency(iqr_val)}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 2 - Tentukan Pagar Batas Aman</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Sistem menghitung batas harga yang dianggap sangat murah tidak wajar (Batas Bawah) dan sangat mahal tidak wajar (Batas Atas). Angka apapun di luar pagar ini disebut Anomali Ekstrem.</span><br>
                <code style='font-size:0.95em;'>Batas Bawah Aman = Q1 - (1.5 x IQR)</code><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Batas Bawah = {format_currency(q1_v)} - (1.5 x {format_currency(iqr_val)}) = <b>{format_currency(lb_v)}</b></code><br>
                <br>
                <code style='font-size:0.95em;'>Batas Atas Aman = Q3 + (1.5 x IQR)</code><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Batas Atas = {format_currency(q3_v)} + (1.5 x {format_currency(iqr_val)}) = <b>{format_currency(ub_v)}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #f59e0b;'>
                <b style='color:#92400e;'>Langkah 3 - Cek Posisi Daerah Anda</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Sistem mengecek apakah BSK Anda ({format_currency(current_bsk)}) melanggar pagar batas aman.</span><br>
                <code style='font-size:0.95em;'>Kondisi Anda saat ini: <b>{d_explain}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #10b981;'>
                <b style='color:#065f46;'>Langkah 4 - Penilaian Skor Kewajaran Ekstrem</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Jika BSK Anda masih berada di dalam kotak Q1 hingga Q3, skor otomatis Sempurna 100. Semakin jauh Anda melampaui pagar batas aman (menjadi outlier yang ekstrem), nilai skor akan dipotong tajam hingga mendekati 0.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Kalkulasi Jarak (d): {d_calc}</code><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Kalkulasi Skor: 100 x exp(-0.5 x ({current_d:.4f} / {sigma_val:.4f})^2)</code><br>
                <code style='font-size:1.1em;'><b style='color:#059669;'>Hasil Akhir -> Skor Dimensi 5 = {score_verify:.1f} dari 100</b></code><br><br>
                <span style='font-size:0.85em;'>Status Keputusan: <b>{status_label}</b></span>
                </div>
                </div>
                """
                st.markdown(dim5_html, unsafe_allow_html=True)
                
                # Tabel referensi skor
                tier_html = (
                    "<details style='margin-top:8px;'><summary style='cursor:pointer;color:#1e3a8a;font-weight:bold;font-size:0.85rem;'>[Chart] Tabel Kalibrasi Skor (Gaussian Decay)</summary>"
                    "<table style='width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:8px;'>"
                    "<tr style='background:#f1f5f9;'><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Fence Distance (d)</th><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Skor</th><th style='padding:8px;text-align:left;border-bottom:1px solid #cbd5e1;'>Interpretasi</th></tr>"
                    "<tr style='background:#f0fdf4;'><td style='padding:6px 8px;text-align:center;'>0.0 (dalam IQR)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>100.0</td><td style='padding:6px 8px;color:#22c55e;'>Sangat Wajar</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>0.5</td><td style='padding:6px 8px;text-align:center;'>92.6</td><td style='padding:6px 8px;color:#22c55e;'>Wajar</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>1.0</td><td style='padding:6px 8px;text-align:center;'>73.4</td><td style='padding:6px 8px;color:#eab308;'>Perlu Perhatian</td></tr>"
                    "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>1.5 (Inner Fence)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50.0</td><td style='padding:6px 8px;color:#ef4444;font-weight:bold;'>Tukey Inner Fence - Batas Anomali</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>2.0</td><td style='padding:6px 8px;text-align:center;'>29.2</td><td style='padding:6px 8px;color:#ef4444;'>Anomali Signifikan</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>2.5</td><td style='padding:6px 8px;text-align:center;'>14.6</td><td style='padding:6px 8px;color:#7f1d1d;'>Anomali Berat</td></tr>"
                    "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>3.0 (Outer Fence)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>6.3</td><td style='padding:6px 8px;color:#7f1d1d;font-weight:bold;'>Tukey Outer Fence - Anomali Ekstrem</td></tr>"
                    "</table>"
                    "<div style='margin-top:8px;font-size:0.8rem;color:#64748b;'>"
                    "<b>Referensi:</b><br>"
                    " Tukey, J.W. (1977). <i>Exploratory Data Analysis</i>. Addison-Wesley.<br>"
                    " Iglewicz, B. & Hoaglin, D.C. (1993). <i>How to Detect and Handle Outliers</i>. ASQC Quality Press.<br>"
                    " Hubert, M. & Vandervieren, E. (2008). An Adjusted Boxplot for Skewed Distributions. <i>Comp. Stat. & Data Analysis</i>, 52(12)."
                    "</div>"
                    "</details>"
                )
                st.markdown(tier_html, unsafe_allow_html=True)
            
            if len(universal_df) >= 3:
                import plotly.graph_objects as go
                
                st.markdown("##### Visualisasi Box Plot - Deteksi Anomali IQR")
                
                bsk_vals = universal_df["bsk"].values
                q1_v = np.percentile(bsk_vals, 25)
                q3_v = np.percentile(bsk_vals, 75)
                iqr_v = q3_v - q1_v
                lb_v = q1_v - 1.5 * iqr_v
                ub_v = q3_v + 1.5 * iqr_v
                current_bsk = row.get("bsk", 0)
                is_outlier_cur = current_bsk < lb_v or current_bsk > ub_v
                
                fig = go.Figure()
                
                # Built-in horizontal box plot (otomatis rapi)
                fig.add_trace(go.Box(
                    x=bsk_vals,
                    name="",
                    marker_color="#94a3b8",
                    line_color="#1e3a8a",
                    fillcolor="rgba(30,58,138,0.1)",
                    boxpoints="all",
                    jitter=0.6,
                    pointpos=0,
                    marker=dict(size=5, opacity=0.4, color="#94a3b8"),
                    hoverinfo="x",
                    showlegend=False
                ))
                
                # Highlight: data yang sedang diuji
                hl_color = "#dc2626" if is_outlier_cur else "#1e3a8a"
                fig.add_trace(go.Scatter(
                    x=[current_bsk], y=[""],
                    mode='markers',
                    marker=dict(size=20, color=hl_color, symbol="diamond",
                                line=dict(width=3, color="white")),
                    name=f"{row['pemda_label']}",
                    hovertemplate=f"<b>{row['pemda_label']}</b><br>BSK: {format_currency(current_bsk)}<br>{'[!] ANOMALI' if is_outlier_cur else '[OK] NORMAL'}<extra></extra>",
                    showlegend=True
                ))
                
                # Batas IQR (garis vertikal)
                fig.add_vline(x=lb_v, line_dash="dot", line_color="#f97316", line_width=2)
                fig.add_vline(x=ub_v, line_dash="dot", line_color="#f97316", line_width=2)
                
                fig.add_annotation(x=lb_v, y=1.15, yref="paper",
                    text=f"Batas Bawah<br>{format_currency(lb_v)}",
                    showarrow=False, font=dict(size=9, color="#f97316"))
                fig.add_annotation(x=ub_v, y=1.15, yref="paper",
                    text=f"Batas Atas<br>{format_currency(ub_v)}",
                    showarrow=False, font=dict(size=9, color="#f97316"))
                
                fig.update_layout(
                    title="Distribusi BSK - Seluruh Pemda & Tahun",
                    xaxis_title="Biaya Satuan Kinerja (BSK)",
                    plot_bgcolor="white",
                    height=280,
                    margin=dict(t=70, b=40, l=20, r=20),
                    xaxis=dict(gridcolor="#e2e8f0"),
                    yaxis=dict(showticklabels=False),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.4, font=dict(size=11))
                )
                
                st.plotly_chart(fig, use_container_width=True)
                st.caption("* = Data yang sedang diuji    Titik abu-abu = Data pembanding    Garis oranye = Batas IQR")
                
                # Tabel komparasi
                st.markdown("##### Tabel Komparasi Universal")
                display_univ = universal_df[["pemda_label", "tahun", "pagu", "target", "bsk"]].copy()
                
                display_univ["is_outlier"] = (display_univ["bsk"] < lb_v) | (display_univ["bsk"] > ub_v)
                is_self_mask = (display_univ["pemda_label"] == row["pemda_label"]) & (display_univ["tahun"] == row["tahun"])
                
                display_univ["status"] = display_univ["is_outlier"].apply(lambda x: "[!] Anomali" if x else "[OK] Normal")
                display_univ.loc[is_self_mask, "pemda_label"] = display_univ.loc[is_self_mask, "pemda_label"] + " <- INI"
                
                display_univ["pagu"] = display_univ["pagu"].apply(format_currency)
                display_univ["bsk"] = display_univ["bsk"].apply(format_currency)
                display_univ["target"] = display_univ["target"].apply(lambda x: format_number(x, 2))
                display_univ["tahun"] = display_univ["tahun"].apply(lambda x: int(x))
                
                display_univ = display_univ[["pemda_label", "tahun", "pagu", "target", "bsk", "status"]]
                display_univ.rename(columns={
                    "pemda_label": "Pemda", "tahun": "Tahun", "pagu": "Pagu",
                    "target": "Target", "bsk": "BSK", "status": "Status"
                }, inplace=True)
                
                # Add No. column
                display_univ.insert(0, "No.", range(1, len(display_univ) + 1))
                
                st.dataframe(display_univ, use_container_width=True, hide_index=True)
            else:
                st.info("Data pembanding universal terlalu sedikit untuk visualisasi statistik.")

