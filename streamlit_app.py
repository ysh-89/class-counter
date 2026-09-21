import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import pandas as pd
import uuid
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# 페이지 기본 설정
st.set_page_config(page_title="제주 카페 실시간 인원 카운터", page_icon="☕", layout="centered")

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
        cafe_df = df[df['상권업종소분류명'].str.contains('카페', na=False)].reset_index(drop=True)
    except Exception as e:
        cafe_df = pd.DataFrame(columns=['상호명', '상권업종소분류명', '시도명', '시군구명', '위도', '경도'])
    
    return {
        "base_location": None,       # (위도, 경도)
        "base_address": "",          # 선택된 카페 이름
        "cafe_active_users": {},     # 카페별 실시간 입실 유저 목록 {"카페명": set(user_ids)}
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

# ==========================================
# 3. 화면 탭 분리 (메인 사용자 화면 / 관리자 전용)
# ==========================================
tab_user, tab_admin = st.tabs(["📱 사용자 화면 (카페 검색/선택)", "🔐 관리자 전용"])

# 공통으로 브라우저 위치 가져오기
location = get_geolocation()

# ------------------------------------------
# [탭 1] 일반 사용자 화면
# ------------------------------------------
with tab_user:
    st.title("☕ 제주 카페 실시간 인원 카운터")
    st.write(f"지도 위의 **☕ 카페 아이콘을 클릭**하거나 직접 선택하세요. 반경 {ALLOWED_RADIUS_METERS}m 진입 시 **자동 입실** 처리됩니다.")

    if location is None:
        st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
    elif not isinstance(location, dict) or "coords" not in location or location["coords"] is None:
        st.warning("⚠️ 위치 정보를 가져올 수 없습니다. GPS가 켜져 있는지 확인해 주세요.")
    else:
        user_lat = location['coords']['latitude']
        user_lon = location['coords']['longitude']
        cafe_df = global_store["cafe_df"]

        # 1. 일반 사용자도 카페를 선택할 수 있는 드롭다운
        st.subheader("📍 카페 위치 선택")
        if not cafe_df.empty:
            cafe_options = ["선택 안함 (지도의 아이콘 클릭 가능)"] + [f"{row['상호명']} ({row['시군구명']})" for _, row in cafe_df.iterrows()]
            selected_option = st.selectbox("제주도 카페 검색/선택", options=cafe_options)

            if selected_option != "선택 안함 (지도의 아이콘 클릭 가능)":
                selected_idx = cafe_options.index(selected_option) - 1
                selected_row = cafe_df.iloc[selected_idx]
                global_store["base_location"] = (float(selected_row['위도']), float(selected_row['경도']))
                global_store["base_address"] = str(selected_row['상호명'])

        # 2. 지도 생성 및 제주도 모든 카페 아이콘 배치
        map_center = global_store["base_location"] if global_store["base_location"] else (user_lat, user_lon)
        m = folium.Map(location=map_center, zoom_start=14, tiles="OpenStreetMap")

        # 3,000여 개 카페 마커 클러스터링 (속도 최적화)
        marker_cluster = MarkerCluster().add_to(m)

        if not cafe_df.empty:
            for _, row in cafe_df.iterrows():
                folium.Marker(
                    location=[row['위도'], row['경도']],
                    popup=row['상호명'],
                    tooltip=row['상호명'],
                    icon=folium.Icon(color="orange", icon="coffee", prefix="fa")
                ).add_to(marker_cluster)

        # 현재 선택된 카페(기준점) 강조 표시
        if global_store["base_location"]:
            base_lat, base_lon = global_store["base_location"]
            folium.Marker(
                [base_lat, base_lon], 
                popup=f"📍 {global_store['base_address']}", 
                icon=folium.Icon(color="red", icon="star")
            ).add_to(m)
            
            folium.Circle(
                location=[base_lat, base_lon],
                radius=ALLOWED_RADIUS_METERS,
                color="#FF0000",
                weight=2,
                fill=True,
                fill_color="#FF0000",
                fill_opacity=0.25,
                popup=f"{ALLOWED_RADIUS_METERS}m 감지 범위"
            ).add_to(m)

        # 사용자 내 위치 마커
        folium.Marker(
            [user_lat, user_lon], 
            popup="📱 내 위치", 
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)

        st.subheader("🗺️ 실시간 제주 카페 지도")
        st.caption("💡 지도 상의 **☕ 카페 아이콘**을 직접 누르면 클릭한 지점의 카페 정보와 인원수가 조회됩니다.")
        
        # 지도 출력 및 클릭 이벤트 수신
        map_data = st_folium(m, width=700, height=400, key="user_cafe_map")

        # 지도의 카페 마커 클릭 시 클릭된 카페 자동 감지
        if map_data and map_data.get("last_object_clicked"):
            clicked_lat = map_data["last_object_clicked"]["lat"]
            clicked_lon = map_data["last_object_clicked"]["lng"]

            # 가장 가까운 카페 찾아내기
            cafe_df['dist_calc'] = (cafe_df['위도'] - clicked_lat)**2 + (cafe_df['경도'] - clicked_lon)**2
            closest_cafe = cafe_df.loc[cafe_df['dist_calc'].idxmin()]
            
            if closest_cafe['dist_calc'] < 0.0001:  # 마커 부근 클릭 시
                new_addr = str(closest_cafe['상호명'])
                new_loc = (float(closest_cafe['위도']), float(closest_cafe['경도']))
                if global_store["base_address"] != new_addr:
                    global_store["base_location"] = new_loc
                    global_store["base_address"] = new_addr
                    st.rerun()

        st.divider()

        # 3. 클릭/선택한 카페의 실시간 인원수 및 거리 표시
        if global_store["base_location"] is None:
            st.info("📍 상단 드롭다운 또는 지도 위의 카페 아이콘을 클릭하여 카페를 선택해 주세요.")
        else:
            target_cafe = global_store["base_address"]
            if target_cafe not in global_store["cafe_active_users"]:
                global_store["cafe_active_users"][target_cafe] = set()

            active_set = global_store["cafe_active_users"][target_cafe]
            b_lat, b_lon = global_store["base_location"]
            distance = geodesic((user_lat, user_lon), (b_lat, b_lon)).meters

            # 50m 이내 자동 입실/퇴실 판정
            if distance <= ALLOWED_RADIUS_METERS:
                active_set.add(user_id)
                status_msg = f"✅ 카페 반경 {ALLOWED_RADIUS_METERS}m 이내에 있어 **[자동 입실]** 처리되었습니다."
                status_box = st.success
            else:
                active_set.discard(user_id)
                status_msg = f"❌ 카페 반경 {ALLOWED_RADIUS_METERS}m 밖에 있어 **[자동 퇴실]** 처리되었습니다."
                status_box = st.error

            st.markdown(f"### ☕ 현재 선택된 카페: **{target_cafe}**")
            st.metric(label=f"📊 현재 해당 카페({ALLOWED_RADIUS_METERS}m 반경) 실시간 이용 인원수", value=f"{len(active_set)} 명")
            st.write(f"📍 내 위치와 카페와의 거리: **약 {int(distance)}m**")
            status_box(status_msg)

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

        st.subheader("📍 수동 위치/기준점 지정")
        col1, col2 = st.columns(2)
        with col1:
            input_lat = st.number_input("위도(Latitude)", value=33.450701, format="%.6f")
        with col2:
            input_lon = st.number_input("경도(Longitude)", value=126.570667, format="%.6f")

        input_address = st.text_input("장소 설명 이름", placeholder="예: 지정 장소")

        if st.button("📌 입력된 위/경도를 관리자 기준점으로 지정", use_container_width=True, type="primary"):
            global_store["base_location"] = (input_lat, input_lon)
            global_store["base_address"] = input_address if input_address else "지정 위치"
            st.success(f"✅ 기준점이 설정되었습니다! ({global_store['base_address']})")
            st.rerun()

        st.divider()

        st.subheader("🔄 데이터 초기화")
        if st.button("⚠️ 전체 데이터 및 기준점 초기화", use_container_width=True):
            global_store["base_location"] = None
            global_store["base_address"] = ""
            global_store["cafe_active_users"] = {}
            st.warning("데이터가 초기화되었습니다.")
            st.rerun()

        st.divider()

        if st.button("🔒 관리자 로그아웃", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
