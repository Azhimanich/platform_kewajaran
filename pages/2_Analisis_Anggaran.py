import streamlit as st
import pandas as pd
import plotly.express as px
from src.pipeline import get_processed_data
from src.ui_helpers import inject_css, render_sidebar, render_header, format_currency

st.set_page_config(page_title="Analisis Anggaran", layout="wide")
inject_css()
render_sidebar()
render_header()

st.title(" Analisis Anggaran")

df = get_processed_data()

if df.empty:
    st.warning("Data tidak tersedia.")
    st.stop()

# Filters
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    selected_year = st.selectbox("Tahun", sorted(df["tahun"].dropna().unique()), index=0)
with col2:
    pemda_options = ["Semua"] + sorted(df["pemda_label"].dropna().unique())
    
    # Read query param for Pemda redirection
    default_pemda_idx = 0
    if "pemda" in st.query_params:
        qp_pemda = st.query_params["pemda"]
        if qp_pemda in pemda_options:
            default_pemda_idx = pemda_options.index(qp_pemda)
            
    selected_pemda = st.selectbox("Pemda", pemda_options, index=default_pemda_idx)
with col3:
    # SKPD Filter (Dynamic based on Pemda)
    skpd_df = df.copy()
    if selected_pemda != "Semua":
        skpd_df = skpd_df[skpd_df["pemda_label"] == selected_pemda]
    skpd_options = ["Semua"] + sorted(skpd_df["uraiskpd"].dropna().unique().tolist())
    selected_skpd = st.selectbox("SKPD / Dinas", skpd_options)
with col4:
    categories = ["Semua"] + sorted(df["ikp_category"].dropna().unique().tolist())
    selected_kategori = st.selectbox("Kategori IKP", categories)
with col5:
    sort_option = st.selectbox("Urutkan IKP", ["Default", "Terendah", "Tertinggi"])
with col6:
    search_query = st.text_input("Cari Sub-Kegiatan")

# Filter Data
filtered_df = df[df["tahun"] == selected_year]
if selected_pemda != "Semua":
    filtered_df = filtered_df[filtered_df["pemda_label"] == selected_pemda]
if selected_skpd != "Semua":
    filtered_df = filtered_df[filtered_df["uraiskpd"] == selected_skpd]
if selected_kategori != "Semua":
    filtered_df = filtered_df[filtered_df["ikp_category"] == selected_kategori]
if search_query:
    filtered_df = filtered_df[filtered_df["uraisubkegiatan"].str.contains(search_query, case=False, na=False)]

# Sorting
if sort_option == "Terendah":
    filtered_df = filtered_df.sort_values(by="ikp_score", ascending=True)
elif sort_option == "Tertinggi":
    filtered_df = filtered_df.sort_values(by="ikp_score", ascending=False)

st.subheader(f"Hasil Pencarian ({len(filtered_df)} Sub-Kegiatan)")

import urllib.parse

# Display Table
if not filtered_df.empty:
    limit = 100
    display_subset = filtered_df.head(limit).reset_index(drop=True)
    
    if len(filtered_df) > limit:
        st.caption(f"Menampilkan {limit} hasil teratas. Gunakan filter untuk pencarian lebih spesifik.")

    def format_detail_link(row, text_col):
        val = row[text_col]
        params = {"tahun": row["tahun"], "pemda": row["pemda_label"], "sub": row["kodesubkegiatan"]}
        return f'<a href="/Detail_Dimensi?{urllib.parse.urlencode(params)}" target="_top" style="color: #1e3a8a; text-decoration: none; font-weight: 600;">{val}</a>'

    def get_ikp_color(val):
        if pd.isna(val): return ""
        if val >= 80: return "background-color: #4ade80; color: #064e3b; font-weight: bold; text-align: center;" # Green
        if val >= 65: return "background-color: #facc15; color: #713f12; font-weight: bold; text-align: center;" # Yellow
        if val >= 50: return "background-color: #f97316; color: #fff; font-weight: bold; text-align: center;" # Orange
        return "background-color: #ef4444; color: #fff; font-weight: bold; text-align: center;" # Red

    # Prepare data
    display_df = pd.DataFrame()
    display_df["No."] = range(1, len(display_subset) + 1)
    display_df["Kode"] = display_subset.apply(lambda r: format_detail_link(r, "kodesubkegiatan"), axis=1)
    display_df["Sub-Kegiatan"] = display_subset.apply(lambda r: format_detail_link(r, "uraisubkegiatan"), axis=1)
    for i in range(1, 6):
        col = f"dimensi_{i}_score"
        display_df[f"D-{i}"] = display_subset[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "-")
    display_df["IKP"] = display_subset["ikp_score"]

    styled = getattr(display_df.style, "map", getattr(display_df.style, "applymap", None))(get_ikp_color, subset=["IKP"]).format({"IKP": lambda x: f"{x:.1f}" if pd.notna(x) else "-"}).hide(axis="index")

    # CSS kustom untuk tabel profesional
    table_design_css = """
    .analisis-table table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 13px; border: 1px solid #e2e8f0; }
    .analisis-table th { background-color: #f8fafc !important; color: #475569 !important; font-weight: 700 !important; text-transform: uppercase !important; font-size: 10px !important; padding: 12px !important; border-bottom: 2px solid #cbd5e1 !important; text-align: center !important; }
    .analisis-table td { padding: 10px !important; border-bottom: 1px solid #e2e8f0 !important; color: #334155 !important; vertical-align: middle !important; }
    .analisis-table tr:hover { background-color: #f1f5f9 !important; }
    .analisis-table td:nth-child(1) { text-align: center !important; width: 40px; }
    .analisis-table td:nth-child(n+4) { text-align: center !important; width: 60px; }
    .analisis-table td:last-child { width: 80px; text-align: center !important; }
    """

    # Generate HTML and MINIFY (remove newlines) to prevent markdown parsing errors
    table_html_min = styled.to_html(escape=False, index=False).replace("\n", "")
    css_min = table_design_css.replace("\n", "")
    
    full_html = f"<style>{css_min}</style><div class='analisis-table'>{table_html_min}</div>"
    st.markdown(full_html, unsafe_allow_html=True)
else:
    st.info("Tidak ada data yang cocok dengan filter.")
