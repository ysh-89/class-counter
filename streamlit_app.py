import streamlit as st


# ==========================================
# Streamlit 기본 설정
# ==========================================

st.set_page_config(
    page_title="우리 반 인원 확인",
    page_icon="📍",
    layout="centered"
)


# ==========================================
# 카카오 JavaScript Key
# ==========================================

KAKAO_JS_KEY = st.secrets["KAKAO_JS_KEY"]


# ==========================================
# 교실 위치
# ==========================================

CLASS_LAT = 33.000000
CLASS_LON = 126.000000


# ==========================================
# 교실로 인정할 반경
# ==========================================

RADIUS_M = 100


# ==========================================
# 화면
# ==========================================

st.title("📍 우리 반 인원 확인")

st.write(
    "현재 위치를 확인하여 "
    "교실 범위 안에 있는지 확인합니다."
)

st.info(
    "이 시스템은 개인의 위치를 공개하지 않고 "
    "현재 교실 안에 있는 인원 수만 계산하는 것을 목표로 합니다."
)


# ==========================================
# 현재 위치 확인
# ==========================================

st.subheader("현재 위치 확인")

st.write(
    "위치 권한을 허용하고 아래 버튼을 눌러주세요."
)


# ==========================================
# 카카오맵 + GPS
# ==========================================

html_code = f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8">

<style>

body {{
    margin: 0;
    padding: 0;
    font-family: Arial, sans-serif;
}}


/* 지도 */

#map {{
    width: 100%;
    height: 300px;
    border-radius: 10px;
    overflow: hidden;
}}


/* 버튼 */

button {{
    width: 100%;
    padding: 15px;
    margin-top: 10px;

    font-size: 16px;
    font-weight: bold;

    border: none;
    border-radius: 8px;

    cursor: pointer;
}}


/* 결과 */

#result {{

    margin-top: 15px;

    padding: 15px;

    border-radius: 8px;

    background: #f1f1f1;

    text-align: center;

}}


</style>


<script
    src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={KAKAO_JS_KEY}">
</script>


</head>


<body>


<!-- ======================================
     지도
======================================= -->

<div id="map"></div>


<!-- ======================================
     현재 위치 확인 버튼
======================================= -->

<button onclick="checkLocation()">

📍 현재 위치 확인

</button>


<!-- ======================================
     결과
======================================= -->

<div id="result">

아직 위치를 확인하지 않았습니다.

</div>


<script>


// ==========================================
// 교실 위치
// ==========================================

const classLatitude = {CLASS_LAT};

const classLongitude = {CLASS_LON};


const classPosition =
    new kakao.maps.LatLng(
        classLatitude,
        classLongitude
    );


// ==========================================
// 지도 생성
// ==========================================

const container =
    document.getElementById("map");


const options = {{

    center: classPosition,

    level: 3

}};


const map =
    new kakao.maps.Map(
        container,
        options
    );


// ==========================================
// 교실 위치 마커
// ==========================================

const classMarker =
    new kakao.maps.Marker({{

        position: classPosition

    }});


classMarker.setMap(map);


// ==========================================
// 교실 범위
// ==========================================

const circle =
    new kakao.maps.Circle({{

        center: classPosition,

        radius: {RADIUS_M},

        strokeWeight: 2,

        strokeOpacity: 0.8,

        fillOpacity: 0.1

    }});


circle.setMap(map);


// ==========================================
// GPS 확인
// ==========================================

function checkLocation() {{

    const result =
        document.getElementById("result");


    result.innerHTML =
        "📡 현재 위치를 확인하고 있습니다...";


    if (!navigator.geolocation) {{

        result.innerHTML =
            "❌ 이 브라우저에서는 GPS를 사용할 수 없습니다.";

        return;

    }}


    navigator.geolocation.getCurrentPosition(

        locationSuccess,

        locationError,

        {{

            enableHighAccuracy: true,

            timeout: 10000,

            maximumAge: 0

        }}

    );

}}


// ==========================================
// GPS 성공
// ==========================================

function locationSuccess(position) {{

    const latitude =
        position.coords.latitude;


    const longitude =
        position.coords.longitude;


    const accuracy =
        position.coords.accuracy;


    // ======================================
    // 거리 계산
    // ======================================

    const distance =
        calculateDistance(

            latitude,
            longitude,

            classLatitude,
            classLongitude

        );


    const result =
        document.getElementById("result");


    // ======================================
    // 교실 안/밖 판단
    // ======================================

    if (distance <= {RADIUS_M}) {{

        result.innerHTML =

            "🟢 현재 교실 범위 안입니다." +

            "<br><br>" +

            "인원 집계에 포함할 수 있습니다." +

            "<br><br>" +

            "GPS 정확도: " +

            accuracy.toFixed(1) +

            "m";

    }}

    else {{

        result.innerHTML =

            "🔴 현재 교실 범위 밖입니다." +

            "<br><br>" +

            "인원 집계에 포함되지 않습니다." +

            "<br><br>" +

            "GPS 정확도: " +

            accuracy.toFixed(1) +

            "m";

    }}

}}


// ==========================================
// GPS 오류
// ==========================================

function locationError(error) {{

    const result =
        document.getElementById("result");


    if (
        error.code ===
        error.PERMISSION_DENIED
    ) {{

        result.innerHTML =
            "❌ 위치 권한이 거부되었습니다.";

    }}

    else if (
        error.code ===
        error.POSITION_UNAVAILABLE
    ) {{

        result.innerHTML =
            "❌ 현재 위치를 가져올 수 없습니다.";

    }}

    else if (
        error.code ===
        error.TIMEOUT
    ) {{

        result.innerHTML =
            "❌ 위치 확인 시간이 초과되었습니다.";

    }}

    else {{

        result.innerHTML =
            "❌ 알 수 없는 GPS 오류입니다.";

    }}

}}


// ==========================================
// 거리 계산
// ==========================================

function calculateDistance(
    lat1,
    lon1,
    lat2,
    lon2
) {{

    const R = 6371000;

    const rad =
        Math.PI / 180;


    const dLat =
        (lat2 - lat1) * rad;


    const dLon =
        (lon2 - lon1) * rad;


    const a =

        Math.sin(dLat / 2) *
        Math.sin(dLat / 2)

        +

        Math.cos(lat1 * rad) *
        Math.cos(lat2 * rad) *

        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);


    const c =
        2 *
        Math.atan2(
            Math.sqrt(a),
            Math.sqrt(1 - a)
        );


    return R * c;

}}

</script>


</body>

</html>
"""


# ==========================================
# HTML 실행
# ==========================================

st.iframe(
    html_code,
    height=500
)
