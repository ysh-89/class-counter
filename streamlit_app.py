import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import uuid
import folium
from streamlit_folium import st_folium

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 50  # 자동 감지 반경 (10m로 수정)

# ==========================================
# 1. 서버 전체 공유 저장소 (실시간 데이터 & 동적 비밀번호)
# ==========================================
@st.cache_resource
def get_global_store():
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
# 3. 사이드바 : 관리자 메뉴 (로그아웃 바로 위에 비밀번호 재설정)
# ==========================================
with st.sidebar:
    st.header("⚙️ 관리자 메뉴")
    
    if not st.session_state.is_admin:
        st.subheader("🔑 관리자 로그인")
        sidebar_pw = st.text_input("비밀번호 입력", type="password", key="sidebar_pw_input")
        if st.button("로그인", key="sidebar_login_btn", use_container_width=True):
            if sidebar_pw == global_store["admin_password"]:
                st.session_state.is_admin = True
                st.success("관리자로 인증되었습니다!")
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    else:
        st.success("🔓 관리자 권한 활성화됨")
        
        # 1) 교실 위치 설정
        st.write("📍 **교실 위치 관리**")
        if st.button("📌 현재 내 위치를 교실 기준점으로 설정", key="sidebar_set_base", use_container_width=True):
            st.session_state.set_base_requested = True
            st.rerun()

        st.divider()

        # 2) 데이터 관리
        st.write("🔄 **데이터 관리**")
        if st.button("⚠️ 전체 데이터 및 기준점 초기화", key="sidebar_reset", use_container_width=True):
            global_store["base_location"] = None
            global_store["active_users"] = set()
            st.warning("전체 데이터가 초기화되었습니다.")
            st.rerun()

        st.divider()

        # 3) 비밀번호 재설정 (로그아웃 버튼 바로 위)
        st.write("🔐 **비밀번호 재설정**")
        side_new_pw = st.text_input("새 비밀번호", type="password", key="side_new_pw")
        side_new_pw_confirm = st.text_input("새 비밀번호 확인", type="password", key="side_new_pw_confirm")
        if st.button("🔑 비밀번호 변경하기", key="side_change_pw_btn", use_container_width=True):
            if not side_new_pw:
                st.warning("새 비밀번호를 입력해 주세요.")
            elif side_new_pw != side_new_pw_confirm:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                global_store["admin_password"] = side_new_pw
                st.success("비밀번호가 변경되었습니다!")

        st.divider()

        # 4) 로그아웃
        if st.button("🔒 관리자 로그아웃", key="sidebar_logout", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()

# ==========================================
# 4. 메인 화면 UI (일반 사용자 화면)
# ==========================================
st.title("🏫 위치 기반 자동 인원 카운터")
st.write(f"위치 권한을 승인하면 반경 {ALLOWED_RADIUS_METERS}m 진입 시 **자동 입실**, 범위를 벗어나면 **자동 퇴실** 처리됩니다.")

# ==========================================
# 5. 위치 수집 및 자동 카운팅 로직 (KeyError 예방 안전 코드)
# ==========================================
location = get_geolocation()

if location is None:
    st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
elif not isinstance(location, dict) or "coords" not in location or location["coords"] is None:
    st.warning("⚠️ 위치 정보를 가져올 수 없습니다. GPS가 켜져 있는지, 브라우저 위치 권한을 허용했는지 확인해 주세요.")
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

    # 🗺️ [지도 표시 부분] 10m 인식 범위 지도 시각화 (10m 관찰을 위해 줌 확대 level 19)
    map_center = global_store["base_location"] if global_store["base_location"] else (user_lat, user_lon)
    
    m = folium.Map(
        location=map_center, 
        zoom_start=19, 
        tiles="OpenStreetMap"
    )

    # 교실 기준점이 설정되어 있다면 지도에 기준점 마커 & 10m 반투명 하얀색 범위 원 추가
    if global_store["base_location"]:
        base_lat, base_lon = global_store["base_location"]
        
        # 교실 마커
        folium.Marker(
            [base_lat, base_lon], 
            popup="🏫 교실 위치", 
            icon=folium.Icon(color="red", icon="home")
        ).add_to(m)

        # 10m 인식 범위 (반투명 하얀색 원)
        folium.Circle(
            location=[base_lat, base_lon],
            radius=ALLOWED_RADIUS_METERS,
            color="#000000",         # 테두리 선: 검은색
            weight=1.5,
            fill=True,
            fill_color="#FFFFFF",    # 원 내부 채우기: 하얀색
            fill_opacity=0.45,       # 투명도 (45% 반투명)
            popup=f"{ALLOWED_RADIUS_METERS}m 자동 인식 범위"
        ).add_to(m)

    # 현재 내 위치 마커 (파란색)
    folium.Marker(
        [user_lat, user_lon], 
        popup="📱 내 위치", 
        icon=folium.Icon(color="blue", icon="user")
    ).add_to(m)

    # Streamlit 화면에 지도 출력
    st_folium(m, width=700, height=350)

    st.divider()

    # 현재 반경 내 자동 감지된 실시간 인원수 표시
    current_count = len(global_store["active_users"])
    st.metric(label=f"📊 현재 교실({ALLOWED_RADIUS_METERS}m 반경) 내 실시간 인원수", value=f"{current_count} 명")

    st.divider()

    # 1) 기준점(교실 위치) 설정 여부 확인 및 판정
    if global_store["base_location"] is None:
        st.warning("📍 교실 기준 위치가 아직 설정되지 않았습니다.")
        st.info("💡 관리자 메뉴에서 비밀번호 입력 후 교실 위치를 지정해 주세요.")
    else:
        # 2) 기준점과 현재 접속자의 거리 계산
        base_lat, base_lon = global_store["base_location"]
        distance = geodesic((user_lat, user_lon), (base_lat, base_lon)).meters

        st.write(f"📍 현재 교실과의 거리: **약 {int(distance)}m**")

        # 3) 반경 10m 안팎 판정 및 자동 집계
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

        # 실시간 인원 확인/새로고침 버튼
        st.divider()
        if st.button("🔄 현재 실시간 인원수 새로고침", use_container_width=True, type="primary"):
            st.rerun()
            
        st.info(f"💡 현재 교실 내 실시간 합산 인원: **{len(global_store['active_users'])}명**")
