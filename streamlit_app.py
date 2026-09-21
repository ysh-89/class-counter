import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import pandas as pd
import uuid
import folium
from streamlit_folium import st_folium

# 페이지 기본 설정
st.set_page_config(page_title="위치 기반 자동 인원 카운터", page_icon="🏫", layout="centered")

ALLOWED_RADIUS_METERS = 50  # 감지 반경 50m

# ==========================================
# 1. 서버 전체 공유 저장소 및 CSV 데이터 로드
# ==========================================
@st.cache_resource
def get_global_store():
    admin_email = st.secrets.get("ADMIN_EMAIL", "seokhwanyun892@gmail.com")
    
    # store.csv 파일에서 제주도 카페 데이터 로드
    try:
        df = pd.read_csv("store.csv")
        # '카페' 관련 업종만 필터링
        cafe_df = df[df['상권업종소분류명'].str.contains('카페', na=False)].reset_index(drop=True)
    except Exception as e:
        cafe_df = pd.DataFrame(columns=['상호명', '상권업종소분류명', '시도명', '시군구명', '위도', '경도'])
    
    return {
        "base_location": None,  # (위도, 경도)
        "base_address": "",     # 장소 이름
        "active_users": set(),
        "admin_email": admin_email,
        "cafe_df": cafe_df
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

# 세션 상태 초기값
if "input_lat" not in st.session_state:
    st.session_state.input_lat = 33.450701
if "input_lon" not in st.session_state:
    st.session_state.input_lon = 126.570667
if "input_addr" not in st.session_state:
    st.session_state.input_addr = ""

# ==========================================
# 3. 화면 탭 분리 (메인 화면 / 관리자 전용 화면)
# ==========================================
tab_user, tab_admin = st.tabs(["📱 사용자 화면", "🔐 관리자 전용"])

# 공통으로 브라우저 위치 가져오기
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

        # 🗺️ Folium 지도 생성
        map_center = global_store["base_location"] if global_store["base_location"] else (user_lat, user_lon)
        m = folium.Map(location=map_center, zoom_start=15, tiles="OpenStreetMap")

        if global_store["base_location"]:
            base_lat, base_lon = global_store["base_location"]
            folium.Marker(
                [base_lat, base_lon], 
                popup="📍 기준 위치", 
                icon=folium.Icon(color="red", icon="home")
            ).add_to(m)
            
            folium.Circle(
                location=[base_lat, base_lon],
                radius=ALLOWED_RADIUS_METERS,
                color="#FF0000",
                weight=2,
                fill=True,
                fill_color="#FF0000",
                fill_opacity=0.2,
                popup=f"{ALLOWED_RADIUS_METERS}m 자동 인식 범위"
            ).add_to(m)

        folium.Marker(
            [user_lat, user_lon], 
            popup="📱 내 위치", 
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)

        st.subheader("🗺️ 실시간 위치 지도")
        st_folium(m, width=700, height=350)
        st.caption("🔴 빨간색 원: 50m 인식 범위 / 🔵 파란 마커: 내 위치")

        st.divider()

        current_count = len(global_store["active_users"])
        st.metric(label=f"📊 현재 지정 장소({ALLOWED_RADIUS_METERS}m 반경) 내 실시간 인원수", value=f"{current_count} 명")
        st.divider()

        if global_store["base_location"] is None:
            st.warning("📍 기준 위치가 아직 설정되지 않았습니다.")
            st.info("💡 상단 '🔐 관리자 전용' 탭에서 위치를 설정해 주세요.")
        else:
            b_lat, b_lon = global_store["base_location"]
            distance = geodesic((user_lat, user_lon), (b_lat, b_lon)).meters
            st.write(f"📍 현재 장소({global_store['base_address']})과의 거리: **약 {int(distance)}m**")

            if distance <= ALLOWED_RADIUS_METERS:
                if user_id not in global_store["active_users"]:
                    global_store["active_users"].add(user_id)
                    st.rerun()
                st.success(f"✅ 반경 {ALLOWED_RADIUS_METERS}m 이내에 있어 **[자동 입실]** 처리되었습니다.")
            else:
                if user_id in global_store["active_users"]:
                    global_store["active_users"].remove(user_id)
                    st.rerun()
                st.error(f"❌ 반경 {ALLOWED_RADIUS_METERS}m 밖에 있어 **[자동 퇴실]** 처리되었습니다.")

            st.divider()
            if st.button("🔄 실시간 인원수 새로고침", use_container_width=True, type="primary"):
                st.rerun()

# ------------------------------------------
# [탭 2] 관리자 전용 화면 (제주도 카페 선택 기능 추가)
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

        st.subheader("☕ 제주도 카페 선택으로 위치 지정")
        st.write("목록에서 제주도 카페를 선택하면 해당 카페의 위치와 이름이 자동으로 입력됩니다.")

        cafe_df = global_store["cafe_df"]
        if not cafe_df.empty:
            # 상호명과 지역을 결합하여 셀렉트박스 목록 생성
            cafe_options = [f"{row['상호명']} ({row['시군구명']})" for _, row in cafe_df.iterrows()]
            selected_cafe_str = st.selectbox("제주도 카페 선택", options=cafe_options)

            if st.button("📌 선택한 카페 정보 불러오기", use_container_width=True):
                selected_idx = cafe_options.index(selected_cafe_str)
                selected_row = cafe_df.iloc[selected_idx]
                
                st.session_state.input_lat = float(selected_row['위도'])
                st.session_state.input_lon = float(selected_row['경도'])
                st.session_state.input_addr = str(selected_row['상호명'])
                st.success(f"✅ 카페 선택 완료: {selected_row['상호명']} ({selected_row['위도']}, {selected_row['경도']})")
                st.rerun()
        else:
            st.warning("⚠️ store.csv 파일에서 카페 데이터를 불러오지 못했습니다.")

        st.divider()

        st.subheader("📍 위치 지정 세부 설정")
        col1, col2 = st.columns(2)
        with col1:
            input_lat = st.number_input("위도(Latitude)", format="%.6f", key="input_lat")
        with col2:
            input_lon = st.number_input("경도(Longitude)", format="%.6f", key="input_lon")

        input_address = st.text_input("장소 설명 이름", key="input_addr", placeholder="예: 선택된 카페 이름")

        if st.button("📌 해당 위/경도를 기준점으로 저장", use_container_width=True, type="primary"):
            global_store["base_location"] = (input_lat, input_lon)
            global_store["base_address"] = input_address if input_address else "지정 위치"
            st.success(f"✅ 기준점이 설정되었습니다! ({global_store['base_address']})")
            st.rerun()

        st.divider()

        if st.button("📌 현재 내 브라우저 위치를 기준점으로 지정", use_container_width=True):
            if location and isinstance(location, dict) and "coords" in location and location["coords"]:
                a_lat = location['coords']['latitude']
                a_lon = location['coords']['longitude']
                global_store["base_location"] = (a_lat, a_lon)
                global_store["base_address"] = "현재 내 위치"
                st.success("✅ 현재 브라우저 위치가 기준점으로 저장되었습니다!")
                st.rerun()
            else:
                st.warning("⚠️ 브라우저 위치를 가져오지 못했습니다. '사용자 화면' 탭에서 위치 권한이 허용되어 있는지 확인해 주세요.")

        st.divider()

        st.subheader("🔄 데이터 초기화")
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
