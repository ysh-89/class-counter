import streamlit as st
from streamlit_js_eval import get_geolocation
import pandas as pd
import numpy as np
import uuid
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# 페이지 기본 설정
st.set_page_config(page_title="제주 실시간 카페/장소 인원 카운터", page_icon="☕", layout="wide")

ALLOWED_RADIUS_METERS = 50  # 감지 반경 50m

# ==========================================
# 1. 데이터 로드 및 캐싱
# ==========================================
@st.cache_resource
def get_global_store():
    admin_email = st.secrets.get("ADMIN_EMAIL", "seokhwanyun892@gmail.com")
    
    try:
        df = pd.read_csv("store.csv")
    except Exception:
        df = pd.DataFrame(columns=['상호명', '상권업종소분류명', '시도명', '시군구명', '위도', '경도'])
    
    return {
        "base_location": None,       # (위도, 경도)
        "base_address": "",          # 선택된 장소 이름
        "cafe_active_users": {},     # 장소별 실시간 입실 유저 목록
        "admin_email": admin_email,
        "store_df": df
    }

global_store = get_global_store()

# 초고속 거리 계산 함수 (위도/경도 -> 미터 단위를 numpy로 순식간에 계산)
def fast_distance_meters(lat1, lon1, lat2, lon2):
    lat_diff = (lat2 - lat1) * 111000
    lon_diff = (lon2 - lon1) * 88000
    return np.sqrt(lat_diff**2 + lon_diff**2)

# ==========================================
# 2. 유저 고정 ID 생성
# ==========================================
if "uid" in st.query_params:
    user_id = st.query_params["uid"]
else:
    user_id = str(uuid.uuid4())[:8]
    st.query_params["uid"] = user_id

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ==========================================
# 3. ⚙️ 사이드바 필터 설정
# ==========================================
st.sidebar.header("⚙️ 지도 표시 필터")

region_list = ["전체", "제주시", "서귀포시"]
selected_region = st.sidebar.selectbox("📍 지역 선택", options=region_list)

st.sidebar.subheader("🏪 카테고리별 아이콘 표시")
all_categories = list(global_store["store_df"]['상권업종소분류명'].unique()) if not global_store["store_df"].empty else ["카페", "편의점"]

selected_categories = []
category_icons = {"카페": "☕ 카페", "편의점": "🏪 편의점"}

for cat in all_categories:
    label = category_icons.get(cat, f"📍 {cat}")
    default_val = True if cat == "카페" else False
    if st.sidebar.checkbox(label, value=default_val, key=f"cat_chk_{cat}"):
        selected_categories.append(cat)

st.sidebar.divider()
dist_filter = st.sidebar.select_slider(
    "📏 표시 거리 범위 (내 위치 기준)",
    options=["전체 보기", "1km 이내", "3km 이내", "5km 이내"],
    value="전체 보기"
)

# ==========================================
# 4. 데이터 필터링
# ==========================================
df_data = global_store["store_df"].copy()

if selected_region != "전체":
    df_data = df_data[df_data['시군구명'] == selected_region]

if selected_categories:
    df_filtered = df_data[df_data['상권업종소분류명'].isin(selected_categories)].reset_index(drop=True)
else:
    df_filtered = pd.DataFrame(columns=df_data.columns)

# ==========================================
# 5. 메인 화면
# ==========================================
tab_user, tab_admin = st.tabs(["📱 사용자 화면 (카페 검색/선택)", "🔐 관리자 전용"])

location = get_geolocation()

with tab_user:
    st.title("☕ 제주 실시간 장소/카페 인원 카운터")
    st.write("사이드바에서 **카페/편의점 체크박스**를 조절할 수 있으며, 지도 상의 **카페 마커를 누르면 해당 카페가 즉시 선택**됩니다.")

    if location is None:
        st.info("🌐 브라우저의 위치 권한 요청을 승인해 주세요...")
    elif not isinstance(location, dict) or "coords" not in location or location["coords"] is None:
        st.warning("⚠️ 위치 정보를 가져올 수 없습니다. 브라우저 GPS 권한을 허용해 주세요.")
    else:
        user_lat = location['coords']['latitude']
        user_lon = location['coords']['longitude']

        # 백터 연산으로 고속 거리 필터링
        if dist_filter != "전체 보기" and not df_filtered.empty:
            max_d = {"1km 이내": 1000, "3km 이내": 3000, "5km 이내": 5000}[dist_filter]
            df_filtered['dist_m'] = fast_distance_meters(user_lat, user_lon, df_filtered['위도'].values, df_filtered['경도'].values)
            df_filtered = df_filtered[df_filtered['dist_m'] <= max_d].reset_index(drop=True)

        st.subheader("📍 장소 직접 검색 / 선택")
        place_options = ["선택 안함 (지도의 아이콘 클릭 가능)"]
        if not df_filtered.empty:
            place_options += [
                f"[{row['상권업종소분류명']}] {row['상호명']} ({row['시군구명']})" for _, row in df_filtered.iterrows()
            ]

        current_addr = global_store["base_address"]
        default_index = 0
        if current_addr and not df_filtered.empty:
            for idx, row in df_filtered.iterrows():
                if str(row['상호명']) == current_addr:
                    default_index = idx + 1
                    break

        selected_option = st.selectbox("선택된 지역 장소 목록", options=place_options, index=default_index, key="place_selectbox")

        if selected_option != "선택 안함 (지도의 아이콘 클릭 가능)":
            selected_idx = place_options.index(selected_option) - 1
            selected_row = df_filtered.iloc[selected_idx]
            global_store["base_location"] = (float(selected_row['위도']), float(selected_row['경도']))
            global_store["base_address"] = str(selected_row['상호명'])

        # 지도 중심 설정
        if global_store["base_location"]:
            map_center = global_store["base_location"]
            map_zoom = 16
        elif selected_region == "제주시":
            map_center = [33.4996, 126.5312]
            map_zoom = 13
        elif selected_region == "서귀포시":
            map_center = [33.2541, 126.5601]
            map_zoom = 13
        else:
            map_center = [33.38, 126.55]
            map_zoom = 11

        m = folium.Map(location=map_center, zoom_start=map_zoom, tiles="OpenStreetMap")
        marker_cluster = MarkerCluster(disableClusteringAtZoom=15).add_to(m)

        if not df_filtered.empty:
            for _, row in df_filtered.iterrows():
                category = str(row['상권업종소분류명'])
                name = str(row['상호명'])
                is_selected = (name == global_store["base_address"])

                if '카페' in category:
                    icon_color = "red" if is_selected else "orange"
                    icon_type = "star" if is_selected else "coffee"
                else:
                    icon_color = "darkred" if is_selected else "blue"
                    icon_type = "star" if is_selected else "shopping-cart"

                folium.Marker(
                    location=[row['위도'], row['경도']],
                    popup=name,
                    tooltip=f"{'⭐ [선택됨] ' if is_selected else ''}{name}",
                    icon=folium.Icon(color=icon_color, icon=icon_type, prefix="fa")
                ).add_to(marker_cluster)

        if global_store["base_location"]:
            base_lat, base_lon = global_store["base_location"]
            folium.Circle(
                location=[base_lat, base_lon],
                radius=ALLOWED_RADIUS_METERS,
                color="#FF0000",
                weight=3,
                fill=True,
                fill_color="#FF0000",
                fill_opacity=0.35,
                popup=f"{global_store['base_address']} (50m 인식 범위)"
            ).add_to(m)

        folium.Marker(
            [user_lat, user_lon], 
            popup="📱 내 위치", 
            tooltip="📱 내 위치",
            icon=folium.Icon(color="purple", icon="user", prefix="fa")
        ).add_to(m)

        st.subheader(f"🗺️ 실시간 지도 ({selected_region})")
        st.caption("💡 지도 상의 **🟠 카페 마커**를 클릭하면 **🔴 빨간색 별 마커(⭐)**로 변경되며 실시간 인원수가 집계됩니다.")
        
        cat_key_str = "_".join(selected_categories) if selected_categories else "none"
        base_addr_str = global_store["base_address"] or "none"
        dynamic_map_key = f"folium_map_{selected_region}_{cat_key_str}_{dist_filter}_{base_addr_str}"

        map_data = st_folium(m, width=800, height=480, key=dynamic_map_key)

        clicked_obj = None
        if map_data:
            clicked_obj = map_data.get("last_marker_clicked") or map_data.get("last_object_clicked")

        if clicked_obj and "lat" in clicked_obj and "lng" in clicked_obj:
            clicked_lat = clicked_obj["lat"]
            clicked_lon = clicked_obj["lng"]

            if not df_filtered.empty:
                df_filtered['dist_calc'] = (df_filtered['위도'] - clicked_lat)**2 + (df_filtered['경도'] - clicked_lon)**2
                closest_place = df_filtered.loc[df_filtered['dist_calc'].idxmin()]
                
                if closest_place['dist_calc'] < 0.0005:
                    new_addr = str(closest_place['상호명'])
                    new_loc = (float(closest_place['위도']), float(closest_place['경도']))
                    if global_store["base_address"] != new_addr:
                        global_store["base_location"] = new_loc
                        global_store["base_address"] = new_addr
                        st.rerun()

        st.divider()

        if global_store["base_location"] is None or not global_store["base_address"]:
            st.warning("📍 **[선택 안 됨]** 현재 선택된 카페/장소가 없습니다. 지도 위 마커나 상단 목록에서 카페를 선택해 주세요.")
        else:
            target_place = global_store["base_address"]
            if target_place not in global_store["cafe_active_users"]:
                global_store["cafe_active_users"][target_place] = set()

            active_set = global_store["cafe_active_users"][target_place]
            b_lat, b_lon = global_store["base_location"]
            
            # 거리 계산
            distance = fast_distance_meters(user_lat, user_lon, b_lat, b_lon)

            if distance <= ALLOWED_RADIUS_METERS:
                active_set.add(user_id)
                status_msg = f"✅ 반경 {ALLOWED_RADIUS_METERS}m 이내에 있어 **[자동 입실]** 처리되었습니다."
                status_box = st.success
            else:
                active_set.discard(user_id)
                status_msg = f"❌ 반경 {ALLOWED_RADIUS_METERS}m 밖에 있어 **[자동 퇴실]** 처리되었습니다."
                status_box = st.error

            st.info(f"☕ **[선택 완료] 현재 선택된 장소:** **{target_place}**")
            st.metric(label=f"📊 '{target_place}' ({ALLOWED_RADIUS_METERS}m 반경) 실시간 이용 인원수", value=f"{len(active_set)} 명")
            st.write(f"📍 내 위치와의 거리: **약 {int(distance)}m**")
            status_box(status_msg)

            st.divider()
            if st.button("🔄 실시간 인원수 새로고침", use_container_width=True, type="primary"):
                st.rerun()

# ==========================================
# 6. 관리자 전용 화면
# ==========================================
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
