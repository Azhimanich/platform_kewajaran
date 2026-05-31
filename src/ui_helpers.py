"""
UI Helpers – Fungsi pendukung antarmuka Streamlit.
"""
import os
import streamlit as st

import os
import streamlit as st
import base64

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def inject_css():
    """Memuat CSS ke dalam Streamlit."""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            
    # Add a custom subtle background gradient and font adjustments globally
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }
        /* Make sidebar Navy */
        [data-testid="stSidebar"] {
            background-color: #0f172a !important;
            background-image: linear-gradient(180deg, #0f172a 0%, #1e3a8a 100%) !important;
            border-right: none !important;
        }
        /* Sidebar texts & links */
        [data-testid="stSidebar"] * {
            color: rgba(255, 255, 255, 0.95) !important;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
            border-radius: 8px;
            margin-bottom: 4px;
            padding: 10px 15px;
            transition: all 0.2s;
        }
        [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: #ffffff !important;
            transform: translateX(4px);
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(255, 255, 255, 0.2) !important;
        }
        .stButton button {
            border-radius: 6px;
            font-weight: 500;
        }
        .stMetric {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
        }
        </style>
    """, unsafe_allow_html=True)

def render_header():
    """Menampilkan header formal ala Kementerian."""
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png")
    
    if os.path.exists(logo_path):
        img_b64 = get_base64_of_bin_file(logo_path)
        img_tag = f'<img src="data:image/png;base64,{img_b64}" style="width: 55px; height: 55px; object-fit: contain; margin-right: 15px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">'
    else:
        img_tag = '<div style="background-color: #1e3a8a; color: white; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 24px; font-weight: bold; margin-right: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">🇮🇩</div>'
        
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; padding: 1rem 1.5rem; margin-bottom: 2rem; background: linear-gradient(90deg, #ffffff 0%, #f8fafc 100%); border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            {img_tag}
            <div>
                <h2 style="margin: 0 !important; color: #0f172a !important; font-size: 1.4rem !important; font-weight: 700; letter-spacing: -0.01em;">PLATFORM KEWAJARAN PENGANGGARAN</h2>
                <p style="margin: 0 !important; color: #3b82f6 !important; font-size: 0.9rem !important; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Pusat Data dan Informasi • Kementerian Dalam Negeri</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_sidebar():
    """Menampilkan navigasi sidebar."""
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logo.png")
    if os.path.exists(logo_path):
        st.logo(logo_path, icon_image=logo_path)
        
    with st.sidebar:
        st.markdown("<h3 style='color: white; margin-bottom: 1rem;'>Pilihan Menu</h3>", unsafe_allow_html=True)
        
        # Navigation
        st.page_link("app.py", label="Home", icon=":material/home:")
        st.page_link("pages/1_Dashboard.py", label="Dashboard Utama", icon=":material/dashboard:")
        st.page_link("pages/2_Analisis_Anggaran.py", label="Analisis Anggaran", icon=":material/analytics:")
        st.page_link("pages/4_Detail_Dimensi.py", label="Detail Per Dimensi", icon=":material/find_in_page:")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.divider()
        st.markdown("""
        <div style="text-align:center; font-size: 0.8rem; color: #cbd5e1;">
            <b>Pusdatin Kemendagri</b><br>
            <i>Objektif, Transparan, Akuntabel</i><br>
            v1.2.0
        </div>
        """, unsafe_allow_html=True)

def format_currency(value):
    """Format angka menjadi Rupiah (Miliar/Juta) dengan gaya Indonesia."""
    if pd.isna(value) or value == 0:
        return "Rp 0"
    
    formatted = ""
    if value >= 1e9:
        num = f"{value/1e9:,.2f}"
        formatted = f"Rp {num} M"
    elif value >= 1e6:
        num = f"{value/1e6:,.2f}"
        formatted = f"Rp {num} Jt"
    else:
        num = f"{value:,.0f}"
        formatted = f"Rp {num}"
        
    # Convert to ID locale: dot for thousands, comma for decimal
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

def format_number(value, decimals=2):
    """Format angka umum dengan gaya Indonesia (titik ribuan, koma desimal)."""
    if pd.isna(value):
        return "-"
    
    pattern = "{:,.%df}" % decimals
    formatted = pattern.format(value)
    
    # Convert to ID locale
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")

def format_score(value):
    """Format skor IKP menjadi string."""
    if pd.isna(value):
        return "-"
    return format_number(value, 1)

def render_badge(category):
    """Menampilkan badge HTML berdasarkan kategori."""
    cat_lower = str(category).lower()
    if "tidak" in cat_lower:
        badge_class = "badge-tidak"
    elif "cukup" in cat_lower:
        badge_class = "badge-cukup"
    elif "wajar" in cat_lower:
        badge_class = "badge-wajar"
    else:
        badge_class = "badge-neutral"
        
    return f'<span class="badge {badge_class}">{category}</span>'

import pandas as pd
