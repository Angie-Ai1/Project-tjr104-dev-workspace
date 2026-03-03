from airflow import DAG
from airflow.decorators import task
from datetime import datetime
import os
import pandas as pd
from sqlalchemy import create_engine


with DAG(dag_id='test_vm_sql', schedule=None) as dag:
    @task
    def check_vm_data():
        # 直接讀取由 docker-compose.yml 注入的環境變數
        # 預期會抓到: mysql+pymysql://root:123456@host.docker.internal:3310/test_db
        cloud_sql_url = os.getenv("CLOUDSQL_URL")
        
        if not cloud_sql_url:
            raise ValueError("找不到 CLOUDSQL_URL，請檢查 docker-compose.yml 的 environment 設定。")
            
        print(f"正在連線至資料庫: {cloud_sql_url}")
        engine = create_engine(cloud_sql_url)
        
        try:
            # 將 LIMIT 1 改為 LIMIT 10
            sql = "SELECT * FROM test_night_market.Night_market_merge LIMIT 10"
            df = pd.read_sql(sql, engine)
            
            # 使用 to_string() 強制完整印出 10 筆資料，避免被 Pandas 自動折疊
            print("✅ 成功連線並抓到資料：\n", df.to_string())
        except Exception as e:
            print(f"❌ 查詢失敗: {e}")
            raise e
            
    check_vm_data()

