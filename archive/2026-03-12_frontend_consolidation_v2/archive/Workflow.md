```
Project-tjr104-dev-workspace/
├── .env                       # 環境變數設定：包含資料庫密碼與 Redis 連線資訊
├── app.py                     # 現行主程式：管理多章節路由導航與介面視覺風格
├── r_app.py                   # 舊版主入口：負責首頁載入動畫與全台事故地圖概覽
├── core/                      # 核心業務邏輯層 (Core Layer)
│   ├── c_data_service.py      # 資料中心：處理地圖熱力、氣象與事故數據的運算邏輯
│   ├── c_db.py                # 資料庫引擎：管理資料庫連線並提供 Schema 檢查工具
│   ├── c_ui.py                # UI 元件庫：負責地圖構建、側邊欄元件與語系翻譯
│   └── r_cache.py             # 快取管理：負責 Redis 二進位數據讀寫與存活時間設定
├── dags/                      # Airflow 自動化任務
│   ├── d_frontend_db_consol.py　# 資料同步：彙整前端所需之事故與地理資訊數據表
│   └── d_precompute_redis.py  　# 數據預熱：定期將大量事故歷史資料存入 Redis 加速
├── pages/                     # Streamlit 網頁模組
    ├── v_act1_home.py         # 專題首頁：夜市行人地獄(?) 專案背景與動機說明
│   ├── v_act2_overview.py     # 數據解析：夜市老實說 — 事故因素與風險深度分析
│   ├── v_act3_avoid.py        # 行人指引：防禦性步行建議與推薦安全入口導航
│   ├── v_act4_gov.py          # 政策建議：政府幫幫忙 — 城市排名與交通改善指引
│   ├── v_act5_policy.py       # 成效檢驗：政策來檢驗 — 行人安全措施之數據回饋
│   ├── v_act6_chat.py         # 互動助手：AI 小幫手 — 生成式數據問答介面
│   ├── v_dashboard.py         # 區域看板：夜市區域事故深度分析與肇因統計
│   ├── v_hist_trend.py        # 趨勢分析：歷年事故發生量與規律之趨勢統計
│   ├── v_policy_impact.py     # 影響評估：交通政策對事故發生率之影響分析
│   └── v_tableau.py           # 外部看板：整合 Tableau 互動式車禍數據看板
└── utils/                     # 通用工具層 (Utils Layer)
    ├── sidebar.py             # 導航工具：負責側邊欄視覺樣式與選單內容渲染
    ├── summary.py             # AI 語境構建：將 DataFrame 數據轉化為 AI 可讀文字
    └── summary_tools.py       # 摘要工具：提供數據縮減、過濾與文字模板格式化
```

```
Project-tjr104-dev-workspace/
├── .env                       # 環境變數：資料庫密碼與 Redis 連線資訊
├── app.py                     # 主程式入口：管理整體路由與側邊欄渲染邏輯
├── r_app.py                   # 專題背景：專案動機說明與全台即時概覽
├── core/                      # 核心業務邏輯層 (Core Layer)
│   ├── c_data_service.py      # 資料服務：計算地圖熱力圖與事故統計數據
│   ├── c_db.py                # 資料庫連線：提供 get_db_engine 與 Schema 檢查
│   ├── c_ui.py                # UI 組件：構建地圖、渲染側邊欄與多國翻譯
│   └── r_cache.py             # 快取管理：實現 Redis 二進位數據讀寫
├── dags/                      # Airflow 自動化排程 (Workflow)
│   ├── d_frontend_db_consol.py # 數據清洗：整合前端所需的事故與夜市資料表
│   └── d_precompute_redis.py  # 數據預熱：將大量歷史數據提前寫入 Redis 以加速
├── pages/                     # 網頁章節模組 (根據最新側邊欄劃分)
│   │   # --- 夜市老實說 - 一窺事故熱點分析 ---
│   ├── v_act1_home.py         # 全台夜市事故嚴重分析 (原本的專題首頁)
│   ├── v_hist_trend.py        # 各縣市夜市事故比較分析 (歷年趨勢)
│   ├── v_dashboard.py         # 單一夜市事故 AI 分析 (區域風險解析)
│   │   # --- 行人看這裡 - 友善導航 (開發中/預留) ---
│   ├── v_act3_avoid.py        # 步行導航：防禦性路徑建議
│   │   # --- 政府幫幫忙 - 政策推行 ---
│   ├── v_policy_impact.py     # 政策成效即時監控 (交通政策成效分析)
│   ├── v_tableau.py           # 歷史車禍數據看板 (Tableau 嵌入)
│   │   # --- 持續開發中 ---
│   ├── v_act6_chat.py         # AI 小幫手：生成式數據問答與互動
│   └── ...                    # 其他未列入選單之舊版檔案 (v_act2, v_act4, v_act5)
└── utils/                     # 通用工具層 (Utils Layer)
    ├── market_tools.py        # 夜市工具：處理座標轉換與基礎資料過濾
    ├── sidebar.py             # 選單樣式：負責側邊欄的視覺風格定義
    ├── summary.py             # AI 語境：將數據轉化為 AI 可讀之文字 Context
    └── summary_tools.py       # 摘要工具：提供 DataFrame 縮減與文字格式化
```