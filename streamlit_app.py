import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import uuid
import folium
from streamlit_folium import st_folium

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 50  # 감지 반경 50m

# ==========================================
# 1. 서버 전체 공유 저장소 (관리자 이메일 지정)
# ==========================================
@st.cache_resource
def get_global_store():
    # 기본 관리자 이메일을 실제 사용하시는 이메일로 설정했습니다.
    default_email = st.secrets.get("ADMIN_EMAIL", "seokhwanyun892@gmail.com")
    return {
        "base_location": None, 
        "active_users": set(),
        "admin_email": default_email
    }

global_store = get_global_store()

# ==========================================
# 2. URL 쿼리 파라미터 기반 사용자 ID 고정
# ==========================================
if "uid" in st.query_params:
    user_id = st.query_params["uid"]
else:
    user_id = str(uuid.uuid4())[:8]
    st.query_params["uid"] = user_id

# 관리자 로그인 인증 상태 세션
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ==========================================
# 3. 화면 탭 분리 (메인 화면 / 관리자 전용 화면)
# ==========================================
tab_user, tab_admin = st.tabs(["📱 사용자 화면", "🔐 관리자 전용"])

# ------------------------------------------
# [탭 1] 일반 사용자 화면
# ------------------------------------------
with tab_user:
    st.title("🏫 위치 기반 자동 인원 카운터")
    st.write(f"위치 권한을 승인하면 반경 {ALLOWED_RADIUS_METERS}m 진입 시 **자동 입실**, 범위를 벗어나면 **자동 퇴실** 처리됩니다.")

    location = get_geolocation()

    if location is None:
        st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
    elif not isinstance(location, dict) or "coords" not in location or location["coords"] is None:
        st.warning("⚠️ 위치 정보를 가져올 수 없습니다. GPS가 켜져 있는지, 브라우저 위치 권한을 허용했는지 확인해 주세요.")
    else:
        user_lat = location['coords']['latitude']
        user_lon = location['coords']['longitude']

        # 관리자 위치 설정 요청 처리
        if st.session_state.get("set_base_requested", False):
            if st.session_state.is_admin:
                global_store["base_location"] = (user_lat, user_lon)
                st.session_state.set_base_requested = False
                st.success("✅ 현재 위치가 교실 기준점으로 저장되었습니다!")
                st.rerun()

        # 지도 표시
        map_center = global_store["base_location"] if global_store["base_location"] else (user_lat, user_lon)
        m = folium.Map(location=map_center, zoom_start=18, tiles="OpenStreetMap")

        # 교실 위치 마커 및 범위 원
        if global_store["base_location"]:
            base_lat, base_lon = global_store["base_location"]
            folium.Marker([base_lat, base_lon], popup="🏫 교실 위치", icon=folium.Icon(color="red", icon="home")).add_to(m)
            folium.Circle(
                location=[base_lat, base_lon],
                radius=ALLOWED_RADIUS_METERS,
                color="#000000",
                weight=1.5,
                fill=True,
                fill_color="#FFFFFF",
                fill_opacity=0.45,
                popup=f"{ALLOWED_RADIUS_METERS}m 자동 인식 범위"
            ).add_to(m)

        # 사용자 내 위치 마커
        folium.Marker([user_lat, user_lon], popup="📱 내 위치", icon=folium.Icon(color="blue", icon="user")).add_to(m)

        st_folium(m, width=700, height=350)
        st.divider()

        # 실시간 인원 표시 및 출퇴실 판정
        current_count = len(global_store["active_users"])
        st.metric(label=f"📊 현재 교실({ALLOWED_RADIUS_METERS}m 반경) 내 실시간 인원수", value=f"{current_count} 명")

        st.divider()

        if global_store["base_location"] is None:
            st.warning("📍 교실 기준 위치가 아직 설정되지 않았습니다.")
            st.info("💡 상단 '🔐 관리자 전용' 탭에서 관리자 이메일 로그인 후 교실 위치를 지정해 주세요.")
        else:
            base_lat, base_lon = global_store["base_location"]
            distance = geodesic((user_lat, user_lon), (base_lat, base_lon)).meters

            st.write(f"📍 현재 교실과의 거리: **약 {int(distance)}m**")

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

            st.divider()
            if st.button("🔄 실시간 인원수 새로고침", use_container_width=True, type="primary"):
                st.rerun()

# ------------------------------------------
# [탭 2] 관리자 전용 이메일 로그인 및 대시보드 화면
# ------------------------------------------
with tab_admin:
    st.header("🔐 관리자 전용 페이지")

    # 관리자 로그인이 안 된 경우 (이메일 입력 폼 표시)
    if not st.session_state.is_admin:
        st.subheader("📧 관리자 이메일 로그인")
        admin_email_input = st.text_input("등록된 관리자 이메일을 입력하세요", placeholder="example@email.com", key="main_admin_email_input")
        
        if st.button("이메일로 로그인하기", key="main_admin_login_btn", use_container_width=True, type="primary"):
            clean_input = admin_email_input.strip().lower()
            target_email = global_store["admin_email"].strip().lower()

            if clean_input and clean_input == target_email:
                st.session_state.is_admin = True
                st.success("관리자 이메일 인증에 성공했습니다!")
                st.rerun()
            else:
                st.error("등록된 관리자 이메일과 일치하지 않습니다.")

    # 관리자 로그인이 완료된 경우 (관리 기능 표시)
    else:
        st.success(f"🔓 관리자 인증 완료 ({global_store['admin_email']})")
        st.divider()

        # 1. 교실 위치 설정
        st.subheader("📍 1. 교실 위치 설정")
        st.write("현재 접속해 있는 내 브라우저 위치를 교실의 기준 위치로 지정합니다.")
        if st.button("📌 현재 내 위치를 교실 기준점으로 저장", key="admin_set_base_btn", use_container_width=True):
            st.session_state.set_base_requested = True
            st.info("위치 수집을 위해 '📱 사용자 화면' 탭을 한번 터치해 주시거나 새로고침해 주세요.")
            st.rerun()

        st.divider()

        # 2. 실시간 현황 및 데이터 초기화
        st.subheader("🔄 2. 인원 데이터 및 위치 초기화")
        st.write(f"현재 등록된 접속자 수: **{len(global_store['active_users'])}명**")
        if st.button("⚠️ 전체 데이터 및 기준점 초기화", key="admin_reset_btn", use_container_width=True):
            global_store["base_location"] = None
            global_store["active_users"] = set()
            st.warning("교실 기준점 및 출석 데이터가 초기화되었습니다.")
            st.rerun()

        st.divider()

        # 3. 관리자 이메일 변경
        st.subheader("📧 3. 관리자 이메일 변경")
        st.write(f"현재 등록된 이메일: **{global_store['admin_email']}**")
        new_email = st.text_input("새 관리자 이메일 입력", placeholder="new_admin@email.com", key="admin_new_email")
        new_email_confirm = st.text_input("새 관리자 이메일 확인", placeholder="new_admin@email.com", key="admin_new_email_confirm")
        
        if st.button("관리자 이메일 변경 저장", key="admin_change_email_btn", use_container_width=True):
            if not new_email:
                st.warning("새 이메일을 입력해 주세요.")
            elif "@" not in new_email or "." not in new_email:
                st.error("올바른 이메일 형식이 아닙니다.")
            elif new_email.strip().lower() != new_email_confirm.strip().lower():
                st.error("입력한 두 이메일이 일치하지 않습니다.")
            else:
                global_store["admin_email"] = new_email.strip()
                st.success("관리자 이메일이 성공적으로 변경되었습니다!")

        st.divider()

        # 4. 로그아웃
        if st.button("🔒 관리자 로그아웃", key="admin_logout_btn", use_container_width=True):
            st.session_state.is_admin = False
            st.success("로그아웃 되었습니다.")
            st.rerun()
