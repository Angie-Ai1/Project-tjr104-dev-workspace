import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import core.c_data_service as ds
import core.c_ui as ui

st.set_page_config(layout="wide", page_title="政策成效即時監控", page_icon="⚖️")

@st.cache_data(show_spinner=False)
def get_policy_analysis_data():
    try:
        raise NotImplementedError("使用模擬數據渲染版面")
    except:
        np.random.seed(42)
        dates = pd.date_range(start="2021-01-01", end=datetime.now().strftime("%Y-%m-%d"), freq="D")
        
        city_region_map = {
            "臺北市": "北部", "新北市": "北部", "桃園市": "北部", "新竹縣": "北部",
            "臺中市": "中部", "彰化縣": "中部",
            "臺南市": "南部", "高雄市": "南部", "屏東縣": "南部",
            "花蓮縣": "東部", "臺東縣": "東部"
        }
        cities = list(city_region_map.keys())
        weathers = ["晴天", "雨天", "陰天"]
        
        data = []
        for d in dates:
            is_after_policy = d >= pd.to_datetime("2023-06-30")
            daily_accidents = np.random.randint(15, 50) if not is_after_policy else np.random.randint(12, 45)
            
            for _ in range(daily_accidents):
                city = np.random.choice(cities)
                region = city_region_map[city]
                death_prob = 0.02 if region in ["東部", "中部"] else 0.008
                death = np.random.choice([0, 1], p=[1-death_prob, death_prob])
                injury = np.random.randint(0, 3)
                cause_prob = [0.35, 0.65] if not is_after_policy else [0.20, 0.80]
                cause = np.random.choice(["車輛未依規定暫停讓行人先行", "其他不當駕駛行為"], p=cause_prob)
                hour = int(np.random.normal(20, 3)) % 24 
                weather = np.random.choice(weathers, p=[0.6, 0.2, 0.2])
                
                data.append({
                    "accident_date": d,
                    "year_month": d.strftime("%Y-%m"),
                    "hour": hour,
                    "city": city,
                    "region": region,
                    "weather": weather,
                    "death_count": death,
                    "injury_count": injury,
                    "primary_cause": cause
                })
        df = pd.DataFrame(data)
        df["pdi"] = df["death_count"] * 5 + df["injury_count"] * 2
        return df

def main():
    df_market = ds.get_all_nightmarkets()
    ui.render_sidebar(df_market)
    
    st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > div { padding-bottom: 0rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='margin-top: 0px; margin-bottom: 5px;'>⚖️ 禮讓行人政策成效：修法前後分析研究</h2>", unsafe_allow_html=True)
    
    st.info("本儀表板持續監控自 2023 年 6 月 30 日《道路交通管理處罰條例》修正案（禮讓行人新制）實施以來的長期成效，資料涵蓋至最新時間。結合多維度數據，旨在找出政策落實的優勢與盲點，作為未來滾動式修正之科學依據。")
    st.markdown("---")

    with st.spinner("正在加載政策成效數據..."):
        df_raw = get_policy_analysis_data()
        
    if df_raw.empty:
        st.warning("目前無數據可供分析。")
        return

    target_cause_pattern = "未依規定暫停讓行人|搶越行人穿越道"

    with st.container(border=True):
        f_col_year, f_col1, f_col2, f_col3 = st.columns([1, 1, 1, 1.5])
        with f_col_year:
            year_opts = ["全部年份"] + sorted(list(df_raw['accident_date'].dt.year.unique()), reverse=True)
            sel_year = st.selectbox("📅 選擇分析年份", year_opts)
        with f_col1:
            region_opts = ["全部區域"] + sorted(list(df_raw['region'].unique()))
            sel_region = st.selectbox("🗺️ 選擇分析區域", region_opts)
        with f_col2:
            if sel_region == "全部區域":
                city_opts = ["全部縣市"] + sorted(list(df_raw['city'].unique()))
            else:
                city_opts = ["全部縣市"] + sorted(list(df_raw[df_raw['region'] == sel_region]['city'].unique()))
            sel_city = st.selectbox("🏙️ 選擇分析縣市", city_opts)
        with f_col3:
            st.markdown("<div style='margin-top: 30px; font-size: 13px; color: #64748b;'>💡 提示：選擇「全部年份」將對比修法前後；選擇「單一年份」將比較該年與前一年的成效變化 (YoY)。</div>", unsafe_allow_html=True)

    # 1. 空間過濾 (區域與縣市)
    df_spatial = df_raw.copy()
    if sel_region != "全部區域":
        df_spatial = df_spatial[df_spatial['region'] == sel_region]
    if sel_city != "全部縣市":
        df_spatial = df_spatial[df_spatial['city'] == sel_city]

    if df_spatial.empty:
        st.info("該條件下無事故資料。")
        return

    # 2. 時間與 YoY 比較邏輯切換
    if sel_year == "全部年份":
        date_policy_start, date_policy_end = pd.to_datetime("2023-07-01"), datetime.now()
        date_pre_start, date_pre_end = pd.to_datetime("2022-07-01"), pd.to_datetime("2023-06-30")

        df_yoy_pre = df_spatial[(df_spatial['accident_date'] >= date_pre_start) & (df_spatial['accident_date'] <= date_pre_end)]
        df_yoy_post = df_spatial[(df_spatial['accident_date'] >= date_policy_start) & (df_spatial['accident_date'] <= date_policy_end)]
        df_trend = df_spatial.copy()

        pre_label = "修法前 (22/07-23/06)"
        post_label = "修法後 (23/07-至今)"
    else:
        target_year = int(sel_year)
        pre_year = target_year - 1

        df_yoy_pre = df_spatial[df_spatial['accident_date'].dt.year == pre_year]
        df_yoy_post = df_spatial[df_spatial['accident_date'].dt.year == target_year]
        df_trend = df_spatial[df_spatial['accident_date'].dt.year == target_year]

        pre_label = f"{pre_year}年"
        post_label = f"{target_year}年"

    col_left, col_right = st.columns([1.5, 1.1], gap="large")

    with col_left:
        st.markdown("#### 事故趨勢軌跡與政策分水嶺")
        with st.container(border=True):
            trend_df = df_trend.groupby('year_month').agg(total_accidents=('accident_date', 'count')).reset_index()
            cause_monthly = df_trend[df_trend['primary_cause'].str.contains(target_cause_pattern, na=False, regex=True)].groupby('year_month').size()
            trend_df['target_ratio'] = (trend_df['year_month'].map(cause_monthly).fillna(0) / trend_df['total_accidents'] * 100).round(1)

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(x=trend_df['year_month'], y=trend_df['total_accidents'], name='每月總事故件數', marker_color='rgba(59, 130, 246, 0.4)', yaxis='y1'))
            fig_trend.add_trace(go.Scatter(x=trend_df['year_month'], y=trend_df['target_ratio'], name='未讓行人佔比 (%)', mode='lines+markers', line=dict(color='#ef4444', width=3), yaxis='y2'))
            
            # 若包含 2023 年，則畫出修法分隔線
            if sel_year == "全部年份" or sel_year == 2023:
                fig_trend.add_vline(x='2023-06', line_dash="dash", line_color="#8b5cf6", line_width=2)
                fig_trend.add_annotation(x='2023-06', y=1.05, yref='paper', text="<b>🚨 2023/6/30 新法上路</b>", showarrow=False, font=dict(size=13, color="#8b5cf6"), xanchor="left")
            
            fig_trend.update_layout(
                xaxis=dict(type='category', tickangle=-45), yaxis=dict(title="總事故數", side="left", showgrid=False),
                yaxis2=dict(title="未讓行人佔比 (%)", side="right", overlaying="y", showgrid=True, gridcolor='#f1f5f9'),
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1), height=320, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor='white'
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        st.markdown("#### 政策盲區：一天中哪個時段的違規純度最高？")
        st.caption(f"分析比較各時段「未停讓行人」佔總事故比例。若 {post_label} 高於 {pre_label}，代表該時段約束力衰退。")
        with st.container(border=True):
            def get_hourly_ratio(data_df):
                if data_df.empty:
                    return pd.DataFrame({'hour': range(24), 'ratio': 0})
                total = data_df.groupby('hour').size().reset_index(name='total_acc')
                target = data_df[data_df['primary_cause'].str.contains(target_cause_pattern, na=False, regex=True)].groupby('hour').size().reset_index(name='target_acc')
                merged = pd.merge(pd.DataFrame({'hour': range(24)}), total, on='hour', how='left')
                merged = pd.merge(merged, target, on='hour', how='left').fillna(0)
                merged['ratio'] = np.where(merged['total_acc'] > 0, (merged['target_acc'] / merged['total_acc'] * 100).round(1), 0)
                return merged

            hourly_pre = get_hourly_ratio(df_yoy_pre)
            hourly_post = get_hourly_ratio(df_yoy_post)

            fig_blind = go.Figure()
            if not df_yoy_pre.empty:
                fig_blind.add_trace(go.Scatter(
                    x=hourly_pre['hour'], y=hourly_pre['ratio'], name=pre_label, mode='lines+markers', 
                    line=dict(color='#94a3b8', width=2, dash='dash'), marker=dict(size=6)
                ))
            if not df_yoy_post.empty:
                fig_blind.add_trace(go.Scatter(
                    x=hourly_post['hour'], y=hourly_post['ratio'], name=post_label, mode='lines+markers', 
                    line=dict(color='#ef4444', width=3), marker=dict(size=8)
                ))
            fig_blind.add_vrect(x0=16.5, x1=23.5, fillcolor="#f59e0b", opacity=0.1, layer="below", line_width=0, annotation_text=" 夜市營運高峰", annotation_position="top left", annotation_font_color="#b45309")
            fig_blind.add_vrect(x0=-0.5, x1=1.5, fillcolor="#f59e0b", opacity=0.1, layer="below", line_width=0)

            max_y = max(hourly_pre['ratio'].max() if not hourly_pre.empty else 0, hourly_post['ratio'].max() if not hourly_post.empty else 0) * 1.2
            
            fig_blind.update_layout(
                height=350, margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(title="小時 (0-23)", tickmode='linear', dtick=1),
                yaxis=dict(title="未讓行人佔比 (%)", range=[0, max_y if max_y > 0 else 10]),
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
                plot_bgcolor='white', hovermode="x unified"
            )
            st.plotly_chart(fig_blind, use_container_width=True)

    with col_right:
        st.markdown("#### 各縣市 YoY 變化狀況")
        st.caption(f"呈現各縣市 {post_label} vs. {pre_label} 的 PDI 改善率。綠色向左為進步，紅色向右為惡化。")
        
        with st.container(border=True):
            city_stats = []
            for city in df_spatial['city'].unique():
                pre_data = df_yoy_pre[df_yoy_pre['city'] == city]
                post_data = df_yoy_post[df_yoy_post['city'] == city]
                
                pdi_pre = pre_data['pdi'].mean() if not pre_data.empty else 0
                pdi_post = post_data['pdi'].mean() if not post_data.empty else 0
                
                if pd.isna(pdi_pre) or pdi_pre == 0: continue
                delta = ((pdi_post - pdi_pre) / pdi_pre * 100)
                city_stats.append({"縣市": city, f"{pre_label} PDI": pdi_pre, f"{post_label} PDI": pdi_post, "改善率": delta})
            
            df_city = pd.DataFrame(city_stats)
            if not df_city.empty:
                df_city = df_city.sort_values('改善率', ascending=True)
                df_city['color'] = np.where(df_city['改善率'] < 0, '#10b981', '#ef4444')
                
                fig_gap = go.Figure()
                fig_gap.add_trace(go.Bar(
                    x=df_city['改善率'], y=df_city['縣市'], orientation='h',
                    marker_color=df_city['color'], text=df_city['改善率'].apply(lambda x: f"{x:+.1f}%"), textposition='outside'
                ))
                fig_gap.update_layout(
                    height=max(250, len(df_city) * 40), margin=dict(l=0, r=40, t=10, b=0),
                    xaxis=dict(title="YoY 改善率 (%)", zeroline=True, zerolinewidth=2, zerolinecolor='black'),
                    yaxis=dict(title="", tickfont=dict(size=13, weight='bold')), plot_bgcolor='white', showlegend=False
                )
                max_abs_val = df_city['改善率'].abs().max()
                if not pd.isna(max_abs_val) and max_abs_val > 0:
                    fig_gap.update_xaxes(range=[-max_abs_val*1.3, max_abs_val*1.3])
                st.plotly_chart(fig_gap, use_container_width=True)
                
                st.markdown("#### 詳細數據")
                st.dataframe(
                    df_city[['縣市', f"{pre_label} PDI", f"{post_label} PDI", '改善率']].style.format({f"{pre_label} PDI": '{:.2f}', f"{post_label} PDI": '{:.2f}', '改善率': '{:+.1f}%'}),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("由於年份或資料範圍限制，無足夠對比資料產生 YoY Gap 分析。")

if __name__ == "__main__":
    main()