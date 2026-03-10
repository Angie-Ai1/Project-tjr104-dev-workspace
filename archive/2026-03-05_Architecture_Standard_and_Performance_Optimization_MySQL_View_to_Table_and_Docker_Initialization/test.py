# import streamlit as st
# import streamlit.components.v1 as components

# def act5_render():
#     st.title("車禍數據看板")

#     st.markdown("""
# <hr style="
#     border: 0;
#     height: 6px;
#     background: linear-gradient(90deg, #e53935, #ff8a80);
#     border-radius: 3px;
# ">
# """, unsafe_allow_html=True)

#     # 建立三個分頁來存放不同的看板
#     tab1, tab2, tab3 = st.tabs(["政策有效嗎 ？", "車禍趨勢", "車禍肇因"])

#     with tab1:
#         st.subheader("政策成效")
#         html_code_2 = """
#         <div class='tableauPlaceholder' id='viz1772686598899' style='position: relative'><noscript><a href='#'><img alt=' ' src='https://public.tableau.com/static/images/BZ/BZD7KXXBD/1_rss.png' style='border: none' /></a></noscript><object class='tableauViz'  style='display:none;'><param name='host_url' value='https%3A%2F%2Fpublic.tableau.com%2F' /> <param name='embed_code_version' value='3' /> <param name='path' value='shared/BZD7KXXBD' /> <param name='toolbar' value='yes' /><param name='static_image' value='https://public.tableau.com/static/images/BZ/BZD7KXXBD/1.png' /> <param name='animate_transition' value='yes' /><param name='display_static_image' value='yes' /><param name='display_spinner' value='yes' /><param name='display_overlay' value='yes' /><param name='display_count' value='yes' /><param name='language' value='zh-TW' /></object></div>                <script type='text/javascript'>                
#         var divElement = document.getElementById('viz1772686598899');                   
#         var vizElement = divElement.getElementsByTagName('object')[0];                 
#         vizElement.style.width='1000px';vizElement.style.height='850px';                  
#         var scriptElement = document.createElement('script');                   
#         scriptElement.src = 'https://public.tableau.com/javascripts/api/viz_v1.js';                    vizElement.parentNode.insertBefore(scriptElement, vizElement);              
#         </script>
#         """
#         components.html(html_code_2, height=850, scrolling=True)

#     with tab2:
#         st.subheader("案件分析")
#         html_code_1 = """
#         <div class='tableauPlaceholder' id='viz1772686396223' style='position: relative'><noscript><a href='#'><img alt=' ' src='https://public.tableau.com/static/images/tj/tjr104_mart/1/1_rss.png' style='border: none' /></a></noscript><object class='tableauViz'  style='display:none;'><param name='host_url' value='https%3A%2F%2Fpublic.tableau.com%2F' /> <param name='embed_code_version' value='3' /> <param name='site_root' value='' /><param name='name' value='tjr104_mart/1' /><param name='tabs' value='no' /><param name='toolbar' value='yes' /><param name='static_image' value='https://public.tableau.com/static/images/tj/tjr104_mart/1/1.png' /> <param name='animate_transition' value='yes' /><param name='display_static_image' value='yes' /><param name='display_spinner' value='yes' /><param name='display_overlay' value='yes' /><param name='display_count' value='yes' /><param name='language' value='zh-TW' /></object></div>                <script type='text/javascript'>                    var divElement = document.getElementById('viz1772686396223');                   
#         var vizElement = divElement.getElementsByTagName('object')[0];                  
#         if ( divElement.offsetWidth > 800 ) { vizElement.style.minWidth='1000px';vizElement.style.maxWidth='100%';vizElement.style.minHeight='850px';vizElement.style.maxHeight=(divElement.offsetWidth*0.75)+'px';} else if ( divElement.offsetWidth > 500 ) { vizElement.style.minWidth='1000px';vizElement.style.maxWidth='100%';vizElement.style.minHeight='850px';vizElement.style.maxHeight=(divElement.offsetWidth*0.75)+'px';} else { vizElement.style.minWidth='1000px';vizElement.style.maxWidth='100%';vizElement.style.minHeight='850px';vizElement.style.maxHeight=(divElement.offsetWidth*1.77)+'px';}                   
#         var scriptElement = document.createElement('script');                  
#         scriptElement.src = 'https://public.tableau.com/javascripts/api/viz_v1.js';                    vizElement.parentNode.insertBefore(scriptElement, vizElement);                </script>
#         """
#         components.html(html_code_1, height=850, scrolling=True)

#     with tab3:
#         st.subheader("車禍分析")
#         html_code_3 = """
#         <div class='tableauPlaceholder' id='viz1772686633136' style='position: relative'><noscript><a href='#'><img alt=' ' src='https://public.tableau.com/static/images/ZX/ZXBD29HNG/1_rss.png' style='border: none' /></a></noscript><object class='tableauViz'  style='display:none;'><param name='host_url' value='https%3A%2F%2Fpublic.tableau.com%2F' /> <param name='embed_code_version' value='3' /> <param name='path' value='shared/ZXBD29HNG' /> <param name='toolbar' value='yes' /><param name='static_image' value='https://public.tableau.com/static/images/ZX/ZXBD29HNG/1.png' /> <param name='animate_transition' value='yes' /><param name='display_static_image' value='yes' /><param name='display_spinner' value='yes' /><param name='display_overlay' value='yes' /><param name='display_count' value='yes' /><param name='language' value='zh-TW' /></object></div>                <script type='text/javascript'>                   
#         var divElement = document.getElementById('viz1772686633136');               
#         var vizElement = divElement.getElementsByTagName('object')[0];                
#         vizElement.style.width='1000px';vizElement.style.height='850px';               
#         var scriptElement = document.createElement('script');                  
#         scriptElement.src = 'https://public.tableau.com/javascripts/api/viz_v1.js';                    vizElement.parentNode.insertBefore(scriptElement, vizElement);              
#         </script>
#         """
#         components.html(html_code_3, height=850, scrolling=True)



import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import altair as alt
import sys
import os
import c_data_service as ds
import c_ui as ui
# AI頁面分析
from dotenv import load_dotenv
from groq import Groq
# 1. 優先讀取根目錄的 .env
load_dotenv() 
# 2. 強制指定上一層目錄的路徑再讀一次 (確保 pages/ 內也能讀到)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dotenv_path = os.path.join(current_dir, '..', '.env')
load_dotenv(dotenv_path=parent_dotenv_path, override=True)
# 測試用：請看您的終端機(Terminal)是否有印出這行
if not os.getenv("GROQ_API_KEY"):
    st.error("❌找不到 GROQ_API_KEY，請檢查 .env 檔案是否在正確位置。")
# 路徑設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
st.set_page_config(layout="wide", page_title="夜市區域事故分析", page_icon="📊")

def main():
    # 加入計時器
    with ui.page_timer():
        traffic_global = ds.get_taiwan_heatmap_data()
        df_market = ds.get_all_nightmarkets()
        
    st.session_state['show_accidents'] = True
    
    # 呼叫側邊欄以保留導航與圖層控制
    _, _, layers = ui.render_sidebar(df_market)
    # =========================================================
    # 頂部佈局：1/2/3 區塊並列
    # =========================================================
    st.markdown("""
        <div class="sticky-header">
            <h2 class="header-title" style="margin-bottom: 10px;">夜市區域事故分析</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # 分配寬度比例：地點(24%) : 年份(24%) : KPI(52%)
    c_loc, c_year, c_kpi = st.columns([1.2, 1.2, 2.6], gap="large")
    # ---------------- 1️⃣ 第一區：選擇分析目標 ----------------
    with c_loc:
        st.markdown("📍 1. 選擇目標")
        
        # 設定預設值變數
        def_dist = "北部"
        def_city = "臺北市"
        def_market = "士林夜市"
        
        # 區域選單
        dist_opts = sorted(df_market['District'].dropna().unique())
        dist_idx = dist_opts.index(def_dist) if def_dist in dist_opts else 0
        sel_dist = st.selectbox("區域", dist_opts, index=dist_idx, key="d_dist", label_visibility="collapsed")
        
        # 縣市選單
        city_opts = sorted(df_market[df_market['District'] == sel_dist]['City'].dropna().unique())
        city_idx = city_opts.index(def_city) if (sel_dist == def_dist and def_city in city_opts) else 0
        sel_city = st.selectbox("縣市", city_opts, index=city_idx, key="d_city", label_visibility="collapsed")
        
        # 夜市選單
        m_opts = ["🔍 全台概覽 (預設)"] + sorted(df_market[df_market['City'] == sel_city]['MarketName'].dropna().unique())
        market_idx = m_opts.index(def_market) if (sel_city == def_city and def_market in m_opts) else 0
        sel_market = st.selectbox("夜市", m_opts, index=market_idx, key="d_market", label_visibility="collapsed")
        
    is_overview = (sel_market == "🔍 全台概覽 (預設)")
    target_market = None if is_overview else df_market[df_market['MarketName'] == sel_market].iloc[0]
    # --- 總覽模式 ---
    if is_overview:
        with c_year: st.info("👈 選擇夜市啟用年份篩選")
        with c_kpi: st.info("👈 選擇夜市後將顯示關鍵數據")
        st.markdown("---")
        m = ui.build_map(True, None, layers, None, 500, traffic_global, None, df_market)
        st_folium(m, height=700, width="stretch", returned_objects=[])
        return
    # --- 單一夜市模式 ---
    if "last_market" not in st.session_state:
        st.session_state.last_market = sel_market
    if st.session_state.last_market != sel_market:
        st.session_state.ai_report_text = ""
        st.session_state.last_market = sel_market
    st.markdown("---")
    # 建立下方三欄式佈局 (地圖2 : 天氣1 : 肇因1)
    col_main, col_weather, col_cause = st.columns([2, 1, 1], gap="medium")
    
    # 在下方畫出滑桿取得數值
    with col_main:
        c_map_title, c_slider = st.columns([1, 1], vertical_alignment="bottom")
        with c_map_title:
            st.subheader(f"🗺️ {target_market['MarketName']} 事故熱點")
            radius_m = st.slider("📍 分析範圍 (m)", min_value=500, max_value=3000, step=500, value=1000)
            radius_km = radius_m / 1000.0
    # 載入數據
    with st.spinner(f"正在載入 {target_market['MarketName']} 周邊 {radius_m}m 事故資料..."):
        df_raw, _, _, yearly_stats_full = ds.get_nearby_accidents(
            target_market['lat'], target_market['lon'], radius_km=radius_km, sample=False
        )
    if df_raw.empty:
        st.warning("此區域暫無事故資料。")
        return
    # ---------------- 2️⃣ 第二區：分析年份 ----------------
    with c_year:
        st.markdown("📅 2. 分析年份")
        available_years = sorted(df_raw['Year'].unique(), reverse=True)
        default_years = available_years
        
        # 初始化「全選」的狀態
        if "d_chk_all" not in st.session_state:
            st.session_state["d_chk_all"] = True
            
        # 初始化各年份狀態
        for year in available_years:
            if f"d_chk_{year}" not in st.session_state:
                st.session_state[f"d_chk_{year}"] = (year in default_years)
        def toggle_all():
            is_checked = st.session_state.get("d_chk_all", False)
            for y in available_years: st.session_state[f"d_chk_{y}"] = is_checked
        st.checkbox("全選", key="d_chk_all", on_change=toggle_all)
        
        y_cols = st.columns(2)
        selected_years = []
        for i, year in enumerate(available_years):
            with y_cols[i % 2]:
                if st.checkbox(str(year), key=f"d_chk_{year}"):
                    selected_years.append(year)
    if not selected_years:
        with c_kpi: st.error("⚠️ 請至少選擇一個年份。")
        return
    
    df_filtered = df_raw[df_raw['Year'].isin(selected_years)]
    # ---------------- 3️⃣ 第三區：關鍵指標 (KPI) ----------------
    with c_kpi:
        st.markdown("📊 3. 關鍵指標")
        stats_new = {
            "total": len(df_filtered),
            "dead": int(df_filtered['death_count'].sum()),
            "hurt": int(df_filtered['injury_count'].sum())
        }
        weather_grp = df_filtered.groupby('weather_condition').agg(件數=('accident_datetime', 'count')).reset_index()
        weather_grp.columns = ['天氣', '件數']
        rain_count = weather_grp[weather_grp['天氣'].astype(str).str.contains('雨')]['件數'].sum() if not weather_grp.empty else 0
        rain_ratio = (rain_count / stats_new['total']) * 100 if stats_new['total'] > 0 else 0
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("📌 事故數", f"{stats_new['total']} 件")
        k2.metric("💀 死亡人數", f"{stats_new['dead']} 人")
        k3.metric("🚑 受傷人數", f"{stats_new['hurt']} 人")
        k4.metric("🌧️ 雨天比例", f"{rain_ratio:.1f}%")
    # =========================================================
    # 🤖 命中要點：AI 深度分析區塊 (精準置中於紅框位置)
    # =========================================================
    st.markdown("---")
    
    # 1. 找出主要肇因與尖峰時段
    top_cause_str = df_filtered['primary_cause'].value_counts().idxmax() if ('primary_cause' in df_filtered.columns and not df_filtered.empty) else "未知"
    peak_hour_str = df_filtered.groupby('Hour').size().idxmax() if ('Hour' in df_filtered.columns and not df_filtered.empty) else "未知"
    
    # 2. 找出最明顯危險路口/死亡事故點
    df_death = df_filtered[df_filtered['death_count'] > 0]
    if not df_death.empty:
        risky_point = df_death.groupby(['latitude', 'longitude']).size().idxmax()
        risky_loc = f"座標 {risky_point} (曾發生死亡事故)"
    elif not df_filtered.empty:
        risky_point = df_filtered.groupby(['latitude', 'longitude']).size().idxmax()
        risky_loc = f"座標 {risky_point} (高頻事故熱點)"
    else:
        risky_loc = "無明顯熱點"
    # 3. UI 渲染 (使用 st.container 確保橫跨滿版)
    if "ai_report_text" not in st.session_state:
        st.session_state.ai_report_text = ""
    with st.container():
        c_ai_t, c_ai_b = st.columns([3, 1], vertical_alignment="center")
        with c_ai_t:
            st.subheader("🤖 生成式 AI 深度分析報告")
        with c_ai_b:
            if st.button("✨ 產生專屬分析報告", type="primary", use_container_width=True):
                with st.spinner("AI 正在解析肇因、路段與預防要點..."):
                    st.session_state.ai_report_text = get_ai_analysis(
                        target_market['MarketName'], stats_new['total'], stats_new['dead'], 
                        stats_new['hurt'], round(rain_ratio, 1), top_cause_str, peak_hour_str, risky_loc
                    )
        if st.session_state.ai_report_text:
            st.info(st.session_state.ai_report_text)
        else:
            st.caption("💡 範圍與年份設定完成後，點擊按鈕針對「肇因預防、尖峰路段、死亡路口」生成深度分析。")
    st.markdown("---")
    # =========================================================
    # 繪製下方地圖與圖表
    # =========================================================
    with col_main:
        # 1. 確保死亡事故優先保留，一般事故隨機抽樣以維持熱力圖真實分佈
        if len(df_filtered) > 1000:
            df_death_map = df_filtered[df_filtered['death_count'] > 0]
            df_other_map = df_filtered[df_filtered['death_count'] == 0]
            
            # 隨機抽取 1500 筆來畫熱力圖，確保能觸發 c_ui.py 的 >800 門檻
            if len(df_other_map) > 1500:
                df_other_map = df_other_map.sample(n=1500, random_state=42)
                
            df_for_map = pd.concat([df_death_map, df_other_map])
        else:
            df_for_map = df_filtered
        # 2. 根據滑桿半徑動態計算縮放級別
        if radius_m <= 500:
            d_zoom = 16
        elif radius_m <= 1000:
            d_zoom = 15
        elif radius_m <= 2000:
            d_zoom = 14
        elif radius_m <= 3000:
            d_zoom = 13
        else:
            d_zoom = 12
        # 3. 將 d_zoom 傳入地圖，並將 use_container_width 修正為最新語法 width="stretch"
        m = ui.build_map(False, target_market, layers, d_zoom, radius_m, None, df_for_map, df_market)
        st_folium(m, height=500, width="stretch", returned_objects=[])
    # --- 中欄：天候風險 ---
    with col_weather:
        st.subheader("☂️ 天候風險")
        if not weather_grp.empty:
            base_pie = alt.Chart(weather_grp).encode(theta=alt.Theta("件數", stack=True))
            pie = base_pie.mark_arc(innerRadius=40).encode(
                color=alt.Color("天氣", scale=alt.Scale(scheme='tableau10')),
                tooltip=['天氣', '件數']
            )
            pie_text = base_pie.mark_text(radius=80).encode(
                text="件數", order=alt.Order("天氣"), color=alt.value("black")
            )
            st.altair_chart((pie + pie_text).properties(height=220), use_container_width=True)
            
            st.subheader("☠️ 死傷程度")
            weather_sev = df_filtered.groupby('weather_condition').agg(
                死亡=('death_count', 'sum'), 受傷=('injury_count', 'sum')
            ).reset_index().rename(columns={'weather_condition': '天氣'})
            df_melt = weather_sev.melt(id_vars=['天氣'], value_vars=['死亡', '受傷'], var_name='類別', value_name='人數')
            df_melt = df_melt[df_melt['人數'] > 0]
            
            base_bar = alt.Chart(df_melt).encode(
                x=alt.X('天氣:N', sort='-x', title=None),
                y=alt.Y('人數:Q'),
                color=alt.Color('類別:N', scale=alt.Scale(range=['#000000', '#e74c3c'])),
            )
            bar = base_bar.mark_bar()
            text = base_bar.mark_text(dy=-10, color='black').encode(text='人數:Q')
            st.altair_chart((bar + text).properties(height=200), use_container_width=True)
        else:
            st.info("無數據")
    # --- 右欄：肇因與時段 ---
    with col_cause:
        st.subheader("🔍 肇因分析")
        if 'primary_cause' in df_filtered.columns:
            df_cause = df_filtered['primary_cause'].value_counts().head(8).reset_index()
            df_cause.columns = ['肇因', '件數']
            
            base_c = alt.Chart(df_cause).encode(
                x=alt.X('件數:Q'),
                y=alt.Y('肇因:N', sort='-x', axis=alt.Axis(labels=True, title=None)),
                tooltip=['肇因', '件數']
            )
            bar_c = base_c.mark_bar().encode(color=alt.Color('件數:Q', scale=alt.Scale(scheme='reds'), legend=None))
            text_c = base_c.mark_text(align='left', dx=2).encode(text='件數:Q')
            st.altair_chart((bar_c + text_c).properties(height=250), use_container_width=True)
        st.subheader("🌙 24H 熱力")
        if 'Hour' in df_filtered.columns:
            df_hour = df_filtered.groupby('Hour').size().reset_index(name='件數')
            chart_hour = alt.Chart(df_hour).mark_area(
                color='lightblue', line={'color':'darkblue'}
            ).encode(
                x=alt.X('Hour:O', title='hr'),
                y=alt.Y('件數:Q', title=None),
                tooltip=['Hour', '件數']
            ).properties(height=180)
            st.altair_chart(chart_hour, use_container_width=True)
@st.cache_data(ttl=3600, show_spinner=False)
def get_ai_analysis(market_name, total, dead, hurt, rain_ratio, top_cause, peak_hour, risky_loc):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        prompt = f"""
        你是一個專業的台灣交通安全分析師。請針對「{market_name}」周邊數據，以繁體中文回答以下五大要點（字數約250字）：
        
        1. 主要肇因與預防：分析為何「{top_cause}」頻繁發生，並給予具體的預防與改善建議。
        2. 事故尖峰時段：針對「{peak_hour}點」的環境危險因素（如視線、車流）提出警告。
        3. 主要發生路段：根據夜市地理與人流行為特徵，推測哪些路段/動線風險最高。
        4. 天氣主因判斷：雨天事故佔 {rain_ratio}%，請判斷天氣是否為關鍵變因。
        5. 最明顯危險路口：針對熱點「{risky_loc}」給予用路人強烈警語。
        
        數據規模參考：總事故{total}件、死亡{dead}、受傷{hurt}。請用條列式說明，語氣客觀專業，直接命中痛點。
        """
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ AI 分析暫時無法使用，錯誤細節：{str(e)}"
if __name__ == "__main__":
    main()