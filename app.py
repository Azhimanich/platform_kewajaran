import streamlit as st
from src.ui_helpers import inject_css, render_sidebar, render_header

st.set_page_config(
    page_title="Platform Kewajaran Anggaran – Kemendagri",
    page_icon="🇮🇩",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_css()
render_sidebar()
render_header()

st.title("Selamat Datang di Platform Kewajaran Anggaran")
st.markdown("""
### Prototype Penilaian Kewajaran Anggaran Daerah
Sistem ini menganalisis kewajaran anggaran berdasarkan 5 dimensi, menghasilkan Indeks Kewajaran Penganggaran (IKP) untuk setiap Sub-Kegiatan.

**Fitur Utama:**
*   **Dashboard Utama**: Ringkasan performa IKP Daerah Istimewa Yogyakarta.
*   **Analisis Anggaran**: Tabel eksplorasi skor per Sub-Kegiatan.
*   **Detail Analisis**: Rincian metrik tiap dimensi.

Silakan pilih menu di *sidebar* untuk memulai eksplorasi data.
""")
