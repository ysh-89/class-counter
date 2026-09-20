import streamlit as st

# 페이지 기본 설정
st.set_page_config(page_title="우리반 교실 인원 카운터", page_icon="🏫", layout="centered")

# ==========================================
# 1. 서버 전체 공유 데이터 (실시간 인원 수 공유)
# ==========================================
@st.cache_resource
def get_global_counter():
    # 모든 접속자가 공유하는 중앙 카운터
    return {"current_count": 0}

global_data = get_global_counter()

# 개인 접속 상태 관리 (중복 클릭 방지)
if "user_status" not in st.session_state:
    st.session_state.user_status = "OUT"  # 기본 상태: 퇴실(OUT)

# ==========================================
# 2. 메인 화면 UI
# ==========================================
st.title("🏫 우리반 현재 인원 카운터")
st.write("교실에 들어오거나 나갈 때 아래 버튼을 눌러 인원을 체크해 주세요.")

st.divider()

# 현재 교실 내 실시간 인원수 표시
st.metric(label="📊 현재 교실 내 인원수", value=f"{global_data['current_count']} 명")

st.divider()

# ==========================================
# 3. 입실 / 퇴실 인원 확인 버튼
# ==========================================
col1, col2 = st.columns(2)

with col1:
    # 입실 버튼
    if st.button("🙋‍♂️ 교실 입실 (+1)", use_container_width=True, type="primary"):
        if st.session_state.user_status != "IN":
            global_data["current_count"] += 1
            st.session_state.user_status = "IN"
            st.rerun()
        else:
            st.warning("이미 입실 처리되었습니다.")

with col2:
    # 퇴실 버튼
    if st.button("🏃‍♂️ 교실 퇴실 (-1)", use_container_width=True):
        if st.session_state.user_status == "IN":
            if global_data["current_count"] > 0:
                global_data["current_count"] -= 1
            st.session_state.user_status = "OUT"
            st.rerun()
        else:
            st.info("현재 퇴실 상태입니다.")

# 내 상태 안내
st.divider()
if st.session_state.user_status == "IN":
    st.success("✅ 현재 **'교실 입실 상태'**입니다.")
else:
    st.info("ℹ️ 현재 **'교실 외 상태'**입니다.")

# ==========================================
# 4. 관리자용 초기화 기능
# ==========================================
with st.expander("⚙️ 관리자 기능"):
    if st.button("🔄 전체 인원수 0명으로 초기화"):
        global_data["current_count"] = 0
        st.session_state.user_status = "OUT"
        st.rerun()
