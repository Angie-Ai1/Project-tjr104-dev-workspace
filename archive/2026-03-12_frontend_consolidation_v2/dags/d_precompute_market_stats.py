from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import redis
import pickle
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_db_engine():
    if cloud_sql_url := os.getenv("CLOUDSQL_URL"):
        return create_engine(cloud_sql_url, pool_pre_ping=True)
    
    passwd = quote_plus(os.getenv("MYSQL_PASSWORD", "123456"))
    target_db = os.getenv("MYSQL_DATABASE", "frontend_db_consol")
    uri = f"mysql+pymysql://root:{passwd}@127.0.0.1:3308/{target_db}?charset=utf8mb4"
    return create_engine(uri, pool_pre_ping=True)

def load_night_markets():
    engine = get_db_engine()
    return pd.read_sql("SELECT * FROM `test_night_market`.`Night_market_merge`", engine)

def precompute_market_stats():
    nm_df = load_night_markets()
    engine = get_db_engine()
    
    final_redis_host = "redis" if os.getenv("AIRFLOW_HOME") else "127.0.0.1"
    r = redis.Redis(host=final_redis_host, port=int(os.getenv("REDIS_PORT", 6379)), password=os.getenv("REDIS_PASSWORD", "123456"), db=0)
    
    # 定義要獨立計算的目標：先算全部，再依序算各個年份
    target_years = ['all', 2026, 2025, 2024, 2023, 2022, 2021]
    
    # ⭐ 新增：用於儲存 Act3 避險指南的字典
    act3_guides = {nm["nightmarket_name"].strip(): {"df_list": []} for _, nm in nm_df.iterrows()}
    
    # 迴圈：一年一年獨立向資料庫查詢，算完就清空記憶體
    for target_year in target_years:
        print(f"開始處理年份: {target_year}")
        
        # 建立該年份專屬的計分板 (⭐ 新增 dead 與 hurt 欄位統計)
        stats_board = {nm["nightmarket_name"].strip(): {"count": 0, "pdi": 0.0, "dead": 0, "hurt": 0} for _, nm in nm_df.iterrows()}
        heatmap_list = []
        
        # 根據年份動態組裝 SQL 語法，把過濾壓力交給資料庫 (⭐ 修改：改向新的大寬表撈取，並多抓 Hour 與 weather_condition)
        if target_year == 'all':
            query = "SELECT latitude, longitude, death_count, injury_count, accident_datetime, weather_condition, Hour FROM `frontend_db_consol`.`tbl_accident_analysis_final`"
        else:
            query = f"SELECT latitude, longitude, death_count, injury_count, accident_datetime, weather_condition, Hour FROM `frontend_db_consol`.`tbl_accident_analysis_final` WHERE Year = {target_year}"
            
        # 針對「該年份」，每次只拿 5 萬筆進來算，算完就丟掉換下一批
        for chunk in pd.read_sql(query, engine, chunksize=50000):
            chunk["accident_datetime"] = pd.to_datetime(chunk["accident_datetime"])
            # chunk["hour"] = chunk["accident_datetime"].dt.hour # 大寬表已經有 Hour 欄位，直接用即可
            
            chunk["weight"] = np.where((chunk["Hour"] >= 17) | (chunk["Hour"] == 0), 3, 1)
            chunk["severity"] = chunk["death_count"] * 5 + chunk["injury_count"] * 2
            chunk["pdi_score"] = chunk["severity"] * chunk["weight"]
            
            lats, lons = chunk["latitude"].values, chunk["longitude"].values
            scores = chunk["pdi_score"].values
            deaths = chunk["death_count"].values
            hurts = chunk["injury_count"].values
            
            for _, nm in nm_df.iterrows():
                name = nm["nightmarket_name"].strip()
                mask = (lats >= nm["nightmarket_southwest_latitude"]) & (lats <= nm["nightmarket_northeast_latitude"]) & \
                       (lons >= nm["nightmarket_southwest_longitude"]) & (lons <= nm["nightmarket_northeast_longitude"])
                
                if mask.any():
                    stats_board[name]["count"] += int(mask.sum())
                    stats_board[name]["pdi"] += float(scores[mask].sum())
                    stats_board[name]["dead"] += int(deaths[mask].sum()) # ⭐ 累加死亡人數
                    stats_board[name]["hurt"] += int(hurts[mask].sum())  # ⭐ 累加受傷人數
                    
                    # ⭐ 新增：如果是 'all' 年份，把這些落在夜市的事故存起來，稍後用來算 Act3 的導航避險
                    if target_year == 'all':
                        act3_guides[name]["df_list"].append(chunk[mask])
                
            valid_heat = chunk[chunk["severity"] > 0]
            heatmap_list.extend(valid_heat[["latitude", "longitude", "pdi_score"]].values.tolist())
            
        # 該年份的資料庫批次讀取結束，準備轉換格式
        final_results = []
        for _, nm in nm_df.iterrows():
            name = nm["nightmarket_name"].strip()
            final_results.append({
                "nightmarket_id": nm.get("nightmarket_id", ""),
                "nightmarket_name": name,
                "nightmarket_city": nm.get("nightmarket_city", ""),
                "nightmarket_rating": float(nm.get("nightmarket_rating", 0.0)),
                "nightmarket_url": nm.get("nightmarket_url", ""),
                "accident_count": stats_board[name]["count"],
                "death_count": stats_board[name]["dead"],     # ⭐ 新增
                "injury_count": stats_board[name]["hurt"],    # ⭐ 新增
                "pdi": stats_board[name]["pdi"]
            })
            
        # 熱力圖抽樣
        if len(heatmap_list) > 8000:
            import random
            heatmap_list = random.sample(heatmap_list, 8000)
            
        # ⭐ 關鍵：算完一個年份，立刻存入 Redis！
        key_suffix = str(target_year)
        r.set(f"market:pdi_stats_cache_{key_suffix}", pickle.dumps(final_results), ex=864000)
        r.set(f"traffic:global_heatmap_cache_{key_suffix}", pickle.dumps(heatmap_list), ex=864000)
        
        print(f"年份 {target_year} 已成功寫入 Redis！")

    # ====================================================
    # ⭐ 新增：產出 Act 3 避險導航懶人包 (等年份跑完後，一次結算)
    # ====================================================
    print("各年份統計已完成。開始計算 Act3 避險導航懶人包...")
    final_act3_guides = {}
    for _, nm in nm_df.iterrows():
        name = nm["nightmarket_name"].strip()
        final_act3_guides[name] = None
        
        if act3_guides[name]["df_list"]:
            df_tight = pd.concat(act3_guides[name]["df_list"], ignore_index=True)
            
            # 1. 天氣與危險時段
            rain_ratio = (df_tight['weather_condition'].fillna('').str.contains('雨').sum() / len(df_tight)) * 100
            peak_hour = df_tight['Hour'].value_counts().idxmax() if not df_tight.empty else 20
            peak_period = "20–22 時" if 20 <= peak_hour <= 22 else f"{peak_hour}:00 時段"
            
            # 2. 區域風險方位
            c_lat, c_lon = nm["nightmarket_latitude"], nm["nightmarket_longitude"]
            zone_map = {
                "北側": df_tight[df_tight["latitude"] > c_lat].shape[0],
                "南側": df_tight[df_tight["latitude"] < c_lat].shape[0],
                "東側": df_tight[df_tight["longitude"] > c_lon].shape[0],
                "西側": df_tight[df_tight["longitude"] < c_lon].shape[0],
            }
            danger_zone = max(zone_map, key=zone_map.get)
            
            # 3. 最安全入口推薦 (尋找離事故群最遠的點)
            north, south = nm["nightmarket_northeast_latitude"], nm["nightmarket_southwest_latitude"]
            east, west = nm["nightmarket_northeast_longitude"], nm["nightmarket_southwest_longitude"]
            
            candidates = {
                "北側入口": [north, (west + east) / 2], "南側入口": [south, (west + east) / 2],
                "東側入口": [(south + north) / 2, east], "西側入口": [(south + north) / 2, west],
                "東北角入口": [north, east], "西北角入口": [north, west],
                "東南角入口": [south, east], "西南角入口": [south, west],
            }
            
            def min_dist(point):
                return min([np.sqrt((point[0] - lat)**2 + (point[1] - lon)**2) for lat, lon in df_tight[["latitude", "longitude"]].values])
                
            best_exit = max(candidates.items(), key=lambda x: min_dist(x[1]))
            
            final_act3_guides[name] = {
                "peak_period": peak_period,
                "rain_increase": int(rain_ratio),
                "danger_zone": f"{danger_zone} ({zone_map[danger_zone]}件)",
                "best_entry_name": best_exit[0],
                "best_entry_coord": best_exit[1]
            }
            
    # ⭐ 將避險導航指南推上 Redis (使用 pickle)
    r.set("market:act3_guide_cache", pickle.dumps(final_act3_guides), ex=864000)
    print("🎉 避險導航懶人包已成功寫入 Redis！")


default_args = {
    'owner': 'traffic_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG('nightmarket_data_sync', default_args=default_args, schedule='0 4 * * *', catchup=False) as dag:
    sync_task = PythonOperator(
        task_id='precompute_and_push_to_redis',
        python_callable=precompute_market_stats
    )