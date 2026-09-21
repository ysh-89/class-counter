import streamlit as st
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import pandas as pd
import uuid
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import time

# 화면 넓게 쓰기
st.set_page_config(page_title="제주 카페 인원 확인", layout="wide")

# --- 1. 상태 초기화 (세션 관리) ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
if 'base_location' not in st.session_state:
    st.session_state.base_location = None
if 'base_address' not in st.session_state:
    st.session_state.base_address = "미지정"
if 'active_users' not in st.session_state:
    st.session_state.active_users = {}

# --- 2. 카페 데이터 불러오기 (캐싱 적용으로 속도 향상) ---
@st.cache_data
def load_cafe_data():
    try:
        df = pd.read_csv('store.csv', encoding='utf-8')
        # '카페'가 포함된 업종만 필터링
        cafe_df = df[df['상권업종소분류명'].str.contains('카페', na=False)]
        return cafe_df[['상호명', '위도', '경도', '도로명주소']].dropna().reset_index(drop=True)
    except Exception as e:
        st.error("데이터를 불러오지 못했습니다. 동일한 폴더에 'store.csv'가 있는지 확인해주세요.")
        return pd.DataFrame(columns=['상호명', '위도', '경도', '도로명주소'])

cafe_df = load_cafe_data()

# --- 3. 사용자 위치 정보 가져오기 ---
loc = get_geolocation()
user_lat, user_lon = None, None

if loc and 'coords' in loc:
    user_lat = loc['coords']['latitude']
    user_lon =웹 지도 API(카카오맵, 네이버 지도, 구글 맵 등)와 자바스크립트를 활용해 구현할 수 있습니다. 국내에서 널리 쓰이는 **카카오맵 API**를 기준으로, 지도에 마커를 띄우고 클릭 시 위치와 인원수를 보여주는 전체 흐름을 구성하는 방법입니다.

## 1. 프론트엔드: 지도 표시 및 클릭 이벤트 구현

데이터베이스나 서버 API에서 카페의 좌표, 주소, 실시간 인원수 데이터를 받아왔다고 가정하고 화면에 렌더링하는 코드입니다.

```javascript
// 1. 지도 초기화
var mapContainer = document.getElementById('map'), // 지도를 표시할 div 
    mapOption = { 
        center: new kakao.maps.LatLng(33.450701, 126.570667), // 지도의 중심좌표
        level: 3 // 지도의 확대 레벨
    };
var map = new kakao.maps.Map(mapContainer, mapOption); 

// 2. 서버에서 받아온 가상의 카페 데이터 배열
var cafes = [
    { 
        name: '제주바당카페', 
        latlng: new kakao.maps.LatLng(33.450705, 126.570677), 
        address: '제주시 애월읍 123',
        peopleCount: 12 
    },
    { 
        name: '오름커피', 
        latlng: new kakao.maps.LatLng(33.450936, 126.569477), 
        address: '제주시 구좌읍 456',
        peopleCount: 5 
    }
];

// 3. 마커 및 인포윈도우(정보창) 생성
cafes.forEach(function(cafe) {
    // 지도에 마커 생성
    var marker = new kakao.maps.Marker({
        map: map,
        position: cafe.latlng
    });

    // 마커 클릭 시 보여줄 HTML 컨텐츠 (위치, 인원수, 위치지정 버튼)
    var iwContent = `
        <div style="padding:10px; width:200px; font-family:sans-serif;">
            <h4 style="margin: 0 0 5px 0;">${cafe.name}</h4>
            <p style="margin: 0 0 5px 0; font-size: 12px; color: #666;">위치: ${cafe.address}</p>
            <p style="margin: 0 0 10px 0; font-size: 14px; font-weight: bold;">
                현재 인원: <span style="color: #ff5722;">${cafe.peopleCount}명</span>
            </p>
            <button onclick="setTargetLocation('${cafe.name}', ${cafe.latlng.getLat()}, ${cafe.latlng.getLng()})" 
                    style="width: 100%; padding: 5px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer;">
                위치 지정하기
            </button>
        </div>
    `;

    var infowindow = new kakao.maps.InfoWindow({
        content: iwContent,
        removable: true // 닫기 버튼 표시
    });

    // 4. 마커 클릭 이벤트 등록
    kakao.maps.event.addListener(marker, 'click', function() {
        // 기존에 열린 인포윈도우가 있다면 닫는 로직을 추가할 수 있습니다.
        infowindow.open(map, marker);
    });
});

// 5. 위치 지정 버튼 클릭 시 실행될 함수
function setTargetLocation(name, lat, lng) {
    // 이 위치를 도착지로 설정하거나 DB에 저장하는 로직을 수행합니다.
    console.log("선택된 카페:", name);
    console.log("좌표:", lat, lng);
    alert(`${name}을(를) 목적지로 지정했습니다.`);
    
    // 예: 지도 중심을 해당 카페로 부드럽게 이동
    var moveLatLon = new kakao.maps.LatLng(lat, lng);
    map.panTo(moveLatLon);
}
