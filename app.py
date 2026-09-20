import streamlit as st
import requests

# 페이지 기본 설정
st.set_page_config(page_title="교실 인원 카운터", page_icon="🏫", layout="centered")

# ==========================================
# 1. 카카오 API 설정 (오직 Secrets에서만 가져옴)
# ==========================================
KAKAO_REST_API_KEY = st.secrets.get("KAKAO_REST_API_KEY", "")
REDIRECT_URI = st.secrets.get("REDIRECT_URI", "")

# ==========================================
# 2. 세션 상태 (초기화 없이 누적 관리)
# ==========================================
if "total_count" not in st.session_state:
    st.session_state.total_count = 0

if "checked_users" not in st.session_state:
    st.session_state.checked_users = set()  # 중복 카운트 방지용 ID 저장소

# ==========================================
# 3. 카카오 로그인 처리 (사용자 ID만 확인)
# ==========================================
def get_kakao_user_id(code):
    """카카오 인가 코드로 사용자 고유 ID만 추출"""
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": code
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
    
    try:
        token_res = requests.post(token_url, data=data, headers=headers)
        access_token = token_res.json().get("access_token")
        
        if not access_token:
            return None

        user_url = "https://kapi.kakao.com/v2/user/me"
        user_headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(user_url, headers=user_headers)
        
        return str(user_res.json().get("id"))
    except:
        return None

# ==========================================
# 4. URL 쿼리 파라미터 확인 및 인원 카운트
# ==========================================
query_params = st.query_params
if "code" in query_params:
    auth_code = query_params["code"]
    user_id = get_kakao_user_id(auth_code)
    
    if user_id:
        # 이전에 버튼을 누른 적 없는 사용자인 경우에만 +1
        if user_id not in st.session_state.checked_users:
            st.session_state.checked_users.add(user_id)
            st.session_state.total_count += 1
            st.success("인증이 완료되었습니다. 교실 인원에 추가되었습니다.")
        else:
            st.warning("이미 인원 체크를 완료하셨습니다.")
            
        # URL에서 인증 코드 제거
        st.query_params.clear()

# ==========================================
# 5. 메인 화면 UI
# ==========================================
st.title("🏫 우리반 현재 인원 카운터")

st.divider()

# 누적 인원수만 표시
st.metric(label="📊 현재 교실 내 인원수", value=f"{st.session_state.total_count} 명")

st.divider()

# 카카오 인증 버튼
if KAKAO_REST_API_KEY and REDIRECT_URI:
    kakao_auth_url = f"https://kauth.kakao.com/oauth/authorize?response_type=code&client_id={KAKAO_REST_API_KEY}&redirect_uri={REDIRECT_URI}"
    st.link_button("🟡 카카오 인증하고 인원 체크하기", kakao_auth_url, use_container_width=True)
else:
    st.error("Streamlit Secrets에 KAKAO_REST_API_KEY 및 REDIRECT_URI를 설정해 주세요.")
