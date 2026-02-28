import pandas as pd
from sqlalchemy import text
from db_utils import get_db_engine

def list_all_databases():
    print("🚀 連線並查詢所有資料庫名稱...")
    engine = get_db_engine()
    
    if not engine:
        print("連線失敗")
        return

    try:
        with engine.connect() as conn:
            # SQL 指令：顯示所有資料庫 (Schemas)
            result = conn.execute(text("SHOW DATABASES;"))
            
            print("\n📋 資料庫清單：")
            print("=" * 20)
            for row in result:
                print(f"📂 {row[0]}")
            print("=" * 20)
            
    except Exception as e:
        print(f"查詢錯誤: {e}")

if __name__ == "__main__":
    list_all_databases()