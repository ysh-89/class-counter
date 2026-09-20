import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="우리 반 인원 확인",
    page_icon="📍",
    layout="centered"
)

# ==========================================
# Kakao JavaScript 키
# Streamlit Secrets에서 가져옴
# ==========================================
KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]

# 교실 위치
CLASS_LAT = 33.000000
CLASS_LON = 126.000000

# 교실로 인정할 범위(m)
RADIUS_M = 100
