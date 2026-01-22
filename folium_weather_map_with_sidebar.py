import os
import requests
import folium
import urllib3
from dotenv import load_dotenv
from folium.plugins import HeatMap

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

api_key = os.getenv("CWA_API_KEY")
url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001?Authorization={api_key}"

#### 1. 抓取資料
def get_rain_data():
    try:
        response = requests.get(url, verify=False)
        data = response.json()
        stations = data['records']['Station']
        all_data = []
        for s in stations:
            geo = s.get('GeoInfo', {})
            coords = geo.get('Coordinates', [{}])[0]
            lat = geo.get('StationLatitude') or coords.get('StationLatitude') or coords.get('CenterLat')
            lon = geo.get('StationLongitude') or coords.get('StationLongitude') or coords.get('CenterLon')
            name = s.get('StationName', '未知')
            try:
                rain = float(s.get('RainfallElement', {}).get('Now', {}).get('Precipitation', -1))
                if lat and lon and rain >= 0:
                    all_data.append({'lat': float(lat), 'lon': float(lon), 'rain': rain, 'name': name})
            except: continue
        return all_data
    except Exception as e:
        print(f"失敗: {e}"); return []

#### 2. 資料處理
rain_info = get_rain_data()
heat_points = [[d['lat'], d['lon'], d['rain']] for d in rain_info if d['rain'] > 0]
# 取得前 10 名做為側邊列表
top_10 = sorted(rain_info, key=lambda x: x['rain'], reverse=True)[:10]

#### 3. 地圖與側邊欄製作
m = folium.Map(location=[23.7, 121.0], zoom_start=8, tiles="CartoDB positron")
if heat_points:
    HeatMap(heat_points, radius=18, blur=10, min_opacity=0.4).add_to(m)

# 建立側邊列表的 HTML
list_items = "".join([f"<li><b>{s['name']}</b>: {s['rain']} mm</li>" for s in top_10 if s['rain'] > 0])
sidebar_html = f"""
<div style="position: fixed; top: 10px; 
            right: 10px; width: 200px; height: auto; 
            max-height: 80%; overflow-y: auto; z-index: 9999; background-color: rgba(255,255,255,0.9);
            border: 2px solid grey; border-radius: 6px; padding: 10px; font-size: 14px;">
    <h4 style="margin-top: 0;">🌧️ 降雨前 10 名</h4>
    <ul style="padding-left: 20px;">
        {list_items if list_items else "<li>目前無降雨資料</li>"}
    </ul>
</div>
"""
m.get_root().html.add_child(folium.Element(sidebar_html))

# 刷新按鈕
refresh_html = """
<div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999; background: white; 
            padding: 10px; border: 2px solid black; cursor: pointer; border-radius: 5px;" 
            onclick="window.location.reload();"><b>🔄 刷新數據</b></div>
"""
m.get_root().html.add_child(folium.Element(refresh_html))

#### 4. 指定資料夾儲存
output_folder = "folium_map" # 指定資料夾名稱
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

file_path = os.path.join(output_folder, "weather_map_with_sidebar.html")
m.save(file_path)
print(f"地圖已儲存至: {file_path}")