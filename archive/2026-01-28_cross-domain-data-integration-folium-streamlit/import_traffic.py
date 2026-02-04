import os
import pandas as pd
import folium
from sqlalchemy import create_engine, text # 用來執行參數化 SQL查詢
from folium.plugins import MarkerCluster, HeatMap
from dotenv import load_dotenv

# ==========================================
# 1. 環境設定
# ==========================================
load_dotenv()

def get_db_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[Error] 錯誤：找不到 DATABASE_URL，請檢查.env 檔案")
        return None
    try:
        # echo=False 代表不印出所有 SQL 語句 (除錯時可設為 True)
        return create_engine(db_url, echo=False)
    except Exception as e:
        print(f"[Error] 資料庫連線失敗: {e}")
        return None

def get_traffic_layers():
    """
    【全台車禍圖層產生器】
    策略：
        由於車禍資料量過大 (可能數十萬筆)，瀏覽器無法一次渲染。
        暫時先採用 'LIMIT 2000' 策略，僅取出部分資料做為「示意熱點」。
    回傳:
        1. fg_cluster (folium.FeatureGroup): 點位聚合圖層 (縮小時合併，放大時展開)。
        2. fg_heat (folium.FeatureGroup): 熱力圖層 (顯示事故密度)。
    """
    print("--- 正在呼叫 MySQL 抓取全台車禍資料 ---")
    engine = get_db_engine()
    if not engine: return None, None

    # SQL 邏輯分析：
    # 1. JOIN main 和 details 資料表取得完整資訊
    # 2. party_sequence = 1 通常代表事故的主要當事人 (避免同一場事故撈出多筆重複資料)
    # 3. LIMIT 2000 是為了前端效能做的妥協 (Trade-off)
    query = """
    SELECT 
        m.longitude, 
        m.latitude, 
        m.accident_date, 
        m.accident_location, 
        d.accident_type_minor
    FROM accident_main m
    JOIN accident_details d ON m.accident_id = d.accident_id
    WHERE d.party_sequence = 1
    LIMIT 2000 
    """

    try:
        # 使用 Pandas 直接讀取 SQL 結果
        df = pd.read_sql(query, engine) # query查詢結果會被載入到 DataFrame
        
        # --- 資料清洗 (ETL) ---
        # 移除空座標
        df = df.dropna(subset=['longitude', 'latitude']) # subset指定只檢查這兩欄

        # 強制轉型為數字，無法轉型者變為 NaN
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        
        # 地理圍欄過濾 (Geofencing)：只保留台灣範圍內的資料，排除誤植的極端值
        df = df[
            (df['longitude'] > 118) & (df['longitude'] < 127) & 
            (df['latitude'] > 20) & (df['latitude'] < 27)
        ]

        print(f"--- [System] 成功取得 {len(df)} 筆有效車禍點位，開始製圖 ---")

        # --- 製作圖層物件 ---
        # 1. 聚合圖層
        # 用途：縮小地圖時，不會看到滿滿的圖釘，而是看到數字 (如: 50)，點擊後散開。
        fg_cluster = folium.FeatureGroup(name="🚗 車禍詳細點位", show=False) # 預設關閉
        cluster = MarkerCluster().add_to(fg_cluster)

        # 迭代 DataFrame 建立圖釘
        for _, row in df.iterrows():  # df.iterrows()會回傳(index, row)二元組
            # 使用 HTML 格式化彈出視窗內容
            popup_html = f"""
            <div style="font-family: Arial; width: 150px;">
                <b>日期:</b> {row['accident_date']}<br>
                <b>類型:</b> {row['accident_type_minor']}<br>
                <b>地點:</b> {row['accident_location']}
            </div>
            """
            # font-family: Arial 是為了避免中文字體亂碼問題

            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=folium.Popup(popup_html, max_width=200),
                icon=folium.Icon(color='red', icon='exclamation-sign')
            ).add_to(cluster)

        # 2. 熱力圖層 (檢視事故密度)
        # folium HeatMap 需要用二維陣列作為輸入，格式為 [[lat, lon], [lat, lon], ...]
        # 所以用列表生成式來產生這個結構
        # gradient 設定熱力圖顏色變化 (藍 -> 綠 -> 紅)
        HeatMap(heat_data, radius=12, blur=18, 
                gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}).add_to(fg_heat)

        # folium.FeatureGroup 可以控制圖層開關
        fg_heat = folium.FeatureGroup(name="🔥 車禍熱點分析", show=False) # 預設關閉
        heat_data = [[row['latitude'], row['longitude']] for _, row in df.iterrows()]
        
        return fg_cluster, fg_heat

    except Exception as e:
        print(f"[Error] SQL 查詢或繪圖失敗: {e}")
        return None, None

# ==========================================
    """
    【周邊熱點分析】
    當使用者選擇某個地點(如夜市)時，動態查詢該地點半徑約 2km 內的「十大易肇事路段」
    參數: center_lat, center_lon: 中心點座標
          radius_km: 搜尋半徑 (預設 2km)
    回傳: pd.DataFrame (欄位: 路段, 事故數, lat, lon)
    """
def get_nearby_top10(center_lat, center_lon, radius_km=2):
    engine = get_db_engine()
    if not engine: return pd.DataFrame()

    # --- 經緯度簡易換算邏輯 ---
    # 緯度 1 度約為 111 公里
    # 0.018 度 * 111 km/度 ≈ 1.998 km (約 2km)
    # 「矩形搜尋 (Bounding Box)」比計算圓形距離 (Haversine Formula) 運算速度快非常多，適合即時查詢
    offset = radius_km / 111

    # 使用 text() 宣告 SQL，並配合:變數名稱 進行參數化查詢
    # 防止 SQL Injection 攻擊的重要防線
    sql = text("""
    SELECT 
        accident_location as 路段, 
        COUNT(*) as 事故數,
        AVG(latitude) as lat,   
        AVG(longitude) as lon   
    FROM accident_main
    WHERE latitude BETWEEN :min_lat AND :max_lat
      AND longitude BETWEEN :min_lon AND :max_lon
    GROUP BY accident_location
    ORDER BY 事故數 DESC
    LIMIT 10;
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
        # 執行查詢
        df = pd.read_sql(sql, engine, params=params)
        return df
    except Exception as e:
        print(f"[Error] 查詢附近熱點失敗: {e}")
        return pd.DataFrame()