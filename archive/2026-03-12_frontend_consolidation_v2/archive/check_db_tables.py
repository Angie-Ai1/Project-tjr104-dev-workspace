import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from sqlalchemy import text
from src.core.c_db import get_db_engine

def get_markdown_report(db_table_list):
    md_content = "# 📊 資料庫資料表檢查報告\n\n"
    md_content += f"產生時間: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n"

    for db_name, table_name in db_table_list:
        print(f"正在處理: {db_name}.{table_name}...")
        engine = get_db_engine(db_name)
        
        md_content += f"## 🗂️ 資料表: {db_name}.{table_name}\n"
        
        try:
            with engine.connect() as conn:
                # 1. 抓取結構 (DESC)
                schema = pd.read_sql(text(f"DESC `{table_name}`"), conn)
                md_content += "### 1. 資料型態 (Schema)\n"
                md_content += schema[['Field', 'Type', 'Null', 'Key']].to_markdown(index=False) + "\n\n"
                
                # 2. 抓取總筆數
                count = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar()
                md_content += f"### 2. 總筆數\n**{count:,}** 筆\n\n"
                
                # 3. 抓取內容預覽 (Limit 2)
                preview = pd.read_sql(text(f"SELECT * FROM `{table_name}` LIMIT 2"), conn)
                md_content += "### 3. 內容預覽 (Limit 2)\n"
                if preview.empty:
                    md_content += "> ⚠️ 此資料表目前無資料。\n\n"
                else:
                    md_content += preview.to_markdown(index=False) + "\n\n"
                    
        except Exception as e:
            md_content += f"### ❌ 錯誤\n無法讀取此表: `{e}`\n\n"
        
        md_content += "---\n"
    
    return md_content

if __name__ == "__main__":
    target_tables = [
        # car_accident
        ("car_accident", "accident_new_sq1_env"), ("car_accident", "accident_new_sq1_human"),
        ("car_accident", "accident_new_sq1_main"), ("car_accident", "accident_new_sq1_process"),
        ("car_accident", "accident_new_sq1_res"), ("car_accident", "accident_new_sq2_human"),
        ("car_accident", "accident_new_sq2_process"), ("car_accident", "accident_new_sq2_res"),
        # frontend_db
        ("frontend_db", "accident_new_sq1_env_temp"), ("frontend_db", "accident_new_sq1_main"),
        ("frontend_db", "accident_new_sq1_process_temp"), ("frontend_db", "tbl_accident_analysis_final"),
        ("frontend_db", "tbl_accident_details"), ("frontend_db", "tbl_accident_heatmap"),
        ("frontend_db", "tbl_pedestrian_accident"),
        # test_db
        ("test_db", "Accident_A1"), ("test_db", "accident_main"),
        ("test_db", "accident_new_sq1_main"), ("test_db", "accident_new_sq2_sub"),
        ("test_db", "accident_sq1_main"), ("test_db", "accident_sq2_sub"),
        ("test_db", "accident_sub"),
        # test_night_market
        ("test_night_market", "Night_market_merge"), ("test_night_market", "Night_market_separate")
    ]

    # 執行查詢並產生內容
    final_report = get_markdown_report(target_tables)

    # 儲存成 Markdown 檔案
    with open("database_inspection.md", "w", encoding="utf-8") as f:
        f.write(final_report)

    print("\n✅ 查詢完成！結果已儲存至: database_inspection.md")