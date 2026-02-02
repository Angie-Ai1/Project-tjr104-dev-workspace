## 整合流程說明:
1. import_night_market.py  ：負責夜市資料的清洗與整理
2. import_weather.py            ：負責從氣象局 API 取得氣象資料
3. import_traffic.py                ：負責從 MySQL 資料庫抓取交通事故資料
4. import_view_manager.py：負責所有視覺呈現的邏輯，包含 Folium 地圖的底板建置、圖層堆疊、側邊欄選單排版，以及地圖彈窗（Popup）的 HTML 內容生成
5. apply_view_adv.py             ：負責整合上面4個模組的資料, 並用 Folium 繪圖, 透過 Streamlit 顯示

## Demo
![[2026-01-28 跨域資料整合 - 交通、氣象、夜市之空間分析 (folium & Streamlit)-1769534113223.webp]]

## Summary
#### 本週進度
1. 研究folium和streamlit可以怎麼搭配與呈現
2. 連結不同資料來源, 並進行後續繪製使用 (夜市 CSV 資料清洗邏輯，如何支援座標與多邊形範圍)
3. 以模組化方式呼叫至主程式
4. 發現龐大資料容易造成電腦效能, 執行崩潰!! 目前嘗試用裝飾器(Decorator)解決: 導入 Streamlit 快取機制 (`@st.cache_data` 與 `@st.cache_resource`)

#### 已解決問題
1. 複雜的地圖圖層物件應使用 `@st.cache_resource` (快取儲存,有更新才重新抓取,這樣電腦效能不會被過度消耗)
2. 網頁呈現時, Streamlit 重刷頁面時產生的 `Map container is already initialized` 報錯。透過給地圖組件動態 `key` 值，強制瀏覽器在每次互動時正確重啟地圖容器。

#### 待解決議題 (下周實作項目)
1. 解決資料潰堤與網頁渲染問題
	- 問題點:
		- Folium 是基於 Leaflet.js，它是用 DOM 節點來畫圖的。一次渲染超過 5,000 ~ 10,000 個點，瀏覽器記憶體就會爆掉或卡死。就算 MongoDB 0.1 秒就把資料丟出來，Chrome 還是會因為要畫 400 萬個點而當機。
		- 目前資料流：  `資料庫 (400萬筆)` ➔ `Python 後端 (Streamlit)` ➔ `轉成 HTML/JS` ➔ `瀏覽器 (電腦)`
			- **資料庫層**：MySQL / MongoDB 皆能輕鬆處理 400 萬筆（有 Index 的話）。
			- **瀏覽器層：Folium 產生的 HTML 檔案會包含所有點的座標。400 萬個座標塞在 HTML 裡，檔案可能高達幾百 MB，瀏覽器根本跑不動。
	- ==待研究方案 (將 Redis 應用於 **H3 空間索引** 的快取)
		- MySQL H3 Index 分群統計與 Streamlit 視覺化
			- 在 MySQL 裡多存一個 `h3_index` 欄位，用 SQL `GROUP BY` 算完數量後，再丟給 Streamlit 用 `pydeck.H3HexagonLayer` 畫出來。
			- H3 做空間分群，SQL 算量，前端只畫圖
			- 把資料用六角格子分區，在資料庫先算好每格有多少事件，之後地圖只負責畫出哪些地方多、哪些少，會比較快也比較清楚。
		- Redis 影像優化與空間節省策略
			- **影像壓縮**：在 Python 中使用 `Pillow` 套件將圖片縮小，並轉換成 `WebP` 格式（WebP 的壓縮率通常比 JPG 高出 30% 以上）。
			- **避免 Base64**：直接儲存圖片的 `bytes` 資料，不要轉為 Base64 字串，因為 Base64 會增加約 33% 的資料體積。
		    - **TTL (Time To Live)**：設定過期時間。例如事故現場圖片只快取 24 小時，過期後自動釋放記憶體資源。
2. 將資料來源全面遷移至 **GCP-MySQL** 雲端資料庫，實現端到端（End-to-End）的動態數據串接與前端互動式分析呈現
	

#### 其他補充
 - Streamlit 有內建的原生「多頁面架構 (Multipage Apps)」
	 - 自動導航：只要在專案資料夾中，建立一個叫 `pages` 的資料夾，Streamlit 就會自動在側邊欄生成分頁選單
	 - 變數共用：使用 `st.session_state['nav_city']`，所有頁面都能讀取到這個變數
 - 氣象即時雨量, 目前我是用API爬取, 若想呈現即時分析, 可以考慮保留 (待與團隊討論)
 - folium視覺呈現圖表補充:

![[Concept - Folium-1769064249725.webp|1000]]