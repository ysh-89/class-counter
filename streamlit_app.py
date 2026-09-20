import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import uuid

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 100  # 자동 감지 반경 (100m)

# ==========================================
# 1. 서버 전체 공유 저장소 (실시간 자동 합산)
# ==========================================
@st.cache_resource
def get_global_store():
    # active_users: 현재 반경 100m 안에 있는 사용자 유저 ID 세트
    return {"base_location": None, "active_users": set()}

global_store = get_global_store()

# ==========================================
# 2. 개별 사용자 식별 고유 ID 생성 (쿠키/세션 역할)
# ==========================================
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

user_id = st.session_state.user_id

# ==========================================
# 3. 메인 화면 UI
# ==========================================
st.title("🏫 위치 기반 자동 인원 카운터")
st.write("위치 권한을 승인하면 반경 100m 진입 시 **자동 입실**, 범위를 벗어나면 **자동 퇴실** 처리됩니다.")

st.divider()

# 현재 반경 내에 존재하는 사용자 수 실시간 합산 표시
current_count = len(global_store["active_users"])
st.metric(label="📊 현재 범위(100m) 내 자동 감지된 인원수", value=f"{current_count} 명")

st.divider()

# ==========================================
# 4. 위치 수집 및 자동 카운팅(진입/이탈) 로직
# ==========================================
location = get_geolocation()

if location is None:
    st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
else:
    user_lat = location['coords']['latitude']
    user_lon = location['coords']['longitude']
    
    # 1) 기준점(교실 좌표)이 설정되지 않은 경우
    if global_store["base_location"] is None:
        st.warning("📍 기준점(교실 위치)이 설정되지 않았습니다.")
        if st.button("📌 현재 내 위치를 기준점(교실)으로 설정하기", use_container_width=True):
            global_store["base_location"] = (user_lat, user_lon)
            st.rerun()
    else:
        # 2) 기준점과 현재 사용자의 거리 계산 (미터 단위)
        base_lat, base_lon = global_store["base_location"]
        distance = geodesic((user_lat, user_lon), (base_lat, base_lon)).meters

        st.write(f"📍 기준점과의 현재 거리: **약 {int(distance)}m**")

        # 3) 반경 100m 안팎 판정 및 자동 추가/제외
        if distance <= ALLOWED_RADIUS_METERS:
            # 반경 안으로 진입한 경우 (자동 카운트 +1)
            if user_id not in global_store["active_users"]:
                global_store["active_users"].add(user_id)
                st.rerun()
            
            st.success(f"✅ 반경 {ALLOWED_RADIUS_METERS}m 이내에 있어 **[자동 입실]** 상태입니다.")
        else:
            # 반경 100m 밖으로 나간 경우 (자동 카운트 -1)
            if user_id in global_store["active_users"]:
                global_store["active_users"].remove(user_id)
                st.rerun()
                
            st.error(f"❌ 반경 {ALLOWED_RADIUS_METERS}m 밖에 있어 **[자동 퇴실]** 처리되었습니다.")

        # 관리자용 초기화 기능
        st.divider()
        with st.expander("⚙️ 관리자 설정"):
            if st.button("🔄 기준점 및 인원수 전체 리셋"):
                global_store["base_location"] = None
                global_store["active_users"] = set()
                st.rerun()
