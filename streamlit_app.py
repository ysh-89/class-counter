import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# 페이지 기본 설정
st.set_page_config(page_title="교실 인원 카운터 (공유 메모리)", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 100

# ==========================================
# 1. 모든 접속자가 공유하는 중앙 저장소 (서버 메모리)
# ==========================================
@st.cache_resource
def get_global_store():
    # 모든 사용자가 공유하는 변수 공간
    return {"total_count": 0, "base_location": None, "checked_users": set()}

global_store = get_global_store()

# 사용자 개인 세션 상태
if "user_checked" not in st.session_state:
    st.session_state.user_checked = False

# ==========================================
# 2. 메인 화면 UI
# ==========================================
st.title("🏫 우리반 현재 인원 카운터 (실시간 공유)")
st.write("모든 사용자가 공유하는 인원 카운터입니다.")

st.divider()

# 중앙 저장소의 전체 누적 인원수 표시
st.metric(label="📊 현재 기준점 내 실시간 전체 인원수", value=f"{global_store['total_count']} 명")

st.divider()

# ==========================================
# 3. 위치 정보 수집 및 거리 계산
# ==========================================
location = get_geolocation()

if location is None:
    st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
else:
    user_lat = location['coords']['latitude']
    user_lon = location['coords']['longitude']
    
    # 기준점이 없으면 현재 위치로 설정
    if global_store["base_location"] is None:
        st.warning("📍 기준점(교실 위치)이 설정되지 않았습니다.")
        if st.button("📌 현재 내 위치를 전체 기준점으로 설정하기", use_container_width=True):
            global_store["base_location"] = (user_lat, user_lon)
            st.rerun()
    else:
        base_lat, base_lon = global_store["base_location"]
        distance = geodesic((user_lat, user_lon), (base_lat, base_lon)).meters

        st.write(f"📍 기준점과의 거리: **약 {int(distance)}m**")

        if distance <= ALLOWED_RADIUS_METERS:
            st.success(f"✅ 반경 {ALLOWED_RADIUS_METERS}m 이내에 있습니다!")
            
            if not st.session_state.user_checked:
                if st.button("🙋‍♂️ 입실 확인 (+1)", use_container_width=True):
                    global_store["total_count"] += 1
                    st.session_state.user_checked = True
                    st.rerun()
            else:
                st.warning("이미 인원 체크를 완료하셨습니다.")
        else:
            st.error(f"❌ 반경 {ALLOWED_RADIUS_METERS}m 밖에 있습니다.")

        st.divider()
        if st.button("🔄 기준점 및 인원수 전체 리셋 (관리자용)"):
            global_store["base_location"] = None
            global_store["total_count"] = 0
            st.session_state.user_checked = False
            st.rerun()
