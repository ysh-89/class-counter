import streamlit as st
from streamlit_js_eval import get_geolocation, set_cookie, get_cookie
from geopy.distance import geodesic
import uuid

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 100  # 자동 감지 반경 (100m)

# ==========================================
# 🔒 관리자 전용 비밀번호 설정
# Streamlit Secrets에 ADMIN_PASSWORD를 설정하거나 아래 기본값을 사용합니다.
# ==========================================
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "1234")

# ==========================================
# 1. 서버 전체 공유 저장소 (실시간 데이터)
# ==========================================
@st.cache_resource
def get_global_store():
    return {"base_location": None, "active_users": set()}

global_store = get_global_store()

# ==========================================
# 2. 브라우저 쿠키/저장소 기반 사용자 ID 고정 (새로고침 중복 방지 핵심)
# ==========================================
# 브라우저 쿠키에서 기존 ID를 불러옵니다.
saved_id = get_cookie("classroom_user_id")

if not saved_id:
    # 저장된 ID가 없으면 새 ID를 만들고 브라우저 쿠키에 1년 동안 저장합니다.
    user_id = str(uuid.uuid4())
    set_cookie("classroom_user_id", user_id, 365)
else:
    user_id = saved_id

# 관리자 인증 상태 세션
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ==========================================
# 3. 사이드바 : 관리자 전용 로그인 및 메뉴 탭
# ==========================================
with st.sidebar:
    st.header("⚙️ 관리자 메뉴")
    
    if not st.session_state.is_admin:
        st.subheader("관리자 로그인")
        admin_input_pw = st.text_input("비밀번호 입력", type="password")
        if st.button("로그인", use_container_width=True):
            if admin_input_pw == ADMIN_PASSWORD:
                st.session_state.is_admin = True
                st.success("관리자로 인증되었습니다!")
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    else:
        st.success("🔓 관리자 권한 활성화됨")
        
        # 관리자 기능 1: 교실 위치 설정
        st.divider()
        st.write("📍 **교실 위치 관리**")
        if st.button("📌 현재 내 위치를 교실 기준점으로 설정", use_container_width=True):
            st.session_state.set_base_requested = True

        # 관리자 기능 2: 전체 초기화
        st.divider()
        st.write("🔄 **데이터 관리**")
        if st.button("⚠️ 전체 데이터 및 기준점 초기화", use_container_width=True):
            global_store["base_location"] = None
            global_store["active_users"] = set()
            st.warning("전체 데이터가 초기화되었습니다.")
            st.rerun()

        # 로그아웃
        st.divider()
        if st.button("🔒 관리자 로그아웃", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()

# ==========================================
# 4. 메인 화면 UI (일반 사용자 화면)
# ==========================================
st.title("🏫 위치 기반 자동 인원 카운터")
st.write("위치 권한을 승인하면 반경 100m 진입 시 **자동 입실**, 범위를 벗어나면 **자동 퇴실** 처리됩니다.")

st.divider()

# 현재 반경 내 자동 감지된 실시간 인원수 표시
current_count = len(global_store["active_users"])
st.metric(label="📊 현재 교실(100m 반경) 내 실시간 인원수", value=f"{current_count} 명")

st.divider()

# ==========================================
# 5. 위치 수집 및 자동 카운팅 로직
# ==========================================
location = get_geolocation()

if location is None:
    st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
else:
    user_lat = location['coords']['latitude']
    user_lon = location['coords']['longitude']
    
    # 관리자가 사이드바에서 '기준점 설정' 버튼을 눌렀을 경우 위치 등록 처리
    if st.session_state.get("set_base_requested", False):
        if st.session_state.is_admin:
            global_store["base_location"] = (user_lat, user_lon)
            st.session_state.set_base_requested = False
            st.success("✅ 현재 위치가 교실 기준점으로 저장되었습니다!")
            st.rerun()

    # 1) 기준점(교실 위치) 설정 여부 확인
    if global_store["base_location"] is None:
        st.warning("📍 교실 기준 위치가 아직 설정되지 않았습니다.")
        st.info("💡 관리자가 사이드바 메뉴에서 비밀번호 입력 후 교실 위치를 지정해야 합니다.")
    else:
        # 2) 기준점과 현재 접속자의 거리 계산
        base_lat, base_lon = global_store["base_location"]
        distance = geodesic((user_lat, user_lon), (base_lat, base_lon)).meters

        st.write(f"📍 현재 교실과의 거리: **약 {int(distance)}m**")

        # 3) 반경 100m 안팎 판정 및 자동 집계
        if distance <= ALLOWED_RADIUS_METERS:
            if user_id not in global_store["active_users"]:
                global_store["active_users"].add(user_id)
                st.rerun()
            st.success(f"✅ 교실 반경 {ALLOWED_RADIUS_METERS}m 이내에 있어 **[자동 입실]** 처리되었습니다.")
        else:
            if user_id in global_store["active_users"]:
                global_store["active_users"].remove(user_id)
                st.rerun()
            st.error(f"❌ 교실 반경 {ALLOWED_RADIUS_METERS}m 밖에 있어 **[자동 퇴실]** 처리되었습니다.")
