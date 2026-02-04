import pandas as pd
import os
from shapely.geometry import Point, MultiPoint

# 台灣範圍定義 (用來區分異常座標)
TW_BOUNDS = {
    'lat_min': 21.0, 'lat_max': 27.0,
    'lon_min': 118.0, 'lon_max': 123.0
}

def load_clean_market_df(csv_path):
    """
    負責讀取並清洗資料，回傳乾淨的 DataFrame
    供給 draw_all_adv.py 使用
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
            # 寫 HTML 字串，定義一個寬度 100% 的表格
            schedule_html = "<table style='width:100%; font-size:14px; border-collapse: collapse;'>"
            
            has_detail = False # 記錄夜市是否有詳細的營業時間

            # B. 開始跑迴圈 (週一到週日)
            for en_day, ch_day in days_map.items():
                # 檢查 CSV 裡是否有這個欄位 (Ex.Monday)
                if en_day in row.index:
                    time_val = str(row[en_day]).strip()  # 取得該欄位的值，轉成字串並去除前後空白
                    
                    # C. 判斷是否為「無效資料」
                    # 如果時間為 'nan', 'none' 或空字串，顯示灰色的「休息」
                    if time_val.lower() in ['nan', '', 'none']:
                        display = '<span style="color:#ccc">休息</span>'
                    else:
                        # 如果有正常營業時間 (Ex.17:00-24:00)，就直接顯示
                        display = time_val
                        has_detail = True # 標記真的有抓到資料
                    
                    # D. 斑馬紋樣式
                    # 如果是二、四、六，做一個淺灰色的背景色，讓表格比較好讀
                    bg = "background-color: #f9f9f9;" if en_day in ['tuesday', 'thursday', 'saturday'] else ""
                    
                    # E. 組合這一列 (tr = table row, td = table data)
                    # 把背景色、星期幾、營業時間全部拼進去
                    schedule_html += f"<tr style='{bg}'><td style='padding:2px 5px; font-weight:bold;'>週{ch_day}</td><td style='padding:2px 5px;'>{display}</td></tr>"
            
            # F. 結束表格
            schedule_html += "</table>" # 後面不屬於表格了
            
            # 【重要修正】補上回傳值，這樣下面的 apply 才能拿到結果
            return schedule_html

        # 【重要修正】這裡的縮排往左移了，移出 format_schedule 函式外面
        df['ScheduleHTML'] = df.apply(format_schedule, axis=1)

        # 4. 處理 Status 欄位 (防止 nan)
        if 'Status' not in df.columns:
            df['Status'] = "詳見營業時間表"
        else:
            df['Status'] = df['Status'].astype(str).replace({'nan': '詳見營業時間表', 'NaN': '詳見營業時間表'})

        # 5. 座標解析 (多重座標 -> 中心點 + 多邊形點)
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

        # 6. 確保必要欄位
        if 'MarketName' not in df.columns: 
            df = df.rename(columns={df.columns[0]: 'MarketName'})
        if 'District' not in df.columns: 
            df['District'] = '全區'
            
        return df

    except Exception as e:
        print(f"資料清洗發生錯誤: {e}")
        return pd.DataFrame()