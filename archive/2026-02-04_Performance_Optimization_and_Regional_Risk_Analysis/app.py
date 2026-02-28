import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import import_weather
# from streamlit_folium import folium_static

# --- 引入模組 ---
import import_night_market as nm
import import_traffic as tr
import import_view_manager as vm
import import_weather_station as wx 

df_local_accidents = pd.DataFrame()
# ---------------------------------------------------------
# 1. 載入資料 (Data Loading)
# ---------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_taiwan_heatmap():
    return tr.get_taiwan_heatmap_data()

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_local_accidents(lat, lon, radius):
    return tr.get_nearby_accidents_data(lat, lon, radius)

# 定義 load_data (完全使用你貼的那段新程式碼)
@st.cache_data(ttl=3600)
def load_data():
    # 1. 載入夜市資料
    df_market = nm.get_all_nightmarkets()
    
    # 2. 載入全台熱力圖數據 (直接用快取函式取代舊的 traffic_global)
    # 這樣 traffic_global 就會變成「全台格網數據」，而且只有 4 個回傳值
    traffic_global = get_cached_taiwan_heatmap() 
    
    # 3. 載入天氣資料
    weather_data = import_weather.fetch_weather_data()
    
    # 4. 載入 Top 10 (預設空值)
    df_top10 = pd.DataFrame()

    # 🔥 確認這裡只回傳 4 個變數，跟 main() 裡面的接收端一致！
    return df_market, traffic_global, weather_data, df_top10

# ---------------------------------------------------------
# 2. 主程式邏輯 (Main)
# ---------------------------------------------------------
def main():
    st.set_page_config(layout="wide", page_title="台灣夜市風險地圖")
    
    # 讀取資料
    df_market, traffic_global, weather_data, _ = load_data()
    
    # --- [A] 側邊欄渲染 (Sidebar) ---
    is_overview, target_market, layers = vm.render_sidebar(df_market)
    
    # 預設變數 (先給空值，避免後面報錯)
    df_top10 = pd.DataFrame()
    nearest_station_info = None  # 準備傳給右邊的變數
    risk_count = 0               # 準備傳給右邊的變數
    df_local_accidents = pd.DataFrame() 
    

    if not is_overview and target_market is not None:
        # 1. 搜尋最近測站
        nearest_station_info = wx.find_nearest_station(target_market['lat'], target_market['lon'])
        
        # 2. 計算 1km 內事故風險
        risk_count = tr.get_zone_stats(target_market['lat'], target_market['lon'], radius_km=1.0)
        
        # 3. 更新 Top 10
        df_top10 = tr.get_nearby_top10(target_market['lat'], target_market['lon'])
        
        # 4. 呼叫後端抓 500m 內的事故點
        df_local_accidents = tr.get_nearby_accidents_data(
            target_market['lat'], 
            target_market['lon'], 
            radius_km=0.5
        )
        # 🟢5. 呼叫有快取的函式
        df_local_accidents = get_cached_local_accidents(target_market['lat'], target_market['lon'], 0.5)


    # --- [B] 地圖渲染 (Map) ---
    st.markdown("<h1 style='text-align: center;'>台灣夜市與交通事故風險地圖</h1>", unsafe_allow_html=True)
    # 建立左右兩欄 (比例 7:3)
    # col_map (左邊 70%): 放地圖
    # col_info (右邊 30%): 放分析數據
    col_map, col_info = st.columns([7, 3])

    with col_map:
        # 1. 左欄：呼叫 View Manager
        m = vm.build_map(
            is_overview, target_market, layers, weather_data, 
            traffic_global, df_top10, df_market,df_local_accidents)
        
        if m:
            # 加上 use_container_width=True，讓地圖自動縮放填滿左欄
            # 動態決定要不要回傳點擊事件
            # 如果是「概覽模式」，要監聽點擊 (為了跳轉夜市) --> ["last_object_clicked"]
            # 如果是「詳細模式」，不監聽任何東西 (純瀏覽) --> []
            objects_to_return = ["last_object_clicked"] if is_overview else []
            
            # 顯示地圖
            map_data = st_folium(
                m, 
                height=850, 
                use_container_width=True, 
                returned_objects=objects_to_return) # 這裡傳入變數
            # 只有在有 map_data 的時候才去處理互動
            if is_overview:
                vm.handle_map_interaction(map_data, df_market)

    with col_info:
        # 2. 右欄：顯示資訊面板
        # 只要縮排在這個 with 底下，所有 st.write 都會自動跑到右邊
        vm.render_info_panel(
            is_overview, 
            target_market, 
            df_top10, 
            weather_data, 
            layers,
            nearest_station_info, 
            risk_count,
            df_local_accidents
            )

if __name__ == "__main__":
    main()