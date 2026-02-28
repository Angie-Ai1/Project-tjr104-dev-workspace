"""
資料來源說明:
- 資料來源：從 本機 MySQL資料庫 遷移至 Cloud SQL (test_db.accident_main)
- 連線方式：透過 SSH Tunnel (使用 db_utils 模組)
"""

import pandas as pd
import folium
from sqlalchemy import text
from folium.plugins import MarkerCluster, HeatMap
import import_weather_station as wx # 事故模組需要用到氣象站資料

# [新程式碼 - 2026-02 新增]
# 引入統一的連線工具 (會自動處理 SSH Tunnel)
from db_utils import get_db_engine 

# [舊程式碼 - 已停用]
# 原本的連線方式 (直接讀取 .env)
# from dotenv import load_dotenv
# load_dotenv()
# def get_db_engine(): ... (舊版連線函式已移除)


# ==========================================
# 1. 全台車禍圖層 
# ==========================================

def get_traffic_layers():
    """
    - 資料來源：已遷移至 Cloud SQL 資料表 `test_db.accident_main`。
    - 欄位變更 (Schema Change): 
        1. 原本的 `accident_date` (int) 僅有日期, 改用 `accident_datetime` (datetime) 以取得完整時間。
        2. 原本的 `accident_location` 因未顯示, 暫時改用 `weather_condition` (天氣) 作為替代顯示。
    - 函式回傳: 產生三個圖層
    1. 車禍點位 (Cluster)
    2. 車禍熱力圖 (Heatmap)
    3. 氣象觀測站 (Stations) [新增]
    """
    print("--- 正在呼叫 MySQL 抓取全台車禍資料 (via SSH Tunnel) ---")
    
    # [新連線方式]
    engine = get_db_engine()
    if not engine:
        return None, None, None 

    # [舊資料讀取邏輯 - 已取代]
    # query = "SELECT * FROM accident_main WHERE ..."
    # df = pd.read_csv('accident_data.csv')

    # [新資料讀取邏輯]
    # 根據Cloud SQL資料庫欄位進行調整
    query = """
    SELECT 
        m.longitude, 
        m.latitude, 
        m.accident_datetime,  -- [修改] 改用 index 8 的完整時間格式
        m.weather_condition,  -- [修改] 改用 index 11 (暫時替代地點)
        m.accident_id
    FROM test_db.accident_main m
    WHERE m.longitude IS NOT NULL 
      AND m.latitude IS NOT NULL
    LIMIT 2000
    """

    # 🟢 [新增] 抓取測站資料
    print("--- [系統] 讀取氣象觀測站資料 ---")
    df_stations = wx.get_all_stations(engine=engine) # 傳入已建立的 engine 以共用連線

    try:
        # 使用 Pandas 讀取
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        # --- 資料清洗 (ETL) ---
        df = df.dropna(subset=['longitude', 'latitude']) # 移除空座標
        
        #   確保經緯度為數值型態
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        
        # 地理圍欄過濾 (Geofencing)：只保留台灣範圍內的資料, 排除誤植的極端值
        df = df[
            (df['longitude'] > 118) & (df['longitude'] < 127) & 
            (df['latitude'] > 20) & (df['latitude'] < 27)
        ]

        print(f"--- [系統] 成功從 accident_main 取得 {len(df)} 筆資料 ---")

        # --- 製作圖層 ---
        # 1. 聚合圖層 
        # 運用 Folium 的 MarkerCluster 功能, 可以自動將密集點位聚合
        # 用途：縮小地圖時, 不會看到滿滿的圖釘, 而是看到數字 (如: 50), 點擊後散開。
        fg_cluster = folium.FeatureGroup(name="🚗 車禍詳細點位", show=False)
        cluster = MarkerCluster().add_to(fg_cluster)

        for _, row in df.iterrows():
            # [遷移註記] 欄位顯示邏輯更新
            # 舊版: date_str = str(row['accident_date'])
            # 新版: 使用 accident_datetime
            time_str = str(row['accident_datetime'])
            
            # 舊版: loc_str = str(row['accident_location'])
            # 新版: 使用 weather_condition 代替
            info_str = str(row['weather_condition'])
            
            popup_html = f"""
            <div style="font-family: Arial; width: 150px;">
                <b>時間:</b> {time_str}<br>
                <b>狀況:</b> {info_str}
            </div>
            """
            
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=200),
                icon=folium.Icon(color='red', icon='exclamation-sign')
            ).add_to(cluster)

        # 2. 熱力圖層 (Heatmap)
        fg_heat = folium.FeatureGroup(name="🔥 車禍熱點分析", show=False)
        heat_data = [[row['latitude'], row['longitude']] for _, row in df.iterrows()]
        
        if heat_data:
            HeatMap(heat_data, radius=12, blur=18, 
                    gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}).add_to(fg_heat)

        # 3. 氣象觀測站圖層 [新增]
        fg_stations = folium.FeatureGroup(name="☁️ 氣象觀測站", show=True) # 預設開啟
        if not df_stations.empty:
            for _, row in df_stations.iterrows():
                # 建立彈出視窗內容
                station_popup = f"""
                <div style="width:150px; font-family:Arial;">
                    <b>測站:</b> {row['Station_name']}<br>
                    <b>ID:</b> {row['Station_ID']}<br>
                    <small>({row['latitude']:.3f}, {row['longitude']:.3f})</small>
                </div>
                """
                folium.Marker(
                    location=[row['latitude'], row['longitude']],
                    popup=folium.Popup(station_popup, max_width=200),
                    # 使用藍色雲朵圖示來區分
                    icon=folium.Icon(color='blue', icon='cloud', prefix='fa')
                ).add_to(fg_stations)
            print(f"--- [系統] 已繪製 {len(df_stations)} 個觀測站 ---")


        return fg_cluster, fg_heat, fg_stations

    except Exception as e:
        print(f"[錯誤] SQL 查詢或繪圖失敗: {e}")
        return None, None, None

# ==========================================
# 2. [新功能] 區域統計分析 (Zone Statistics)
# ==========================================
def get_zone_stats(center_lat, center_lon, radius_km=1.0):
    """
    【新功能】計算指定半徑範圍內的車禍總數
    改用 pd.read_sql 以確保參數傳遞的穩定性。
    """
    engine = get_db_engine()
    if not engine: return 0

    # 1度約等於 111km
    offset = radius_km / 111.0

    # SQL: 只計算總數
    sql = text("""
    SELECT COUNT(*) as total_accidents
    FROM test_db.accident_main
    WHERE latitude BETWEEN :min_lat AND :max_lat
      AND longitude BETWEEN :min_lon AND :max_lon
    """)
    
    params = {
        "min_lat": center_lat - offset, "max_lat": center_lat + offset,
        "min_lon": center_lon - offset, "max_lon": center_lon + offset
    }

    try:
        with engine.connect() as conn:
            # 改用 pandas 讀取，避開 SQLAlchemy 底層 execute 的版本相容性問題
            df = pd.read_sql(sql, conn, params=params)
            
            # 取出第一列的 total_accidents 欄位
            if not df.empty:
                return int(df.iloc[0]['total_accidents'])
            return 0
            
    except Exception as e:
        print(f"[錯誤] 統計區域車禍失敗: {e}")
        return 0
    
# ==========================================
# 3. 周邊熱點排行 (Top 10 Breakdown)
# ==========================================

def get_nearby_top10(center_lat, center_lon, radius_km=1.0):
    """
    查詢範圍內的車禍分類排行
    """
    engine = get_db_engine()
    if not engine: return pd.DataFrame()

    offset = radius_km / 111.0

    # [已取代]
    # 原本是 Group By 路段 (accident_location)
    # sql_old = "SELECT accident_location, COUNT(*) ... GROUP BY accident_location"

    # [新邏輯]
    # 因為截圖中暫時沒看到 accident_location, 改為 Group By 天氣狀況 (weather_condition)

    # 改抓「最近發生的 10 筆事故」或是「特定地點」，這裡先抓具體的事故點
    # 為了配合 View Manager，我們必須 `AS` 成它看得懂的名字：
    # 1. latitude -> lat
    # 2. longitude -> lon
    # 3. weather_condition (或其他欄位) -> 路段 (暫時替代，讓畫面有東西)
    
    sql = text("""
    SELECT 
        latitude as lat,
        longitude as lon,
        weather_condition as 路段,  -- 暫時用天氣當作路段顯示 (因為目前資料庫可能沒路段欄位)
        1 as 事故數                 -- 每筆算 1 次
    FROM test_db.accident_main
    WHERE latitude BETWEEN :min_lat AND :max_lat
      AND longitude BETWEEN :min_lon AND :max_lon
    LIMIT 10
    """)

     # 定義查詢邊界 params是安全網，確保要查詢的「數值」能精確地填入 SQL 的「空位」中
    # min_lat, max_lat, min_lon, max_lon 分別代表查詢矩形的四個邊界 (台灣範圍內)   
    params = {
        "min_lat": center_lat - offset, # 緯度往南減少
        "max_lat": center_lat + offset, # 緯度往北增加
        "min_lon": center_lon - offset, # 經度往西減少
        "max_lon": center_lon + offset  # 經度往東增加
    }

    try:
        with engine.connect() as conn:
            return pd.read_sql(sql, conn, params=params)
    except Exception as e:
        print(f"[錯誤] 查詢附近熱點失敗: {e}")
        return pd.DataFrame()



# ==========================================
# 4. 測試程式
# ==========================================
if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    print("\n 測試開始...")

    # 模擬士林夜市座標
    shilin_lat, shilin_lon = 25.088, 121.524

    # 測試 1: 產生全台圖層
    print("\n[測試 1] 產生全台圖層 ...")
    c, h, s = get_traffic_layers() # C是聚合圖層, H是熱力圖層, S是氣象站圖層
    if c and h:
        print("✅ 成功取得 Folium 圖層物件！")
    else:
        print("❌ 取得圖層失敗")
        
    print("-" * 30)
    
    # 測試 2: 區域統計 (新功能)
    print(f"\n[測試 2] 計算士林夜市方圓 1km 內的車禍總數...")
    total_1km = get_zone_stats(shilin_lat, shilin_lon, radius_km=1.0)
    print(f"結果: {total_1km} 起事故")

    print(f"\n[測試 2-2] 計算士林夜市方圓 0.5km (500m) 內的車禍總數...")
    total_500m = get_zone_stats(shilin_lat, shilin_lon, radius_km=0.5)
    print(f"結果: {total_500m} 起事故")

    # 測試 3: 分類排行
    print(f"\n[測試 3] 查詢事故分類排行 (1km)...")
    df_test = get_nearby_top10(shilin_lat, shilin_lon, radius_km=1.0)
    
    if not df_test.empty:
        print("查詢成功！統計結果前 5 筆：")
        print(df_test.head())
    else:
        print("查詢無結果")

    # 測試4 : 產生3個圖層
    layers = get_traffic_layers()
    if layers[0] and layers[1] and layers[2]:
        print("✅ 成功取得 3 個圖層 (聚合、熱力、觀測站)！")
    else:
        print("❌ 取得圖層失敗")

# ====================================================================
# import_traffic.py (請貼在檔案最下面，取代原本錯誤的那段)

# ==========================================
# 5. 全台概覽優化 (Grid Aggregation)
# ==========================================
def get_taiwan_heatmap_data():
    """
    [針對全台概覽的優化]
    不抓取 150 萬筆明細，而是讓資料庫幫我們「算好」每個格子的車禍數量。
    使用 ROUND(lat, 2) 大約是 1.1km 的方格。
    """
    engine = get_db_engine()
    if not engine: return []

    # 🟢 關鍵 SQL：拿掉 LIMIT，改用 GROUP BY
    # 這樣回傳的資料量會從 150萬筆 -> 縮減成 1~2萬個「格子」
    sql = text("""
    SELECT 
        ROUND(latitude, 2) as lat, 
        ROUND(longitude, 2) as lon, 
        COUNT(*) as count 
    FROM test_db.accident_main
    WHERE latitude BETWEEN 21 AND 26 
      AND longitude BETWEEN 119 AND 122
    GROUP BY ROUND(latitude, 2), ROUND(longitude, 2)
    """)
    
    try:
        print("--- [系統] 正在聚合全台 150 萬筆資料 (Grid Mode) ---")
        with engine.connect() as conn:
            df = pd.read_sql(sql, conn)
            
        # 轉換成 HeatMap 需要的格式 [[lat, lon, weight], ...]
        return df[['lat', 'lon', 'count']].values.tolist()
        
    except Exception as e:
        print(f"[Error] 全台聚合失敗: {e}")
        return []

# ==========================================
# 6. 單點詳細搜尋 (Local Details)
# ==========================================
def get_nearby_accidents_data(center_lat, center_lon, radius_km=0.5):
    """
    [詳細模式] 抓取指定半徑內的所有事故詳細資料
    用於：畫地圖上的藍色小點點、製作右側的統計表格
    """
    engine = get_db_engine()
    if not engine: return pd.DataFrame()

    offset = radius_km / 111.0
    
    # 🟢 針對單點的 SQL (詳細資料)
    # 必須包含 death_count, injury_count, accident_year 等欄位，統計表才畫得出來
    sql = text("""
    SELECT 
        latitude as lat,
        longitude as lon,
        weather_condition,
        accident_hour,
        accident_year,        -- 統計表需要
        death_count,          -- 統計表需要
        injury_count          -- 統計表需要
    FROM test_db.accident_main
    WHERE latitude BETWEEN :min_lat AND :max_lat
      AND longitude BETWEEN :min_lon AND :max_lon
    ORDER BY accident_datetime DESC
    LIMIT 800  -- 限制數量避免瀏覽器卡死
    """)
    
    params = {
        "min_lat": center_lat - offset, "max_lat": center_lat + offset,
        "min_lon": center_lon - offset, "max_lon": center_lon + offset
    }

    try:
        with engine.connect() as conn:
            return pd.read_sql(sql, conn, params=params)
    except Exception as e:
        print(f"[Error] 查詢詳細事故失敗: {e}")
        return pd.DataFrame()