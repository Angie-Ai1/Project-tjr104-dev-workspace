import os
import requests
import urllib3 
from dotenv import load_dotenv

# ==========================================
# 在模組內載入環境變數，確保能讀到 API Key
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_weather_data():
    """
    獨立的氣象抓取模組
    回傳: heat_data, rain_info, raining_only, top_station
    """
    print("--- 正在呼叫氣象局 API ---")
    api_key = os.getenv("CWA_API_KEY")
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001?Authorization={api_key}"

    # ==========================================
    # 初始化回傳資料結構
    # ==========================================
    heat_data, rain_info, raining_only = [], [], []
    top_station = {"name": "計算中", "rain": 0}

    try:
        # 呼叫氣象局 API
        response = requests.get(url, verify=False, timeout=10)  # 關閉 SSL 驗證
        data = response.json()                                  # 解析 JSON 回應
        stations = data.get('records', {}).get('Station', [])   # 取得氣象站列表
        
        for station in stations: 
            # 取得站點狀態\
            status = station.get('StationState', '1') 
            
            # 如果狀態不是正常，就跳過
            if status != '1' and status != '正常': continue
            
            geo = station.get('GeoInfo', {})  # 取得地理資訊
            lat = geo.get('StationLatitude') or geo.get('Coordinates', [{}])[0].get('StationLatitude')   # 取得緯度
            lon = geo.get('StationLongitude') or geo.get('Coordinates', [{}])[0].get('StationLongitude') # 取得經度
            
            try:
                # 從 station 抓取雨量
                rain = float(station.get('RainfallElement', {}).get('Now', {}).get('Precipitation', -1))
                
                # 合理範圍檢查, rain 必須在 0 到 1500 之間
                if lat and lon and 0 <= rain < 1500:
                    lat, lon = float(lat), float(lon)
                    # 從 station 抓取站名
                    station_data = {'lat': lat, 'lon': lon, 'name': station.get('StationName'), 'rain': rain}
                    
                    rain_info.append(station_data)
                    
                    if rain > 0:
                        heat_data.append([lat, lon, rain])
                        raining_only.append(station_data)
                        if rain > top_station['rain']:
                            top_station = {"name": station.get('StationName'), "rain": rain}
            except:
                continue
                
        print(f"--- 氣象資料抓取完成 (共 {len(stations)} 站) ---")
        return heat_data, rain_info, raining_only, top_station

    except Exception as e:
        print(f"氣象模組錯誤: {e}")
        return [], [], [], top_station