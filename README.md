## Spatial Analysis Project (Traffic × Weather × Night Market)
本專案目標：整合交通事故、即時氣象、夜市資料，做互動式地圖呈現與空間分析（Folium + Streamlit）[WIP]

---

## Quick Start (Local) - How to Run
- 目前實作項目已遷移至 Poetry 管理環境
- 安裝環境：poetry install
- 變數設定：參考 .env.template 建立 .env
- 執行專案：poetry run streamlit run src/apply_view_adv.py

---

## Tech Stack
- Python, Pandas（資料處理）
- MySQL（資料儲存與查詢驗證）
- Folium / Leaflet（互動式地圖輸出）
- Streamlit（前端互動與展示）
(ongoing...)

---

## Current Status (已實作)
### Week1: Traffic accidents crawler → MySQL ingestion + 初版 Folium 地圖
- 交通事故資料：爬取/解壓縮/清洗，匯入 MySQL，並完成初步查詢驗證

- Demo / Screenshot:
![Traffic Data Crawler Result](doc_weekly_logs/assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-01.webp)
![MySQL DB Preview](doc_weekly_logs/assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-02.webp)
![Initial Folium Map](doc_weekly_logs/assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-03.webp)


### Week2: Cross-domain integration (Traffic + Weather + Night Market) + Streamlit
- 初版視覺化：使用 Folium 產出事故點位地圖（HTML）
- 跨域整合：夜市 CSV（座標/多邊形）＋ 氣象局 API ＋ MySQL 事故資料，完成模組化整合並以 Streamlit 呈現
- 效能與穩定性：嘗試導入 Streamlit 快取（@st.cache_data / @st.cache_resource），並修正「Map container is already initialized」問題（動態 key）
  Pipeline Overview (模組分工)
    - import_night_market.py：夜市資料清洗整理（座標與多邊形）
    - import_weather.py：氣象局 API 取得氣象資料
    - import_traffic.py：從 MySQL 抓取交通事故資料
    - import_view_manager.py：視覺呈現邏輯（底圖、圖層、側邊欄、Popup HTML）
    - apply_view_adv.py（或 main.py）：整合上述模組並用 Folium 繪圖，透過 Streamlit 顯示
- System Flowchart / Data Pipeline:
![Data Pipeline](doc_weekly_logs/assets/2026-01-28_cross-domain-data-integration-folium-streamlit-02.webp)

- Demo / Screenshot:
![Streamlit Spatial Analysis Demo](doc_weekly_logs/assets/2026-01-28_cross-domain-data-integration-folium-streamlit-01.webp)


### Week3: Performance Optimization & Regional Risk Analysis (1.5M+ Data)
- 完成資料來源遷移與安全性提升：
  - 成功將資料從 Local MySQL/.csv 遷移至 GCP VM -> MYSQL
  - 實作 db_utils.py 統一管理連線邏輯，並透過 SSH Tunnel 確保資料傳輸安全

- 效能優化
  - 全台概覽模式：實作 **SQL 格網聚合技術** (`GROUP BY ROUND(lat, 2)`)，將 150 萬筆原始資料轉化為輕量級熱力圖數據
  - 對單一夜市半徑搜尋，設定 LIMIT 800 並按時間排序（只抓最新），確保地圖標記清晰且載入快速
  - 快取機制：導入 st.cache_data 與 st.cache_resource，大幅減少重複的 SQL 查詢與資料庫連線，將地圖切換時間從20~30秒縮短至3秒

- UI/UX優化
  - 車禍事故資訊 - 運用 Pandas Pivot Table 將直式資料轉為橫向報表，並新增「各年度統計」

- Demo / Screenshot:
![Overview](doc_weekly_logs/assets/2026-02-04_Performance Optimization & Regional Risk Analysis (1.5M+ Data)-01.webp)
![Night_Market_view](doc_weekly_logs/assets/2026-02-04_Performance Optimization & Regional Risk Analysis (1.5M+ Data)-02.webp)

---

## Next Steps
### Week4: (2/11)
- [架構評估] 持續優化地理空間索引 (H3 評估) 與 分散式快取 (Redis 導入規劃)
- [數據分析] 實作事故與天氣關聯性分析：鎖定特定夜市周邊觀測站之歷史氣象數據

### Week4: (2/15)
- [視覺化] 導入多維度統計圖表 (Plotly/Altair)：包含事故主因(圓餅圖)、各項因素(長條圖)及歷年趨勢折線圖
- [前端優化] 整合即時天氣與夜市連動功能，支援自定義日期時間篩選

---

## Notes / Dev Logs
-  Week1: Traffic accidents crawler → MySQL ingestion + 初版 Folium 地圖
-  Week2: Cross-domain integration (Traffic + Weather + Night Market) + Streamlit → 展示與快取研究
-  Week3: Performance Optimization & Regional Risk Analysis (1.5M+ Data)

