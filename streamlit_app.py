import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import pandas as pd
import uuid
import folium
from streamlit_folium import st_folium

# 페이지 기본 설정
st.set_page_config(page_title="제주 카페 실시간 인원 카운터", page_icon="☕", layout="wide")

ALLOWED_RADIUS_METERS = 50  # 감지 반경 50m

# ==========================================
# 1. 서버 전체 공유 저장소 및 CSV 데이터 로드
# ==========================================
@st.cache_resource
def get_global_store():
    admin_email = st.secrets.get("ADMIN_EMAIL", "seokhwanyun892@gmail.com")
    
    try:
        df = pd.read_csv("store.csv")
    except Exception as e:
        df = pd.DataFrame(columns=['상호명', '상권업종소분류명', '시도명', '시군구명', '위도', '경도'])
    
    return {
        "base_location": None,
        "base_address": "",
        "cafe_active_users": {},
        "admin_email": admin_email,
        "store_df": df
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
# 3. ⚙️ 좌측 사이드바 필터 설정
# ==========================================
st.sidebar.header("⚙️ 지도 표시 필터")

region_list = ["전체", "제주시", "서귀포시"]
selected_region = st.sidebar.selectbox("📍 지역 선택", options=region_list)

all_categories = list(global_store["store_df"]['상권업종소분류명'].unique()) if not global_store["store_df"].empty else ["카페", "편의점"]
selected_categories = st.sidebar.multiselect(
    "🏪 지도에 표시할 아이콘 선택", 
    options=all_categories, 
    default=["카페"]
)

st.sidebar.divider()
st.sidebar.info("💡 사이드바에서 지역을 변경하면 해당 지역으로 지도가 자동 이동하고 해당 정보만 필터링됩니다.")

# ==========================================
# 4. 데이터 필터링 및 중심 좌표 계산
# ==========================================
df_data = global_store["store_df"].copy()

if selected_region != "전체":
    df_data = df_data[df_data['시군구명'] == selected_region]

if selected_categories:
    df_filtered = df_data[df_data['상권업종소분류명'].isin(selected_categories)].reset_index(drop=True)
else:
    df_filtered = pd.DataFrame(columns=df_data.columns)

if selected_region == "제주시":
    map_center = [33.4996, 126.5312]
    map_zoom = 13
elif selected_region == "서귀포시":
    map_center = [33.2541, 126.5601]
    map_zoom = 13
else:
    map_center = [33.38, 126.55]
    map_zoom = 11

# ==========================================
# 5. 메인 화면 탭 분리
# ==========================================
tab_user, tab_admin = st.tabs(["📱 사용자 화면 (카페 검색/선택)", "🔐 관리자 전용"])

location = get_geolocation()

# ------------------------------------------
# [탭 1] 일반 사용자 화면
# ------------------------------------------
with tab_user:
    st.title("☕ 제주 실시간 장소/카페 인원 카운터")
    st.write(f"왼쪽 사이드바에서 **지역 및 표시할 아이콘**을 설정하세요. 지도 상의 마커를 클릭하거나 검색하여 장소를 선택할 수 있습니다.")

    if location is None:
        st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
    elif not isinstance(location, dict) or "coords" not in location or location["coords"] is None:
        st.warning("⚠️ 위치 정보를 가져올 수 없습니다. 브라우저 GPS 권한을 확인해 주세요.")
    else:
        user_lat = location['coords']['latitude']
        user_lon = location['coords']['longitude']

        st.subheader("📍 장소 직접 선택")
        if not df_filtered.empty:
            place_options = ["선택 안함 (지도의 마커 클릭 가능)"] + [f"[{row['상권업종소분류명']}] {row['상호명']} ({row['시군구명']})" for _, row in df_filtered.iterrows()]
            selected_option = st.selectbox("선택된 지역 장소 목록", options=place_options)

            if selected_option != "선택 안함 (지도의 마커 클릭 가능)":
                selected_idx = place_options.index(selected_option) - 1
                selected_row = df_filtered.iloc[selected_idx]
                global_store["base_location"] = (float(selected_row['위도']), float(selected_row['경도']))
                global_store["base_address"] = str(selected_row['상호명'])

        if global_store["base_location"]:
            map_center = global_store["base_location"]
            map_zoom = 16

        m = folium.Map(location=map_center, zoom_start=map_zoom, tiles="OpenStreetMap")

        # ☕ 큼직하고 선명한 카페 전용 HTML 아이콘 스타일링
        cafe_icon_html = """
        <div style="
            background-color: #FF3D00;
            color: #FFFFFF;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
            border: 3px solid #FFFFFF;
            box-shadow: 0px 3px 8px rgba(0,0,0,0.5);
            cursor: pointer;
        ">☕</div>
        """

        # 🏪 기타 매장 HTML 아이콘 스타일링
        store_icon_html = """
        <div style="
            background-color: #1E88E5;
            color: #FFFFFF;
            border-radius: 50%;
            width: 26px;
            height: 26px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            border: 2px solid #FFFFFF;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.3);
        ">🏪</div>
        """

        # 마커 추가 (클러스터 묶음 없이 바로 개별 아이콘으로 표시)
        if not df_filtered.empty:
            for _, row in df_filtered.iterrows():
                is_cafe = '카페' in str(row['상권업종소분류명'])
                
                if is_cafe:
                    folium.Marker(
                        location=[row['위도'], row['경도']],
                        popup=row['상호명'],
                        tooltip=f"☕ {row['상호명']}",
                        icon=folium.DivIcon(html=cafe_icon_html, icon_size=(36, 36), icon_anchor=(18, 18))
                    ).add_to(m)
                else:
                    folium.Marker(
                        location=[row['위도'], row['경도']],
                        popup=row['상호명'],
                        tooltip=f"🏪 {row['상호명']}",
                        icon=folium.DivIcon(html=store_icon_html, icon_size=(26, 26), icon_anchor=(13, 13))
                    ).add_to(m)

        # 선택된 기준 장소 강조 마커 및 50m 범위 원
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
                weight=3,
                fill=True,
                fill_color="#FF0000",
                fill_opacity=0.3,
                popup=f"{ALLOWED_RADIUS_METERS}m 감지 범위"
            ).add_to(m)

        # 사용자 내 위치 마커
        folium.Marker(
            [user_lat, user_lon], 
            popup="📱 내 위치", 
            icon=folium.Icon(color="blue", icon="user")
        ).add_to(m)

        st.subheader(f"🗺️ 실시간 지도 ({selected_region})")
        st.caption("💡 지도 위의 선명한 **☕ 카페 아이콘**을 누르면 클릭한 위치의 인원수가 자동 조회됩니다.")
        
        map_data = st_folium(m, width=800, height=480, key="main_user_map")

        if map_data and map_data.get("last_object_clicked"):
            clicked_lat = map_data["last_object_clicked"]["lat"]
            clicked_lon = map_data["last_object_clicked"]["lng"]

            if not df_filtered.empty:
                df_filtered['dist_calc'] = (df_filtered['위도'] - clicked_lat)**2 + (df_filtered['경도'] - clicked_lon)**2
                closest_place = df_filtered.loc[df_filtered['dist_calc'].idxmin()]
                
                if closest_place['dist_calc'] < 0.0001:
                    new_addr = str(closest_place['상호명'])
                    new_loc = (float(closest_place['위도']), float(closest_place['경도']))
                    if global_store["base_address"] != new_addr:
                        global_store["base_location"] = new_loc
                        global_store["base_address"] = new_addr
                        st.rerun()

        st.divider()

        if global_store["base_location"] is None:
            st.info("📍 상단 드롭다운 또는 지도 위의 아이콘을 클릭하여 장소를 선택해 주세요.")
        else:
            target_place = global_store["base_address"]
            if target_place not in global_store["cafe_active_users"]:
                global_store["cafe_active_users"][target_place] = set()

            active_set = global_store["cafe_active_users"][target_place]
            b_lat, b_lon = global_store["base_location"]
            distance = geodesic((user_lat, user_lon), (b_lat, b_lon)).meters

            if distance <= ALLOWED_RADIUS_METERS:
                active_set.add(user_id)
                status_msg = f"✅ 반경 {ALLOWED_RADIUS_METERS}m 이내에 있어 **[자동 입실]** 처리되었습니다."
                status_box = st.success
            else:
                active_set.discard(user_id)
                status_msg = f"❌ 반경 {ALLOWED_RADIUS_METERS}m 밖에 있어 **[자동 퇴실]** 처리되었습니다."
                status_box = st.error

            st.markdown(f"### 📍 현재 선택된 장소: **{target_place}**")
            st.metric(label=f"📊 현재 장소({ALLOWED_RADIUS_METERS}m 반경) 실시간 이용 인원수", value=f"{len(active_set)} 명")
            st.write(f"📍 내 위치와의 거리: **약 {int(distance)}m**")
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
