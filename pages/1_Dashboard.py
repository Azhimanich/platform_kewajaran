import streamlit as st
import plotly.express as px
import pandas as pd
import json
import os
import urllib.parse

from src.pipeline import get_processed_data
from src.ui_helpers import inject_css, render_sidebar, render_header, format_currency

st.set_page_config(page_title="Dashboard Utama", layout="wide")
inject_css()
render_sidebar()
render_header()

st.title("📊 Dashboard Utama Kewajaran Anggaran")

# Load data
df = get_processed_data()

if df.empty:
    st.warning("Data tidak tersedia.")
    st.stop()

# Filters
col1, col2 = st.columns(2)
with col1:
    selected_year = st.selectbox("Pilih Tahun", sorted(df["tahun"].dropna().unique()), index=0)
with col2:
    selected_pemda = st.selectbox("Pilih Pemda", ["Semua"] + sorted(df["pemda_label"].dropna().unique()))

# Filter Data
filtered_df = df[df["tahun"] == selected_year]
if selected_pemda != "Semua":
    filtered_df = filtered_df[filtered_df["pemda_label"] == selected_pemda]

# KPI Cards
total_pagu = filtered_df["pagu"].sum()
avg_ikp = filtered_df["ikp_score"].mean()

valid_ikp = filtered_df.dropna(subset=["ikp_score"])
wajar_count = len(valid_ikp[valid_ikp["ikp_category"] == "Wajar"])
total_count = len(valid_ikp)
pct_wajar = (wajar_count / total_count * 100) if total_count > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Total Pagu", format_currency(total_pagu))
c2.metric("Rata-rata IKP", f"{avg_ikp:.1f}" if pd.notna(avg_ikp) else "-")
c3.metric("Persentase Kategori Wajar", f"{pct_wajar:.1f}%")

st.divider()

# ==========================================
# SUMMARY TABLE SECTION (MOVED UP)
# ==========================================
st.subheader("Ringkasan per Pemerintah Daerah")

# Aggregate IKP and Dimensions per Pemda WITH coverage info
import numpy as np

def agg_with_coverage(group):
    total = len(group)
    result = {}
    for i in range(1, 6):
        col = f"dimensi_{i}_score"
        valid = group[col].notna().sum()
        result[f"d{i}"] = group[col].mean() if valid > 0 else np.nan
        result[f"d{i}_cov"] = valid / total * 100 if total > 0 else 0
    result["ikp"] = group["ikp_score"].mean()
    result["total_sub"] = total
    return pd.Series(result)

summary_df = filtered_df.groupby(["kodepemda", "pemda_label"], dropna=False).apply(agg_with_coverage).reset_index()

# Pisahkan Kab/Kota dan Provinsi — konteks utama adalah perbandingan antar Kab/Kota
summary_df["is_provinsi"] = summary_df["pemda_label"].str.contains("Prov.", case=False, na=False)
summary_df = summary_df.sort_values(by=["is_provinsi", "kodepemda"], ascending=[True, True]).reset_index(drop=True)

def format_nama(row):
    pemda = row["pemda_label"]
    if pd.isna(pemda):
        return "-"
    pemda_enc = urllib.parse.quote(pemda)
    is_prov = row.get("is_provinsi", False)
    if is_prov:
        badge = '<span style="display:inline-block;background:#fef2f2;color:#991b1b;font-size:0.65em;padding:2px 8px;border-radius:4px;font-weight:700;margin-left:8px;vertical-align:middle;border:1px solid #fecaca;">PROVINSI</span>'
        return f'<a href="/Analisis_Anggaran?pemda={pemda_enc}" target="_self" style="color: #64748b; text-decoration: none; font-weight: 700;">{pemda}</a>{badge}'
    return f'<a href="/Analisis_Anggaran?pemda={pemda_enc}" target="_self" style="color: #1e3a8a; text-decoration: none; font-weight: 700;">{pemda}</a>'

def get_ikp_color(val):
    if pd.isna(val): return ""
    if val >= 80: return "background-color: #4ade80; color: #064e3b; font-weight: bold; text-align: center;"
    if val >= 65: return "background-color: #facc15; color: #713f12; font-weight: bold; text-align: center;"
    if val >= 50: return "background-color: #f97316; color: #fff; font-weight: bold; text-align: center;"
    return "background-color: #ef4444; color: #fff; font-weight: bold; text-align: center;"

def format_dim_with_coverage(mean_val, coverage_pct):
    """Format dimensi score: tampilkan skor + coverage, atau '-' jika tidak ada data."""
    if pd.isna(mean_val):
        return "-"
    cov = int(round(coverage_pct))
    if cov < 100:
        return f"{mean_val:.1f} <span style='font-size:0.7em;color:#94a3b8;'>({cov}%)</span>"
    return f"{mean_val:.1f}"

# Build HTML table manually to allow per-row styling for Provinsi
is_prov_list = summary_df["is_provinsi"].tolist()

# Build header
header_cols = ["No.", "Kode", "Nama Pemda", "D-1", "D-2", "D-3", "D-4", "D-5", "IKP"]
header_html = "".join([f"<th style='padding:12px 16px;text-align:center;'>{c}</th>" for c in header_cols])

# Build rows
rows_html = ""
for i, (_, srow) in enumerate(summary_df.iterrows()):
    is_prov = srow["is_provinsi"]
    
    # Row style: Provinsi gets distinct background
    if is_prov:
        row_style = "background-color:#fef2f2; border-top:2px solid #fecaca;"
    else:
        row_style = ""
    
    # Format cells
    no = i + 1
    kode = srow["kodepemda"]
    nama = format_nama(srow)
    dims = []
    for d in range(1, 6):
        dims.append(format_dim_with_coverage(srow[f"d{d}"], srow[f"d{d}_cov"]))
    
    ikp_val = srow["ikp"]
    if pd.notna(ikp_val):
        ikp_text = f"{ikp_val:.1f}%"
        if ikp_val >= 80:
            ikp_style = "background-color:#4ade80;color:#064e3b;font-weight:bold;"
        elif ikp_val >= 65:
            ikp_style = "background-color:#facc15;color:#713f12;font-weight:bold;"
        elif ikp_val >= 50:
            ikp_style = "background-color:#f97316;color:#fff;font-weight:bold;"
        else:
            ikp_style = "background-color:#ef4444;color:#fff;font-weight:bold;"
    else:
        ikp_text = "-"
        ikp_style = ""
    
    td_center = "padding:12px 16px;text-align:center;border-bottom:1px solid #e2e8f0;"
    td_left = "padding:12px 16px;border-bottom:1px solid #e2e8f0;"
    
    row_html = f"<tr style='{row_style}'>"
    row_html += f"<td style='{td_center}'>{no}</td>"
    row_html += f"<td style='{td_center}'>{kode}</td>"
    row_html += f"<td style='{td_left}'>{nama}</td>"
    for dim_val in dims:
        row_html += f"<td style='{td_center}'>{dim_val}</td>"
    row_html += f"<td style='{td_center}{ikp_style}'>{ikp_text}</td>"
    row_html += "</tr>"
    
    # Add separator before Provinsi section
    if is_prov and (i == 0 or not is_prov_list[i - 1]):
        sep_html = f"<tr><td colspan='{len(header_cols)}' style='padding:6px 16px;background:#f8fafc;font-size:0.75rem;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;border-top:2px solid #e2e8f0;'>Data Provinsi (bukan bagian perbandingan antar Kab/Kota)</td></tr>"
        rows_html += sep_html
    
    rows_html += row_html

full_table_html = (
    f"<table style='width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;"
    f"box-shadow:0 4px 6px -1px rgba(15,23,42,0.05);font-family:sans-serif;border:1px solid #e2e8f0;margin-bottom:2rem;'>"
    f"<thead style='background-color:#f1f5f9;'><tr>{header_html}</tr></thead>"
    f"<tbody>{rows_html}</tbody></table>"
)

# Inject custom table CSS
table_css = """
<style>
.custom-summary-table th {
    color: #475569;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 0.85rem;
    border-bottom: 2px solid #cbd5e1;
}
.custom-summary-table td {
    color: #334155;
    font-size: 0.95rem;
}
.custom-summary-table tr:hover td {
    background-color: #f8fafc;
}
</style>
"""

st.markdown(f"{table_css}<div class='custom-summary-table'>{full_table_html}</div>", unsafe_allow_html=True)
st.caption("ℹ️ Angka dalam tanda kurung (%) menunjukkan **cakupan data** — persentase sub-kegiatan yang memiliki data valid untuk dimensi tersebut. Contoh: *74.3 (23%)* berarti rata-rata skor 74.3 dihitung dari hanya 23% sub-kegiatan yang memiliki data historis.")

st.divider()

# ==========================================
# TOP ANOMALI SECTION
# ==========================================
st.subheader("🚩 Top 5 Sub-Kegiatan Perlu Perhatian")
top_anomali = filtered_df.sort_values(by="ikp_score", ascending=True).head(5)

if not top_anomali.empty:
    cols_top = st.columns(5)
    for i, (idx, row) in enumerate(top_anomali.iterrows()):
        with cols_top[i]:
            params = {"tahun": row["tahun"], "pemda": row["pemda_label"], "sub": row["kodesubkegiatan"]}
            url = f"/Detail_Dimensi?{urllib.parse.urlencode(params)}"
            
            st.markdown(f"""
            <div style="background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #ef4444; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); height: 180px; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden;">
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; font-weight: 800; text-transform: uppercase; margin-bottom: 8px;">{row['pemda_label']}</div>
                    <div style="font-size: 0.9rem; font-weight: 700; color: #0f172a; margin: 0; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.3;">{row['uraisubkegiatan']}</div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; border-top: 1px solid #f1f5f9; padding-top: 10px;">
                    <span style="background: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 800;">IKP: {row['ikp_score']:.1f}</span>
                    <a href="{url}" target="_self" style="font-size: 0.8rem; color: #3b82f6; text-decoration: none; font-weight: 700;">Detail →</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Tidak ada data anomali yang ditemukan.")

st.divider()

# ==========================================
# MAP AND CHART SECTION (MOVED DOWN)
# ==========================================
col_map, col_chart = st.columns([2, 1])

with col_map:
    st.subheader("Peta Persebaran IKP")
    
    # Aggregate IKP by pemda
    agg_df = filtered_df.groupby("pemda_label", as_index=False)["ikp_score"].mean()
    
    geojson_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "diy_kab_kota.geojson")
    try:
        with open(geojson_path) as f:
            geojson_data = json.load(f)
            
        fig = px.choropleth_mapbox(
            agg_df,
            geojson=geojson_data,
            locations="pemda_label",
            featureidkey="properties.NAME_2", # Match the GeoJSON feature key
            color="ikp_score",
            color_continuous_scale="Viridis",
            mapbox_style="carto-positron",
            zoom=8,
            center={"lat": -7.9, "lon": 110.4},
            opacity=0.5,
            labels={'ikp_score': 'Rata-rata IKP'}
        )
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        # Fallback if map fails
        st.warning("Peta tidak dapat dirender. Memuat tabel rata-rata wilayah sebagai gantinya.")
        st.dataframe(agg_df.rename(columns={"pemda_label": "Pemda", "ikp_score": "Rata-rata IKP"}).style.format({"Rata-rata IKP": "{:.1f}"}), use_container_width=True)

with col_chart:
    st.subheader("Distribusi Kategori")
    cat_counts = filtered_df["ikp_category"].value_counts().reset_index()
    cat_counts.columns = ["Kategori", "Jumlah"]
    
    fig2 = px.pie(cat_counts, values="Jumlah", names="Kategori", hole=0.4, 
                  color="Kategori", 
                  color_discrete_map={
                      "Wajar": "#166534", 
                      "Cukup Wajar": "#ca8a04", 
                      "Tidak Wajar": "#991b1b",
                      "Tidak Dapat Dinilai": "#64748b"
                  })
    fig2.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3)
    )
    st.plotly_chart(fig2, use_container_width=True)
