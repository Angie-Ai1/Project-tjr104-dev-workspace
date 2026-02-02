# Spatial Analysis Project (Traffic × Weather × Night Market)
本專案目標：整合交通事故、即時氣象、夜市資料，做互動式地圖呈現與空間分析（Folium + Streamlit）[WIP]

---

## Quick Start (Local) - How to Run
目前實作項目已遷移至 Poetry 管理環境
安裝環境：poetry install
變數設定：參考 .env.template 建立 .env
執行專案：poetry run streamlit run src/apply_view_adv.py

---

## Tech Stack
- Python, Pandas（資料處理）
- MySQL（資料儲存與查詢驗證）
- Folium / Leaflet（互動式地圖輸出）
- Streamlit（前端互動與展示）
(ongoing...)

---

## Current Status (已實作)
#### Week1: Traffic accidents crawler → MySQL ingestion + 初版 Folium 地圖
- 交通事故資料：爬取/解壓縮/清洗，匯入 MySQL，並完成初步查詢驗證
- Demo / Screenshot:
![Traffic Data Crawler Result](doc_weekly_logs/assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-01.webp)
![MySQL DB Preview](doc_weekly_logs/assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-02.webp)
![Initial Folium Map](doc_weekly_logs/assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-03.webp)


#### Week2: Cross-domain integration (Traffic + Weather + Night Market) + Streamlit
- 初版視覺化：使用 Folium 產出事故點位地圖（HTML）
- 跨域整合：夜市 CSV（座標/多邊形）＋ 氣象局 API ＋ MySQL 事故資料，完成模組化整合並以 Streamlit 呈現
- 效能與穩定性：嘗試導入 Streamlit 快取（@st.cache_data / @st.cache_resource），並修正「Map container is already initialized」問題（動態 key）
  Pipeline Overview (模組分工)
    - import_night_market.py：夜市資料清洗整理（座標與多邊形）
    - import_weather.py：氣象局 API 取得氣象資料
    - import_traffic.py：從 MySQL 抓取交通事故資料
    - import_view_manager.py：視覺呈現邏輯（底圖、圖層、側邊欄、Popup HTML）
    - apply_view_adv.py（或 main.py）：整合上述模組並用 Folium 繪圖，透過 Streamlit 顯示
- Demo / Screenshot:
![Streamlit Spatial Analysis Demo](doc_weekly_logs/assets/2026-01-28_cross-domain-data-integration-folium-streamlit-1769534113223.webp)

---

## In Progress / Next Steps (研究中)
#### Week3:
- 解決大資料量（約 400 萬筆）在 Folium/瀏覽器端渲染造成的卡頓/崩潰問題
- 研究方案：H3 空間索引分群（SQL GROUP BY 先算量）→ 前端只畫聚合結果；並評估 Redis 快取策略（TTL、避免 Base64、圖片壓縮 WebP）
- 規劃資料來源遷移至 GCP-MySQL（端到端動態串接）

---

## Notes / Dev Logs
[📂Open weekly_logs_folder](/docs/weekly_logs/) 
-  Week1: Traffic accidents crawler → MySQL ingestion + 初版 Folium 地圖
-  Week2: Cross-domain integration (Traffic + Weather + Night Market) + Streamlit → 展示與快取研究
