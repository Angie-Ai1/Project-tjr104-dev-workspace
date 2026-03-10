from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'update_frontend_db_consol',
    default_args=default_args,
    schedule='@monthly',
    catchup=False,
    tags=['accident_data', 'tables_only'],
) as dag:

    #### 1. 跨庫合併基礎資料表 (main, env, process, human)
    merge_base_tables = SQLExecuteQueryOperator(
        task_id='merge_base_tables',
        conn_id='mysql_db',
        split_statements=True,
        sql="""
        CREATE DATABASE IF NOT EXISTS frontend_db;
        USE frontend_db;
        
        -- 清除舊暫存表
        DROP TABLE IF EXISTS accident_new_sq1_main_temp;
        DROP TABLE IF EXISTS accident_new_sq1_env_temp;
        DROP TABLE IF EXISTS accident_new_sq1_process_temp;
        DROP TABLE IF EXISTS accident_new_sq1_human_temp;

        -- 合併 main 主表 (2021-2025 來自 test_accident, 2026 來自 car_accident)
        CREATE TABLE accident_new_sq1_main_temp AS
        SELECT accident_id, latitude, longitude, death_count, injury_count, accident_datetime, weather_condition, accident_weekday 
        FROM test_accident.accident_sq1_main WHERE YEAR(accident_datetime) BETWEEN 2021 AND 2025
        UNION ALL
        SELECT accident_id, latitude, longitude, death_count, injury_count, accident_datetime, weather_condition, accident_weekday 
        FROM car_accident.accident_new_sq1_main WHERE YEAR(accident_datetime) = 2026;

        -- 合併 env 環境因子表
        CREATE TABLE accident_new_sq1_env_temp AS
        SELECT accident_id, light_condition, road_surface_condition FROM test_accident.accident_sq1_env
        UNION ALL
        SELECT accident_id, light_condition, road_surface_condition FROM car_accident.accident_new_sq1_env;

        -- 合併 process 人為因子表
        CREATE TABLE accident_new_sq1_process_temp AS
        SELECT accident_id, cause_analysis_minor_primary FROM test_accident.accident_sq1_process
        UNION ALL
        SELECT accident_id, cause_analysis_minor_primary FROM car_accident.accident_new_sq1_process;

        -- 合併 human 當事人表
        CREATE TABLE accident_new_sq1_human_temp AS
        SELECT accident_id, party_action_major FROM test_accident.accident_sq1_human
        UNION ALL
        SELECT accident_id, party_action_major FROM car_accident.accident_new_sq1_human;
        """
    )

    #### 2. 建立最終分析寬表與衍生表
    build_analysis_tables = SQLExecuteQueryOperator(
        task_id='build_analysis_tables',
        conn_id='mysql_db',
        split_statements=True,
        sql="""
        USE frontend_db;
        
        DROP TABLE IF EXISTS tbl_accident_analysis_final_temp;
        DROP TABLE IF EXISTS tbl_accident_details_temp;
        DROP TABLE IF EXISTS tbl_pedestrian_accident_temp;
        DROP TABLE IF EXISTS tbl_accident_heatmap_temp;

        -- 建立最終分析寬表 (加入 env 細節欄位)
        CREATE TABLE tbl_accident_analysis_final_temp AS 
        SELECT 
            m.accident_id, m.accident_datetime, m.accident_weekday AS Weekday_CN, 
            m.latitude, m.longitude, m.death_count, m.injury_count, m.weather_condition, 
            IFNULL(p.cause_analysis_minor_primary, '未詳查') AS primary_cause, 
            IFNULL(h.party_action_major, '未詳查') AS party_action, 
            YEAR(m.accident_datetime) AS Year, HOUR(m.accident_datetime) AS Hour,
            e.light_condition, e.road_surface_condition
        FROM accident_new_sq1_main_temp m 
        LEFT JOIN accident_new_sq1_process_temp p ON m.accident_id = p.accident_id 
        LEFT JOIN accident_new_sq1_env_temp e ON m.accident_id = e.accident_id
        LEFT JOIN accident_new_sq1_human_temp h ON m.accident_id = h.accident_id;
        
        -- 建立明細表
        CREATE TABLE tbl_accident_details_temp AS 
        SELECT m.*, YEAR(m.accident_datetime) AS Year FROM accident_new_sq1_main_temp m;

        -- 建立行人事故子表
        CREATE TABLE tbl_pedestrian_accident_temp AS 
        SELECT * FROM tbl_accident_analysis_final_temp 
        WHERE primary_cause LIKE '%行人%' OR party_action LIKE '%行人%';

        -- 建立熱力圖子表
        CREATE TABLE tbl_accident_heatmap_temp AS 
        SELECT ROUND(latitude, 4) AS lat, ROUND(longitude, 4) AS lon, COUNT(*) AS count 
        FROM tbl_accident_analysis_final_temp GROUP BY lat, lon;

        -- 建立關鍵索引
        ALTER TABLE tbl_accident_analysis_final_temp ADD INDEX idx_tmp_loc (latitude, longitude), ADD INDEX idx_tmp_year (Year);
        ALTER TABLE tbl_pedestrian_accident_temp ADD INDEX idx_tmp_ped_loc (latitude, longitude);
        ALTER TABLE tbl_accident_heatmap_temp ADD INDEX idx_tmp_heat_loc (lat, lon);
        ALTER TABLE accident_new_sq1_main_temp ADD INDEX idx_tmp_main_id (accident_id);
        """
    )

    #### 3. 瞬間更名切換
    atomic_swap = SQLExecuteQueryOperator(
        task_id='atomic_swap',
        conn_id='mysql_db',
        split_statements=True,
        sql="""
        USE frontend_db;
        -- 確保正式表存在 (避免初次執行 RENAME 失敗)
        CREATE TABLE IF NOT EXISTS tbl_accident_analysis_final LIKE tbl_accident_analysis_final_temp;
        CREATE TABLE IF NOT EXISTS tbl_accident_details LIKE tbl_accident_details_temp;
        CREATE TABLE IF NOT EXISTS accident_new_sq1_main LIKE accident_new_sq1_main_temp;
        CREATE TABLE IF NOT EXISTS tbl_pedestrian_accident LIKE tbl_pedestrian_accident_temp;
        CREATE TABLE IF NOT EXISTS tbl_accident_heatmap LIKE tbl_accident_heatmap_temp;
        CREATE TABLE IF NOT EXISTS accident_new_sq1_env LIKE accident_new_sq1_env_temp;
        CREATE TABLE IF NOT EXISTS accident_new_sq1_process LIKE accident_new_sq1_process_temp;
        CREATE TABLE IF NOT EXISTS accident_new_sq1_human LIKE accident_new_sq1_human_temp;

        -- 執行更名切換
        RENAME TABLE 
            tbl_accident_analysis_final TO tbl_old_main, tbl_accident_analysis_final_temp TO tbl_accident_analysis_final,
            tbl_accident_details TO tbl_old_det, tbl_accident_details_temp TO tbl_accident_details,
            accident_new_sq1_main TO tbl_old_comp, accident_new_sq1_main_temp TO accident_new_sq1_main,
            tbl_pedestrian_accident TO tbl_old_ped, tbl_pedestrian_accident_temp TO tbl_pedestrian_accident,
            tbl_accident_heatmap TO tbl_old_heat, tbl_accident_heatmap_temp TO tbl_accident_heatmap,
            accident_new_sq1_env TO tbl_old_env, accident_new_sq1_env_temp TO accident_new_sq1_env,
            accident_new_sq1_process TO tbl_old_proc, accident_new_sq1_process_temp TO accident_new_sq1_process,
            accident_new_sq1_human TO tbl_old_human, accident_new_sq1_human_temp TO accident_new_sq1_human;

        -- 刪除舊表
        DROP TABLE IF EXISTS tbl_old_main, tbl_old_det, tbl_old_comp, tbl_old_ped, tbl_old_heat, tbl_old_env, tbl_old_proc, tbl_old_human;
        """
    )

    merge_base_tables >> build_analysis_tables >> atomic_swap