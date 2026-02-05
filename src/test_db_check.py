import pandas as pd
from sqlalchemy import text
from db_utils import get_db_engine 

# 設定 Pandas 顯示選項，避免欄位太多被折疊
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def inspect_table(engine, db_name, table_name): 
    # 檢查每個資料表的函式
    full_table_name = f"{db_name}.{table_name}"
    print(f"\n{'='*60}")
    print(f"Check Table: [ {full_table_name} ]")
    print(f"{'='*60}")

    try:
        with engine.connect() as conn:
            # 1. 查詢總筆數
            count_query = text(f"SELECT COUNT(*) FROM {full_table_name}")
            total_rows = conn.execute(count_query).scalar()
            print(f"Total Rows: {total_rows:,}")
            print("-" * 30)

            # 2. 查詢欄位資訊 (使用 Pandas 讀取 DESCRIBE 結果)
            # 列出 Field(欄位名), Type(屬性), Null(是否可空), Key...
            schema_df = pd.read_sql(text(f"DESCRIBE {full_table_name}"), conn)
            print("Field structure (Schema):")
            print(schema_df[['Field', 'Type', 'Null', 'Key']])
            print("-" * 30)

            # 3. 讀取前 10 筆資料
            data_df = pd.read_sql(text(f"SELECT * FROM {full_table_name} LIMIT 5"), conn)
            print("Preview of the first 5 items:")
            if not data_df.empty:
                print(data_df)
            else:
                print("(NO DATA)")
                
    except Exception as e:
        print(f"Failed to inspect table: {e}")

def main():
    # 1. 取得資料庫連線 (會自動觸發 SSH Tunnel)
    print("Starting connection to database...")
    engine = get_db_engine()
    
    if not engine:
        print("Connection failed. Please check .env and db_utils.py")
        return

    # 2. 定義要檢查的目標清單 (資料庫名稱, 資料表名稱)
    # ⚠️ MYSQL的表分別在不同的資料庫底下
    target_tables = [
        ("test_db", "accident_main"),
        ("test_db", "Obs_Stations"),
        ("test_db", "Station_near_accidents"),
        ("test_NM", "nightmarkets") 
    ]

    # 3. 執行迴圈檢查
    for db, table in target_tables:
        inspect_table(engine, db, table)

    print("\nfinish checking all tables.")

if __name__ == "__main__":
    main()