import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import uuid

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 100  # 자동 감지 반경 (100m)

# ==========================================
# 1. 서버 전체 공유 저장소 (실시간 데이터 & 동적 비밀번호)
# ==========================================
@st.cache_resource
def get_global_store():
    # Secrets에 설정된 비밀번호가 있으면 사용하고, 없으면 기본값 '1234'
    default_pw = st.secrets.get("ADMIN_PASSWORD", "1234")
    return {
        "base_location": None, 
        "active_users": set(),
        "admin_password": default_pw
    }

global_store = get_global_store()

# ==========================================
# 2. URL 쿼리 파라미터 기반 사용자 ID 고정 (중복 증가 방지)
# ==========================================
if "uid" in st.query_params:
    user_id = st.query_params["uid"]
else:
    user_id = str(uuid.uuid4())[:8]
    st.query_params["uid"] = user_id

# 관리자 인증 상태 세션
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ==========================================
# 3. 메인 화면 UI (일반 사용자 화면)
# ==========================================
st.title("🏫 위치 기반 자동 인원 카운터")
st.write("위치 권한을 승인하면 반경 100m 진입 시 **자동 입실**, 범위를 벗어나면 **자동 퇴실** 처리됩니다.")

st.divider()

# 현재 반경 내 자동 감지된 실시간 인원수 표시
current_count = len(global_store["active_users"])
st.metric(label="📊 현재 교실(100m 반경) 내 실시간 인원수", value=f"{current_count} 명")

st.divider()

# ==========================================
# 4. 위치 수집 및 자동 카운팅 로직
# ==========================================
location = get_geolocation()

if location is None:
    st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
else:
    user_lat = location['coords']['latitude']
    user_lon = location['coords']['longitude']
    
    # 관리자가 '기준점 설정' 버튼을 눌렀을 경우 위치 등록 처리
    if st.session_state.get("set_base_requested", False):
        if st.session_state.is_admin:
            global_store["base_location"] = (user_lat, user_lon)
            st.session_state.set_base_requested = False
            st.success("✅ 현재 위치가 교실 기준점으로 저장되었습니다!")
            st.rerun()

    # 1) 기준점(교실 위치) 설정 여부 확인
    if global_store["base_location"] is None:
        st.warning("📍 교실 기준 위치가 아직 설정되지 않았습니다.")
        st.info("💡 하단의 관리자 전용 메뉴에서 비밀번호 입력 후 교실 위치를 지정해 주세요.")
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

        # ==========================================
        # 5. 실시간 인원 확인/새로고침 버튼
        # ==========================================
        st.divider()
        if st.button("🔄 현재 실시간 인원수 새로고침", use_container_width=True, type="primary"):
            st.rerun()
            
        st.info(f"💡 현재 교실 내 실시간 합산 인원: **{len(global_store['active_users'])}명**")

    # ==========================================
    # 6. 관리자 전용 메뉴 (로그인 & 비밀번호 변경 기능 포함)
    # ==========================================
    st.divider()
    with st.expander("⚙️ 관리자 설정 (터치하여 열기)"):
        if not st.session_state.is_admin:
            st.subheader("🔑 관리자 로그인")
            admin_input_pw = st.text_input("비밀번호 입력", type="password", key="main_admin_pw")
            if st.button("로그인", use_container_width=True):
                if admin_input_pw == global_store["admin_password"]:
                    st.session_state.is_admin = True
                    st.success("관리자로 인증되었습니다!")
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")
        else:
            st.success("🔓 관리자 권한 활성화됨")
            
            # 1) 교실 위치 설정
            st.write("📍 **교실 위치 관리**")
            if st.button("📌 현재 내 위치를 교실 기준점으로 설정", use_container_width=True):
                st.session_state.set_base_requested = True
                st.rerun()

            st.divider()
            
            # 2) 비밀번호 변경 기능
            st.write("🔐 **비밀번호 변경**")
            new_pw = st.text_input("새로운 비밀번호 입력", type="password", key="new_pw_input")
            new_pw_confirm = st.text_input("새로운 비밀번호 확인", type="password", key="new_pw_confirm")
            
            if st.button("🔑 비밀번호 변경하기", use_container_width=True):
                if not new_pw:
                    st.warning("새 비밀번호를 입력해 주세요.")
                elif new_pw != new_pw_confirm:
                    st.error("새 비밀번호가 서로 일치하지 않습니다.")
                else:
                    global_store["admin_password"] = new_pw
                    st.success("비밀번호가 성공적으로 변경되었습니다!")

            st.divider()
            
            # 3) 데이터 초기화
            st.write("🔄 **데이터 관리**")
            if st.button("⚠️ 전체 데이터 및 기준점 초기화", use_container_width=True):
                global_store["base_location"] = None
                global_store["active_users"] = set()
                st.warning("전체 데이터가 초기화되었습니다.")
                st.rerun()

            st.divider()
            
            # 4) 로그아웃
            if st.button("🔒 관리자 로그아웃", use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()
