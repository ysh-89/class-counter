import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic

# 페이지 기본 설정
st.set_page_config(page_title="교실 인원 카운터", page_icon="🏫", layout="centered")

# ==========================================
# 1. 우리반 교실 위치 설정 (학교/교실 위도, 경도 입력)
# ==========================================
# 예시 좌표 (실제 교실의 위도와 경도로 수정하세요)
CLASSROOM_LAT = 37.5665
CLASSROOM_LON = 126.9780
ALLOWED_RADIUS_METERS = 50  # 반경 50m 이내만 허용

# ==========================================
# 2. 세션 상태 (누적 인원 관리)
# ==========================================
if "total_count" not in st.session_state:
    st.session_state.total_count = 0

if "already_checked" not in st.session_state:
    st.session_state.already_checked = False

# ==========================================
# 3. 메인 화면 UI
# ==========================================
st.title("🏫 우리반 현재 인원 카운터")
st.write("교실 도착 후 브라우저의 **위치 권한을 승인**해 주세요.")

st.divider()

# 누적 인원수 표시
st.metric(label="📊 현재 교실 내 인원수", value=f"{st.session_state.total_count} 명")

st.divider()

# ==========================================
# 4. 위치 권한 요청 및 거리 계산
# ==========================================
# 브라우저에 위치 정보 요청
location = get_geolocation()

if location is None:
    st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
else:
    # 사용자 현재 위도/경도 추출
    user_lat = location['coords']['latitude']
    user_lon = location['coords']['longitude']
    
    # 교실과 사용자 사이의 거리 계산 (미터 단위)
    user_pos = (user_lat, user_lon)
    classroom_pos = (CLASSROOM_LAT, CLASSROOM_LON)
    distance = geodesic(user_pos, classroom_pos).meters

    st.write(f"📍 현재 교실과의 거리: **약 {int(distance)}m**")

    # 교실 반경 내에 있는지 확인
    if distance <= ALLOWED_RADIUS_METERS:
        st.success("✅ 교실 위치가 확인되었습니다!")
        
        if not st.session_state.already_checked:
            if st.button("🙋‍♂️ 교실 입실 확인 (+1)", use_container_width=True):
                st.session_state.total_count += 1
                st.session_state.already_checked = True
                st.rerun()
        else:
            st.warning("이미 인원 체크를 완료하셨습니다.")
    else:
        st.error(f"❌ 교실 범위({ALLOWED_RADIUS_METERS}m) 밖에 있습니다. 교실에 도착한 뒤 다시 시도해 주세요.")
