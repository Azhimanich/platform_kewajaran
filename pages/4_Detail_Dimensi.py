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
            Menilai kewajaran BSK daerah dibandingkan dengan rata-rata regional menggunakan standar deviasi (**Z-Score**). Semua daerah (termasuk daerah subjek) dimasukkan dalam perhitungan rata-rata dan standar deviasi regional. Deviasi dikonversi menggunakan **Asymmetric Gaussian Decay Function**.
            
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
                <span style='color:#64748b;font-size:0.85em;'>Sistem mengumpulkan nilai BSK dari <b>{int(n_pemb)} daerah pembanding</b> yang memiliki kegiatan sama (termasuk daerah Anda sendiri).</span><br>
                <span style='color:#64748b;font-size:0.85em;'>Dari data regional tersebut, dicari Nilai Rata-Rata (Total BSK / Jumlah Daerah) dan seberapa menyebar datanya (Standar Deviasi).</span><br>
                <code style='font-size:0.95em;'>Rata-rata Regional = Total BSK / {int(n_pemb)} = <b>{format_currency(med_cpu)}</b></code><br>
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
                
                # Hitung Z-Score regional (termasuk subjek) untuk tampilan tabel
                mu_regional = spasial_df["bsk"].mean()
                sig_regional = spasial_df["bsk"].std() if len(spasial_df) > 1 else 0.0
                if pd.isna(sig_regional):
                    sig_regional = 0.0
                
                spasial_df["z_loo"] = np.where(
                    sig_regional > 0,
                    (spasial_df["bsk"] - mu_regional) / sig_regional,
                    np.where(spasial_df["bsk"] == mu_regional, 0.0, np.where(mu_regional > 0, (spasial_df["bsk"] - mu_regional) / mu_regional, 0.0))
                )
                
                def get_z_status(z):
                    az = abs(z)
                    if az < 1: return "[OK] Wajar"
                    elif az < 2: return "[Warning] Perhatian"
                    else: return "[!] Outlier"
                
                def get_skor_d2(z):
                    sigma_high = 1.96 / np.sqrt(2 * np.log(2))
                    sigma_low = 3.00 / np.sqrt(2 * np.log(2))
                    sigma_z = sigma_high if z >= 0 else sigma_low
                    return 100.0 * np.exp(-0.5 * (z / sigma_z) ** 2)
                        
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
                
                # Check if we have valid Z-scores
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
        st.subheader("Dimensi 3: Kewajaran Kinerja (Matriks Efisiensi × Efektivitas)")
        with st.container(border=True):
            d3_score = row.get("dimensi_3_score", pd.NA)
            efs_ratio = row.get("efisiensi_ratio", pd.NA)
            efk_ratio = row.get("efektivitas_ratio", pd.NA)
            efs_label = row.get("efisiensi_label", "")
            efk_label = row.get("efektivitas_label", "")
            kondisi_kinerja = row.get("dimensi_3_kondisi", "")
            score_efs = row.get("score_efisiensi", pd.NA)
            score_efk = row.get("score_efektivitas", pd.NA)
            
            st.markdown(r"""
            **Metodologi - Matriks Efisiensi & Efektivitas Kinerja (Goal Setting & Resource Allocation):**  
            Mengevaluasi kewajaran kinerja sub-kegiatan berdasarkan dua sumbu independen:
            1. **Efisiensi (Input/Proses):** Membandingkan pagu anggaran yang diusulkan saat ini terhadap rata-rata pagu historis.
            2. **Efektivitas (Output/Hasil):** Membandingkan target output yang diusulkan terhadap target prognosis (berdasarkan produktivitas historis).
            
            Kombinasi kedua rasio ini mengklasifikasikan usulan kinerja ke dalam 4 kuadran: **Ideal**, **Sangat Efisien**, **Kurang Dana**, atau **Tidak Wajar/Boros**.
            """)
            
            # Menampilkan Status & Skor
            col_status, col_score = st.columns([2, 1])
            with col_status:
                if kondisi_kinerja:
                    badge_color = "#22c55e" if kondisi_kinerja == "Ideal" else "#0284c7" if kondisi_kinerja == "Sangat Efisien" else "#f59e0b" if kondisi_kinerja == "Kurang Dana" else "#ef4444"
                    st.markdown(f"""
                    <div style='padding:15px; border-radius:10px; background:{badge_color}15; border:1px solid {badge_color}; text-align:center;'>
                        <span style='font-size:0.9rem; color:#64748b; text-transform:uppercase;'>Kondisi Kinerja</span><br>
                        <b style='font-size:1.8rem; color:{badge_color};'>{kondisi_kinerja}</b>
                    </div>
                    """, unsafe_allow_html=True)
            with col_score:
                if pd.notna(d3_score):
                    st.markdown(f"""
                    <div style='padding:15px; border-radius:10px; background:#f1f5f9; border:1px solid #e2e8f0; text-align:center;'>
                        <span style='font-size:0.9rem; color:#64748b; text-transform:uppercase;'>Skor Dimensi 3</span><br>
                        <b style='font-size:1.8rem; color:#1e3a8a;'>{d3_score:.1f} <span style='font-size:1rem; font-weight:normal; color:#64748b;'>/ 100</span></b>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.metric("Skor Dimensi 3", "Data Minim")

            st.write("---")
            
            # Row 1: Efisiensi (Input)
            st.markdown("##### Sumbu Efisiensi (Input & Anggaran)")
            c1_1, c1_2, c1_3, c1_4 = st.columns(4)
            pagu_val = row.get("pagu", pd.NA)
            hist_pagu_avg = row.get("hist_pagu_avg", pd.NA)
            c1_1.metric("Pagu Usulan", format_currency(pagu_val) if pd.notna(pagu_val) else "-")
            c1_2.metric("Rata-rata Pagu Historis", format_currency(hist_pagu_avg) if pd.notna(hist_pagu_avg) else "-")
            c1_3.metric("Rasio Efisiensi", f"{efs_ratio:.2f}x" if pd.notna(efs_ratio) else "-")
            c1_4.metric("Skor Efisiensi (Input)", f"{score_efs:.1f}" if pd.notna(score_efs) else "-")
            
            # Row 2: Efektivitas (Output)
            st.markdown("##### Sumbu Efektivitas (Output & Target)")
            c2_1, c2_2, c2_3, c2_4 = st.columns(4)
            avg_e = row.get("hist_efficiency_avg", pd.NA)
            prog_out = row.get("prognosis_output", pd.NA)
            curr_target = row.get("target", 0)
            c2_1.metric("Target Usulan", format_number(curr_target, 2))
            c2_2.metric("Target Prognosis", format_number(prog_out, 2) if pd.notna(prog_out) else "-")
            c2_3.metric("Rasio Efektivitas", f"{efk_ratio:.2f}x" if pd.notna(efk_ratio) else "-")
            c2_4.metric("Skor Efektivitas (Output)", f"{score_efk:.1f}" if pd.notna(score_efk) else "-")

            # Matriks Visual 2x3 Grid
            if kondisi_kinerja and pd.notna(efs_ratio) and pd.notna(efk_ratio):
                # Hitung cell highlight styles
                def get_cell_style(is_active, base_border, base_bg, base_color):
                    if is_active:
                        return f"padding: 12px; border-radius: 6px; border: 3px solid {base_border}; background: {base_bg}; color: {base_color}; text-align: center; box-shadow: 0 0 15px {base_border}80; font-weight: bold; opacity: 1.0; transform: scale(1.02);"
                    else:
                        return f"padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0; background: #ffffff; color: #94a3b8; text-align: center; opacity: 0.45; font-weight: normal;"

                cell_1_active = (efs_label == "Rendah" and efk_label == "Rendah")
                cell_2_active = (efs_label == "Rendah" and efk_label == "Sedang")
                cell_3_active = (efs_label == "Rendah" and efk_label == "Tinggi")
                cell_4_active = (efs_label == "Tinggi" and efk_label == "Rendah")
                cell_5_active = (efs_label == "Tinggi" and efk_label == "Sedang")
                cell_6_active = (efs_label == "Tinggi" and efk_label == "Tinggi")

                style_cell_1 = get_cell_style(cell_1_active, "#ef4444", "#fee2e2", "#991b1b") # Tidak Wajar/Boros
                style_cell_2 = get_cell_style(cell_2_active, "#ef4444", "#fee2e2", "#991b1b") # Tidak Wajar/Boros
                style_cell_3 = get_cell_style(cell_3_active, "#22c55e", "#dcfce7", "#166534") # Ideal (anggaran naik tapi diimbangi target memadai)
                style_cell_4 = get_cell_style(cell_4_active, "#f59e0b", "#fef3c7", "#92400e") # Kurang Dana
                style_cell_5 = get_cell_style(cell_5_active, "#0284c7", "#e0f2fe", "#075985") # Sangat Efisien
                style_cell_6 = get_cell_style(cell_6_active, "#22c55e", "#dcfce7", "#166534") # Ideal

                matrix_html = f"""
                <div style="margin: 25px 0; padding: 20px; background: #f8fafc; border-radius: 12px; border: 1px solid #e2e8f0;">
                    <h5 style="margin-top:0; color: #1e293b; text-align: center; font-weight: 700; font-size: 0.95rem; letter-spacing: 0.05em; text-transform: uppercase;">Posisi Sub-Kegiatan pada Matriks Kinerja</h5>
                    <div style="display: grid; grid-template-columns: 140px 1fr 1fr 1fr; gap: 12px; align-items: center; max-width: 800px; margin: 20px auto; font-family: sans-serif;">
                        <!-- Header Row -->
                        <div></div>
                        <div style="text-align: center; font-weight: bold; color: #475569; font-size: 0.8rem; background: #e2e8f0; padding: 8px; border-radius: 4px;">Efektivitas Rendah<br><span style="font-weight:normal; font-size:0.7rem;">(Target &lt; 50% Prognosis)</span></div>
                        <div style="text-align: center; font-weight: bold; color: #475569; font-size: 0.8rem; background: #e2e8f0; padding: 8px; border-radius: 4px;">Efektivitas Sedang<br><span style="font-weight:normal; font-size:0.7rem;">(Target 50% - 80%)</span></div>
                        <div style="text-align: center; font-weight: bold; color: #475569; font-size: 0.8rem; background: #e2e8f0; padding: 8px; border-radius: 4px;">Efektivitas Tinggi<br><span style="font-weight:normal; font-size:0.7rem;">(Target &ge; 80% Prognosis)</span></div>
                        
                        <!-- Row 1: Efisiensi Rendah -->
                        <div style="font-weight: bold; color: #475569; font-size: 0.8rem; text-align: right; padding-right: 10px; background: #f1f5f9; padding: 8px; border-radius: 4px;">Efisiensi Rendah<br><span style="font-weight:normal; font-size:0.7rem;">(Pagu &gt; 1.2x Historis)</span></div>
                        <div style="{style_cell_1}">
                            <div style="font-size:0.85rem;">Tidak Wajar / Boros</div>
                            <div style="font-size:0.7rem; font-weight:normal; margin-top:2px;">(Anggaran Boros, Output Rendah)</div>
                        </div>
                        <div style="{style_cell_2}">
                            <div style="font-size:0.85rem;">Tidak Wajar / Boros</div>
                            <div style="font-size:0.7rem; font-weight:normal; margin-top:2px;">(Anggaran Boros, Output Sedang)</div>
                        </div>
                        <div style="{style_cell_3}">
                            <div style="font-size:0.85rem;">Ideal</div>
                            <div style="font-size:0.7rem; font-weight:normal; margin-top:2px;">(Anggaran Naik & Output Tinggi)</div>
                        </div>

                        <!-- Row 2: Efisiensi Tinggi -->
                        <div style="font-weight: bold; color: #475569; font-size: 0.8rem; text-align: right; padding-right: 10px; background: #f1f5f9; padding: 8px; border-radius: 4px;">Efisiensi Tinggi<br><span style="font-weight:normal; font-size:0.7rem;">(Pagu &le; 1.2x Historis)</span></div>
                        <div style="{style_cell_4}">
                            <div style="font-size:0.85rem;">Kurang Dana</div>
                            <div style="font-size:0.7rem; font-weight:normal; margin-top:2px;">(Anggaran Rendah, Output Rendah)</div>
                        </div>
                        <div style="{style_cell_5}">
                            <div style="font-size:0.85rem;">Sangat Efisien</div>
                            <div style="font-size:0.7rem; font-weight:normal; margin-top:2px;">(Anggaran Rendah, Output Sedang)</div>
                        </div>
                        <div style="{style_cell_6}">
                            <div style="font-size:0.85rem;">Ideal</div>
                            <div style="font-size:0.7rem; font-weight:normal; margin-top:2px;">(Anggaran Hemat & Output Tinggi)</div>
                        </div>
                    </div>
                </div>
                """
                st.markdown(matrix_html, unsafe_allow_html=True)

            # Detail Perhitungan Transparan
            if pd.notna(avg_e) and pd.notna(prog_out) and pd.notna(efs_ratio) and pd.notna(efk_ratio):
                st.markdown(f"""
                <div style='background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:20px;border-radius:12px;border:1px solid #c7d2fe;margin:12px 0;'>
                <h4 style='color:#1e3a8a;margin:0 0 16px 0;'>[Kalkulasi] Langkah Perhitungan Dimensi 3</h4>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 1 - Menghitung Efisiensi Kemampuan Historis & Target Prognosis (Hasil)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Sistem menghitung rata-rata output per rupiah dari realisasi historis: <b>{avg_e:.10f}</b> unit/Rupiah.</span><br>
                <span style='color:#64748b;font-size:0.85em;'>Berdasarkan pagu berjalan ({format_currency(pagu_val)}), target prognosis (yang seharusnya mampu dicapai) adalah:</span><br>
                <code style='font-size:0.95em;'>Target Prognosis = Pagu × Efisiensi Historis = {format_currency(pagu_val)} × {avg_e:.10f} = <b>{format_number(prog_out, 2)} unit</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 2 - Menghitung Rasio & Label Sumbu</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Kedua rasio sumbu dihitung secara independen:</span><br>
                <code style='font-size:0.95em;'>Rasio Efisiensi (Input) = Pagu Usulan / Rata-rata Pagu Historis = {format_currency(pagu_val)} / {format_currency(hist_pagu_avg) if pd.notna(hist_pagu_avg) else "-"} = <b>{efs_ratio:.2f}x</b> (Status: {efs_label})</code><br>
                <code style='font-size:0.95em;'>Rasio Efektivitas (Output) = Target Usulan / Target Prognosis = {format_number(curr_target, 2)} / {format_number(prog_out, 2)} = <b>{efk_ratio:.2f}x</b> (Status: {efk_label})</code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #f59e0b;'>
                <b style='color:#92400e;'>Langkah 3 - Penentuan Kuadran Kondisi Kinerja</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Menggunakan matriks evaluasi 4 kuadran:</span><br>
                <span style='color:#64748b;font-size:0.85em;'>Efisiensi <b>{efs_label}</b> ({'Pagu wajar/hemat' if efs_label == 'Tinggi' else 'Pagu tinggi/boros'}) &times; Efektivitas <b>{efk_label}</b> ({'Target memadai/tinggi' if efk_label == 'Tinggi' else 'Target sedang' if efk_label == 'Sedang' else 'Target rendah'}) menghasilkan status: <b>{kondisi_kinerja}</b>.</span>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #10b981;'>
                <b style='color:#065f46;'>Langkah 4 - Perhitungan Skor Akhir (Gaussian Decay pada Kedua Sumbu)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Masing-masing sumbu diberi skor 0-100 menggunakan fungsi Gaussian Decay. Efisiensi diberi penalti jika rasio > 1.0 (overbudgeting). Efektivitas diberi penalti jika rasio < 1.0 (underachieving). Skor akhir adalah rata-rata keduanya.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>Skor Efisiensi = {score_efs:.1f} | Skor Efektivitas = {score_efk:.1f}</code><br>
                <code style='font-size:1.1em;'><b style='color:#059669;'>Hasil Akhir -> Skor Dimensi 3 = {d3_score:.1f} dari 100</b></code>
                </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("[Info] Tidak ada data realisasi historis atau pagu historis. Dimensi ini tidak berkontribusi terhadap IKP (Dynamic Weighting).")

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
        st.subheader("Dimensi 4: Kewajaran Perencanaan (Konsistensi Renstra vs RKPD)")
        with st.container(border=True):
            d4_score = row.get("dimensi_4_score", pd.NA)
            consistency_ratio = row.get("d4_consistency_ratio", pd.NA)
            rkpd_programs_count = row.get("d4_rkpd_programs", pd.NA)
            renstra_programs_count = row.get("d4_renstra_programs", pd.NA)
            consistent_programs_count = row.get("d4_consistent_programs", pd.NA)
            phantom_count = row.get("d4_phantom_programs", pd.NA)
            phantom_list_str = row.get("d4_phantom_list", "")
            phantom_pagu = row.get("d4_phantom_pagu", pd.NA)
            phantom_pagu_ratio = row.get("d4_phantom_pagu_ratio", pd.NA)
            
            st.markdown(r"""
            **Metodologi - Consistency Score (Renstra 5 Tahun vs RKPD Tahunan):**  
            Mengukur tingkat konsistensi antara dokumen perencanaan strategis jangka menengah (Renstra 5 Tahun)  
            dengan dokumen rencana kerja tahunan (RKPD). Skor mencerminkan seberapa banyak program kerja di  
            RKPD yang memiliki landasan perencanaan di Renstra.

            **Formula Consistency Score:**
            $$\text{Consistency} = \frac{|\text{Program}_{\text{RKPD}} \cap \text{Program}_{\text{Renstra}}|}{|\text{Program}_{\text{RKPD}}|}$$
            
            **Konversi ke Skor (Gaussian Decay):**
            $$\text{Score} = 100 \times \exp\left(-\frac{1}{2}\left(\frac{1 - \text{Consistency}}{\sigma_c}\right)^2\right), \quad \sigma_c \approx 0{,}255$$
            
            *Kalibrasi $\sigma_c$ agar konsistensi 70% (discrepancy 30%) menghasilkan skor tepat 50.*
            """)
            
            # Red flags info box
            st.markdown("""
            > 🚨 **Red Flags yang Dideteksi:**
            > - **Program Siluman**: Program di RKPD yang tidak ada di Renstra
            > - **Alokasi Non-Prioritas**: Total pagu pada program non-Renstra
            > - **Pergeseran Fokus**: Indikasi tidak terencana dari dokumen strategis
            """)
            
            # Metrics row
            c1, c2, c3, c4 = st.columns(4)
            
            if pd.notna(rkpd_programs_count):
                c1.metric("Program di RKPD", f"{int(rkpd_programs_count)}")
            else:
                c1.metric("Program di RKPD", "-")
                
            if pd.notna(renstra_programs_count):
                c2.metric("Program di Renstra", f"{int(renstra_programs_count)}")
            else:
                c2.metric("Program di Renstra", "-")
                
            if pd.notna(phantom_count):
                c3.metric("Program Siluman",
                         f"{int(phantom_count)}",
                         delta="Tidak terencana" if int(phantom_count) > 0 else "Nihil",
                         delta_color="inverse" if int(phantom_count) > 0 else "normal")
            else:
                c3.metric("Program Siluman", "-")
                
            if pd.isna(d4_score):
                c4.metric("Skor Dimensi 4", "Tidak Ada Data")
            else:
                c4.metric("Skor Dimensi 4", f"{d4_score:.1f} / 100")
            
            # Show full calculation if data is available
            if pd.notna(d4_score) and pd.notna(consistency_ratio):
                sigma_c = 0.30 / np.sqrt(2 * np.log(2))
                discrepancy = 1.0 - consistency_ratio
                score_verify = 100.0 * np.exp(-0.5 * (discrepancy / sigma_c) ** 2)
                
                # Consistency grade
                if consistency_ratio >= 0.90:
                    cons_label = "Sangat Konsisten"
                    cons_color = "#16a34a"
                elif consistency_ratio >= 0.80:
                    cons_label = "Konsisten"
                    cons_color = "#ca8a04"
                elif consistency_ratio >= 0.70:
                    cons_label = "Cukup Konsisten"
                    cons_color = "#ea580c"
                else:
                    cons_label = "Kurang Konsisten"
                    cons_color = "#dc2626"
                
                tahun_val = int(row.get("tahun", 0))
                rkpd_p = int(rkpd_programs_count)
                renstra_p = int(renstra_programs_count)
                consistent_p = int(consistent_programs_count)
                phantom_p = int(phantom_count)
                
                step_html = f"""
                <div style='background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:20px;border-radius:12px;border:1px solid #c7d2fe;margin:12px 0;'>
                <h4 style='color:#1e3a8a;margin:0 0 16px 0;'>[Kalkulasi] Langkah Perhitungan Dimensi 4</h4>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 1 - Kumpulkan Himpunan Program</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Sistem mengidentifikasi semua kode program unik dari dua sumber data: RKPD {tahun_val} dan Renstra 2025-2029.</span><br>
                <code style='font-size:0.95em;'>Program RKPD {tahun_val} = <b>{rkpd_p} program unik</b></code><br>
                <code style='font-size:0.95em;'>Program Renstra 2025-2029 = <b>{renstra_p} program unik</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #f59e0b;'>
                <b style='color:#92400e;'>Langkah 2 - Hitung Irisan (Intersection)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Dari {rkpd_p} program RKPD, berapa yang memiliki landasan di Renstra?</span><br>
                <code style='font-size:0.95em;'>Program Konsisten (RKPD &cap; Renstra) = <b>{consistent_p} program</b></code><br>
                <code style='font-size:0.95em;'>Program Siluman (RKPD - Renstra) = <b>{phantom_p} program</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #8b5cf6;'>
                <b style='color:#5b21b6;'>Langkah 3 - Hitung Rasio Konsistensi</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Consistency = Program Konsisten / Total Program RKPD</span><br>
                <code style='font-size:0.95em;'>Consistency = {consistent_p} / {rkpd_p} = <b style='color:{cons_color};'>{consistency_ratio:.4f} ({consistency_ratio*100:.1f}%) &mdash; {cons_label}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #10b981;'>
                <b style='color:#065f46;'>Langkah 4 - Konversi ke Skor (Gaussian Decay)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Discrepancy = 1 - Consistency = {discrepancy:.4f}. Semakin besar discrepancy, skor turun melengkung.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>100 &times; exp(-0.5 &times; ({discrepancy:.4f} / {sigma_c:.4f})&sup2;)</code><br>
                <code style='font-size:1.1em;'><b style='color:#059669;'>Hasil Akhir &rarr; Skor Dimensi 4 = {score_verify:.1f} dari 100</b></code>
                </div>
                </div>
                """
                st.markdown(step_html, unsafe_allow_html=True)
                
                # Red Flags Section
                if pd.notna(phantom_count) and int(phantom_count) > 0:
                    phantom_pagu_fmt = format_currency(phantom_pagu) if pd.notna(phantom_pagu) else "N/A"
                    phantom_ratio_fmt = f"{phantom_pagu_ratio*100:.1f}%" if pd.notna(phantom_pagu_ratio) else "N/A"
                    
                    rf_html = f"""
                    <div style='background:linear-gradient(135deg,#fff5f5,#fee2e2);padding:16px;border-radius:12px;border:2px solid #fca5a5;margin:12px 0;'>
                    <h4 style='color:#991b1b;margin:0 0 12px 0;'>Red Flag Terdeteksi: Program Siluman / Inkonsistensi</h4>
                    <div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;'>
                      <div style='background:white;padding:12px;border-radius:8px;'>
                        <div style='color:#7f1d1d;font-weight:bold;font-size:0.9em;'>Jumlah Program Siluman</div>
                        <div style='font-size:1.8em;font-weight:800;color:#dc2626;'>{int(phantom_count)}</div>
                        <div style='color:#64748b;font-size:0.8em;'>Program di RKPD tanpa dasar Renstra</div>
                      </div>
                      <div style='background:white;padding:12px;border-radius:8px;'>
                        <div style='color:#7f1d1d;font-weight:bold;font-size:0.9em;'>Total Pagu Tidak Terencana</div>
                        <div style='font-size:1.3em;font-weight:800;color:#dc2626;'>{phantom_pagu_fmt}</div>
                        <div style='color:#64748b;font-size:0.8em;'>({phantom_ratio_fmt} dari total pagu)</div>
                      </div>
                    </div>
                    </div>
                    """
                    st.markdown(rf_html, unsafe_allow_html=True)
                    
                    # Show phantom program list
                    if phantom_list_str:
                        phantom_codes = [c.strip() for c in phantom_list_str.split(",") if c.strip()]
                        phantom_details = []
                        rkpd_year_df = df[(df["kodepemda"] == row["kodepemda"]) & (df["tahun"] == row["tahun"])]
                        for pcode in phantom_codes:
                            match = rkpd_year_df[rkpd_year_df["kodeprogram"] == pcode]
                            prog_name = match["uraiprogram"].iloc[0] if not match.empty else "N/A"
                            prog_pagu_sum = match["pagu"].sum() if not match.empty else 0
                            n_sub = len(match)
                            phantom_details.append({
                                "Kode Program": pcode,
                                "Nama Program": prog_name[:80] + "..." if len(prog_name) > 80 else prog_name,
                                "Sub-Kegiatan": n_sub,
                                "Total Pagu": format_currency(prog_pagu_sum),
                                "Status": "Tidak ada di Renstra"
                            })
                        
                        if phantom_details:
                            st.markdown("##### Daftar Program Siluman (Ada di RKPD, Tidak Ada di Renstra)")
                            phantom_df_show = pd.DataFrame(phantom_details)
                            phantom_df_show.insert(0, "No.", range(1, len(phantom_df_show)+1))
                            st.dataframe(phantom_df_show, use_container_width=True, hide_index=True)
                else:
                    st.success("Tidak ada program siluman terdeteksi. Seluruh program RKPD memiliki landasan yang valid di dokumen Renstra.")
                
                # Calibration table
                tier_html = (
                    "<details style='margin-top:8px;'><summary style='cursor:pointer;color:#1e3a8a;font-weight:bold;font-size:0.85rem;'>[Chart] Tabel Kalibrasi Skor Konsistensi Renstra-RKPD</summary>"
                    "<table style='width:100%;border-collapse:collapse;font-size:0.85rem;margin-top:8px;'>"
                    "<tr style='background:#f1f5f9;'><th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Rasio Konsistensi</th>"
                    "<th style='padding:8px;text-align:center;border-bottom:1px solid #cbd5e1;'>Skor</th>"
                    "<th style='padding:8px;text-align:left;border-bottom:1px solid #cbd5e1;'>Interpretasi</th></tr>"
                    "<tr style='background:#f0fdf4;'><td style='padding:6px 8px;text-align:center;'>100% (Sempurna)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>100.0</td><td style='padding:6px 8px;color:#22c55e;'>Sangat Konsisten</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>90%</td><td style='padding:6px 8px;text-align:center;'>88.2</td><td style='padding:6px 8px;color:#22c55e;'>Konsisten</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>80%</td><td style='padding:6px 8px;text-align:center;'>59.5</td><td style='padding:6px 8px;color:#eab308;'>Cukup Konsisten</td></tr>"
                    "<tr style='background:#fef2f2;'><td style='padding:6px 8px;text-align:center;font-weight:bold;'>70% (Batas Wajar)</td><td style='padding:6px 8px;text-align:center;font-weight:bold;'>50.0</td><td style='padding:6px 8px;color:#ef4444;font-weight:bold;'>Batas Toleransi</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>60%</td><td style='padding:6px 8px;text-align:center;'>26.3</td><td style='padding:6px 8px;color:#7f1d1d;'>Tidak Konsisten</td></tr>"
                    "<tr><td style='padding:6px 8px;text-align:center;'>50%</td><td style='padding:6px 8px;text-align:center;'>7.9</td><td style='padding:6px 8px;color:#7f1d1d;'>Sangat Tidak Konsisten</td></tr>"
                    "</table>"
                    "<div style='margin-top:8px;font-size:0.8rem;color:#64748b;'>"
                    "<b>Referensi:</b> Consistency Score = |Program_RKPD &cap; Program_Renstra| / |Program_RKPD|. "
                    "Gaussian Decay: sigma_c = 0.30/sqrt(2*ln(2)). Sumber: renstra_data_pagu_diy.csv (Renstra DIY 2025-2029)."
                    "</div>"
                    "</details>"
                )
                st.markdown(tier_html, unsafe_allow_html=True)
                
                # Venn visualization
                st.markdown("##### Visualisasi Diagram Konsistensi Renstra vs RKPD")
                import plotly.graph_objects as go
                
                n_only_renstra = int(renstra_programs_count) - int(consistent_programs_count)
                n_intersection = int(consistent_programs_count)
                n_only_rkpd = int(phantom_count)
                
                fig_venn = go.Figure()
                theta_arr = np.linspace(0, 2*np.pi, 100)
                cx1, cy1, r1 = -0.35, 0, 1.0
                cx2, cy2, r2 = 0.35, 0, 1.0
                
                fig_venn.add_trace(go.Scatter(
                    x=cx1 + r1*np.cos(theta_arr), y=cy1 + r1*np.sin(theta_arr),
                    fill='toself', fillcolor='rgba(59,130,246,0.15)',
                    line=dict(color='#1d4ed8', width=3),
                    name=f'Renstra ({int(renstra_programs_count)} program)', showlegend=True
                ))
                fig_venn.add_trace(go.Scatter(
                    x=cx2 + r2*np.cos(theta_arr), y=cy2 + r2*np.sin(theta_arr),
                    fill='toself', fillcolor='rgba(239,68,68,0.12)',
                    line=dict(color='#dc2626', width=3),
                    name=f'RKPD {int(row.get("tahun",""))} ({int(rkpd_programs_count)} program)', showlegend=True
                ))
                
                fig_venn.add_annotation(x=-0.88, y=0,
                    text=f"<b>Hanya di<br>Renstra</b><br>{n_only_renstra}",
                    showarrow=False, font=dict(size=13, color='#1d4ed8'))
                fig_venn.add_annotation(x=0, y=0,
                    text=f"<b>Konsisten</b><br>{n_intersection} program",
                    showarrow=False, bgcolor='rgba(240,255,244,0.9)',
                    font=dict(size=13, color='#065f46'))
                fig_venn.add_annotation(x=0.88, y=0,
                    text=f"<b>Siluman<br>di RKPD</b><br>{n_only_rkpd}",
                    showarrow=False, font=dict(size=13, color='#dc2626'))
                fig_venn.add_annotation(x=0, y=1.4,
                    text=f"<b>Konsistensi: {consistency_ratio*100:.1f}%  Skor D4: {d4_score:.1f}/100</b>",
                    showarrow=False, font=dict(size=15, color='#1e3a8a'))
                
                fig_venn.update_layout(
                    height=340, showlegend=True,
                    xaxis=dict(visible=False, range=[-1.8, 1.8]),
                    yaxis=dict(visible=False, range=[-1.4, 1.6], scaleanchor='x'),
                    plot_bgcolor='white',
                    margin=dict(t=20, b=20, l=20, r=20),
                    legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5)
                )
                st.plotly_chart(fig_venn, use_container_width=True)
                
            else:
                st.info("ℹ️ **Data Renstra Tidak Tersedia**: Dokumen `renstra_data_pagu_diy.csv` yang diunggah hanya mencakup data perencanaan untuk **Kab. Bantul, Kab. Gunungkidul, Kab. Kulon Progo, dan Kota Yogyakarta**. Untuk Pemda Sleman dan Provinsi DIY, Dimensi 4 secara otomatis dikecualikan dari pembobotan IKP (menggunakan *Dynamic Weighting*).")

        # DIMENSI 5
        st.subheader("Dimensi 5: Kewajaran Statistik (Asymmetric Tukey's Fences)")
        with st.container(border=True):
            d5_score = row.get("dimensi_5_score", pd.NA)
            is_anomali = row.get("is_anomali", False)
            
            st.markdown(r"""
            **Metodologi - Pagar Asimetris Berbasis Kebijakan (Asymmetric Tukey's Fences):**  
            Mendeteksi anomali BSK menggunakan batas atas ketat (pemborosan) dan batas bawah yang aman (tidak boleh negatif).
            
            **Formula Batas Aman:**
            $$\text{Batas Atas} = Q_3 + 1{,}5 \times IQR$$
            $$\text{Batas Bawah} = Q_1 - 0{,}2 \times IQR$$
            
            **Jarak Outlier ($d$):**
            $$d = \begin{cases} 0 & \text{jika Batas Bawah} \le BSK \le \text{Batas Atas} \\ \dfrac{\text{Batas Bawah} - BSK}{IQR} & \text{jika } BSK < \text{Batas Bawah} \\ \dfrac{BSK - \text{Batas Atas}}{IQR} & \text{jika } BSK > \text{Batas Atas} \end{cases}$$
            
            **Skor Gaussian Decay:**
            $$\text{Skor} = 100 \times \exp\left(-\frac{1}{2}\left(\frac{d}{\sigma}\right)^2\right), \quad \sigma = 0{,}5$$
            """)
            
            # Metrics row
            c1, c2, c3, c4 = st.columns(4)
            q1_v  = row.get("stat_q1", pd.NA)
            q3_v  = row.get("stat_q3", pd.NA)
            ub_v  = row.get("stat_upper_bound", pd.NA)
            lb_v  = row.get("stat_lower_bound", pd.NA)
            d_val = row.get("stat_iqr_distance", pd.NA)
            
            c1.metric("Batas Bawah (k₂=0.2)", format_currency(lb_v) if pd.notna(lb_v) else "-")
            c2.metric("Batas Atas (k₁=1.5)", format_currency(ub_v) if pd.notna(ub_v) else "-")
            c3.metric("Jarak Outlier (d)", f"{d_val:.4f}" if pd.notna(d_val) else "-")
            
            if pd.isna(d5_score):
                c4.metric("Skor Dimensi 5", "Tidak Ada Data")
            elif is_anomali:
                c4.metric("Skor Dimensi 5", f"{d5_score:.1f} / 100", delta="ANOMALI", delta_color="inverse")
            else:
                c4.metric("Skor Dimensi 5", f"{d5_score:.1f} / 100", delta="Wajar", delta_color="normal")
            
            # --- Detail Perhitungan ---
            universal_df = df[
                (df["kodesubkegiatan"] == row["kodesubkegiatan"]) &
                (df["satuan"] == row["satuan"]) &
                (df["bsk"].notna()) & (df["bsk"] > 0)
            ].sort_values(by="bsk")
            
            if not universal_df.empty and len(universal_df) >= 4:
                bsk_arr   = universal_df["bsk"].values
                n_data    = len(bsk_arr)
                q1_calc   = np.percentile(bsk_arr, 25)
                q2_calc   = np.percentile(bsk_arr, 50)
                q3_calc   = np.percentile(bsk_arr, 75)
                iqr_calc  = q3_calc - q1_calc
                ub_calc   = q3_calc + 1.5 * iqr_calc
                lb_calc   = q1_calc - 0.2 * iqr_calc
                current_bsk = row.get("bsk", 0)
                
                # Jarak d manual untuk verifikasi UI
                if current_bsk < lb_calc:
                    current_d = (lb_calc - current_bsk) / iqr_calc if iqr_calc > 0 else 0.0
                elif current_bsk > ub_calc:
                    current_d = (current_bsk - ub_calc) / iqr_calc if iqr_calc > 0 else 0.0
                else:
                    current_d = 0.0
                    
                sigma_val = 0.5
                score_verify = 100.0 * np.exp(-0.5 * (current_d / sigma_val) ** 2) if current_d > 0 else 100.0
                
                # Status label
                if current_d > 0 and current_bsk < lb_calc:
                    status_label = '<b style="color:#7f1d1d;">ANOMALI BAWAH (Anggaran Terlalu Rendah)</b>'
                elif current_d > 0 and current_bsk > ub_calc:
                    status_label = '<b style="color:#ef4444;">ANOMALI ATAS (Anggaran Terlalu Tinggi / Pemborosan)</b>'
                else:
                    status_label = '<b style="color:#22c55e;">DALAM BATAS WAJAR (Sempurna)</b>'
                
                # Distance calc text explanation
                if current_bsk < lb_calc:
                    d_calc = f"d = (Batas Bawah - BSK) / IQR = ({format_currency(lb_calc)} - {format_currency(current_bsk)}) / {format_currency(iqr_calc)} = <b>{current_d:.4f}</b>"
                elif current_bsk > ub_calc:
                    d_calc = f"d = (BSK - Batas Atas) / IQR = ({format_currency(current_bsk)} - {format_currency(ub_calc)}) / {format_currency(iqr_calc)} = <b>{current_d:.4f}</b>"
                else:
                    d_calc = "d = <b>0.0000</b> (karena BSK di dalam batas aman)"
                
                dim5_html = f"""
                <div style='background:linear-gradient(135deg,#f8fafc,#eef2ff);padding:20px;border-radius:12px;border:1px solid #c7d2fe;margin:12px 0;'>
                <h4 style='color:#1e3a8a;margin:0 0 16px 0;'>[Kalkulasi] Langkah Perhitungan Dimensi 5 (Asymmetric Tukey)</h4>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #3b82f6;'>
                <b style='color:#1e40af;'>Langkah 1 - Susun Data &amp; Hitung Kuartil ({n_data} daerah pembanding)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>BSK daerah pembanding diurutkan dari yang terkecil ke terbesar.</span><br>
                <ul style='font-size:0.85em;color:#64748b;margin-top:4px;'>
                   <li><b>Q1 (25% Terendah):</b> {format_currency(q1_calc)}</li>
                   <li><b>Q3 (75% Tertinggi):</b> {format_currency(q3_calc)}</li>
                   <li><b>IQR (Rentang Tengah):</b> Q3 - Q1 = <b>{format_currency(iqr_calc)}</b></li>
                </ul>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #8b5cf6;'>
                <b style='color:#5b21b6;'>Langkah 2 - Tentukan Batas Aman Kebijakan</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Batas atas ketat untuk deteksi pemborosan (k1=1.5). Batas bawah longgar dan tidak boleh negatif (k2=0.2).</span><br>
                <code style='font-size:0.95em;'><b>Batas Atas</b> = Q3 + (1.5 × IQR) = {format_currency(q3_calc)} + (1.5 × {format_currency(iqr_calc)}) = <b style='color:#dc2626;'>{format_currency(ub_calc)}</b></code><br>
                <code style='font-size:0.95em;'><b>Batas Bawah</b> = Q1 - (0.2 × IQR) = {format_currency(q1_calc)} - (0.2 × {format_currency(iqr_calc)}) = <b style='color:#2563eb;'>{format_currency(lb_calc)}</b></code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #f59e0b;'>
                <b style='color:#92400e;'>Langkah 3 - Cek Jarak Outlier (d)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>BSK daerah Anda = {format_currency(current_bsk)}.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>{d_calc}</code>
                </div>
                
                <div style='background:white;padding:14px 16px;border-radius:8px;margin-bottom:10px;border-left:4px solid #10b981;'>
                <b style='color:#065f46;'>Langkah 4 - Hitung Skor Akhir (Gaussian Decay)</b><br>
                <span style='color:#64748b;font-size:0.85em;'>Jika d = 0 (di dalam batas aman), skor langsung Sempurna (100). Jika di luar batas, skor turun secara Gaussian.</span><br>
                <code style='font-size:0.95em;color:#475569;background:#f1f5f9;padding:2px 6px;border-radius:4px;'>100 × exp(-0.5 × ({current_d:.4f} / 0.5)²)</code><br>
                <code style='font-size:1.1em;'><b style='color:#059669;'>Skor Dimensi 5 = {score_verify:.1f} / 100</b></code><br><br>
                <span style='font-size:0.85em;'>Status: {status_label}</span>
                </div>
                </div>
                """
                st.markdown(dim5_html, unsafe_allow_html=True)
                
                if is_anomali:
                    dir_label = "BAWAH (Terlahu Murah)" if current_bsk < lb_calc else "ATAS (Terlalu Mahal / Pemborosan)"
                    st.warning(
                        f"⚠️ **Terdeteksi Outlier {dir_label}!** BSK Anda ({format_currency(current_bsk)}) "
                        f"berada di luar rentang wajar ({format_currency(lb_calc)} s/d {format_currency(ub_calc)})."
                    )
            
            # --- Visualisasi Plotly ---
            if len(universal_df) >= 3:
                import plotly.graph_objects as go
                
                st.markdown("##### Visualisasi Distribusi BSK - Asymmetric Tukey's Fences")
                
                bsk_arr   = universal_df["bsk"].values
                q1_calc   = np.percentile(bsk_arr, 25)
                q3_calc   = np.percentile(bsk_arr, 75)
                iqr_calc  = q3_calc - q1_calc
                ub_calc   = q3_calc + 1.5 * iqr_calc
                lb_calc   = q1_calc - 0.2 * iqr_calc
                current_bsk  = row.get("bsk", 0)
                is_outlier_cur = bool(current_bsk < lb_calc or current_bsk > ub_calc)
                
                fig = go.Figure()
                
                x_range = max(bsk_arr.max(), ub_calc) * 1.15
                x_min   = min(0.0, lb_calc * 1.15) if lb_calc < 0 else 0.0
                
                # Rectangles for safe/unsafe zones
                if lb_calc > x_min:
                    fig.add_shape(type="rect", x0=x_min, x1=lb_calc, y0=-0.5, y1=0.5,
                                  fillcolor="rgba(239,68,68,0.08)", line_width=0, layer="below")
                fig.add_shape(type="rect", x0=lb_calc, x1=ub_calc, y0=-0.5, y1=0.5,
                              fillcolor="rgba(74,222,128,0.12)", line_width=0, layer="below")
                fig.add_shape(type="rect", x0=ub_calc, x1=x_range, y0=-0.5, y1=0.5,
                              fillcolor="rgba(239,68,68,0.08)", line_width=0, layer="below")
                
                # Scatter points
                for _, r_u in universal_df.iterrows():
                    bsk_i = r_u["bsk"]
                    is_out = bool(bsk_i < lb_calc or bsk_i > ub_calc)
                    is_self = bool((r_u["pemda_label"] == row["pemda_label"]) and (r_u["tahun"] == row["tahun"]))
                    color = ("#dc2626" if is_out else "#3b82f6") if not is_self else ("#7c3aed" if not is_out else "#dc2626")
                    symbol = "diamond" if is_self else "circle"
                    size   = 18 if is_self else 8
                    fig.add_trace(go.Scatter(
                        x=[bsk_i], y=[0],
                        mode="markers",
                        marker=dict(size=size, color=color, symbol=symbol,
                                    line=dict(width=2 if is_self else 1, color="white")),
                        name=f"{r_u['pemda_label']} {int(r_u['tahun'])}",
                        hovertemplate=(
                            f"<b>{r_u['pemda_label']} {int(r_u['tahun'])}</b><br>"
                            f"BSK: {format_currency(bsk_i)}<br>"
                            f"{'⚠️ ANOMALI' if is_out else '✅ Normal'}"
                            "<extra></extra>"
                        ),
                        showlegend=is_self
                    ))
                
                # Fence boundary lines
                fig.add_vline(x=lb_calc, line_dash="dash", line_color="#2563eb", line_width=2.5,
                              annotation_text=f"Batas Bawah (k₂=0.2)<br>{format_currency(lb_calc)}",
                              annotation_position="top left", annotation_font=dict(size=10, color="#2563eb"))
                fig.add_vline(x=ub_calc, line_dash="dash", line_color="#dc2626", line_width=2.5,
                              annotation_text=f"Batas Atas (k₁=1.5)<br>{format_currency(ub_calc)}",
                              annotation_position="top right", annotation_font=dict(size=10, color="#dc2626"))
                
                fig.update_layout(
                    title=dict(text="Distribusi BSK — Pagar Asimetris (Biru=Bawah k₂=0.2 | Merah=Atas k₁=1.5)", font=dict(size=13)),
                    xaxis_title="Biaya Satuan Kinerja (BSK)",
                    plot_bgcolor="white",
                    height=280,
                    margin=dict(t=80, b=40, l=20, r=20),
                    xaxis=dict(gridcolor="#e2e8f0", tickformat=","),
                    yaxis=dict(visible=False, range=[-1, 1]),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.45, font=dict(size=11))
                )
                
                st.plotly_chart(fig, use_container_width=True)
                st.caption(
                    "◆ = Daerah yang diuji | ● = Daerah lain | "
                    "Zona Hijau = Batas Aman | Zona Merah = Anomali"
                )
                
                # Comparison table
                st.markdown("##### Tabel Komparasi Universal")
                display_univ = universal_df[["pemda_label", "tahun", "pagu", "target", "bsk"]].copy()
                display_univ["is_outlier"] = (display_univ["bsk"] < lb_calc) | (display_univ["bsk"] > ub_calc)
                is_self_mask = ((display_univ["pemda_label"] == row["pemda_label"]) &
                                (display_univ["tahun"] == row["tahun"]))
                display_univ["status"] = display_univ["is_outlier"].apply(
                    lambda x: "⚠️ Anomali" if x else "✅ Normal"
                )
                display_univ.loc[is_self_mask, "pemda_label"] = (
                    display_univ.loc[is_self_mask, "pemda_label"] + " ← INI"
                )
                display_univ["pagu"]  = display_univ["pagu"].apply(format_currency)
                display_univ["bsk"]   = display_univ["bsk"].apply(format_currency)
                display_univ["target"] = display_univ["target"].apply(lambda x: format_number(x, 2))
                display_univ["tahun"] = display_univ["tahun"].apply(lambda x: int(x))
                display_univ = display_univ[["pemda_label","tahun","pagu","target","bsk","status"]]
                display_univ.rename(columns={
                    "pemda_label": "Pemda", "tahun": "Tahun", "pagu": "Pagu",
                    "target": "Target", "bsk": "BSK", "status": "Status"
                }, inplace=True)
                display_univ.insert(0, "No.", range(1, len(display_univ)+1))
                st.dataframe(display_univ, use_container_width=True, hide_index=True)
            else:
                st.info("Data pembanding universal terlalu sedikit untuk visualisasi statistik.")
