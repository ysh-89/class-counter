import streamlit as st
from streamlit_js_eval import get_geolocation, set_cookie, get_cookie
from geopy.distance import geodesic
import uuid

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 100  # 자동 감지 반경 (100m)

# ==========================================
# 🔒 관리자 기기 ID 등록
# 주소창에 ?admin_check=true 입력 후 확인한 내 ID를 아래에 넣으세요.
# ==========================================
ADMIN_USER_ID = "36e0f652-5d3d-4125-a64d-7c8b9f30470a"

# ==========================================
# 1. 서버 전체 공유 저장소 (실시간 데이터)
# ==========================================
@st.cache_resource
def get_global_store():
    return {"base_location": None, "active_users": set()}

global_store = get_global_store()

# ==========================================
# 2. 브라우저 쿠키 기반 사용자 고유 ID 고정 (중복 방지)
# ==========================================
user_id = get_cookie("classroom_user_id")

if not user_id:
    user_id = str(uuid.uuid4())
    set_cookie("classroom_user_id", user_id, 365)

# ==========================================
# 3. 관리자 ID 확인용 디버그 도구 (?admin_check=true 접속 시 실행)
# ==========================================
if st.query_params.get("admin_check") == "true":
    st.error(f"🆔 내 기기 고유 ID: `{user_id}`")
    st.info("위 ID를 복사하여 코드의 ADMIN_USER_ID에 붙여넣으세요!")

# ==========================================
# 4. 메인 화면 UI (일반 사용자 공통)
# ==========================================
st.title("🏫 위치 기반 자동 인원 카운터")
st.write("위치 권한을 승인하면 반경 100m 진입 시 **자동 입실**, 범위를 벗어나면 **자동 퇴실** 처리됩니다.")

st.divider()

# 현재 반경 내 자동 감지된 실시간 인원수 표시
current_count = len(global_store["active_users"])
st.metric(label="📊 현재 교실(100m 반경) 내 인원수", value=f"{current_count} 명")

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
    
    # 1) 기준점(교실 위치) 설정 여부 확인
    if global_store["base_location"] is None:
        st.warning("📍 교실 기준 위치가 아직 설정되지 않았습니다.")
        st.info("💡 관리자가 교실 위치를 설정할 때까지 잠시만 기다려 주세요.")
    else:
        # 2) 기준점과 현재 접속자의 거리 계산
        base_lat, base_lon = global_store["base_location"]
        distance = geodesic((user_lat, user_lon), (base_lat, base_lon)).meters

        st.write(f"📍 현재 교실과의 거리: **약 {int(distance)}m**")

        # 3) 반경 100m 안팎 판정 및 자동 집계 (중복 방지)
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
    # 6. 관리자 전용 메뉴 (오직 등록된 ADMIN_USER_ID에만 노출)
    # ==========================================
    if user_id == ADMIN_USER_ID:
        st.divider()
        with st.expander("👑 관리자 전용 설정", expanded=True):
            st.success("🔓 관리자 권한이 확인되었습니다.")
            
            if st.button("📌 현재 내 위치를 교실 기준점으로 설정하기", use_container_width=True):
                global_store["base_location"] = (user_lat, user_lon)
                st.success("교실 위치가 새로 설정되었습니다!")
                st.rerun()
                
            if st.button("🔄 전체 인원수 및 기준점 초기화", use_container_width=True):
                global_store["base_location"] = None
                global_store["active_users"] = set()
                st.warning("초기화되었습니다.")
                st.rerun()
