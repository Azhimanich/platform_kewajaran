"""
Pipeline utama - Mengeksekusi seluruh dimensi dan IKP.
Trigger cache invalidate
"""
import streamlit as st
import pandas as pd

from src.data_loader import load_raw
from src.dimensions import dimensi_1_kewajaran
from src.dimensions import dimensi_2_kinerja
from src.dimensions import dimensi_3_kinerja
from src.dimensions import dimensi_4_perencanaan
from src.dimensions import dimensi_5_kualitas_data
from src.ikp_calculator import calculate_ikp

@st.cache_data(show_spinner="[Setup] Mengkalkulasi 5 Dimensi Kewajaran & IKP...")
def get_processed_data() -> pd.DataFrame:
    """
    Menjalankan seluruh pipeline data dari raw CSV hingga kalkulasi skor akhir.
    """
    # Cache invalidation trigger: v28 (Dimensi 3 - 2x2 Matrix BSK-based)
    df = load_raw()
    
    if df.empty:
        return df
        
    df = dimensi_1_kewajaran.calculate(df)
    df = dimensi_2_kinerja.calculate(df)
    df = dimensi_3_kinerja.calculate(df)
    df = dimensi_4_perencanaan.calculate(df)
    df = dimensi_5_kualitas_data.calculate(df)
    
    df = calculate_ikp(df)
    
    return df
