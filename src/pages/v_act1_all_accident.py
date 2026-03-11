import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import pickle
import redis

# 引用核心服務模組
import core.c_data_service as ds
import core.c_ui as ui
import utils.market_tools as mt
from core.r_cache import REDIS_POOL

# 使用滿版寬度
st.set_page_config(layout="wide", page_title="全台夜市事故嚴重分析", page_icon="🚦")

# ---------------------------------------------------------
# 資料層
# ---------------------------------------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def get_redis_data(sel_year):
    year_key = "all" if sel_year == "全部年份" else str(sel_year)
    pdi_df = pd.DataFrame()
    
    try:
        r = redis.Redis(connection_pool=REDIS_POOL)
        stats_data = r.get(f"market:pdi_stats_cache_{year_key}")
        
        if stats_data:
            try:
                pdi_df = pd.DataFrame(pickle.loads(stats_data))
            except:
                pdi_df = pd.DataFrame(json.loads(stats_data))
    except Exception as e:
        print(f"Redis 讀取失敗: {e}")
        
    return pdi_df

def build_rank_change_table(df, entity_col):
    df['Rank'] = df.groupby('Year')['pdi'].rank(ascending=False, method='first')
    rank_pivot = df.pivot(index=entity_col, columns='Year', values='Rank')
    
    years = sorted(df['Year'].unique(), reverse=True)
    display_years = [y for y in years if int(y) >= 2023]
    
    result_dict = {}
    for y in display_years:
        prev_y = str(int(y) - 1)
        current_top10 = df[(df['Year'] == y) & (df['Rank'] <= 10)].sort_values('Rank')
        
        formatted_list = []
        for _, row in current_top10.iterrows():
            entity = row[entity_col]
            curr_rank = row['Rank']
            
            if prev_y in rank_pivot.columns and not pd.isna(rank_pivot.at[entity, prev_y]):
                prev_rank = rank_pivot.at[entity, prev_y]
                diff = prev_rank - curr_rank
                if diff > 0:
                    trend = f"🔼 {int(diff)}"
                elif diff < 0:
                    trend = f"🔽 {int(-diff)}"
                else:
                    trend = "➖"
            else:
                trend = "🆕"
                
            formatted_list.append(f"{entity} ({trend})")
            
        while len(formatted_list) < 10:
            formatted_list.append("-")
            
        result_dict[y] = formatted_list
        
    res_df = pd.DataFrame(result_dict)
    res_df.insert(0, '名次', [f"第 {i} 名" for i in range(1, 11)])
    return res_df

@st.cache_data(ttl=86400, show_spinner=False)
def get_yearly_trend_and_rankings():
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    dfs = []
    trend_data = []
    
    try:
        r = redis.Redis(connection_pool=REDIS_POOL)
        for y in years:
            data = r.get(f"market:pdi_stats_cache_{y}")
            if data:
                try:
                    df = pd.DataFrame(pickle.loads(data))
                except:
                    df = pd.DataFrame(json.loads(data))
                df['Year'] = str(y)
                
                # 清洗歷年資料中的「台」
                if 'nightmarket_city' in df.columns:
                    df['nightmarket_city'] = df['nightmarket_city'].str.replace('台', '臺')
                    
                dfs.append(df)
                total_acc = df['accident_count'].sum() if 'accident_count' in df.columns else 0
                total_pdi = df['pdi'].sum() if 'pdi' in df.columns else 0
                trend_data.append({'Year': str(y), '事故總數': total_acc, 'PDI': total_pdi})
    except:
        pass
        
    trend_df = pd.DataFrame(trend_data)
        
    if not dfs:
        return pd.DataFrame(), pd.DataFrame(), trend_df
        
    hist_df = pd.concat(dfs, ignore_index=True)
    city_df = hist_df.groupby(['Year', 'nightmarket_city'])['pdi'].sum().reset_index()
    city_rank_table = build_rank_change_table(city_df, 'nightmarket_city')
    
    mkt_df = hist_df.groupby(['Year', 'nightmarket_name'])['pdi'].sum().reset_index()
    mkt_rank_table = build_rank_change_table(mkt_df, 'nightmarket_name')
    
    return city_rank_table, mkt_rank_table, trend_df

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

# ---------------------------------------------------------
# UI 渲染層
# ---------------------------------------------------------
def main():
    df_market = ds.get_all_nightmarkets()
    ui.render_sidebar(df_market)

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

    with st.spinner("從快取載入全台大數據..."):
        city_rank_table, mkt_rank_table, trend_df = get_yearly_trend_and_rankings()

    col_left, col_right = st.columns([1, 2.3], gap="large")

    with col_left:
        st.markdown('<div class="section-title">📅 2. 分析時間篩選</div>', unsafe_allow_html=True)
        
        l_c1, l_c2 = st.columns(2)
        with l_c1: sel_year = st.selectbox("年份", ["全部年份", "2026", "2025", "2024", "2023", "2022", "2021"])
        with l_c2: sel_q = st.selectbox("季度", ["全年"], disabled=True)
        
        l_c3, l_c4 = st.columns(2)
        with l_c3: sel_m = st.selectbox("月份", ["全部"], disabled=True)
        with l_c4: sel_w = st.selectbox("星期", ["全部"], disabled=True)
        
        st.radio("時段", ["全部", "白天 (06-18)", "夜間 (18-06)"], horizontal=True, disabled=True)
        
        st.caption("⚠️ 提示：極速快取模式僅支援「年份」篩選，進階時段分析請至「單一夜市事故分析」頁面。")
        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
        
        pdi_df = get_redis_data(sel_year)
        if not pdi_df.empty and 'nightmarket_city' in pdi_df.columns:
            pdi_df['nightmarket_city'] = pdi_df['nightmarket_city'].str.replace('台', '臺')

        if "death_count" not in pdi_df.columns:
            pdi_df["death_count"] = 0

        st.markdown('<div class="section-title">📈 歷年事故趨勢</div>', unsafe_allow_html=True)
        if not trend_df.empty:
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(x=trend_df['Year'], y=trend_df['事故總數'], name='事故總數', marker_color='#90a4ae', yaxis='y1'))
            fig_trend.add_trace(go.Scatter(x=trend_df['Year'], y=trend_df['PDI'], name='PDI', marker_color='#e53935', mode='lines+markers', line=dict(width=3), yaxis='y2'))
            fig_trend.update_layout(
                margin=dict(l=0, r=0, t=30, b=0), height=250,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(title='事故總數', side='left', showgrid=False),
                yaxis2=dict(title='PDI', side='right', overlaying='y', showgrid=False),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

        st.markdown('<div class="section-title">🍩 區域風險佔比 (PDI)</div>', unsafe_allow_html=True)
        if not pdi_df.empty:
            pie_df = pdi_df.copy()
            pie_df['Region'] = pie_df['nightmarket_city'].apply(get_region)
            region_pie = pie_df.groupby("Region")["pdi"].sum().reset_index()
            
            color_map = {'北部': '#4fc3f7', '中部': '#ff8a65', '南部': '#ffd54f', '東部': '#aed581', '離島': '#e0e0e0'}
            fig_pie = px.pie(region_pie, values='pdi', names='Region', hole=0.45, color='Region', color_discrete_map=color_map)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='#FFFFFF', width=2)))
            fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False, height=250, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        if not pdi_df.empty:
            days_divisor = 2190 if sel_year == "全部年份" else 365
            
            def get_dynamic_level(val, avg_val):
                if val > avg_val * 1.3: return "🔴 極危險"
                elif val > avg_val * 1.2: return "🟠 危險"
                elif val > avg_val * 1.1: return "🟡 注意"
                else: return "🟢 安全"

            rank_colors = [
                "linear-gradient(135deg, #c62828, #e53935)",
                "linear-gradient(135deg, #d32f2f, #ef5350)",
                "linear-gradient(135deg, #e53935, #e57373)",
                "linear-gradient(135deg, #f4511e, #ff8a65)",
                "linear-gradient(135deg, #fb8c00, #ffb74d)",
            ]

            st.markdown('<div class="section-title">🔥 危險指數 (PDI) - 縣市平均 Top 5</div>', unsafe_allow_html=True)
            st.caption("呈現各縣市整體的平均危險度，反映該城市的宏觀交通體質。")
            
            city_rank = pdi_df.groupby("nightmarket_city").agg(
                夜市數量=("nightmarket_name", "count"),
                事故總數=("accident_count", "sum"),
                death_count=("death_count", "sum"),
                PDI總和=("pdi", "sum"),
            ).reset_index().rename(columns={"nightmarket_city": "城市"})
            
            city_rank["日均PDI"] = (city_rank["PDI總和"] / city_rank["夜市數量"] / days_divisor).round(2)
            city_avg_pdi = city_rank["日均PDI"].mean()
            city_rank["危險等級"] = city_rank["日均PDI"].apply(lambda x: get_dynamic_level(x, city_avg_pdi))
            
            city_top5 = city_rank.sort_values("日均PDI", ascending=False).head(5)
            
            cols_city = st.columns(5)
            for idx, (_, row) in enumerate(city_top5.reset_index(drop=True).iterrows()):
                bg_color = rank_colors[idx]
                diff_pct = ((row["日均PDI"] - city_avg_pdi) / city_avg_pdi * 100) if city_avg_pdi > 0 else 0
                with cols_city[idx]:
                    st.markdown(f"""
                    <div class="pdi-card" style="background:{bg_color};">
                        <div style="font-size:12px; font-weight:bold; margin-bottom:5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">🏆 第 {idx+1} 名</div>
                        <div style="font-size:20px; font-weight:900; margin-bottom:5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">{row['城市']}</div>
                        <div style="font-size:13px; font-weight:bold; margin-bottom:8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">高於全台均值：{diff_pct:.1f}%</div>
                        <div style="font-size:12px; background:rgba(0,0,0,0.2); padding:5px; border-radius:5px; line-height:1.4;">
                            💀 死亡人數：{row['death_count']} 人<br>💥 事故總數：{row['事故總數']} 件
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            st.markdown('<div class="section-title">🔥 危險指數 (PDI) - 單一夜市 Top 5</div>', unsafe_allow_html=True)
            st.caption("獨立比較全台各個夜市，找出肇事率最高的微觀熱點。")
            
            mkt_df = pdi_df.copy()
            mkt_df["日均PDI"] = (mkt_df["pdi"] / days_divisor).round(2)
            mkt_avg_pdi = mkt_df["日均PDI"].mean()
            mkt_df["危險等級"] = mkt_df["日均PDI"].apply(lambda x: get_dynamic_level(x, mkt_avg_pdi))
            
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
                        <div style="font-size:13px; font-weight:bold; margin-bottom:8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">高於全台均值：{diff_pct:.1f}%</div>
                        <div style="font-size:12px; background:rgba(0,0,0,0.2); padding:5px; border-radius:5px; line-height:1.4;">
                            💀 死亡人數：{row['death_count']} 人<br>💥 事故總數：{row['accident_count']} 件
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
            st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)

            col_t1, col_t2 = st.columns(2, gap="large")
            with col_t1:
                st.markdown('<div class="section-title">🏙️ 城市排行榜 TOP10</div>', unsafe_allow_html=True)
                city_rank_display = city_rank.sort_values("日均PDI", ascending=False).head(10).reset_index(drop=True)
                st.dataframe(city_rank_display[["城市", "夜市數量", "事故總數", "日均PDI", "危險等級"]], height=320, use_container_width=True, hide_index=True)

            with col_t2:
                st.markdown('<div class="section-title">⭐ 全台夜市: 危險程度 TOP10</div>', unsafe_allow_html=True)
                mkt_display = mkt_df.sort_values("日均PDI", ascending=False).head(10)
                st.dataframe(
                    mkt_display.rename(columns={"nightmarket_name": "夜市名稱", "nightmarket_rating": "Google 評分"})
                    [["nightmarket_city", "夜市名稱", "Google 評分", "日均PDI", "危險等級"]], 
                    height=320, use_container_width=True, hide_index=True
                )
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_c1, col_c2 = st.columns(2, gap="large")
            with col_c1:
                st.markdown('<div class="section-title">📈 歷年縣市排行變化 (Top 10)</div>', unsafe_allow_html=True)
                st.caption("與前一年度比較之排名升降")
                if not city_rank_table.empty:
                    st.dataframe(city_rank_table, height=350, use_container_width=True, hide_index=True)

            with col_c2:
                st.markdown('<div class="section-title">📈 歷年夜市排行變化 (Top 10)</div>', unsafe_allow_html=True)
                st.caption("與前一年度比較之排名升降")
                if not mkt_rank_table.empty:
                    st.dataframe(mkt_rank_table, height=350, use_container_width=True, hide_index=True)

        else:
            st.info("👈 在目前條件下，無任何符合的快取資料。")

if __name__ == "__main__":
    main()