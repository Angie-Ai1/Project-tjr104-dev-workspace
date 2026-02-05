import streamlit as st
import folium
from folium.plugins import HeatMap
from sqlalchemy import text
from import_traffic import get_db_engine 
import import_traffic as tr

# ---------------------------------------------------------
# Helper Function
# 運算函式，只負責算數學，不涉及畫圖!!
# ---------------------------------------------------------
def get_nearest_station(market_lat, market_lon, rain_info):
    # 如果氣象局 API 掛了 (rain_info 是空的)，直接回傳 None，避免程式報錯 crash
    if not rain_info: return None 
    
    # Python 進階語法：min() 配合 key 和 lambda ->「在 rain_info 裡面找一個站點 s」
    # 「評判標準 (key) 是：該站點與夜市的距離平方 (歐幾里得距離)」
    # 找出距離最小的站點回傳
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
    with st.sidebar.expander("🔌 系統連線狀態", expanded=True):
        if not df_market.empty: st.success("✅ 夜市資料: 正常")
        else: st.error("夜市資料: 失敗")
        
        # 資料庫連線測試
        # 使用 try-except 是為了防止網路斷線時整個網頁當機
        try:
            engine = get_db_engine()
            if engine:
                # 執行一個最簡單的 SQL "SELECT 1" 來確認連線是活著的
                with engine.connect() as conn: conn.execute(text("SELECT 1")) 
                st.success("車禍資料: 連線成功")
            else: st.error("車禍資料: 設定錯誤")
        except: st.error("資料庫連線失敗")
    
    st.sidebar.markdown("---")

    # -----------------------------------------------------
    # Session State (狀態記憶)
        # Streamlit 的特性是「每次互動都會重跑整個程式」。
        # 如果沒有把使用者的選擇存進 session_state，
        # 每次點選完，變數就會被重置，導致選單跳回第一個選項。
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
    # 新增了 'show_stations' 來控制觀測站圖層
    layer_keys = ['show_weather', 'show_traffic_heat', 'show_stations', 'show_night_market'] # 先移除'show_traffic_top10'
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
    # 字典中加入了 stations 的 checkbox
    layers = {
        "weather": st.sidebar.checkbox("顯示降雨熱力", key='show_weather'),
        "stations": st.sidebar.checkbox("顯示氣象觀測站", key='show_stations'), # [New] 新增這行
        "traffic_heat": st.sidebar.checkbox("顯示車禍熱區 (全台)", key='show_traffic_heat'),
        "night_market": st.sidebar.checkbox("顯示夜市位置", key='show_night_market')
      # "traffic_top10": st.sidebar.checkbox("顯示 TOP10 肇事點", key='show_traffic_top10') # 先移除'show_traffic_top10'
    }
    
    # 判斷目前模式：是看全台/特定夜市
    is_overview = (st.session_state['nav_market'] == "🔍 全台概覽 (預設)")
    target_market = None
    if not is_overview:
        # 如果選了特定夜市，把那筆資料抓出來 (Series 物件)
        target_market = markets[markets['MarketName'] == st.session_state['nav_market']].iloc[0]
        
    # 回傳三個關鍵資訊給主程式：1.是否概覽模式 2.目標夜市資料 3.圖層開關狀態
    return is_overview, target_market, layers

# ---------------------------------------------------------
# Folium 地圖建置
# 這裡是「資料視覺化」的核心，負責把數據疊加到地圖上
# ---------------------------------------------------------
def build_map(is_overview, target_market, layers, weather_data, traffic_global, df_top10, df_market, df_local_accidents=None):
    # 1. 決定地圖的初始中心點和縮放比例 (Zoom Level)
    if is_overview:
        # 概覽模式：中心點設在台灣中心 (南投附近)，縮放設 8 (可以看到全島)
        m = folium.Map(location=[23.7, 120.95], zoom_start=8, tiles="CartoDB positron")
    else:
        # 詳細模式：中心點設在夜市座標，縮放設 16 (街道等級)
        m = folium.Map(location=[target_market['lat'], target_market['lon']], zoom_start=16, tiles="CartoDB positron")

    # traffic_global 是從 import_traffic.py 回傳的那一包
    if traffic_global and len(traffic_global) == 3:
        t_cluster, t_heat, t_stations = traffic_global
    else:
        # 萬一 traffic_global 是 None 或數量不對
        t_cluster, t_heat, t_stations = None, None, None

    # 2. 堆疊圖層：氣象資料
    if layers['weather']:
        heat_data, _, _, _ = weather_data
        # FeatureGroup 就像 Photoshop 的圖層，可以整組開關
        fg = folium.FeatureGroup(name="🌧️ 降雨熱力")
        if heat_data: 
            # 繪製熱力圖，radius 是擴散半徑，blur 是模糊度
            HeatMap(heat_data, radius=20, blur=25, min_opacity=0.3).add_to(fg)
        fg.add_to(m) # 把圖層貼到地圖底板上

    # 3. 堆疊圖層：全台車禍熱區
    if layers['traffic_heat']:
        # 確認 traffic_global 是有資料的列表
        if traffic_global and isinstance(traffic_global, list):
            HeatMap(
                traffic_global, 
                radius=15,       # 格子點
                blur=10,         # 模糊度低一點，看起來比較精確
                max_zoom=10,     # 拉近地圖後(Zoom > 10) 自動隱藏熱力圖，改看詳細藍點
            ).add_to(m)


    # 堆疊圖層：氣象觀測站
    if layers['stations']:
        # 1. 從 weather_data 解包取出 rain_info (是第 2 個元素)
        # weather_data 結構: (heat_data, rain_info, raining_only, top_station)
        _, rain_info, _, _ = weather_data
        
        if rain_info:
            fg_stations = folium.FeatureGroup(name="☁️ 氣象觀測站", show=True)
            for station in rain_info:
                # 建立Popup 內容，顯示站名與即時雨量
                popup_html = f"""
                <div style="font-family: Arial; width: 150px;">
                    <b>測站:</b> {station['name']}<br>
                    <b>雨量:</b> {station['rain']} mm
                </div>
                """
                folium.Marker(
                    location=[station['lat'], station['lon']],
                    popup=folium.Popup(popup_html, max_width=200),
                    # 使用藍色雲朵圖示 (icon='cloud')
                    icon=folium.Icon(color='blue', icon='cloud', prefix='fa')
                ).add_to(fg_stations)
            
            fg_stations.add_to(m)

    # 4. 堆疊圖層：夜市位置標記
    if layers['night_market']:
        fg_market = folium.FeatureGroup(name="🏠 夜市位置")
        if is_overview:
            # 概覽模式：用迴圈畫出全台所有夜市的小圓點
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
            # 詳細模式：畫出該夜市的範圍(多邊形) + 一顆大星星
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
        fg_market.add_to(m)

    # 5. 堆疊圖層：周邊十大易肇事路段 (只有詳細模式才顯示)
    if not is_overview and target_market is not None:
        
        # 以夜市為中心, 呈現範圍(黃色圈)
        folium.Circle(
            location=[target_market['lat'], target_market['lon']],
            radius=500,
            color='orange',
            fill=True,
            fill_color='yellow',
            fill_opacity=0.1 # 設淡一點，不要擋到底圖
        ).add_to(m)

        # 2. 以夜市為中心, 呈現事故(藍色點)
        if df_local_accidents is not None and not df_local_accidents.empty:
            fg_details = folium.FeatureGroup(name="🔵 周邊事故詳情", show=True)
            for _, row in df_local_accidents.iterrows():
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=3,           # 很小一顆
                    color='blue',
                    fill=True,
                    fill_color='blue',
                    fill_opacity=0.6,
                    popup=f"位置: {row['weather_condition']}" 
                ).add_to(fg_details)
            fg_details.add_to(m)
    return m

# ==========================================
# 資訊面板與互動 (Logic)
# ==========================================

# 增加兩個參數: station_data, risk_count
def render_info_panel(is_overview, target_market, df_top10, weather_data, layers, station_data=None, risk_count=0, df_details=None):
    """負責繪製畫面右邊的資訊欄 (Info Panel)"""
    _, rain_info, _, top_station = weather_data
    
    if is_overview:
        st.subheader("🇹🇼 全台概覽模式")
        st.info("💡 點擊地圖上的夜市紫色圓點，或從左側選單選擇夜市，即可進入查看相關資訊")
        location_str = f"{top_station.get('city', '')} {top_station.get('town', '')}"
        st.metric(label="🌧️ 全台最大雨量", value=f"{top_station['rain']} mm", delta=f"{location_str} - {top_station['name']}")
    else:
        st.subheader(f"📍 {target_market['MarketName']}")
        
        # --- 1. 營業時間 ---
        with st.expander("🕒 查看每週營業時間", expanded=True):
             st.markdown(target_market['ScheduleHTML'], unsafe_allow_html=True)
        
        # --- 2. [新增] 進階分析儀表板 ---
        st.markdown("### 📊 風險與環境分析")
        
        # 使用 columns 讓排版更整齊 (左右兩欄)
        col1, col2 = st.columns(2)
        
        with col1:
            # 顯示事故風險
            risk_label = "高風險" if risk_count > 3000 else "中風險" if risk_count > 1000 else "一般"
            st.metric(
                label="⚠️ 1km內事故總數", 
                value=f"{risk_count:,}", 
                delta=risk_label,
                delta_color="inverse" )        
        with col2:
            # 顯示最近測站
            if station_data:
                info, dist = station_data
                st.metric(
                    label="📡 最近氣象站", 
                    value=info['Station_name'], 
                    delta=f"{dist:.2f} km")
            else:
                st.metric(label="📡 最近氣象站", value="N/A")

        # --- 3. 歷年分佈統計表格 ---
        st.markdown("###### 📊 歷年事故時段與傷亡統計 (500m內)")
        if df_details is not None and not df_details.empty:
            try:
                if 'accident_year' in df_details.columns:
                    # 1. 定義時段分類 (加上編號方便排序: 01_晚上, 02_早上...)
                    def get_period(h):
                        if 6 <= h < 12: return "01_早上" # 06:00~11:59
                        elif 12 <= h < 18: return "02_下午" # 12:00~17:59
                        else: return "03_晚上" # 18:00~05:59

                    df_details['時段'] = df_details['accident_hour'].apply(get_period)
                    
                    # 2. 統計聚合：依年份和時段，計算死傷總數
                    summary = df_details.groupby([
                        'accident_year', '時段']).agg({
                        'death_count': 'sum', 
                        'injury_count': 'sum'
                    }).reset_index()

                    # 3. 格式化顯示內容 (將數字轉為字串： 0💀 12🚑)
                    # 💀 = 死亡, 🚑 = 受傷
                    summary['數據'] = summary.apply(
                        lambda x: f"死亡數: {x['death_count']} / 受傷數: {x['injury_count']}", axis=1
                    )

                    # 4. 樞紐分析 (Pivot)：讓時段變橫向
                    # Index=年份, Columns=時段, Values=數據字串
                    pivot_table = summary.pivot(index='accident_year', columns='時段', values='數據')
                    
                    # 5. 美化欄位名稱 (把排序用的 01_, 02_ 去掉)
                    pivot_table.columns = [c.split('_')[1] for c in pivot_table.columns]
                    
                    # 6. 填補空值 (如果某年某時段沒資料，顯示 - )
                    pivot_table = pivot_table.fillna("-")
                    
                    # 7. 排序 (年份由大到小)
                    pivot_table = pivot_table.sort_index(ascending=False)

                    # 顯示表格
                    st.dataframe(pivot_table, use_container_width=True)
                    st.caption("註: 💀死亡數  🚑受傷數")

                else:
                    st.warning("⚠️ 無法顯示統計：缺少 'accident_year' 欄位")
            except Exception as e:
                st.error(f"統計失敗: {e}")
        else:
            st.caption("無詳細統計資料")

        st.markdown("---")
        st.write("🔥 **周邊易肇事路段 TOP 10**")
        with st.expander("點擊展開列表", expanded=False):
            if not df_top10.empty:
                st.dataframe(df_top10[['路段', '事故數']], hide_index=True, use_container_width=True)
            else:
                st.info("此區域無足夠事故數據。")

def handle_map_interaction(map_data, df_market):
    """
    處理地圖點擊事件：
    當使用者點了地圖上某個點，如果是點到了某夜市，就更新 session_state，讓頁面跳轉到該夜市詳細視角。
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