import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
from streamlit_local_storage import LocalStorage
import uuid

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 100  # 자동 감지 반경 (100m)

# ==========================================
# 🔒 관리자 기기 ID 등록
# ==========================================
ADMIN_USER_ID = "여기에_관리자_기기_ID를_입력하세요"

# ==========================================
# 1. 서버 전체 공유 저장소 (실시간 데이터)
# ==========================================
@st.cache_resource
def get_global_store():
    return {"base_location": None, "active_users": set()}

global_store = get_global_store()

# ==========================================
# 2. 브라우저 쿠키(Local Storage)를 이용한 고유 ID 유효성 보장
# ==========================================
localStorage = LocalStorage()

# 브라우저 저장소에서 기존 ID 불러오기
saved_user_id = localStorage.getItem("classroom_user_id")

if saved_user_id is None:
    # 저장된 ID가 없으면 새로 생성 후 브라우저에 저장
    new_id = str(uuid.uuid4())
    localStorage.setItem("classroom_user_id", new_id)
    user_id = new_id
else:
    user_id = saved_user_id

# ==========================================
# 3. 메인 화면 UI
# ==========================================
st.title("🏫 위치 기반 자동 인원 카운터")
st.write("위치 권한을 승인하면 반경 100m 진입 시 **자동 입실**, 범위를 벗어나면 **자동 퇴실** 처리됩니다.")

st.divider()

# 현재 반경 내 자동 감지된 실시간 인원수 표시
current_count = len(global_store["active_users"])
st.metric(label="📊 현재 교실(100m 반경) 내 인원수", value=f"{current_count} 명")

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
    
    # 1) 기준점(교실 위치) 설정 여부 확인
    if global_store["base_location"] is None:
        st.warning("📍 교실 기준 위치가 아직 설정되지 않았습니다.")
        st.info("💡 관리자가 교실 위치를 설정할 때까지 잠시만 기다려 주세요.")
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
    # 5. 관리자 전용 메뉴 (오직 관리자 기기에만 노출)
    # ==========================================
    if user_id == ADMIN_USER_ID:
        st.divider()
        with st.expander("👑 관리자 전용 설정", expanded=True):
            st.success("🔓 관리자 기기로 접속되었습니다.")
            
            if st.button("📌 현재 내 위치를 교실 기준점으로 설정하기", use_container_width=True):
                global_store["base_location"] = (user_lat, user_lon)
                st.success("교실 위치가 새로 설정되었습니다!")
                st.rerun()
                
            if st.button("🔄 전체 인원수 및 기준점 초기화", use_container_width=True):
                global_store["base_location"] = None
                global_store["active_users"] = set()
                st.warning("초기화되었습니다.")
                st.rerun()
