import streamlit as st
import pandas as pd
from streamlit_folium import st_folium

# ==========================================
# 架構區塊：模組匯入
# 1. 後端模組: 負責跟資料庫和 API 拿資料
# 2. 視圖模組: 負責管畫面怎麼畫
# ==========================================
# --- 匯入後端模組 ---
from import_weather import fetch_weather_data
from import_traffic import get_traffic_layers, get_nearby_top10
from import_night_market import load_clean_market_df 

# --- 匯入視圖模組 ---
from import_view_manager import render_sidebar, build_map, render_info_panel, handle_map_interaction

# ==========================================
# 1.全域設定與快取機制 (@st.cache_data / @st.cache_resource)
# ==========================================

# 設定網頁標題與預設寬度 (layout="wide" 讓地圖可以橫向展開)
st.set_page_config(layout="wide", page_title="夜市交通決策系統")

# ------------------------------------------
# 主程式傳入路徑
# Streamlit 檢查這個路徑對應的資料有沒有讀過
# 如果讀過，直接回傳記憶體裡的結果；如果沒讀過，才去import處理
# ------------------------------------------
# @st.cache_data
# 用途：適用於「數據型」資料 (DataFrame, List, JSON)
# 原理：如果 CSV 沒變，就不會重新讀取，直接從記憶體拿，速度變快 10 倍
@st.cache_data
def load_market_data(csv_path):
    return load_clean_market_df(csv_path)

@st.cache_data
def get_weather(): return fetch_weather_data()

# 這裡快取了「特定座標」的查詢結果，避免來回切換夜市時一直回資料庫呼叫
@st.cache_data
def get_cached_top10(lat, lon): return get_nearby_top10(lat, lon)

# @st.cache_resource
# 用途：適用於「物件型/連線型」資料 (Database Engine, ML Model, Folium Map)。
# 區別：Folium 的圖層物件很複雜，無法被序列化(Pickle)，所以要用 cache_resource。
@st.cache_resource
def get_global_traffic(): return get_traffic_layers()

# ==========================================
# 2. 主程式 main()
# ==========================================

def main():
    # 1. 顯示大標題
    st.markdown("<h1 style='text-align: center;'>全台夜市交通與天氣綜合決策系統</h1>", unsafe_allow_html=True)
    
    # 2. 資料載入階段
    # 程式一啟動，先把所有需要的資料一一載入
    df_market = load_market_data('night_market_data.csv')
    weather_data = get_weather()
    traffic_global = get_global_traffic()
    
    # 防呆：如果 CSV 讀不到，直接停止執行，避免後面報錯
    if df_market.empty: st.stop()

    # 3. 互動階段
    # 呼叫 view_manager 畫出側邊欄，並接收使用者的結果 (target_market)
    is_overview, target_market, layers = render_sidebar(df_market)
    
    # 4. 運算階段
    # 只有在「非全台概覽」時，才去資料庫查詢周邊肇事熱點 (節省資源)
    df_top10 = pd.DataFrame()
    if not is_overview: # 從側邊欄選了某個夜市
        with st.spinner('分析周邊肇事熱點...'): # 顯示轉圈圈特效
            df_top10 = get_cached_top10(target_market['lat'], target_market['lon'])

    # 5. 製圖階段
    # 把所有準備好的資料 (資料庫數據 + 使用者選項) 全部放進去，產生一張地圖物件
    m = build_map(is_overview, target_market, layers, weather_data, traffic_global, df_top10, df_market)
  
    # 6. 網頁排版階段
    col1, col2 = st.columns([5, 1.5])     # 切割畫面：左邊佔 5 份 (地圖)，右邊佔 1.5 份 (資訊欄)
    
    # 給 Key 加上夜市名稱，確保每次切換夜市時，Key 都會改變
    # 強制瀏覽器毀掉舊地圖，重新畫一張新的，避免 "already initialized" 錯誤(網頁檢視器 Console 會看到)
    with col1: # 左邊放地圖
        # 給一個會隨夜市名稱變動的 key，強制瀏覽器重啟地圖容器
        map_key = f"map_render_{st.session_state.get('nav_market', 'default')}"
        map_data = st_folium(
            m,                         # 地圖物件 (在 5. build_map 裡面產生的)
            key="main_map",            # 強制重新初始化
            width=1200,                # 固定寬度
            height=800, 
            returned_objects=["last_object_clicked"]
    )
        
    with col2: # 右邊放資訊欄 
        render_info_panel(is_overview, target_market, df_top10, weather_data, layers)

if __name__ == "__main__":
    main()