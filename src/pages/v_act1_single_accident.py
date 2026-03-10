import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import altair as alt
import plotly.express as px
import sys
import os
import core.c_data_service as ds
import core.c_ui as ui
import utils.market_tools as mt

# AI頁面分析
from dotenv import load_dotenv
from groq import Groq

# 讀取環境變數
load_dotenv() 
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dotenv_path = os.path.join(current_dir, '..', '.env')
load_dotenv(dotenv_path=parent_dotenv_path, override=True)

if not os.getenv("GROQ_API_KEY"):
    st.error("❌找不到 GROQ_API_KEY，請檢查 .env 檔案是否在正確位置。")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

st.set_page_config(layout="wide", page_title="夜市區域事故分析", page_icon="📊")

def main():
    # 🌟 強化版 CSS：解決縮放擠壓、手機版換行問題
    st.markdown("""
    <style>
    /* 強制讓所有欄位區塊在空間不足時自動換行 */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    /* 當螢幕小於 1400px 時，欄位最小寬度為 450px (適合平板/小筆電) */
    @media (max-width: 1400px) {
        div[data-testid="column"] {
            min-width: 450px !important;
            flex: 1 1 450px !important;
            margin-bottom: 20px;
        }
    }
    /* 當螢幕小於 768px 時，欄位佔滿 100% 寬度 (適合手機) */
    @media (max-width: 768px) {
        div[data-testid="column"] {
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    with ui.page_timer():
        traffic_global = ds.get_taiwan_heatmap_data()
        df_market = ds.get_all_nightmarkets()
        
    st.session_state['show_accidents'] = True
    _, _, layers = ui.render_sidebar(df_market)

    st.markdown("""
        <div class="sticky-header">
            <h2 class="header-title" style="margin-bottom: 10px;">夜市區域事故分析</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # =========================================================
    # 🌟 頂部四大區塊：[1.過濾] | [2.KPI] | [3.地圖] | [4.AI]
    # =========================================================
    c_col1, c_col2, c_col3, c_col4 = st.columns([0.7, 0.7, 2, 2], gap="medium")

    # ---------------------------------------------------------
    # 欄位 1：選擇目標
    # ---------------------------------------------------------
    with c_col1:
        st.markdown("📍 **1. 選擇目標**")
        def_dist, def_city, def_market = "北部", "臺北市", "士林夜市"
        
        dist_opts = sorted(df_market['District'].dropna().unique())
        dist_idx = dist_opts.index(def_dist) if def_dist in dist_opts else 0
        sel_dist = st.selectbox("區域", dist_opts, index=dist_idx, key="d_dist", label_visibility="collapsed")
        
        city_opts = sorted(df_market[df_market['District'] == sel_dist]['City'].dropna().unique())
        city_idx = city_opts.index(def_city) if (sel_dist == def_dist and def_city in city_opts) else 0
        sel_city = st.selectbox("縣市", city_opts, index=city_idx, key="d_city", label_visibility="collapsed")
        
        m_opts = ["🔍 全台概覽 (預設)"] + sorted(df_market[df_market['City'] == sel_city]['MarketName'].dropna().unique())
        market_idx = m_opts.index(def_market) if (sel_city == def_city and def_market in m_opts) else 0
        sel_market = st.selectbox("夜市", m_opts, index=market_idx, key="d_market", label_visibility="collapsed")
        
    is_overview = (sel_market == "🔍 全台概覽 (預設)")
    target_market = None if is_overview else df_market[df_market['MarketName'] == sel_market].iloc[0]

    # 🌟 新增：狀態清理機制 (切換夜市時清空舊 AI 報告)
    if "last_market" not in st.session_state:
        st.session_state.last_market = sel_market
    if st.session_state.last_market != sel_market:
        if "ai_report_text" in st.session_state:
            st.session_state.ai_report_text = ""
        st.session_state.last_market = sel_market

    if is_overview:
        with c_col1: st.info("👈 選擇夜市啟用進階分析")
        with c_col2:
            st.markdown("📊 **3. 關鍵指標**")
            st.info("請先選擇夜市")
        with c_col3:
            m = ui.build_map(True, None, layers, None, 500, traffic_global, None, df_market)
            st_folium(m, height=550, width="stretch", returned_objects=[])
        return

    # ---------------------------------------------------------
    # 欄位 3 前置作業：取得範圍與資料
    # ---------------------------------------------------------
    with c_col3:
        c_m_title, c_m_slider = st.columns([1.2, 1], vertical_alignment="bottom")
        with c_m_title:
            st.markdown(f"### 🗺️ {target_market['MarketName']} 事故熱點")
            heat_mode = st.radio("切換事故圖層", ["🌍 全部", "☀️ 白天 (06-18)", "🌙 夜間 (18-06)"], horizontal=True, label_visibility="collapsed")
        with c_m_slider:
            radius_m = st.slider("📍 分析範圍 (m)", min_value=500, max_value=3000, step=500, value=1000)

    radius_km = radius_m / 1000.0
    with st.spinner(f"正在載入資料..."):
        df_raw, _, _, _ = ds.get_nearby_accidents(target_market['lat'], target_market['lon'], radius_km=radius_km, sample=False)

    if df_raw.empty:
        with c_col3: st.warning("此區域暫無事故資料。")
        return

    # ---------------------------------------------------------
    # 欄位 1 (下半部)：時間篩選
    # ---------------------------------------------------------
    with c_col1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("📅 **2. 分析時間篩選**")
        df_raw['accident_datetime'] = pd.to_datetime(df_raw['accident_datetime'])
        df_raw['Year'] = df_raw['accident_datetime'].dt.year
        df_raw['Quarter'] = df_raw['accident_datetime'].dt.quarter
        df_raw['Month'] = df_raw['accident_datetime'].dt.month
        df_raw['Weekday'] = df_raw['accident_datetime'].dt.weekday + 1

        yrs = sorted(df_raw['Year'].dropna().unique(), reverse=True)
        sel_y = st.selectbox("年份", ["全部年份"] + [str(int(y)) for y in yrs], key="sel_y")
        sel_q = st.selectbox("季度", ["全年", "第 1 季", "第 2 季", "第 3 季", "第 4 季"], key="sel_q")
        sel_m = st.selectbox("月份", ["全部"] + [f"{m} 月" for m in range(1, 13)], key="sel_m")
        week_map = {0: "全部", 1: "週一", 2: "週二", 3: "週三", 4: "週四", 5: "週五", 6: "週六", 7: "週日"}
        sel_w = st.selectbox("星期幾", list(week_map.values()), key="sel_w")

    # 過濾
    df_filtered = df_raw.copy()
    if sel_y != "全部年份": df_filtered = df_filtered[df_filtered['Year'] == int(sel_y)]
    if sel_q != "全年": df_filtered = df_filtered[df_filtered['Quarter'] == int(sel_q.split()[1])]
    if sel_m != "全部": df_filtered = df_filtered[df_filtered['Month'] == int(sel_m.split()[0])]
    if sel_w != "全部": df_filtered = df_filtered[df_filtered['Weekday'] == {v: k for k, v in week_map.items()}[sel_w]]
    if "白天" in heat_mode: df_filtered = df_filtered[(df_filtered['Hour'] >= 6) & (df_filtered['Hour'] < 18)]
    elif "夜間" in heat_mode: df_filtered = df_filtered[(df_filtered['Hour'] >= 18) | (df_filtered['Hour'] < 6)]

    if df_filtered.empty:
        with c_col3: st.error("⚠️ 該篩選條件下無事故資料。")
        return

    # 計算數值
    total_count = len(df_filtered)
    dead_count = int(df_filtered['death_count'].sum())
    hurt_count = int(df_filtered['injury_count'].sum())
    
    df_radar = df_filtered.copy()
    df_radar['weather_condition'] = df_radar['weather_condition'].fillna('')
    df_radar['light_condition'] = df_radar['light_condition'].fillna('')
    df_radar['road_surface_condition'] = df_radar['road_surface_condition'].fillna('')
    
    df_radar["is_rain"] = df_radar["weather_condition"].apply(lambda w: 1 if "雨" in w else 0)
    df_radar["is_dark"] = df_radar["light_condition"].apply(lambda x: 1 if any(k in x for k in ["暗", "夜", "未開啟", "無照明"]) else 0)
    df_radar["is_wet"] = df_radar["road_surface_condition"].apply(lambda r: 1 if any(k in r for k in ["濕", "積水"]) else 0)
    
    rain_ratio = df_radar["is_rain"].mean() * 100 if total_count > 0 else 0
    dark_ratio = df_radar["is_dark"].mean() * 100 if total_count > 0 else 0
    wet_ratio = df_radar["is_wet"].mean() * 100 if total_count > 0 else 0

    # ---------------------------------------------------------
    # 欄位 2：關鍵指標
    # ---------------------------------------------------------
    with c_col2:
        st.markdown("📊 **3. 關鍵指標**")
        st.metric("📌 事故數", f"{total_count} 件")
        st.metric("💀 死亡人數", f"{dead_count} 人")
        st.metric("🚑 受傷人數", f"{hurt_count} 人")
        st.metric("🌧️ 雨天比例", f"{rain_ratio:.1f}%")

    # ---------------------------------------------------------
    # 欄位 3：地圖渲染
    # ---------------------------------------------------------
    with c_col3:
        df_for_map = df_filtered.copy()
        if len(df_for_map) > 1000:
            df_death_map = df_for_map[df_for_map['death_count'] > 0]
            df_other_map = df_for_map[df_for_map['death_count'] == 0]
            if len(df_other_map) > 1500: df_other_map = df_other_map.sample(n=1500, random_state=42)
            df_for_map = pd.concat([df_death_map, df_other_map])

        d_zoom = 16 if radius_m <= 500 else 15 if radius_m <= 1000 else 14 if radius_m <= 2000 else 13
        m = ui.build_map(False, target_market, layers, d_zoom, radius_m, None, df_for_map, df_market, custom_tiles="OpenStreetMap")
        st_folium(m, height=450, width="stretch", returned_objects=[])

    # ---------------------------------------------------------
    # 欄位 4：AI 分析
    # ---------------------------------------------------------
    with c_col4:
        st.markdown("""
            <div style="background-color: #f8f9fa; padding: 18px; border-radius: 12px; border: 1px solid #e9ecef;">
                <h3 style="margin-top: 0; color: #1f2937;">💡 專屬 AI 深度分析</h3>
                <p style="color: #6c757d; font-size: 14px;">結合時段、環境與熱點進行診斷。</p>
            </div>
        """, unsafe_allow_html=True)
        
        top_cause_str = df_filtered['primary_cause'].value_counts().idxmax() if not df_filtered.empty else "未知"
        peak_hour_str = df_filtered.groupby('Hour').size().idxmax() if not df_filtered.empty else "未知"
        
        # 產生純淨版 Google Maps 搜尋連結
        df_death = df_filtered[df_filtered['death_count'] > 0]
        if not df_death.empty:
            r_lat, r_lon = df_death.groupby(['latitude', 'longitude']).size().idxmax()
            risky_loc = f"https://www.google.com/maps/search/?api=1&query={r_lat},{r_lon} (曾發生死亡事故)"
        elif not df_filtered.empty:
            r_lat, r_lon = df_filtered.groupby(['latitude', 'longitude']).size().idxmax()
            risky_loc = f"https://www.google.com/maps/search/?api=1&query={r_lat},{r_lon} (高頻事故熱點)"
        else: 
            risky_loc = "無明顯熱點"

        if st.button("✨ 生成分析報告", type="primary", use_container_width=True):
            with st.spinner("AI 正在整合數據..."):
                st.session_state.ai_report_text = get_ai_analysis(
                    target_market['MarketName'], total_count, dead_count, hurt_count, 
                    top_cause_str, peak_hour_str, rain_ratio, dark_ratio, wet_ratio, risky_loc
                )
        
        # 顯示報告 (若有)
        if st.session_state.get("ai_report_text"):
            st.markdown(st.session_state.ai_report_text)

    # =========================================================
    # 🌟 底部圖表 (全寬排列)
    # =========================================================
    st.markdown("---")
    c_chart1, c_chart2, c_chart3, c_chart4, c_chart5 = st.columns(5, gap="medium")
    chart_h = 260
    
    with c_chart1:
        st.markdown("#### 🕸️ 環境風險")
        risk_df = pd.DataFrame({"risk": ["雨天", "光線不佳", "濕滑路面"], "value": [rain_ratio, dark_ratio, wet_ratio]})
        fig = px.line_polar(risk_df, r="value", theta="risk", line_close=True, markers=True, range_r=[0, max(risk_df["value"].max() * 1.2, 10)])
        fig.update_traces(fill="toself", marker=dict(color="#8E44AD", size=6), line=dict(color="#8E44AD"))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, ticksuffix="%", tickfont=dict(size=10)), angularaxis=dict(tickfont=dict(size=14))), margin=dict(l=25, r=25, t=20, b=20), height=chart_h, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with c_chart2:
        st.markdown("#### 🔍 肇因分析")
        if 'primary_cause' in df_filtered.columns:
            df_cause = df_filtered['primary_cause'].value_counts().head(5).reset_index()
            df_cause.columns = ['肇因', '件數']
            bar_c = alt.Chart(df_cause).mark_bar(color="#b91d47").encode(
                x=alt.X('件數:Q', axis=None),
                y=alt.Y('肇因:N', sort='-x', axis=alt.Axis(labels=True, title=None, labelLimit=80)),
                tooltip=['肇因', '件數']
            )
            text_c = bar_c.mark_text(align='left', dx=3, fontWeight='bold', color='black').encode(text='件數:Q')
            st.altair_chart((bar_c + text_c).properties(height=chart_h), use_container_width=True)

    with c_chart3:
        st.markdown("#### 🌙 24H 熱力")
        df_h = df_filtered.groupby('Hour').size().reset_index(name='n')
        h_chart = alt.Chart(df_h).mark_area(color='lightblue', line={'color':'darkblue'}).encode(x=alt.X('Hour:O', title='時段'), y=alt.Y('n:Q', title=None))
        st.altair_chart(h_chart.properties(height=chart_h), use_container_width=True)

    with c_chart4:
        st.markdown("#### 🌤️ 天氣比例")
        df_w = df_filtered.copy()
        df_w['天氣'] = df_w['weather_condition'].apply(lambda w: '雨天' if '雨' in str(w) else '晴天' if '晴' in str(w) else '陰天' if '陰' in str(w) else '其他')
        df_w['時段'] = df_w['Hour'].apply(lambda h: '白天' if 6 <= h < 18 else '夜間')
        chart_w_df = df_w.groupby(['時段', '天氣']).size().reset_index(name='件數')
        base_bar = alt.Chart(chart_w_df).encode(x=alt.X('時段:N', title=None), y=alt.Y('件數:Q', title=None), color=alt.Color('天氣:N', scale=alt.Scale(range=['#f1c40f', '#95a5a6', '#3498db', '#bdc3c7'])))
        text_w = base_bar.mark_text(dy=10, color='black', fontWeight='bold', size=14).encode(y=alt.Y('件數:Q', stack='zero'), text=alt.condition(alt.datum.件數 > 0, alt.Text('件數:Q'), alt.value('')))
        st.altair_chart((base_bar.mark_bar() + text_w).properties(height=chart_h), use_container_width=True)

    with c_chart5:
        st.markdown("#### 📈 事故趨勢")
        df_t = df_filtered.copy()
        df_t['年季'] = df_t['accident_datetime'].dt.year.astype(str) + " Q" + df_t['accident_datetime'].dt.quarter.astype(str)
        trend_grp = df_t.groupby('年季').agg(
            事故總數=('accident_id', 'count'), 
            受傷人數=('injury_count', 'sum'), 
            死亡人數=('death_count', 'sum')
        ).reset_index()
        
        if not trend_grp.empty:
            bar = alt.Chart(trend_grp).mark_bar(opacity=0.4, color='#dc2626').encode(
                x=alt.X('年季:N', title=None, axis=alt.Axis(labelAngle=-45)),
                y=alt.Y('死亡人數:Q', title='死亡', axis=alt.Axis(orient='right', grid=False, titleColor='#dc2626', labelColor='#dc2626')),
                tooltip=['年季', '死亡人數']
            )
            trend_m = trend_grp.melt(id_vars=['年季'], value_vars=['事故總數', '受傷人數'], var_name='類別', value_name='數量')
            line = alt.Chart(trend_m).mark_line(point=True).encode(
                x=alt.X('年季:N', title=None, axis=alt.Axis(labelAngle=-45)), 
                y=alt.Y('數量:Q', title='件數/人數', axis=alt.Axis(grid=True)), 
                color=alt.Color('類別:N', scale=alt.Scale(domain=['事故總數', '受傷人數'], range=['#3b82f6', '#f59e0b']), legend=alt.Legend(orient="bottom", title=None)),
                tooltip=['年季', '類別', '數量']
            )
            dual_chart = alt.layer(bar, line).resolve_scale(y='independent').properties(height=chart_h)
            st.altair_chart(dual_chart, use_container_width=True)
        else:
            st.info("無趨勢數據")


@st.cache_data(ttl=3600, show_spinner=False)
def get_ai_analysis(market_name, total, dead, hurt, top_cause, peak_hour, rain, dark, wet, risky_loc):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        prompt = f"""
        你是一個交通專家。請分析「{market_name}」數據（字數150字）。
        數據：總事故{total}件、死亡{dead}、受傷{hurt}。榜首肇因：{top_cause}。尖峰：{peak_hour}點。
        環境：雨天{rain:.1f}%、昏暗{dark:.1f}%、路濕{wet:.1f}%。
        最危險熱點：{risky_loc}
        
        請回答五大重點：
        1. 肇因與預防。
        2. 綜合環境風險：結合雨天/昏暗/濕滑評估。
        3. 路段特徵推測。
        4. 熱點改善對策：針對最危險熱點，給予強烈警語與防範對策（請在內文提供 Google Maps 網址連結，方便使用者點擊查看）。
        5. 安全總結標語。
        格式：請用 Markdown 條列式，語氣專業，每次生成的內容，請固定都用- 並且字體大小要相同。
        """
        res = client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile")
        return res.choices[0].message.content
    except Exception as e: return f"⚠️ AI 暫時無法使用：{str(e)}"

if __name__ == "__main__":
    main()