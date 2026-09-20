import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import uuid
import streamlit.components.v1 as components

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 50  # 감지 반경 50m

# ==========================================
# 1. 서버 전체 공유 저장소 및 Secrets 연동
# ==========================================
@st.cache_resource
def get_global_store():
    admin_email = st.secrets.get("ADMIN_EMAIL", "seokhwanyun892@gmail.com")
    kakao_key = st.secrets.get("KAKAO_JS_KEY", "")
    
    return {
        "base_location": None,  # (위도, 경도)
        "base_address": "",     # 교실 주소 이름
        "active_users": set(),
        "admin_email": admin_email,
        "kakao_js_key": kakao_key
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

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ==========================================
# 3. 화면 탭 분리 (메인 화면 / 관리자 전용 화면)
# ==========================================
tab_user, tab_admin = st.tabs(["📱 사용자 화면", "🔐 관리자 전용"])

# 공통으로 브라우저 위치 가져오기 (에러 방지를 위해 key 인자 제거)
location = get_geolocation()

# ------------------------------------------
# [탭 1] 일반 사용자 화면
# ------------------------------------------
with tab_user:
    st.title("🏫 위치 기반 자동 인원 카운터")
    st.write(f"위치 권한을 승인하면 반경 {ALLOWED_RADIUS_METERS}m 진입 시 **자동 입실**, 범위를 벗어나면 **자동 퇴실** 처리됩니다.")

    if location is None:
        st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
    elif not isinstance(location, dict) or "coords" not in location or location["coords"] is None:
        st.warning("⚠️ 위치 정보를 가져올 수 없습니다. GPS가 켜져 있는지, 브라우저 위치 권한을 허용했는지 확인해 주세요.")
    else:
        user_lat = location['coords']['latitude']
        user_lon = location['coords']['longitude']

        kakao_js_key = global_store["kakao_js_key"]
        
        if not kakao_js_key:
            st.error("⚠️ Streamlit Secrets에 'KAKAO_JS_KEY'가 설정되어 있지 않습니다. 설정 후 다시 시도해 주세요.")
        else:
            base_lat = global_store["base_location"][0] if global_store["base_location"] else user_lat
            base_lon = global_store["base_location"][1] if global_store["base_location"] else user_lon
            has_base = "true" if global_store["base_location"] else "false"

            kakao_map_html = f"""
            <div id="map" style="width:100%;height:350px;border-radius:10px;"></div>
            <script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_js_key}"></script>
            <script>
                var container = document.getElementById('map');
                var options = {{
                    center: new kakao.maps.LatLng({base_lat}, {base_lon}),
                    level: 3
                }};
                var map = new kakao.maps.Map(container, options);

                var hasBase = {has_base};
                if (hasBase) {{
                    var basePosition = new kakao.maps.LatLng({base_lat}, {base_lon});
                    var baseMarker = new kakao.maps.Marker({{ position: basePosition }});
                    baseMarker.setMap(map);

                    var circle = new kakao.maps.Circle({{
                        center: basePosition,
                        radius: {ALLOWED_RADIUS_METERS},
                        strokeWeight: 2,
                        strokeColor: '#FF0000',
                        strokeOpacity: 0.8,
                        fillColor: '#FF0000',
                        fillOpacity: 0.2
                    }});
                    circle.setMap(map);
                }}

                var userPosition = new kakao.maps.LatLng({user_lat}, {user_lon});
                var userMarker = new kakao.maps.Marker({{ position: userPosition }});
                userMarker.setMap(map);
            </script>
            """
            components.html(kakao_map_html, height=370)

        st.divider()

        current_count = len(global_store["active_users"])
        st.metric(label=f"📊 현재 교실({ALLOWED_RADIUS_METERS}m 반경) 내 실시간 인원수", value=f"{current_count} 명")
        st.divider()

        if global_store["base_location"] is None:
            st.warning("📍 교실 기준 위치가 아직 설정되지 않았습니다.")
            st.info("💡 상단 '🔐 관리자 전용' 탭에서 교실 위치를 설정해 주세요.")
        else:
            b_lat, b_lon = global_store["base_location"]
            distance = geodesic((user_lat, user_lon), (b_lat, b_lon)).meters
            st.write(f"📍 현재 교실({global_store['base_address']})과의 거리: **약 {int(distance)}m**")

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
# [탭 2] 관리자 전용 화면
# ------------------------------------------
with tab_admin:
    st.header("🔐 관리자 전용 페이지")

    if not st.session_state.is_admin:
        st.subheader("📧 관리자 이메일 로그인")
        admin_email_input = st.text_input("등록된 관리자 이메일을 입력하세요", placeholder="seokhwanyun892@gmail.com")
        
        if st.button("이메일로 로그인하기", use_container_width=True, type="primary"):
            if admin_email_input.strip().lower() == global_store["admin_email"].lower():
                st.session_state.is_admin = True
                st.success("관리자 인증 성공!")
                st.rerun()
            else:
                st.error("등록된 관리자 이메일과 일치하지 않습니다.")

    else:
        st.success(f"🔓 관리자 인증 완료 ({global_store['admin_email']})")
        st.divider()

        st.subheader("📍 1. 교실 위치 지정")
        col1, col2 = st.columns(2)
        with col1:
            input_lat = st.number_input("위도(Latitude)", value=33.450701, format="%.6f")
        with col2:
            input_lon = st.number_input("경도(Longitude)", value=126.570667, format="%.6f")

        input_address = st.text_input("교실 이름 또는 장소 설명", placeholder="예: 3학년 2반 교실")

        if st.button("📌 해당 위/경도를 교실 기준점으로 저장", use_container_width=True, type="primary"):
            global_store["base_location"] = (input_lat, input_lon)
            global_store["base_address"] = input_address if input_address else "지정 위치"
            st.success(f"✅ 교실 기준점이 설정되었습니다! ({global_store['base_address']})")
            st.rerun()

        st.divider()

        if st.button("📌 현재 내 브라우저 위치를 교실로 지정", use_container_width=True):
            if location and isinstance(location, dict) and "coords" in location and location["coords"]:
                a_lat = location['coords']['latitude']
                a_lon = location['coords']['longitude']
                global_store["base_location"] = (a_lat, a_lon)
                global_store["base_address"] = "현재 내 위치"
                st.success("✅ 현재 브라우저 위치가 교실 기준점으로 저장되었습니다!")
                st.rerun()
            else:
                st.warning("⚠️ 브라우저 위치를 가져오지 못했습니다. '사용자 화면' 탭에서 위치 권한이 허용되어 있는지 확인해 주세요.")

        st.divider()

        st.subheader("🔄 3. 데이터 초기화")
        st.write(f"현재 등록된 접속자 수: **{len(global_store['active_users'])}명**")
        if st.button("⚠️ 전체 데이터 및 기준점 초기화", use_container_width=True):
            global_store["base_location"] = None
            global_store["base_address"] = ""
            global_store["active_users"] = set()
            st.warning("데이터가 초기화되었습니다.")
            st.rerun()

        st.divider()

        if st.button("🔒 관리자 로그아웃", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
