import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import sys
import os
import json
import pickle
import redis

# 引用核心服務模組
import core.c_data_service as ds
import core.c_ui as ui
import utils.market_tools as mt
from core.r_cache import REDIS_POOL

# 🌟 使用滿版寬度
st.set_page_config(layout="wide", page_title="全台夜市事故嚴重分析", page_icon="🚦")

@st.cache_data(ttl=86400, show_spinner=False)
def get_dynamic_national_data():
    """
    動態抓取全台所有夜市的 3.0km Redis 快取，
    並依據每個夜市的精準 Bounding Box 切出真正的核心事故，組合為全台原始大表。
    """
    r = redis.Redis(connection_pool=REDIS_POOL)
    df_market = ds.get_all_nightmarkets()
    all_dfs = []
    
    for _, nm in df_market.iterrows():
        lat, lon = nm['lat'], nm['lon']
        key = f"traffic:nearby_v12:{lat:.4f}_{lon:.4f}_3.0_all_sample"
        data = r.get(key)
        if data:
            result = pickle.loads(data)
            df = result[0] if isinstance(result, tuple) else result
            if isinstance(df, pd.DataFrame) and not df.empty:
                north = nm.get("nightmarket_northeast_latitude", lat + 0.005)
                south = nm.get("nightmarket_southwest_latitude", lat - 0.005)
                east = nm.get("nightmarket_northeast_longitude", lon + 0.005)
                west = nm.get("nightmarket_southwest_longitude", lon - 0.005)
                
                mask = (df["latitude"] >= south) & (df["latitude"] <= north) & \
                       (df["longitude"] >= west) & (df["longitude"] <= east)
                df_strict = df[mask].copy()
                
                if not df_strict.empty:
                    df_strict['nightmarket_name'] = nm['MarketName']
                    df_strict['nightmarket_city'] = str(nm['City']).replace('台', '臺')
                    df_strict['nightmarket_rating'] = float(nm.get('nightmarket_rating', 0.0))
                    all_dfs.append(df_strict)
    
    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        if "Hour" not in final_df.columns:
            final_df['accident_datetime'] = pd.to_datetime(final_df['accident_datetime'])
            final_df['Hour'] = final_df['accident_datetime'].dt.hour
            
        final_df["weight"] = np.where((final_df["Hour"] >= 17) | (final_df["Hour"] == 0), 3, 1)
        final_df["severity"] = final_df["death_count"] * 5 + final_df["injury_count"] * 2
        final_df["pdi_score"] = final_df["severity"] * final_df["weight"]
        
        final_df['accident_datetime'] = pd.to_datetime(final_df['accident_datetime'])
        final_df['Year'] = final_df['accident_datetime'].dt.year
        final_df['Quarter'] = final_df['accident_datetime'].dt.quarter
        final_df['Month'] = final_df['accident_datetime'].dt.month
        final_df['Weekday'] = final_df['accident_datetime'].dt.weekday + 1
        return final_df
    return pd.DataFrame()

def get_region(city):
    north = ['臺北市', '新北市', '基隆市', '桃園市', '新竹市', '新竹縣', '宜蘭縣']
    center = ['苗栗縣', '臺中市', '彰化縣', '南投縣', '雲林縣']
    south = ['嘉義市', '嘉義縣', '臺南市', '高雄市', '屏東縣']
    east = ['花蓮縣', '臺東縣']
    if city in north: return '北部'
    elif city in center: return '中部'
    elif city in south: return '南部'
    elif city in east: return '東部'
    else: return '離島'

def main():
    df_market = ds.get_all_nightmarkets()
    ui.render_sidebar(df_market)
    ui.load_custom_css() # 載入共用 CSS

    st.markdown("""
    <style>
    .pdi-card { padding: 18px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); transition: 0.2s; height: 100%; color: white; margin-bottom: 10px;}
    .pdi-card:hover { transform: translateY(-3px); box-shadow: 0 6px 15px rgba(0,0,0,0.25); }
    .title-highlight { color: #e11d48; font-weight: bold; }
    .section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: #333; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <h1 style="margin-bottom:5px;">🚦 臺灣夜市交通安全總體檢：<span class="title-highlight">全台數據揭密</span></h1>
        <p style="color:#555; margin-bottom:20px;">逛夜市是臺灣人的日常，但你知道哪個縣市的夜市周邊最危險嗎？<br>我們透過獨家 PDI 演算法找出交通治理的盲區，讓「人本交通」不再只是口號。</p>
    """, unsafe_allow_html=True)

    with st.spinner("正在動態運算全台數據..."):
        df_raw = get_dynamic_national_data()

    col_left, col_right = st.columns([1, 2.3], gap="large")

    with col_left:

        #分析時間篩選
        st.markdown('<div class="section-title">📅 2. 分析時間篩選</div>', unsafe_allow_html=True)

        l_c1, l_c2 = st.columns(2)
        with l_c1: sel_year = st.selectbox("年份", ["全部年份", "2026", "2025", "2024", "2023", "2022", "2021"])
        with l_c2: sel_q = st.selectbox("季度", ["全年", "第 1 季", "第 2 季", "第 3 季", "第 4 季"])
        
        l_c3, l_c4 = st.columns(2)
        with l_c3: sel_m = st.selectbox("月份", ["全部"] + [f"{i} 月" for i in range(1, 13)])
        week_map = {0: "全部", 1: "週一", 2: "週二", 3: "週三", 4: "週四", 5: "週五", 6: "週六", 7: "週日"}
        with l_c4: sel_w = st.selectbox("星期", list(week_map.values()))
        
        heat_mode = st.radio("時段", ["全部", "白天 (06-18)", "夜間 (18-06)"], horizontal=True)
        
        st.caption("💡 提示：您現在可以自由組合年份、季度、月份與時段，系統會為您即時計算全台夜市排名！")
        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
        
        df_filtered = df_raw.copy()
        if not df_filtered.empty:
            if sel_year != "全部年份": df_filtered = df_filtered[df_filtered['Year'] == int(sel_year)]
            if sel_q != "全年": df_filtered = df_filtered[df_filtered['Quarter'] == int(sel_q.split()[1])]
            if sel_m != "全部": df_filtered = df_filtered[df_filtered['Month'] == int(sel_m.split()[0])]
            if sel_w != "全部": df_filtered = df_filtered[df_filtered['Weekday'] == {v: k for k, v in week_map.items()}[sel_w]]
            if "白天" in heat_mode: df_filtered = df_filtered[(df_filtered['Hour'] >= 6) & (df_filtered['Hour'] < 18)]
            elif "夜間" in heat_mode: df_filtered = df_filtered[(df_filtered['Hour'] >= 18) | (df_filtered['Hour'] < 6)]

        df_trend_base = df_raw.copy()
        if not df_trend_base.empty:
            if sel_q != "全年": df_trend_base = df_trend_base[df_trend_base['Quarter'] == int(sel_q.split()[1])]
            if sel_m != "全部": df_trend_base = df_trend_base[df_trend_base['Month'] == int(sel_m.split()[0])]
            if sel_w != "全部": df_trend_base = df_trend_base[df_trend_base['Weekday'] == {v: k for k, v in week_map.items()}[sel_w]]
            if "白天" in heat_mode: df_trend_base = df_trend_base[(df_trend_base['Hour'] >= 6) & (df_trend_base['Hour'] < 18)]
            elif "夜間" in heat_mode: df_trend_base = df_trend_base[(df_trend_base['Hour'] >= 18) | (df_trend_base['Hour'] < 6)]

        trend_df = df_trend_base.groupby('Year').agg(
            事故總數=('accident_id', 'count'),
            PDI=('pdi_score', 'sum')
        ).reset_index()
        trend_df = trend_df.sort_values('Year')
        trend_df['Year'] = trend_df['Year'].astype(str)

        st.markdown('<div class="section-title">🍩 區域風險佔比 (PDI)</div>', unsafe_allow_html=True)
        if not df_filtered.empty:
            pie_df = df_filtered.groupby("nightmarket_city")["pdi_score"].sum().reset_index()
            pie_df['Region'] = pie_df['nightmarket_city'].apply(get_region)
            region_pie = pie_df.groupby("Region")["pdi_score"].sum().reset_index()
            
            color_map = {'北部': '#4fc3f7', '中部': '#ff8a65', '南部': '#ffd54f', '東部': '#aed581', '離島': '#e0e0e0'}
            fig_pie = px.pie(region_pie, values='pdi_score', names='Region', hole=0.45, color='Region', color_discrete_map=color_map)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)))
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False, height=250, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

        # 分歷年事故趨勢
        st.markdown('<div class="section-title">📈 歷年事故趨勢</div>', unsafe_allow_html=True)
        if not trend_df.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(x=trend_df['Year'], y=trend_df['事故總數'], name='事故總數', marker_color='#3b82f6', yaxis='y1'))
            fig_trend.add_trace(go.Scatter(x=trend_df['Year'], y=trend_df['PDI'], name='PDI', marker_color='#e53935', mode='lines+markers', line=dict(width=3), yaxis='y2'))
            fig_trend.update_layout(
                margin=dict(l=0, r=0, t=30, b=0), height=250,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(title='事故總數', side='left', showgrid=False),
                yaxis2=dict(title='PDI', side='right', overlaying='y', showgrid=False),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)


    with col_right:
        if not df_filtered.empty:
            days_divisor = 365
            if sel_year == "全部年份": days_divisor = 2190
            
            if sel_q != "全年": days_divisor /= 4
            if sel_m != "全部": days_divisor = 30
            if sel_w != "全部": days_divisor /= 7
            if heat_mode != "全部": days_divisor /= 2
            days_divisor = max(1, days_divisor)
            rank_colors = [
                "linear-gradient(135deg, #c62828, #e53935)",
                "linear-gradient(135deg, #d32f2f, #ef5350)",
                "linear-gradient(135deg, #e53935, #e57373)",
                "linear-gradient(135deg, #f4511e, #ff8a65)",
                "linear-gradient(135deg, #fb8c00, #ffb74d)",]

            # --- [卡片 1] 縣市 TOP 5 ---
            st.markdown('<div class="section-title">🔥 縣市最多事故 TOP 5</div>', unsafe_allow_html=True)
            st.caption("呈現各縣市夜市周邊發生的總事故量排行。")
            
            city_rank = df_filtered.groupby("nightmarket_city").agg(
                夜市數量=("nightmarket_name", "nunique"),
                事故總數=("accident_id", "count"),
                death_count=("death_count", "sum"),
                PDI總和=("pdi_score", "sum"),
            ).reset_index().rename(columns={"nightmarket_city": "城市"})
            
            city_rank["日均PDI"] = (city_rank["PDI總和"] / city_rank["夜市數量"] / days_divisor).round(2)
            city_avg_pdi = city_rank["日均PDI"].mean()
            city_rank["危險等級"] = city_rank["日均PDI"].apply(lambda x: ds.get_dynamic_level(x, city_avg_pdi))
            
            # ⭐ 修改：排序依據改為「事故總數」並計算事故均值
            city_avg_acc = city_rank["事故總數"].mean()
            city_top5 = city_rank.sort_values("事故總數", ascending=False).head(5)
            
            cols_city = st.columns(5)
            for idx, (_, row) in enumerate(city_top5.reset_index(drop=True).iterrows()):
                bg_color = rank_colors[idx]
                # ⭐ 修改：卡片顯示的百分比改為比較「事故量高於均值」
                diff_pct = ((row["事故總數"] - city_avg_acc) / city_avg_acc * 100) if city_avg_acc > 0 else 0
                with cols_city[idx]:
                    st.markdown(f"""
                    <div class="pdi-card" style="background:{bg_color};">
                        <div style="font-size:12px; font-weight:bold; margin-bottom:5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">🏆 第 {idx+1} 名</div>
                        <div style="font-size:20px; font-weight:900; margin-bottom:5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">{row['城市']}</div>
                        <div style="font-size:13px; font-weight:bold; margin-bottom:8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">事故量高於均值：{diff_pct:.1f}%</div>
                        <div style="font-size:12px; background:rgba(0,0,0,0.2); padding:5px; border-radius:5px; line-height:1.4;">
                            💀 死亡人數：{row['death_count']} 人<br>💥 事故總數：{row['事故總數']} 件
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # --- [卡片 2] 夜市 Top 5 ---
            st.markdown('<div class="section-title">🔥 危險指數 (PDI) - 單一夜市 TOP 5</div>', unsafe_allow_html=True)
            st.caption("獨立比較全台各個夜市，找出肇事率最高的微觀熱點。")
            
            mkt_df = df_filtered.groupby(["nightmarket_name", "nightmarket_city", "nightmarket_rating"]).agg(
                accident_count=("accident_id", "count"),
                death_count=("death_count", "sum"),
                PDI總和=("pdi_score", "sum"),
            ).reset_index()
            mkt_df["日均PDI"] = (mkt_df["PDI總和"] / days_divisor).round(2)
            mkt_avg_pdi = mkt_df["日均PDI"].mean()
            mkt_df["危險等級"] = mkt_df["日均PDI"].apply(lambda x: ds.get_dynamic_level(x, mkt_avg_pdi))
            
            mkt_top5 = mkt_df.sort_values("日均PDI", ascending=False).head(5)
            
            cols_mkt = st.columns(5)
            for idx, (_, row) in enumerate(mkt_top5.reset_index(drop=True).iterrows()):
                bg_color = rank_colors[idx]
                diff_pct = ((row["日均PDI"] - mkt_avg_pdi) / mkt_avg_pdi * 100) if mkt_avg_pdi > 0 else 0
                with cols_mkt[idx]:
                    st.markdown(f"""
                    <div class="pdi-card" style="background:{bg_color};">
                        <div style="font-size:12px; font-weight:bold; margin-bottom:5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">🏆 第 {idx+1} 名</div>
                        <div style="font-size:18px; font-weight:900; margin-bottom:5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{row['nightmarket_name']}</div>
                        <div style="font-size:13px; font-weight:bold; margin-bottom:8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">高於條件均值：{diff_pct:.1f}%</div>
                        <div style="font-size:12px; background:rgba(0,0,0,0.2); padding:5px; border-radius:5px; line-height:1.4;">
                            💀 死亡人數：{row['death_count']} 人<br>💥 事故總數：{row['accident_count']} 件
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)

            # --- [表格 1] 靜態排行榜 ---
            col_t1, col_t2 = st.columns(2, gap="large")
            with col_t1:
                # ⭐ 修改：表格標題與排序皆改為「最多事故」
                st.markdown('<div class="section-title">🏙️ 城市最多事故 TOP 5</div>', unsafe_allow_html=True) 
                city_rank_display = city_rank.sort_values("事故總數", ascending=False).head(5).reset_index(drop=True)
                st.dataframe(city_rank_display[["城市", "夜市數量", "事故總數", "日均PDI", "危險等級"]], height=215, use_container_width=True, hide_index=True)

            with col_t2:
                st.markdown('<div class="section-title">⭐ 全台夜市: 危險程度 TOP 5</div>', unsafe_allow_html=True)
                mkt_display = mkt_df.sort_values("日均PDI", ascending=False).head(5)
                st.dataframe(
                    mkt_display.rename(columns={"nightmarket_name": "夜市名稱", "nightmarket_rating": "Google 評分", "accident_count": "事故總數"})
                    [["nightmarket_city", "夜市名稱", "Google 評分", "日均PDI", "危險等級"]], 
                    height=215, use_container_width=True, hide_index=True
                )
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- [表格 2] 歷年排行變化 ---
            col_c1, col_c2 = st.columns(2, gap="large")
            
            # 事故數量
            city_rank_table = ds.calculate_rank_changes(df_trend_base, 'nightmarket_city', 'accident_id', top_n=5)
            mkt_rank_table = ds.calculate_rank_changes(df_trend_base, 'nightmarket_name', 'pdi_score', top_n=5)

            with col_c1:
                # 最多事故排行
                st.markdown('<div class="section-title">📈 歷年縣市最多事故排行變化 (TOP 5)</div>', unsafe_allow_html=True) 
                st.caption("與前一年度比較之排名升降")
                if not city_rank_table.empty:
                    st.dataframe(city_rank_table, height=215, use_container_width=True, hide_index=True)

            with col_c2:
                st.markdown('<div class="section-title">📈 歷年夜市危險排行變化 (TOP 5)</div>', unsafe_allow_html=True) 
                st.caption("與前一年度比較之排名升降")
                if not mkt_rank_table.empty:
                    st.dataframe(mkt_rank_table, height=215, use_container_width=True, hide_index=True)

        else:
            st.info("👈 在目前條件下，無任何符合的資料。")

if __name__ == "__main__":
    main()