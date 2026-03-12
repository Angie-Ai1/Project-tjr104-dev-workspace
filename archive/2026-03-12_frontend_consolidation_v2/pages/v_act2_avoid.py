from folium.plugins import HeatMap
from streamlit_folium import st_folium
from folium.features import DivIcon

import numpy as np
import random
import folium
import streamlit as st
import pandas as pd
import utils.market_tools as mt
import requests
import polyline
import core.c_data_service as ds
import core.c_ui as ui

import redis
import pickle
from core.r_cache import REDIS_POOL

# -----------------------------------------------------
# nm_df (夜市資料) - DataFrame
# -----------------------------------------------------
nm_df = ds.get_all_nightmarkets()

if 'nightmarket_name' not in nm_df.columns: nm_df['nightmarket_name'] = nm_df['MarketName']
if 'nightmarket_city' not in nm_df.columns: nm_df['nightmarket_city'] = nm_df['City']
if 'nightmarket_latitude' not in nm_df.columns: nm_df['nightmarket_latitude'] = nm_df['lat']
if 'nightmarket_longitude' not in nm_df.columns: nm_df['nightmarket_longitude'] = nm_df['lon']

nm_df['nightmarket_city'] = nm_df['nightmarket_city'].str.replace('台', '臺')

if 'District' in nm_df.columns and nm_df['District'].isin(['北部', '中部', '南部', '東部', '離島']).any():
    nm_df['Region'] = nm_df['District'] 
else:
    region_map = {
        "臺北市": "北部", "新北市": "北部", "基隆市": "北部", "桃園市": "北部", "新竹市": "北部", "新竹縣": "北部", "宜蘭縣": "北部",
        "臺中市": "中部", "苗栗縣": "中部", "彰化縣": "中部", "南投縣": "中部", "雲林縣": "中部",
        "臺南市": "南部", "高雄市": "南部", "嘉義市": "南部", "嘉義縣": "南部", "屏東縣": "南部",
        "臺東縣": "東部", "花蓮縣": "東部",
        "澎湖縣": "離島", "金門縣": "離島", "連江縣": "離島"
    }
    nm_df['Region'] = nm_df['nightmarket_city'].map(region_map).fillna("其他")

possible_admin_cols = ['Town', 'Township', 'Area', '鄉鎮市區', 'admin_district', 'AdminDistrict']
admin_col_found = False
for col in possible_admin_cols:
    if col in nm_df.columns and not nm_df[col].isin(['北部', '中部', '南部', '東部']).any():
        nm_df['AdminDistrict'] = nm_df[col]
        admin_col_found = True
        break

if not admin_col_found:
    if 'District' in nm_df.columns and not nm_df['District'].isin(['北部', '中部', '南部', '東部']).any():
        nm_df['AdminDistrict'] = nm_df['District']
    else:
        nm_df['AdminDistrict'] = "全區"

# ---------------------------------------------------------
# Act3 主頁面
# ---------------------------------------------------------
def act3_render():
    if "page_data" in st.session_state:
        st.session_state["page_data"].clear()

    # -----------------------------------------------------
    # ⭐ 完美四層過濾器 + 關鍵字搜尋：加入士林區預設
    # -----------------------------------------------------
    # st.markdown("### 📍 1. 選擇目標")
    
    # 新增：提供兩種尋找方式的切換開關
    search_mode = st.radio("尋找方式：", ["🗺️ 區域層層篩選", "🔍 直接關鍵字搜尋"], horizontal=True)
    
    def_region, def_city, def_dist, def_market = "北部", "臺北市", "士林區", "士林夜市"
    
    # 模式 A：四層下拉選單
    if search_mode == "🗺️ 區域層層篩選":
        col_r, col_c, col_d, col_m = st.columns(4)
        with col_r:
            regions = sorted(nm_df["Region"].unique())
            def_r_idx = regions.index(def_region) if def_region in regions else 0
            selected_region = st.selectbox("選擇區域", regions, index=def_r_idx)
            
        with col_c:
            cities = sorted(nm_df[nm_df["Region"] == selected_region]["nightmarket_city"].unique())
            def_c_idx = cities.index(def_city) if (selected_region == def_region and def_city in cities) else 0
            selected_city = st.selectbox("選擇縣市", cities, index=def_c_idx)
            
        with col_d:
            dists = sorted(nm_df[(nm_df["Region"] == selected_region) & (nm_df["nightmarket_city"] == selected_city)]["AdminDistrict"].unique())
            def_d_idx = dists.index(def_dist) if (selected_city == def_city and def_dist in dists) else 0
            selected_dist = st.selectbox("選擇行政區", dists, index=def_d_idx)
            
        with col_m:
            markets = sorted(nm_df[(nm_df["Region"] == selected_region) & (nm_df["nightmarket_city"] == selected_city) & (nm_df["AdminDistrict"] == selected_dist)]["nightmarket_name"].unique())
            if not markets:
                st.warning("此區域無夜市")
                return
            def_m_idx = markets.index(def_market) if (selected_dist == def_dist and def_market in markets) else 0
            selected_market = st.selectbox("選擇夜市", markets, index=def_m_idx)
            
    # 模式 B：全台夜市關鍵字直搜
    else:
        all_markets = sorted(nm_df["nightmarket_name"].unique())
        global_def_idx = all_markets.index(def_market) if def_market in all_markets else 0
        # Streamlit 的 selectbox 本身點擊後就可以直接打字搜尋
        selected_market = st.selectbox("請輸入或選擇夜市名稱：", all_markets, index=global_def_idx, help="點擊展開後，可直接打字輸入關鍵字來尋找夜市")

    # -----------------------------------------------------
    # 依照選擇的夜市取得資料
    # -----------------------------------------------------
    nm_match = nm_df[nm_df["nightmarket_name"] == selected_market]
    if nm_match.empty:
        st.error(f"找不到夜市：{selected_market}，請重新選擇。")
        return
    nm_row = nm_match.iloc[0]

    try:
        r = redis.Redis(connection_pool=REDIS_POOL)
        cache_key = f"traffic:nearby_v12:{nm_row['lat']:.4f}_{nm_row['lon']:.4f}_3.0_all_sample"
        raw_data = r.get(cache_key)
        
        if raw_data:
            result = pickle.loads(raw_data)
            df_cache = pd.DataFrame()
            if isinstance(result, tuple) and len(result) >= 1:
                df_cache = result[0]
            elif isinstance(result, pd.DataFrame):
                df_cache = result
                
            date_filtered_df = df_cache.copy()
            if not date_filtered_df.empty:
                date_filtered_df["accident_hour"] = date_filtered_df["Hour"]
                if "risk_score" not in date_filtered_df.columns:
                    date_filtered_df["risk_score"] = date_filtered_df["death_count"] * 3 + date_filtered_df["injury_count"]
        else:
            date_filtered_df = pd.DataFrame()
    except Exception as e:
        st.error(f"Redis 讀取失敗: {e}")
        date_filtered_df = pd.DataFrame()

    if date_filtered_df.empty:
        st.warning("⚠️ 該夜市周邊暫無快取事故資料")
        return

    north = nm_row.get("nightmarket_northeast_latitude", nm_row['lat'] + 0.005)
    south = nm_row.get("nightmarket_southwest_latitude", nm_row['lat'] - 0.005)
    east = nm_row.get("nightmarket_northeast_longitude", nm_row['lon'] + 0.005)
    west = nm_row.get("nightmarket_southwest_longitude", nm_row['lon'] - 0.005)

    grid_size = 3
    lat_bins = np.linspace(south, north, grid_size + 1)
    lon_bins = np.linspace(west, east, grid_size + 1)

    date_filtered_df["lat_bin"] = pd.cut(date_filtered_df["latitude"], bins=lat_bins, labels=False, include_lowest=True)
    date_filtered_df["lon_bin"] = pd.cut(date_filtered_df["longitude"], bins=lon_bins, labels=False, include_lowest=True)

    grid_list = []
    for i in range(grid_size):
        for j in range(grid_size):
            cell = date_filtered_df[(date_filtered_df["lat_bin"] == i) & (date_filtered_df["lon_bin"] == j)]
            score = cell["risk_score"].sum()

            if score >= 6: color = "red"
            elif score >= 3: color = "yellow"
            else: color = "green"

            grid_list.append({
                "grid_row": i, "grid_col": j, "score": score,
                "color": color, "accident_count": len(cell)
            })

    grid_df = pd.DataFrame(grid_list)

    accidents_inside_strict = date_filtered_df[
        (date_filtered_df["latitude"]  >= south) &
        (date_filtered_df["latitude"]  <= north) &
        (date_filtered_df["longitude"] >= west) &
        (date_filtered_df["longitude"] <= east)
    ]

    accidents_for_entry = accidents_inside_strict.copy()
    if len(accidents_for_entry) == 0:
        accidents_for_entry = date_filtered_df.copy()

    north_mid = [north, (west + east) / 2]
    south_mid = [south, (west + east) / 2]
    east_mid  = [(south + north) / 2, east]
    west_mid  = [(south + north) / 2, west]

    candidates = {
        "北側出口": north_mid, "南側出口": south_mid, "東側出口": east_mid, "西側出口": west_mid,
        "東北角出口": [north, east], "西北角出口": [north, west], "東南角出口": [south, east], "西南角出口": [south, west],
    }

    def min_dist_to_accident(point):
        return min([
            np.sqrt((point[0] - lat)**2 + (point[1] - lon)**2)
            for lat, lon in accidents_for_entry[["latitude", "longitude"]].values
        ])

    best_exit = max(candidates.items(), key=lambda x: min_dist_to_accident(x[1]))
    exit_name, exit_point = best_exit

    insight_text = mt.generate_insight_V3( selected_market, grid_df, best_exit )
    icons = ["⚠️", "🚨", "❗"]
    icon = random.choice(icons)

    # =========================================================
    # 🌟 上半部：觀光客實用基礎包與安全提醒
    # =========================================================
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"## 🚶‍♂️ {selected_market} 安心導航指南")
    
    rating = nm_row.get('nightmarket_rating', '4.0')
    st.markdown(f"**⭐ Google 評分**：{rating} 顆星 &nbsp;|&nbsp; 📍 [點擊開啟 Google Maps 導航](https://www.google.com/maps/search/?api=1&query={nm_row['nightmarket_latitude']},{nm_row['nightmarket_longitude']})")
    st.info("💡 建議交通方式：為了您的安全，建議搭乘大眾運輸，或將車輛停放在周邊 500 公尺外的停車場再步行前往，避開人車交織熱區。")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### ⭐ 行人安全提醒")

    def compute_safety_stats(nm_row, strict_df):
        df = strict_df 
        if df.empty:
            return {"peak_period": "無事故資料", "rain_increase": 0, "danger_zone": "無資料", "best_entry": None}

        peak_hour = df["accident_hour"].value_counts().idxmax()
        peak_period = "20–22 時" if 20 <= peak_hour <= 22 else f"{peak_hour}:00 時段"

        rain_count = df[df["weather_condition"].fillna("").str.contains("雨")].shape[0]
        rain_ratio = round((rain_count / len(df)) * 100)

        center_lat, center_lon = nm_row["nightmarket_latitude"], nm_row["nightmarket_longitude"]
        zone_map = {
            "北側": df[df["latitude"] > center_lat].shape[0], "南側": df[df["latitude"] < center_lat].shape[0],
            "東側": df[df["longitude"] > center_lon].shape[0], "西側": df[df["longitude"] < center_lon].shape[0],
            "東北側": df[(df["latitude"] > center_lat) & (df["longitude"] > center_lon)].shape[0],
            "西北側": df[(df["latitude"] > center_lat) & (df["longitude"] < center_lon)].shape[0],
            "東南側": df[(df["latitude"] < center_lat) & (df["longitude"] > center_lon)].shape[0],
            "西南側": df[(df["latitude"] < center_lat) & (df["longitude"] < center_lon)].shape[0]
        }
        danger_zone = max(zone_map, key=zone_map.get)

        return {
            "peak_period": peak_period, "rain_increase": rain_ratio,
            "danger_zone": danger_zone, "best_entry": None
        }

    stats = compute_safety_stats(nm_row, accidents_inside_strict)
    stats["best_entry"] = exit_name



    # =========================================================
    # 🌟 下半部：地圖與路線 (左右雙欄)
    # =========================================================
    col_map, col_route = st.columns([1.5, 1], gap="large")

    with col_map:
        st.markdown(f"#### ⚡ 區段危險等級 ｜ {selected_market} 夜市推薦入口")

        center = [nm_row["nightmarket_latitude"], nm_row["nightmarket_longitude"]]
        m = folium.Map(location=center, zoom_start=16)
        bounds = [[south, west], [north, east]]
        folium.Rectangle(bounds=bounds, color="blue", fill=False).add_to(m)
        folium.Marker(center, tooltip=f"{nm_row['nightmarket_name']}（夜市中心）", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)

        lat_step = (north - south) / grid_size
        lon_step = (east - west) / grid_size

        for _, row in grid_df.iterrows():
            i = row["grid_row"]
            j = row["grid_col"]
            south_i = south + i * lat_step
            north_i = south_i + lat_step
            west_j = west + j * lon_step
            east_j = west_j + lon_step
            bounds_grid = [[south_i, west_j], [north_i, east_j]]

            folium.Rectangle(
                bounds=bounds_grid, color=row["color"], fill=True, fill_opacity=0.3,
                tooltip=f"Score: {row['score']} | Accidents: {row['accident_count']}"
            ).add_to(m)

        heat_data = accidents_inside_strict[["latitude", "longitude"]].values.tolist()
        if heat_data:
            HeatMap(heat_data, radius=20, blur=15).add_to(m)

        center_point = [nm_row["nightmarket_latitude"], nm_row["nightmarket_longitude"]]
        start = f"{center_point[1]},{center_point[0]}"
        end = f"{exit_point[1]},{exit_point[0]}"
        url = f"http://router.project-osrm.org/route/v1/foot/{start};{end}?overview=full&geometries=polyline&steps=true"
        route_instructions = []

        try:
            res = requests.get(url).json()
            route = polyline.decode(res["routes"][0]["geometry"])
            folium.PolyLine(locations=route, color="blue", weight=7, opacity=1).add_to(m)

            steps = res["routes"][0]["legs"][0]["steps"]
            steps = list(reversed(steps))

            def translate_maneuver(step, is_first, is_last):
                m = step["maneuver"]
                t = m.get("type", "")
                mod = m.get("modifier", "")
                if is_first: return "從推薦入口開始步行"
                if is_last: return "抵達夜市中心"
                if t == "turn":
                    if mod == "left": return "左轉"
                    if mod == "right": return "右轉"
                    if mod == "straight": return "直走"
                    return "轉彎"
                if t == "new name": return "沿著道路前進"
                if t == "continue": return "繼續直走"
                return "前進"

            for idx, step in enumerate(steps):
                action = translate_maneuver(step, is_first=(idx == 0), is_last=(idx == len(steps) - 1))
                road = step["name"] if step["name"] != "" else "路線引導"
                dist = int(step["distance"])

                if idx == 0 or idx == len(steps) - 1:
                    route_instructions.append(f"{action}")
                else:
                    route_instructions.append(f"{action}，沿著 **{road}** 前進 **{dist} 公尺**")

        except Exception as e:
            folium.PolyLine(locations=[center_point, exit_point], color="blue", weight=7, opacity=1).add_to(m)
            route_instructions = []

        m.fit_bounds([[north, east], [north, west], [south, east], [south, west]])

        is_north = abs(exit_point[0] - north) < 1e-7
        offset_lat = -0.00030 if is_north else 0.00030
        triangle_position = "up" if is_north else "down"

        if triangle_position == "down":
            html_box = """
            <div style="position: relative; background: white; padding: 6px 10px; border-radius: 6px; border: 1.5px solid #333; font-size: 14px; font-weight: bold; color: #222; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.45);">推薦入口
            <div style="position: absolute; bottom: -12px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 10px solid transparent; border-right: 10px solid transparent; border-top: 12px solid white; filter: drop-shadow(0 -2px 2px rgba(0,0,0,0.3));"></div></div>
            """
        else:
            html_box = """
            <div style="position: relative; background: white; padding: 6px 10px; border-radius: 6px; border: 1.5px solid #333; font-size: 14px; font-weight: bold; color: #222; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.45);">推薦入口
            <div style="position: absolute; top: -12px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 10px solid transparent; border-right: 10px solid transparent; border-bottom: 12px solid white; filter: drop-shadow(0 2px 2px rgba(0,0,0,0.3));"></div></div>
            """

        folium.Marker(
            location=[exit_point[0] + offset_lat, exit_point[1]],
            icon=DivIcon(icon_size=(150, 40), icon_anchor=(75, 0), html=html_box)
        ).add_to(m)

        folium.Marker(
            location=exit_point,
            icon=DivIcon(icon_size=(30, 30), icon_anchor=(15, 15), html="""<div style="width: 30px; height: 30px; border-radius: 50%; background-color: #0096FF; color: white; display: flex; justify-content: center; align-items: center; font-size: 16px; font-weight: bold;">i</div>""")
        ).add_to(m)

        st_folium(m, height=450, use_container_width=True, returned_objects=[])

    with col_route:
        st.markdown("#### 🧭 路線說明（步行）")
        if route_instructions:
            for i, inst in enumerate(route_instructions, 1):
                st.markdown(f"""
                <div style="
                    background-color: #f4f6f9; padding: 12px 15px; border-radius: 6px;
                    color: #333; font-weight: 500; margin-bottom: 10px;
                    border-left: 4px solid #e11d48; font-size: 15px;
                ">
                    《 {i}. {inst} 》
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("無法取得路線規劃建議。")
       
    # -----------------------------------------------------
    # 把CH3資料放入 session_state
    # -----------------------------------------------------
    templates = [insight_text] * 5
    st.session_state["ch3"] = {
        "selected_market": selected_market,
        "grid_df": grid_df,
        "exit_name": exit_name,
        "route_instructions": route_instructions,
        "stats": stats,
        "templates": templates
    }

    def card(title, content, color):
        st.markdown(f"""
        <div style="
            padding: 16px;
            border-radius: 12px;
            background-color: {color};
            color: white;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            height: 100%;
        ">
            <h4 style="margin-top: 0; margin-bottom: 10px; color:white;">{title}</h4>
            <p style="font-size: 14px; line-height: 1.5; margin-bottom: 0;">{content}</p>
        </div>
        """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: card("🟥 事故時段", f"最危險時段：<b>{stats['peak_period']}</b><br>建議避開此尖峰。", "#E74C3C")
    with c2: card("🟦 事故原因", f"雨天事故提升 <b>{stats['rain_increase']}%</b><br>濕滑與視線不良為主因。", "#3498DB")
    with c3: card("🟨 區域風險", f"事故最高發區域：<b>{stats['danger_zone']}</b><br>建議避免穿越該區。", "#F1C40F")
    with c4: card("🟩 安全建議", f"建議從 <b>{stats['best_entry']}</b> 進入<br>路幅較寬，人車分流佳。", "#27AE60")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="
        background-color: #f8f9fa;
        padding: 15px 20px;
        border-radius: 10px;
        border-left: 6px solid #4a90e2;
        font-size: 16px;
        color: #333;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    ">
        <b style="color:#222;">{icon} 洞察：</b>
        <span style="color:#222;">{insight_text}</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import core.c_data_service as ds
    import core.c_ui as ui
    st.set_page_config(layout="wide", page_title="行人看這裡", page_icon="🚶")
    df_market = ds.get_all_nightmarkets()
    ui.render_sidebar(df_market)
    act3_render()