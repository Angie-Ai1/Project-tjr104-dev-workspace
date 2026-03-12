import streamlit as st
import folium
from folium.plugins import HeatMap, MarkerCluster
import pandas as pd
import altair as alt 
import time
from contextlib import contextmanager
# 外國觀光客友善（多國語系翻譯）
import time
import streamlit.components.v1 as components
import uuid

# ==========================================
# 1. 側邊欄 (Sidebar)
# ==========================================
def render_sidebar(df_market):
    st.sidebar.markdown("### 🌐 語言切換 / Language")
    render_google_translator()
    # 側邊欄結構
    st.sidebar.markdown("## 數據揭密")
    st.sidebar.page_link("r_app.py", label="🏠 首頁")
    st.sidebar.page_link("pages/v_act1_all_accident.py", label="全台夜市事故總體檢", icon="🗺️")
    st.sidebar.page_link("pages/v_act1_city_accident.py", label="縣市安全對標與趨勢", icon="🏙️")
    st.sidebar.page_link("pages/v_act1_single_accident.py", label="單一夜市 AI 深度診斷", icon="🔍")
    st.sidebar.markdown("## 化數據為行動")
    st.sidebar.page_link("pages/v_act2_policy.py", label="政策成效即時監控", icon="⚖️")
    st.sidebar.page_link("pages/v_act2_tableau.py", label="政策成效歷史數據 (Tableau)", icon="📈") 
    st.sidebar.page_link("pages/v_act2_avoid.py", label="友善步行導航路線", icon="🧭")
    st.sidebar.markdown("### 持續開發中")
    st.sidebar.page_link("pages/v_act3_chat.py", label="AI交通小幫手", icon="💬")
    st.sidebar.page_link("pages/v_act3_policy_impact.py", label="政策成效初版", icon="⚖️")

    layers = {
        "traffic_heat": True,
        "night_market": True,
        "weather": False,
        "accidents": True}
    
    return True, None, layers

@contextmanager
def page_timer():
    """
    保留此函式以防止報錯
    計算時間但不再 st.sidebar 中顯示內容
    """
    start_time = time.time()
    yield # 執行頁面主內容
    end_time = time.time()
    # 計算結果僅保留，不進行 UI 輸出
    _ = end_time - start_time
    
# ==========================================
# 地圖
# ==========================================
def build_map(is_overview, target_market, layers, dynamic_zoom, radius_m, traffic_global, df_local, df_market, custom_tiles="CartoDB positron"):
    if is_overview: 
        loc, zoom = [23.7, 120.95], 8
    elif target_market is not None: 
        loc = [target_market['lat'], target_market['lon']]
        # 接收 v_act1_single_accident 傳來的動態縮放值，若無則預設 16
        zoom = dynamic_zoom if dynamic_zoom is not None else 16
    else: 
        loc, zoom = [25.03, 121.56], 12
    # 將 tiles 改為使用傳入的 custom_tiles 變數
    m = folium.Map(location=loc, zoom_start=zoom, tiles=custom_tiles, prefer_canvas=True)

    if layers.get('traffic_heat') and traffic_global:
        HeatMap(traffic_global, radius=15, blur=12, min_opacity=0.3).add_to(m)

    if layers.get('night_market'):
        fg_m = folium.FeatureGroup(name="夜市")
        if target_market is not None:
            folium.Marker([target_market['lat'], target_market['lon']], icon=folium.Icon(color='purple', icon='star', prefix='fa'), tooltip=target_market['MarketName']).add_to(fg_m)
            folium.Circle([target_market['lat'], target_market['lon']], radius=radius_m, color='orange', fill=True, fill_opacity=0.1).add_to(fg_m)
        else:
            for _, r in df_market.iterrows():
                folium.CircleMarker([r['lat'], r['lon']], radius=3, color='purple', tooltip=r['MarketName']).add_to(fg_m)
        fg_m.add_to(m)

    if not is_overview and layers.get('accidents') and df_local is not None and not df_local.empty:
        df_death = df_local[df_local['death_count'] > 0]
        df_other = df_local[df_local['death_count'] == 0]

        # 將一般事故放入專屬圖層
        fg_other = folium.FeatureGroup(name="一般事故")
        if len(df_other) > 800:
            heat_data = [[r.latitude, r.longitude] for r in df_other.itertuples()]
            folium.plugins.HeatMap(heat_data, radius=12, blur=15, min_opacity=0.3).add_to(fg_other)
        else:
            cluster_other = MarkerCluster(maxClusterRadius=30, disableClusteringAtZoom=16).add_to(fg_other)
            for r in df_other.itertuples():
                i_count = getattr(r, 'injury_count', 0)
                color = 'blue' if i_count > 0 else 'black'
                cause = getattr(r, 'primary_cause', '未知')
                
                dt = getattr(r, 'accident_datetime', None)
                dt_str = dt.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(dt) else '未知時間'
                
                popup_text = f"一般事故<br>{dt_str}<br>{cause}<br>傷:{i_count}"
                folium.CircleMarker(
                    [r.latitude, r.longitude], 
                    radius=5, color=color, fill=True, fill_opacity=0.7, 
                    popup=folium.Popup(popup_text, max_width=200)
                ).add_to(cluster_other)
        fg_other.add_to(m)

        # 將死亡事故放入另一個專屬圖層
        if not df_death.empty:
            fg_death = folium.FeatureGroup(name="死亡事故", show=True)
            for r in df_death.itertuples():
                d_count = getattr(r, 'death_count', 0)
                i_count = getattr(r, 'injury_count', 0)
                
                dt = getattr(r, 'accident_datetime', None)
                dt_str = dt.strftime('%Y-%m-%d %H:%M:%S') if pd.notnull(dt) else '未知時間'
                cause = getattr(r, 'primary_cause', '未知')
                
                popup_text = f"🚨 死亡事故<br>{dt_str}<br>{cause}<br>死:{d_count} 傷:{i_count}"
                
                # 使用 HTML DivIcon 取代 CircleMarker，強制提升 Z-index 到最頂層
                icon_html = '<div style="background-color: #ff0000; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 6px rgba(0,0,0,0.8);"></div>'
                
                folium.Marker(
                    [r.latitude, r.longitude], 
                    icon=folium.DivIcon(html=icon_html, icon_anchor=(8, 8)),
                    popup=folium.Popup(popup_text, max_width=200),
                    z_index_offset=1000 # 強制永遠顯示在其他點位之上
                ).add_to(fg_death)
                
            fg_death.add_to(m)
            
        # 加入圖層控制面板 (地圖右上角)
        folium.LayerControl(collapsed=False).add_to(m)

    return m # 將畫好的地圖交還給主程式

# ==========================================
# 外國觀光客友善（多國語系翻譯）
# ==========================================
def render_google_translator():
    container_id = f"google_translate_{uuid.uuid4().hex}"
    st.sidebar.markdown(f'<div id="{container_id}"></div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    components.html(
        f"""
        <script>
        const parentWindow = window.parent;
        const parentDoc = parentWindow.document;

        if (!parentWindow.persistent_google_translate) {{
            parentWindow.persistent_google_translate = parentDoc.createElement('div');
            parentWindow.persistent_google_translate.id = 'persistent_google_translate';
            
            parentWindow.googleTranslateElementInit = function() {{
                new parentWindow.google.translate.TranslateElement({{
                    pageLanguage: 'zh-TW',
                    includedLanguages: 'zh-TW,en,ja,ko',
                    layout: parentWindow.google.translate.TranslateElement.InlineLayout.SIMPLE
                }}, 'persistent_google_translate'); 
            }};
            
            const script = parentDoc.createElement('script');
            script.id = 'google-translate-script';
            script.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
            parentDoc.body.appendChild(script);
        }}

        let attempts = 0;
        const timer = setInterval(() => {{
            const newContainer = parentDoc.getElementById('{container_id}');
            if (newContainer && parentWindow.persistent_google_translate) {{
                newContainer.appendChild(parentWindow.persistent_google_translate);
                clearInterval(timer);
            }}
            attempts++;
            if (attempts > 50) clearInterval(timer);
        }}, 100);
        </script>
        """,
        height=0, width=0)

# ==========================================
# 所有頁面的卡片、標題、KPI 樣式
# ==========================================
def load_custom_css():
    st.markdown("""
    <style>
        /* 共用：PDI 危險指數卡片 */
        .pdi-card { padding: 18px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); transition: 0.2s; height: 100%; color: white; margin-bottom: 10px;}
        .pdi-card:hover { transform: translateY(-3px); box-shadow: 0 6px 15px rgba(0,0,0,0.25); }
        
        /* 共用：標題與區塊排版 */
        .title-highlight { color: #e11d48; font-weight: bold; }
        .section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #333; }
        div[data-testid="stVerticalBlock"] > div { padding-bottom: 0rem; }
        
        /* 共用：KPI 數據方塊 (用於各縣市比較頁面) */
        .kpi-box { background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #e5e7eb; }
        .kpi-title { font-size: 13px; color: #6b7280; margin-bottom: 2px; }
        .kpi-value { font-size: 22px; font-weight: bold; color: #111827; }
        .kpi-delta { font-size: 12px; font-weight: bold; }
        .delta-good { color: #10b981; }
        .delta-bad { color: #ef4444; }
    </style>
    """, unsafe_allow_html=True)