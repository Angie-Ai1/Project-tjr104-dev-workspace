import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import redis
import pickle
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import core.c_data_service as ds
import core.c_ui as ui

st.set_page_config(layout="wide", page_title="各縣市夜市事故比較分析", page_icon="🏙️")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_redis_stats(year):
    try:
        final_redis_host = "redis" if os.getenv("AIRFLOW_HOME") else "127.0.0.1"
        r = redis.Redis(host=final_redis_host, port=int(os.getenv("REDIS_PORT", 6379)), password=os.getenv("REDIS_PASSWORD", "123456"), db=0)
        
        key = f"market:pdi_stats_cache_{year}"
        data = r.get(key)
        
        if data:
            df = pd.DataFrame(pickle.loads(data))
            df['year'] = year
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

def build_rank_change_table(df, entity_col):
    if df.empty: return pd.DataFrame()
    
    yearly_df = df.groupby(['year', entity_col])['pdi'].sum().reset_index()
    # 使用 method='first' 強制排序，避免抓出超過 10 筆資料
    yearly_df['Rank'] = yearly_df.groupby('year')['pdi'].rank(ascending=False, method='first')
    
    rank_pivot = yearly_df.pivot(index=entity_col, columns='year', values='Rank')
    years = sorted(yearly_df['year'].unique(), reverse=True)
    display_years = [y for y in years if y >= 2023]
    
    result_dict = {}
    for y in display_years:
        prev_y = y - 1
        current_top10 = yearly_df[(yearly_df['year'] == y) & (yearly_df['Rank'] <= 10)].sort_values('Rank')
        
        formatted_list = []
        for _, row in current_top10.iterrows():
            entity = row[entity_col]
            curr_rank = row['Rank']
            
            if prev_y in rank_pivot.columns and not pd.isna(rank_pivot.at[entity, prev_y]):
                prev_rank = rank_pivot.at[entity, prev_y]
                diff = prev_rank - curr_rank
                if diff > 0: trend = f"🔼 {int(diff)}"
                elif diff < 0: trend = f"🔽 {int(-diff)}"
                else: trend = "➖"
            else:
                trend = "🆕"
            formatted_list.append(f"{entity} ({trend})")
            
        while len(formatted_list) < 10:
            formatted_list.append("-")
        result_dict[str(y)] = formatted_list
        
    res_df = pd.DataFrame(result_dict)
    if not res_df.empty:
        res_df.insert(0, '名次', [f"第 {i} 名" for i in range(1, 11)])
    return res_df

def get_dynamic_level(val, avg_val):
    if avg_val == 0: return "🟢 安全"
    if val > avg_val * 1.3: return "🔴 極危險"
    elif val > avg_val * 1.2: return "🟠 危險"
    elif val > avg_val * 1.1: return "🟡 注意"
    else: return "🟢 安全"

def main():
    df_market = ds.get_all_nightmarkets()
    ui.render_sidebar(df_market)
    
    st.markdown("""
    <style>
    .kpi-box { background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #e5e7eb; }
    .kpi-title { font-size: 13px; color: #6b7280; margin-bottom: 2px; }
    .kpi-value { font-size: 22px; font-weight: bold; color: #111827; }
    .kpi-delta { font-size: 12px; font-weight: bold; }
    .delta-good { color: #10b981; }
    .delta-bad { color: #ef4444; }
    div[data-testid="stVerticalBlock"] > div { padding-bottom: 0rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <h2 style="margin-top: 0px; margin-bottom: 5px;">🏙️ 各縣市夜市事故比較分析：<span style="color:#3b82f6;">城市安全對標</span></h2>
        <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; border-left: 5px solid #10b981; margin-bottom: 15px; font-size: 14px; color: #374151; line-height: 1.6;">
            <b>終結行人地獄，從客觀對標開始；每一個數據，都攸關您我安全回家的路。</b><br>
            我們深知在地居民最在乎的是「我家附近的夜市夠安全嗎？」同時，數據的起伏也是檢驗地方交通治理的重要指標。我們將單一城市的事故現況與「全台平均基準」進行嚴格對標，不只點出最需要改善的交通熱點，更如實呈現歷年安全政策的進步軌跡。讓我們一起督促並規劃更低風險的安全生活圈！
        </div>
    """, unsafe_allow_html=True)

    all_years = [2021, 2022, 2023, 2024, 2025, 2026]
    dict_all_data = {}
    for y in all_years:
        df_y = fetch_redis_stats(y)
        if not df_y.empty:
            dict_all_data[y] = df_y
    df_all_years = pd.concat(dict_all_data.values(), ignore_index=True) if dict_all_data else pd.DataFrame()

    col_left, col_mid, col_right = st.columns([1, 2, 1.3], gap="small")

    with col_left:
        st.markdown("#### 1. 選擇目標")
        region_map = {
            "臺北市": "北部", "新北市": "北部", "基隆市": "北部", "桃園市": "北部", "新竹市": "北部", "新竹縣": "北部",
            "臺中市": "中部", "苗栗縣": "中部", "彰化縣": "中部", "南投縣": "中部", "雲林縣": "中部",
            "臺南市": "南部", "高雄市": "南部", "嘉義市": "南部", "嘉義縣": "南部", "屏東縣": "南部",
            "宜蘭縣": "東部", "花蓮縣": "東部", "臺東縣": "東部",
            "澎湖縣": "離島", "金門縣": "離島", "連江縣": "離島"
        }
        df_market['Region'] = df_market['nightmarket_city'].map(region_map).fillna("其他")
        
        dist_opts = sorted(df_market['Region'].dropna().unique())
        def_dist_idx = dist_opts.index("北部") if "北部" in dist_opts else 0
        sel_region = st.selectbox("區域", dist_opts, index=def_dist_idx, label_visibility="collapsed")
        
        city_opts = sorted(df_market[df_market['Region'] == sel_region]['nightmarket_city'].unique())
        def_city_idx = city_opts.index("臺北市") if "臺北市" in city_opts else 0
        sel_city = st.selectbox("縣市", city_opts, index=def_city_idx, label_visibility="collapsed")
        
        st.markdown("#### 2. 分析時間篩選")
        year_options = ["全部年份"] + [str(y) for y in sorted(dict_all_data.keys(), reverse=True)]
        
        # 設定預設年份為 2025
        def_year_idx = year_options.index("2025") if "2025" in year_options else 0
        sel_year_str = st.selectbox("年份", year_options, index=def_year_idx)
        
        c_q, c_m, c_w = st.columns(3)
        with c_q: st.selectbox("季度", ["全年"], disabled=True)
        with c_m: st.selectbox("月份", ["全部"], disabled=True)
        with c_w: st.selectbox("星期", ["全部"], disabled=True)
        
        st.radio("時段", ["🔴 全部", "☀️ 白天 (06-18)", "🌙 夜間 (18-06)"], horizontal=True, key="time_shift")

        with st.container(border=True):
            st.markdown("#### 歷年事故趨勢")
            city_trend = df_all_years[df_all_years['nightmarket_city'] == sel_city]
            if not city_trend.empty:
                trend_agg = city_trend.groupby('year').agg({'pdi': 'mean', 'accident_count': 'sum'}).reset_index().sort_values('year')
                nat_trend_agg = df_all_years.groupby('year').agg({'pdi': 'mean'}).reset_index().sort_values('year')
                
                fig = go.Figure()
                fig.add_trace(go.Bar(x=trend_agg['year'], y=trend_agg['accident_count'], name='該縣市總事故數', marker_color='#3b82f6', yaxis='y1'))
                fig.add_trace(go.Scatter(x=trend_agg['year'], y=trend_agg['pdi'], name='該縣市平均 PDI', mode='lines+markers', line=dict(color='#ef4444', width=2), marker=dict(size=6), yaxis='y2'))
                fig.add_trace(go.Scatter(x=nat_trend_agg['year'], y=nat_trend_agg['pdi'], name='全國平均 PDI', mode='lines', line=dict(color='#64748b', width=2, dash='dash'), yaxis='y2'))
                
                fig.update_layout(
                    xaxis=dict(type='category'),
                    yaxis=dict(title="事故數", side="left", showgrid=False),
                    yaxis2=dict(title="平均 PDI", side="right", overlaying="y", showgrid=True, gridcolor='#f1f5f9'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="right", x=1),
                    margin=dict(l=0, r=0, t=0, b=0), height=250
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("無趨勢資料")

    if df_all_years.empty:
        st.warning("⚠️ 無法取得 Redis 資料，請確認排程狀態。")
        return

    if sel_year_str == "全部年份":
        df_sel = fetch_redis_stats('all')
        calc_year = "歷年累計"
        days_count = len(all_years) * 365
        yoy_val, yoy_text = 0, "無 (請選擇單一年份)"
        yoy_title_suffix = ""
    else:
        calc_year = int(sel_year_str)
        days_count = 365
        df_sel = dict_all_data.get(calc_year, pd.DataFrame())
        yoy_val, yoy_text = 0, "無前期資料"
        
        if calc_year - 1 in dict_all_data:
            df_prev = dict_all_data[calc_year - 1]
            pdi_curr = df_sel[df_sel['nightmarket_city'] == sel_city]['pdi'].sum()
            pdi_prev = df_prev[df_prev['nightmarket_city'] == sel_city]['pdi'].sum()
            if pdi_prev > 0:
                yoy_val = ((pdi_curr - pdi_prev) / pdi_prev) * 100
                yoy_text = "↑ 惡化" if yoy_val > 0 else "↓ 進步"

    df_city_sel = df_sel[df_sel['nightmarket_city'] == sel_city] if not df_sel.empty else pd.DataFrame()
    
    nat_avg_pdi = df_sel['pdi'].mean() if not df_sel.empty else 0
    nat_avg_acc = df_sel['accident_count'].mean() if not df_sel.empty else 0
    daily_nat_avg_pdi = nat_avg_pdi / days_count if days_count > 0 else 0

    city_avg_pdi = df_city_sel['pdi'].mean() if not df_city_sel.empty else 0
    city_avg_acc = df_city_sel['accident_count'].mean() if not df_city_sel.empty else 0
    daily_city_avg_pdi = city_avg_pdi / days_count if days_count > 0 else 0

    with col_mid:
        with st.container(border=True):
            st.markdown(f"#### 📊 {sel_city} 安全體檢表 ({calc_year})")
            st.caption("💡 PDI 評估基準：計算「日均 PDI」並對標全台平均。高於均值 10% 🟡注意，高於 20% 🟠危險，高於 30% 🔴極危險。")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                delta_pdi = city_avg_pdi - nat_avg_pdi
                c_class = "delta-bad" if delta_pdi > 0 else "delta-good"
                sign = "+" if delta_pdi > 0 else ""
                st.markdown(f"<div class='kpi-box'><div class='kpi-title'>平均夜市 PDI</div><div class='kpi-value'>{city_avg_pdi:.1f}</div><div class='kpi-delta {c_class}'>{sign}{delta_pdi:.1f} (vs國均)</div></div>", unsafe_allow_html=True)
            with k2:
                st.markdown(f"<div class='kpi-box'><div class='kpi-title'>日均危險評級</div><div class='kpi-value'>{get_dynamic_level(daily_city_avg_pdi, daily_nat_avg_pdi)}</div><div class='kpi-delta' style='color:#6b7280;'>依日均 PDI 判定</div></div>", unsafe_allow_html=True)
            with k3:
                delta_acc = city_avg_acc - nat_avg_acc
                c_class_acc = "delta-bad" if delta_acc > 0 else "delta-good"
                sign_acc = "+" if delta_acc > 0 else ""
                st.markdown(f"<div class='kpi-box'><div class='kpi-title'>平均事故件數</div><div class='kpi-value'>{city_avg_acc:.0f} 件</div><div class='kpi-delta {c_class_acc}'>{sign_acc}{delta_acc:.0f} (vs國均)</div></div>", unsafe_allow_html=True)
            with k4:
                c_class_yoy = "delta-bad" if yoy_val > 0 else "delta-good" if yoy_val < 0 else ""
                display_yoy = f"{abs(yoy_val):.1f}%" if sel_year_str != "全部年份" and yoy_val != 0 else "-"
                st.markdown(f"<div class='kpi-box'><div class='kpi-title'>年度 PDI 進步率</div><div class='kpi-value'>{display_yoy}</div><div class='kpi-delta {c_class_yoy}'>{yoy_text}</div></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown(f"#### 🎯 {sel_city} 夜市安全風險象限分析")
            if not df_city_sel.empty and len(df_city_sel) > 1:
                fig_scatter = px.scatter(
                    df_city_sel, x="accident_count", y="pdi", text="nightmarket_name",
                    hover_data=["accident_count", "pdi"], color="pdi", color_continuous_scale="Reds",
                    labels={"accident_count": "事故發生件數", "pdi": "危險指數 PDI"}
                )
                fig_scatter.add_hline(y=nat_avg_pdi, line_dash="dot", line_color="#64748b", annotation_text="全國平均 PDI")
                fig_scatter.add_vline(x=nat_avg_acc, line_dash="dot", line_color="#64748b", annotation_text="全國平均事故數")
                fig_scatter.update_traces(textposition='top center', marker=dict(size=12, opacity=0.8))
                fig_scatter.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.info("資料點不足以繪製象限圖")

        with st.container(border=True):
            st.markdown(f"#### 📉 歷年夜市排行變化 (Top 10)")
            if not df_all_years.empty:
                city_hist_df = df_all_years[df_all_years['nightmarket_city'] == sel_city]
                mkt_rank_table = build_rank_change_table(city_hist_df, 'nightmarket_name')
                if not mkt_rank_table.empty:
                    st.dataframe(mkt_rank_table, use_container_width=True, hide_index=True)
                else:
                    st.info("尚無足夠歷年數據可供比較")
            else:
                st.info("尚無歷年數據")

    with col_right:
        with st.container(border=True):
            st.markdown(f"#### ⏳ {sel_city} 危險夜市 TOP10")
            if not df_city_sel.empty:
                top10_df = df_city_sel.sort_values('pdi', ascending=False).head(10).reset_index(drop=True)
                top10_df['排名'] = top10_df.index + 1
                top10_df['等級'] = top10_df['pdi'].apply(lambda x: get_dynamic_level(x/days_count, daily_nat_avg_pdi).split(' ')[0])
                st.dataframe(
                    top10_df[['排名', 'nightmarket_name', 'pdi', 'accident_count', '等級']].rename(columns={'nightmarket_name':'夜市名稱', 'accident_count':'事故數'}),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("無資料")

        with st.container(border=True):
            yoy_list = []
            if sel_year_str != "全部年份" and (calc_year - 1) in dict_all_data:
                df_prev_city = dict_all_data[calc_year - 1][dict_all_data[calc_year - 1]['nightmarket_city'] == sel_city]
                for _, row in df_city_sel.iterrows():
                    nm_name = row['nightmarket_name']
                    curr_pdi = row['pdi']
                    prev_row = df_prev_city[df_prev_city['nightmarket_name'] == nm_name]
                    if not prev_row.empty:
                        prev_pdi = prev_row.iloc[0]['pdi']
                        if prev_pdi > 0:
                            delta = ((curr_pdi - prev_pdi) / prev_pdi) * 100
                            yoy_list.append({'夜市': nm_name, 'YoY': delta})
            
            worse_cnt = sum(1 for x in yoy_list if x['YoY'] > 0)
            better_cnt = sum(1 for x in yoy_list if x['YoY'] < 0)
            
            if sel_year_str == "全部年份":
                yoy_title_suffix = ""
            elif not yoy_list:
                yoy_title_suffix = f"({calc_year} vs {calc_year-1})"
            else:
                yoy_title_suffix = f"({calc_year} vs {calc_year-1}) &nbsp;|&nbsp; 🔴 {worse_cnt} 惡化, 🟢 {better_cnt} 進步"

            st.markdown(f"#### ⚖️ YoY 變化率 <span style='font-size:14px; color:#6b7280; font-weight:normal;'>{yoy_title_suffix}</span>", unsafe_allow_html=True)
            
            if sel_year_str == "全部年份":
                st.info("請選擇單一年份比較。")
            else:
                if yoy_list:
                    yoy_df = pd.DataFrame(yoy_list).sort_values('YoY', ascending=False)
                    st.dataframe(
                        yoy_df.style.format({'YoY': '{:+.1f}%'}).map(lambda x: 'color: #ef4444' if x > 0 else 'color: #10b981', subset=['YoY']),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.write("無同期比較資料")

if __name__ == "__main__":
    main()