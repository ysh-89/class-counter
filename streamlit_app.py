import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import uuid

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 100  # 자동 감지 반경 (100m)

# ==========================================
# 🔒 나만의 관리자 고유 ID (내 기기 ID로 수정 필요)
# 아래 생성된 ID를 확인한 뒤, 이 부분에 똑같이 적어두면 나만 관리자가 됩니다.
# ==========================================
ADMIN_USER_ID = "여기에_내_고유_ID를_복사해서_붙여넣으세요"

# ==========================================
# 1. 서버 전체 공유 저장소
# ==========================================
@st.cache_resource
def get_global_store():
    return {"base_location": None, "active_users": set()}

global_store = get_global_store()

# ==========================================
# 2. 개별 사용자 식별 고유 ID 생성 (기기 고유 식별자)
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

# 현재 반경 내 자동 감지 인원수
current_count = len(global_store["active_users"])
st.metric(label="📊 현재 범위(100m) 내 자동 감지된 인원수", value=f"{current_count} 명")

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
    
    # 1) 기준점이 설정되지 않은 경우
    if global_store["base_location"] is None:
        st.warning("📍 기준점(교실 위치)이 아직 설정되지 않았습니다.")
        st.info("💡 관리자 전용 기기에서 접속하여 교실 기준점을 먼저 설정해 주세요.")
    else:
        # 2) 기준점과 현재 사용자의 거리 계산
        base_lat, base_lon = global_store["base_location"]
        distance = geodesic((user_lat, user_lon), (base_lat, base_lon)).meters

        st.write(f"📍 기준점과의 현재 거리: **약 {int(distance)}m**")

        # 3) 반경 100m 안팎 판정 및 자동 추가/제외
        if distance <= ALLOWED_RADIUS_METERS:
            if user_id not in global_store["active_users"]:
                global_store["active_users"].add(user_id)
                st.rerun()
            st.success(f"✅ 반경 {ALLOWED_RADIUS_METERS}m 이내에 있어 **[자동 입실]** 상태입니다.")
        else:
            if user_id in global_store["active_users"]:
                global_store["active_users"].remove(user_id)
                st.rerun()
            st.error(f"❌ 반경 {ALLOWED_RADIUS_METERS}m 밖에 있어 **[자동 퇴실]** 처리되었습니다.")

    # ==========================================
    # 5. 오직 '나의 기기(ADMIN_USER_ID)'에만 나타나는 관리자 설정
    # ==========================================
    st.divider()
    
    # 내가 관리자로 등록되어 있는지 확인
    if user_id == ADMIN_USER_ID:
        with st.expander("👑 관리자 전용 설정 (나에게만 보임)", expanded=True):
            st.success("🔓 등록된 관리자 기기로 확인되었습니다.")
            
            if st.button("📌 현재 내 위치를 교실 기준점으로 설정/변경하기", use_container_width=True):
                global_store["base_location"] = (user_lat, user_lon)
                st.success("교실 기준점이 새롭게 등록되었습니다!")
                st.rerun()
                
            if st.button("🔄 기준점 및 인원수 전체 리셋", use_container_width=True):
                global_store["base_location"] = None
                global_store["active_users"] = set()
                st.warning("전체 데이터가 초기화되었습니다.")
                st.rerun()
    else:
        # 일반 접속자에게는 내 기기의 고유 ID만 보여주고 버튼은 완전히 숨김
        with st.expander("ℹ️ 내 기기 고유 ID 확인"):
            st.write("현재 접속 기기 ID:")
            st.code(user_id)
            st.caption("위 ID를 코드의 ADMIN_USER_ID에 넣으면 이 기기만 관리자 권한을 가집니다.")
