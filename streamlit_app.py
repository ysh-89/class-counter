import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# 페이지 기본 설정
st.set_page_config(page_title="교실 인원 카운터 (실험용)", page_icon="🏫", layout="centered")

# ==========================================
# 1. 설정 및 세션 상태 초기화
# ==========================================
ALLOWED_RADIUS_METERS = 100  # 반경 100m 이내 설정

if "total_count" not in st.session_state:
    st.session_state.total_count = 0

if "already_checked" not in st.session_state:
    st.session_state.already_checked = False

# 실험용: 현재 위치를 기준점(교실 좌표)으로 저장
if "base_location" not in st.session_state:
    st.session_state.base_location = None

# ==========================================
# 2. 메인 화면 UI
# ==========================================
st.title("🏫 우리반 현재 인원 카운터 (100m 반경 실험)")
st.write("현재 위치를 기준점으로 설정하고 반경 100m 이내의 인원을 집계합니다.")

st.divider()

# 누적 인원수 표시
st.metric(label="📊 현재 기준점 내 인원수", value=f"{st.session_state.total_count} 명")

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
    
    # 1) 기준점이 설정되지 않은 경우 현재 위치를 기준점으로 등록하는 버튼 제공
    if st.session_state.base_location is None:
        st.warning("📍 기준점(교실 위치)이 설정되지 않았습니다.")
        if st.button("📌 현재 내 위치를 기준점(교실)으로 설정하기", use_container_width=True):
            st.session_state.base_location = (user_lat, user_lon)
            st.rerun()
    else:
        # 2) 기준점과 현재 사용자의 거리 계산 (미터 단위)
        base_lat, base_lon = st.session_state.base_location
        distance = geodesic((user_lat, user_lon), (base_lat, base_lon)).meters

        st.write(f"📍 기준점과의 거리: **약 {int(distance)}m**")

        # 3) 반경 100m 판정 및 인원 체크
        if distance <= ALLOWED_RADIUS_METERS:
            st.success(f"✅ 반경 {ALLOWED_RADIUS_METERS}m 이내에 있습니다!")
            
            if not st.session_state.already_checked:
                if st.button("🙋‍♂️ 입실 확인 (+1)", use_container_width=True):
                    st.session_state.total_count += 1
                    st.session_state.already_checked = True
                    st.rerun()
            else:
                st.warning("이미 인원 체크를 완료하셨습니다.")
        else:
            st.error(f"❌ 반경 {ALLOWED_RADIUS_METERS}m 밖에 있습니다. 범위 안으로 이동해 주세요.")

        # 기준점 리셋 버튼 (실험 재진행용)
        st.divider()
        if st.button("🔄 기준점 다시 설정하기"):
            st.session_state.base_location = None
            st.session_state.already_checked = False
            st.rerun()
