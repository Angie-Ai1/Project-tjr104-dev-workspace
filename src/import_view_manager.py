import streamlit as st
import folium
from folium.plugins import HeatMap
from sqlalchemy import text
from import_traffic import get_db_engine 

# ---------------------------------------------------------
# Helper Function
# ---------------------------------------------------------
def get_nearest_station(market_lat, market_lon, rain_info):
    if not rain_info: return None
    # Python 進階語法：min() 配合 key 和 lambda
    # 在 rain_info 裡面找一個站點 s
    # 「評判標準 (key) 是：該站點與夜市的距離平方 (歐幾里得距離)」
    # 找出距離最小的那個站點回傳
    return min(rain_info, key=lambda s: (s['lat']-market_lat)**2 + (s['lon']-market_lon)**2)

# ==========================================
# 網站介面
# ==========================================

def render_sidebar(df_market):
    """
    負責繪製側邊欄 (Sidebar) 的所有元件
    """
    st.sidebar.header("🔍 篩選導航")
    
    # 1. 系統連線狀態區塊
    # expanded=False 代表預設是收合的，點擊才會打開，節省版面
    with st.sidebar.expander("🔌 系統連線狀態", expanded=False):
        if not df_market.empty: st.success("✅ 夜市資料: 正常")
        else: st.error("夜市資料: 失敗")
        
        # 資料庫連線測試
        # 使用 try-except 是為了防止網路斷線時整個網頁當機
        try:
            engine = get_db_engine()
            if engine:
                # 執行一個最簡單的 SQL "SELECT 1" 來確認連線是活著的
                with engine.connect() as conn: conn.execute(text("SELECT 1")) 
                st.success("✅ 車禍資料: 連線成功")
            else: st.error("❌ 車禍資料: 設定錯誤")
        except: st.error("❌ 資料庫連線失敗")
    
    st.sidebar.markdown("---")

    # -----------------------------------------------------
    # Session State (狀態記憶):「每次互動都會重跑整個程式」
        # 若未將使用者的選擇存進 session_state，
        # 每次點選完，變數就會被重置，導致選單跳回第一個選項
    # -----------------------------------------------------
    
    # 初始化：如果是第一次打開網頁，預設選第一個縣市
    if 'nav_city' not in st.session_state:
        st.session_state['nav_city'] = df_market['City'].unique()[0]
    
    # 2. 級聯選單 (Cascading Selectbox) - 第一層：縣市
    city_options = list(df_market['City'].unique())
    
    # 避免 session 紀錄的城市不在目前的選單中 (例如資料換了)
    if st.session_state['nav_city'] not in city_options:
        st.session_state['nav_city'] = city_options[0]

    # Callback 函式：當使用者改變縣市時，執行此函式
    def update_city():
        st.session_state['nav_city'] = st.session_state['widget_city'] # 更新選擇
        st.session_state['nav_district'] = '全區' # 把下一層(區域)重置為全區
    
    # 找出目前選擇在清單中的位置 (index)，讓選單預設選中它
    city_idx = city_options.index(st.session_state['nav_city'])
    
    city = st.sidebar.selectbox(
        "1️⃣ 選擇縣市", city_options, index=city_idx,
        key='widget_city', on_change=update_city # 綁定 key 和 callback
    )
    
    # 3. 級聯選單 - 第二層：區域 (根據上層 city 過濾)
    dist_options = list(df_market[df_market['City'] == city]['District'].unique())
    
    # 如果切換了縣市，原本紀錄的區域可能不存在新縣市裡，所以要重置
    if 'nav_district' not in st.session_state or st.session_state['nav_district'] not in dist_options:
        st.session_state['nav_district'] = dist_options[0]
        
    def update_district():
        st.session_state['nav_district'] = st.session_state['widget_district']
        
    dist_idx = dist_options.index(st.session_state['nav_district'])
    
    district = st.sidebar.selectbox(
        "2️⃣ 選擇區域", dist_options, index=dist_idx,
        key='widget_district', on_change=update_district
    )
    
    # 4. 級聯選單 - 第三層：夜市
    if district == '全區': markets = df_market[df_market['City'] == city]
    else: markets = df_market[(df_market['City'] == city) & (df_market['District'] == district)]
    
    # 加入「全台概覽」作為特殊選項
    m_list = ["🔍 全台概覽 (預設)"] + sorted(markets['MarketName'].unique())
    
    if 'nav_market' not in st.session_state or st.session_state['nav_market'] not in m_list:
        st.session_state['nav_market'] = m_list[0]
        
    def update_market():
        st.session_state['nav_market'] = st.session_state['widget_market']
        
    market_idx = m_list.index(st.session_state['nav_market'])
    
    market_name = st.sidebar.selectbox(
        "3️⃣ 選擇夜市", m_list, index=market_idx,
        key='widget_market', on_change=update_market
    )
    
    # 5. 圖層控制區 (Checkbox)
    st.sidebar.markdown("---")
    st.sidebar.subheader("圖層控制")

    # 定義所有的圖層開關 Key
    layer_keys = ['show_weather', 'show_traffic_heat', 'show_night_market', 'show_traffic_top10']
    for key in layer_keys:
        if key not in st.session_state: st.session_state[key] = True

    # 快速全選/取消按鈕的邏輯
    def select_all():
        for key in layer_keys: st.session_state[key] = True
    def deselect_all():
        for key in layer_keys: st.session_state[key] = False

    c1, c2 = st.sidebar.columns(2)
    with c1: st.button("✅ 全選", on_click=select_all, use_container_width=True)
    with c2: st.button("⬜ 取消", on_click=deselect_all, use_container_width=True)

    # 建立一個字典來存所有開關的狀態，方便回傳
    layers = {
        "weather": st.sidebar.checkbox("顯示降雨熱力", key='show_weather'),
        "traffic_heat": st.sidebar.checkbox("顯示車禍熱區 (全台)", key='show_traffic_heat'),
        "night_market": st.sidebar.checkbox("顯示夜市位置", key='show_night_market'),
        "traffic_top10": st.sidebar.checkbox("顯示 TOP10 肇事點", key='show_traffic_top10')
    }
    
    # 判斷目前模式：全台灣/特定夜市
    is_overview = (st.session_state['nav_market'] == "🔍 全台概覽 (預設)")
    target_market = None
    if not is_overview:
        # 特定夜市: 將該筆資料抓出來 (Series 物件)
        target_market = markets[markets['MarketName'] == st.session_state['nav_market']].iloc[0]
        
    # 回傳三個關鍵資訊給主程式：1.是否概覽模式 2.目標夜市資料 3.圖層開關狀態
    return is_overview, target_market, layers

# ---------------------------------------------------------
# Folium 地圖建置
# ---------------------------------------------------------
def build_map(is_overview, target_market, layers, weather_data, traffic_global, df_top10, df_market):
    # 1. 決定地圖的初始中心點和縮放比例 (Zoom Level)
    if is_overview:
        # 概覽模式：中心點設在台灣中心 (南投附近)，縮放設 8 (可以看到全島)
        map = folium.Map(location=[23.7, 120.95], zoom_start=8, tiles="CartoDB positron")
    else:
        # 詳細模式：中心點設在夜市座標，縮放設 16 (街道等級)
        map = folium.Map(location=[target_market['lat'], target_market['lon']], zoom_start=16, tiles="CartoDB positron")

    # 2. 堆疊圖層：氣象資料
    if layers['weather']:
        heat_data, _, _, _ = weather_data
        # FeatureGroup 就像 Photoshop 的圖層，可以整組開關
        fg = folium.FeatureGroup(name="🌧️ 降雨熱力")
        if heat_data: 
            # 繪製熱力圖，radius 是擴散半徑，blur 是模糊度
            HeatMap(heat_data, radius=20, blur=25, min_opacity=0.3).add_to(fg)
        fg.add_to(map) # 把圖層貼到地圖底板上

    # 3. 堆疊圖層：全台車禍熱區
    if layers['traffic_heat']:
        _, t_heat = traffic_global # 取出 traffic_global 中的熱力圖物件
        if t_heat: t_heat.add_to(map)

    # 4. 堆疊圖層：夜市位置標記
    if layers['night_market']:
        fg_market = folium.FeatureGroup(name="🏠 夜市位置")
        if is_overview:
            # 概覽模式：以迴圈畫出全台所有夜市的小圓點
            for _, row in df_market.iterrows():
                status_html = f"""
                <div style="width:250px">
                    <h4>{row['MarketName']}</h4>
                    <hr>
                    {row['ScheduleHTML']}
                </div>
                """
                folium.CircleMarker(
                    location=[row['lat'], row['lon']], radius=5, color='purple', fill=True, fill_opacity=0.7,
                    popup=folium.Popup(status_html, max_width=300), 
                    tooltip=row['MarketName'] 
                ).add_to(fg_market)
        elif target_market is not None:
            # 詳細模式：畫出該夜市範圍(多邊形)及夜市標記
            pts = target_market.get('poly_points', [])
            if len(pts) > 1:
                folium.Polygon(pts, color="orange", weight=3, fill=True, fill_color="orange", fill_opacity=0.4).add_to(fg_market)
            
            status_html = f"""
            <div style="width:250px">
                <h3 style="color:purple">{target_market['MarketName']}</h3>
                <hr>
                {target_market['ScheduleHTML']}
            </div>
            """
            folium.Marker(
                [target_market['lat'], target_market['lon']], 
                popup=folium.Popup(status_html, max_width=350),
                icon=folium.Icon(color='purple', icon='star', prefix='fa')
            ).add_to(fg_market)
        fg_market.add_to(map)

    # 5. 堆疊圖層：周邊十大易肇事路段 (只有詳細模式才顯示)
    if not is_overview and target_market is not None:
        if layers['traffic_top10'] and not df_top10.empty:
            for _, row in df_top10.iterrows():
                # 圓圈大小 (radius) 根據事故數動態調整：事故越多，圈圈越大
                r = max(5, row['事故數']/2)
                popup_html = f"""
                <div style="width:250px">
                    <b>📍 {row['路段']}</b><br>
                    <span style="color:red; font-size:14px;">💥 事故數: {row['事故數']}</span>
                </div>
                """
                folium.CircleMarker(
                    [row['lat'], row['lon']], radius=r, color='#e74c3c', fill=True, fill_color='#c0392b', fill_opacity=0.6,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(map)
    return map

# ==========================================
# 資訊面板與互動 (Logic)
# ==========================================

def render_info_panel(is_overview, target_market, df_top10, weather_data, layers):
    """負責繪製畫面右邊的資訊欄 (Info Panel)"""
    _, rain_info, _, top_station = weather_data
    
    if is_overview:
        st.subheader("🇹🇼 全台概覽模式")
        st.info("💡點擊地圖上的紫色圓點，可直接跳轉至該夜市詳細資訊。")
        # st.metric 用來顯示醒目的關鍵數字
        location_str = f"{top_station.get('city', '')} {top_station.get('town', '')}"
        st.metric(label="🌧️ 全台最大雨量", value=f"{top_station['rain']} mm", delta=f"{location_str} - {top_station['name']}")
    else:
        st.subheader(f"📍 {target_market['MarketName']}")
        
        # 顯示營業時間 HTML 表格
        with st.expander("🕒 查看每週營業時間", expanded=True):
             st.markdown(target_market['ScheduleHTML'], unsafe_allow_html=True)
        
        st.markdown("---")
        st.write("🔥 **周邊易肇事路段 TOP 10**")
        if not df_top10.empty:
            # 顯示車禍數據表格
            st.dataframe(df_top10[['路段', '事故數']], hide_index=True, use_container_width=True, height=420)
        else:
            st.info("無肇事紀錄。")
        
        # 顯示最近氣象站雨量
        st.markdown("---")
        if layers['weather']:
            local_station = get_nearest_station(target_market['lat'], target_market['lon'], rain_info)
            if local_station:
                st.metric(f"🌧️ 最近測站 ({local_station['name']})", f"{local_station['rain']} mm")

def handle_map_interaction(map_data, df_market):
    """
    處理地圖點擊事件：
    當使用者點了地圖上的某個點，更新 session_state，讓頁面跳轉到該夜市視角
    """
    if map_data and map_data.get("last_object_clicked"):
        clicked_lat = map_data["last_object_clicked"]["lat"]
        clicked_lng = map_data["last_object_clicked"]["lng"]
        
        # 搜尋演算法：找出所有夜市中，距離點擊位置非常近 (0.0005度 ≈ 50公尺) 的候選者
        candidates = df_market[
            (abs(df_market['lat'] - clicked_lat) < 0.0005) & 
            (abs(df_market['lon'] - clicked_lng) < 0.0005)
        ]
        
        if not candidates.empty:
            target = candidates.iloc[0]
            # 如果點擊的夜市跟當前顯示的不一樣，才需要刷新頁面
            if st.session_state.get('nav_market') != target['MarketName']:
                st.session_state['nav_city'] = target['City']
                st.session_state['nav_district'] = target['District']
                st.session_state['nav_market'] = target['MarketName']
                st.rerun() # 強制 Streamlit 重新執行，更新畫面

