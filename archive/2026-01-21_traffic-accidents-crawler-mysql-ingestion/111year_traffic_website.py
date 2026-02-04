import pandas as pd
from sqlalchemy import create_engine, text
import folium
from folium.plugins import MarkerCluster, HeatMap

# --- 設定區 ---
DB_URL = 'mysql+pymysql://root:password@localhost:3306/traffic_111_db'
engine = create_engine(DB_URL)

#### 1. 從資料庫提取資料
# 結合 Main(座標) 與 Details(篩選第一當事者)
query = """
SELECT 
    m.longitude, 
    m.latitude, 
    m.accident_location, 
    m.accident_date,
    d.accident_type_minor,
    d.vehicle_type_minor
FROM accident_main m
JOIN accident_details d ON m.accident_id = d.accident_id
WHERE d.party_sequence = 1
"""

print("正在從資料庫讀取資料...")
df = pd.read_sql(query, engine)

#### 2. 資料清洗 (過濾異常座標)
# 台灣經緯度合理範圍：經度 119~123, 緯度 21~26
df = df.dropna(subset=['longitude', 'latitude'])
df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
df = df[(df['longitude'] > 118) & (df['longitude'] < 127) & 
        (df['latitude'] > 20) & (df['latitude'] < 27)]

print(f"共計抓取 {len(df)} 筆有效事故點位。")

#### 3. 建立 Folium 地圖
# 以台灣地理中心點初始化
m = folium.Map(location=[23.6, 120.9], zoom_start=8, control_scale=True)

# 模式 A：標記聚合器 (適合查看詳細內容)
marker_cluster = MarkerCluster(name="事故詳細點位").add_to(m)

# 為了效能，若資料量極大(如>5萬筆)，建議繪製前10000筆作為範例，或改用熱點圖
sample_df = df.head(10000) 

for _, row in sample_df.iterrows():
    popup_text = f"""
    <b>日期：</b>{row['accident_date']}<br>
    <b>地點：</b>{row['accident_location']}<br>
    <b>類型：</b>{row['accident_type_minor']}<br>
    <b>車種：</b>{row['vehicle_type_minor']}
    """
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=folium.Popup(popup_text, max_width=300),
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(marker_cluster)

# 模式 B：熱點圖層 (適合觀察事故熱區)
heat_data = [[row['latitude'], row['longitude']] for _, row in df.iterrows()]
HeatMap(heat_data, name="事故熱點分布", radius=10).add_to(m)

# 加入圖層控制開關
folium.LayerControl().add_to(m)

#### 4. 匯出地圖
output_file = "taiwan_traffic_map_111.html"
m.save(output_file)
print(f"地圖已成功生成：{output_file}")