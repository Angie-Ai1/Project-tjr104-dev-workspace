import pandas as pd
import os
import ast
from shapely.geometry import Point, MultiPoint
from db_utils import get_db_engine

# ==========================================
# 1. 資料讀取
# ==========================================

def load_clean_market_df(source="mysql", csv_path="night_market_data.csv"):
    """
    :param source: 'mysql' (預設) 或 'csv'
    :param csv_path: 當 source='csv' 時的檔案路徑
    """
    if source == "mysql":
        print("--- 正在從 MYSQL 讀取夜市資料 ---")
        return _fetch_from_mysql()
    elif source == "csv":
        print(f"--- 正在從 CSV 讀取夜市資料 (Backup Mode) : {csv_path} ---")
        return _fetch_from_csv(csv_path)
    else:
        print(f"[Error] 不支援的資料來源: {source}")
        return pd.DataFrame()

# ==========================================
# 2. MYSQL 處理邏輯 (夜市經緯度為中心點格式)
# ==========================================

def _fetch_from_mysql():
    """從 MYSQL (test_NM.nightmarkets) 讀取並清洗資料"""
    engine = get_db_engine()
    if not engine:
        return pd.DataFrame()

    try:
        query = "SELECT * FROM test_NM.nightmarkets"
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if df.empty: return df
        # 1. 欄位名稱標準化 (轉小寫)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # 2. 欄位對應 (Mapping) - 針對 SQL 的新欄位名稱
        rename_map = {
            'nightmarket_name': 'MarketName',
            'city': 'City',
            'latitude': 'lat',
            'longitude': 'lon'
        }
        df = df.rename(columns=rename_map)

        # 3. 補齊缺失欄位
        if 'District' not in df.columns:
            df['District'] = '全區' 

        # 4. 清洗 'wt' 欄位, 並產生 HTML格式的營業時間表
        """
        每個 item 用 day, time_val = item.split(':', 1) 拆成「星期 → 時間」，
        再組成 schedule_dict，最後輸出成前端要顯示的 HTML 表格字串。
        """
        def format_schedule_from_wt(row):
            if 'wt' not in row or pd.isna(row['wt']):
                return '<span style="color:#ccc">無營業資訊</span>'
            try:
                # 將字串變列表: "['Mon...']" -> ['Mon...']
                schedule_list = ast.literal_eval(row['wt']) # ast.literal_eval 比較安全
                
                # 轉成字典方便查詢
                schedule_dict = {}
                for item in schedule_list:
                    if ':' in item:
                        day, time_val = item.split(':', 1)
                        schedule_dict[day.strip()] = time_val.strip()

                # 產生 HTML
                days_map = {'Monday': '一', 'Tuesday': '二', 'Wednesday': '三', 
                            'Thursday': '四', 'Friday': '五', 'Saturday': '六', 'Sunday': '日'}
                
                html = "<table style='width:100%; font-size:14px; border-collapse: collapse;'>"
                for en_day, ch_day in days_map.items():
                    time_str = schedule_dict.get(en_day, "休息")
                    display = time_str
                    if "Closed" in time_str or "休息" in time_str:
                            display = '<span style="color:#ccc">休息</span>'
                    bg = "background-color: #f9f9f9;" if en_day in ['Tuesday', 'Thursday', 'Saturday'] else ""
                    html += f"<tr style='{bg}'><td style='padding:2px 5px; font-weight:bold;'>週{ch_day}</td><td style='padding:2px 5px;'>{display}</td></tr>"
                html += "</table>"
                return html
            except Exception:
                return "<span style='color:red'>格式錯誤</span>"

        df['ScheduleHTML'] = df.apply(format_schedule_from_wt, axis=1)

        # 5. 座標格式轉換 (確保為數值型態)
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        
        return df.dropna(subset=['lat', 'lon']) # 移除座標無效的列

    except Exception as e:
        print(f"[SQL Error] 讀取失敗: {e}")
        return pd.DataFrame()

def get_all_nightmarkets():
    return load_clean_market_df(source="mysql")

# ============================================================================
# 3. CSV 處理邏輯 (夜市經緯度目前包含多重座標點, 程式碼有計算中心點 + 多邊形點格式)
# ============================================================================

def _fetch_from_csv(csv_path):
    """
    負責讀取並清洗資料, 回傳乾淨的 DataFrame (Legacy Mode)
    保留原始專案的所有註解與邏輯
    """
    if not os.path.exists(csv_path):
        print(f"找不到檔案: {csv_path}")
        return pd.DataFrame()

    try:
        # 1. 讀取 CSV
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except:
            df = pd.read_csv(csv_path, encoding='cp950')

        # 2. 欄位名稱標準化 (轉小寫、去空白)
        df.columns = [str(c).strip().lower() for c in df.columns]

        rename_map = {
            'night_market': 'MarketName', 'night_market_name': 'MarketName',
            'city': 'City', 'latitude': 'lat', 'longitude': 'lon', 'status': 'Status'
        }
        df = df.rename(columns=rename_map)

        # 3. 處理營業時間表 (HTML產生邏輯)
        days_map = {
            'monday': '一', 'tuesday': '二', 'wednesday': '三', 
            'thursday': '四', 'friday': '五', 'saturday': '六', 'sunday': '日'
        }

        # 2. 定義格式化函式 (對每一列資料執行一次)
        def format_schedule(row):
            # A. 建立表格標頭
            # 寫 HTML 字串, 定義一個寬度 100% 的表格
            schedule_html = "<table style='width:100%; font-size:14px; border-collapse: collapse;'>"
            
            has_detail = False # 記錄夜市是否有詳細的營業時間

            # B. 開始跑迴圈 (週一到週日)
            for en_day, ch_day in days_map.items():
                # 檢查 CSV 裡是否有這個欄位 (Ex結束表格, .Monday)
                if en_day in row.index:
                    time_val = str(row[en_day]).strip()  # 取得該欄位的值, 轉成字串並去除前後空白
                    
                    # C. 判斷是否為「無效資料」
                    # 如果時間為 'nan', 'none' 或空字串, 顯示灰色的「休息」
                    if time_val.lower() in ['nan', '', 'none']:
                        display = '<span style="color:#ccc">休息</span>'
                    else:
                        # 如果有正常營業時間 (Ex.17:00-24:00), 就直接顯示
                        display = time_val
                        has_detail = True # 標記真的有抓到資料
                    
                    # D. 斑馬紋樣式
                    # 如果是二、四、六, 做一個淺灰色的背景色, 讓表格比較好讀
                    bg = "background-color: #f9f9f9;" if en_day in ['tuesday', 'thursday', 'saturday'] else ""
                    
                    # E. 組合這一列 (tr = table row, td = table data)
                    # 把背景色、星期幾、營業時間全部拼進去
                    schedule_html += f"<tr style='{bg}'><td style='padding:2px 5px; font-weight:bold;'>週{ch_day}</td><td style='padding:2px 5px;'>{display}</td></tr>"
            
            # F. 結束表格
            schedule_html += "</table>" # 後面不屬於表格了
            return schedule_html

        df['ScheduleHTML'] = df.apply(format_schedule, axis=1)

        # 處理 Status 欄位 (防止 nan)
        if 'Status' not in df.columns:
            df['Status'] = "詳見營業時間表"
        else:
            df['Status'] = df['Status'].astype(str).replace({'nan': '詳見營業時間表', 'NaN': '詳見營業時間表'})

        # 座標解析 (多重座標 -> 中心點 + 多邊形點)
        def parse_coords(row):
            try:
                raw_lat = str(row['lat']).replace('"', '').replace("'", "").strip().split(',')
                raw_lon = str(row['lon']).replace('"', '').replace("'", "").strip().split(',')
                lats = [float(x) for x in raw_lat if x.strip()]
                lons = [float(x) for x in raw_lon if x.strip()]
                min_len = min(len(lats), len(lons))
                points = list(zip(lats[:min_len], lons[:min_len]))
                
                if not points: return None, None, []
                
                # 計算平均中心點
                avg_lat = sum(lats[:min_len]) / min_len
                avg_lon = sum(lons[:min_len]) / min_len
                
                return avg_lat, avg_lon, points
            except:
                return None, None, []

        if 'lat' in df.columns and 'lon' in df.columns:
            parsed = df.apply(parse_coords, axis=1, result_type='expand')
            df['lat'] = parsed[0]
            df['lon'] = parsed[1]
            df['poly_points'] = parsed[2]
            
            # 移除座標解析失敗的資料
            df = df.dropna(subset=['lat', 'lon'])

        # 確保必要欄位
        if 'MarketName' not in df.columns: 
            df = df.rename(columns={df.columns[0]: 'MarketName'})
        if 'District' not in df.columns: 
            df['District'] = '全區'
            
        return df

    except Exception as e:
        print(f"資料清洗發生錯誤: {e}")
        return pd.DataFrame()
    
# ==========================================
# 4. 程式測試
# ==========================================

if __name__ == "__main__":
    # 設定 Pandas 顯示選項，避免欄位被 ... 隱藏
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', 50) # 限制內容長度以免洗版

    print("\n 正在進行測試: 從 MySQL 讀取夜市資料...")
    
    # 呼叫讀取函式
    df_test = load_clean_market_df(source="mysql")
    
    if not df_test.empty:
        print(f"\n測試成功！共取得 {len(df_test)} 筆資料。")
        print("-" * 60)
        
        # 1. 檢查欄位名稱是否正確 (有無成功 rename)
        print("欄位清單:", list(df_test.columns))
        print("-" * 60)
        
        # 2. 印出前 3 筆資料
        print("前 3 筆資料:")
        print(df_test[['MarketName', 'City', 'lat', 'lon']].head(3))
        print("-" * 60)
        
        # 3. 營業時間 HTML 產生是否正確
        print("檢查第一筆資料的營業時間 HTML:")
        sample_html = df_test.iloc[0].get('ScheduleHTML', '無此欄位')
        print(sample_html)
        
    else:
        print("\n測試失敗：回傳的 DataFrame 是空的。")
        print("請檢查：1. SSH Tunnel 是否連通  2. db_utils.py 設定  3. 資料庫是否有資料")


        