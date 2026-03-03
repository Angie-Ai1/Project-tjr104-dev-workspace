from airflow import DAG
from airflow.decorators import task
from datetime import datetime

with DAG(dag_id='test_print_only', schedule=None) as dag:
    @task
    def check_vm_data():
        # 不載入 pandas, 不連資料庫, 只印一句話
        print("Hello! This is a pure Airflow test.")
        return "Success"

    check_vm_data()

    from airflow.sdk import DAG, task
from datetime import datetime
