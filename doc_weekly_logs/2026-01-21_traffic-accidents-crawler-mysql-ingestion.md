#### 可與團隊討論的事項
- PK 生成邏輯：目前採 hashlib 封裝（發生日期 + 時間 + 地點 + 經緯度）作為唯一識別碼，需確認此組合是否足以應對極端狀況下的重複性
- 時間維度定義：針對原始數據中不規則的時間格式（如 22, 200, 722 等非標準呈現），需進一步討論轉換邏輯
- Schema 優化：目前的 MySQL 關聯表結構可依據後續分析需求（如熱點運算、氣象關聯）進行動態調整
#### 程式碼設計邏輯
- 環境配置：開發環境初始化
- Schema 定義：規劃資料庫欄位與型態
- 資料清洗：處理異常值與格式統一 (如圖1)
- MySQL 匯入：資料落地
- 數據驗證：檢查匯入精確度與執行 SQL 查詢 (如圖2)
- 地圖繪製：初步嘗試經緯度點位渲染 (Spatial Visualization) (如圖3)

#### 我的學習要點
1. 自動化採集：處理 ZIP 壓縮檔的解壓與大規模 CSV 的清洗流
2. 資料清洗技術：實作日期時間正規化，並自動化生成雜湊主鍵 (Hash PK)
3. 資料庫整合：成功建立 main_table 與 detail_table 關聯，並將傷亡人數拆分欄位以利分析
	- 確定各欄位資料型態與PK順利產生
	- 死亡/受傷分兩欄
	- 匯入資訊，並查詢驗證
4. 整合 Folium(Leaflet.js)，將 Python 處理完之數據生成互動式 HTML 地圖

#### 備註
- 清洗後的各項欄位精確度仍需與團隊成員進行交叉比對
- 未來擴展至「多年度」自動化採集時，需額外注意數據結構是否有版本差異

##### 圖1: Python執行結果
![Python執行結果](assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-01.webp)

##### 圖2:  MySQL 內容呈現
![MySQL內容呈現](assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-02.webp)

##### 圖3: import folium, 產生111年全台各地的事故點(透過經緯度判別)
![Folium事故點圖](assets/2026-01-21_traffic-accidents-crawler-mysql-ingestion-03.webp)
