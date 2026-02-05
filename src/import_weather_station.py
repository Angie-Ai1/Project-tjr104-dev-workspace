import pandas as pd
import numpy as np
from sqlalchemy import text
from db_utils import get_db_engine

# ==========================================
# 1. 取得所有觀測站資料
# ==========================================
def get_all_stations(engine=None):
    if engine is None:
        engine = get_db_engine()
    if not engine:
        return pd.DataFrame()

    # ⚠️ 資料庫欄位有括號和空格，必須用 `反引號` 包起來
    # 用 as 將名字改短，方便後面寫程式
    query = """
    SELECT 
        Station_ID, 
        Station_name, 
        `Latitude (WGS84)` as latitude, 
        `Longitude (WGS84)` as longitude
    FROM test_db.Obs_Stations
    WHERE `Latitude (WGS84)` IS NOT NULL 
      AND `Longitude (WGS84)` IS NOT NULL
    """

    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        # 確保經緯度是浮點數類型
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        
        return df.dropna(subset=['latitude', 'longitude'])

    except Exception as e:
        print(f"[錯誤] 讀取觀測站資料失敗: {e}")
        return pd.DataFrame()

# ==========================================
# 2. 計算最近的測站
# ==========================================
def haversine_distance(lat1, lon1, lat2, lon2):
    """
    使用 Haversine 公式計算地球上兩點的距離 (單位: 公里)
    """
    R = 6371  # 地球半徑 (km)

    # 將角度轉為弧度
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c

def find_nearest_station(target_lat, target_lon):
    """
    輸入：目標地點 (夜市) 的經緯度
    輸出：距離最近的測站資訊 (Dict) 與 距離 (km)
    """
    # 1. 取得所有測站
    df_stations = get_all_stations()
    
    if df_stations.empty:
        print("找不到任何測站資料")
        return None, 0

    # 2. 計算目標點與所有測站的距離 (向量化運算)
    distances = haversine_distance(
        target_lat, target_lon,
        df_stations['latitude'].values,
        df_stations['longitude'].values
    )
    
    # 3. 找出最小距離的索引
    min_idx = np.argmin(distances)
    nearest_station = df_stations.iloc[min_idx].to_dict()
    min_dist = distances[min_idx]
    
    return nearest_station, min_dist

# ==========================================
# 測試程式
# ==========================================
if __name__ == "__main__":
    print("\n測試: 尋找最近的氣象站 ...")
    
    # 模擬：士林夜市座標
    shilin_lat = 25.0888
    shilin_lon = 121.5245
    print(f"目標地點：士林夜市 ({shilin_lat}, {shilin_lon})")

    station, dist = find_nearest_station(shilin_lat, shilin_lon)
    
    if station:
        print("-" * 30)
        print(f"找到最近測站：{station.get('Station_name')} ({station.get('Station_ID')})")
        print(f"直線距離：{dist:.2f} 公里")
        print("-" * 30)
    else:
        print("測試失敗")