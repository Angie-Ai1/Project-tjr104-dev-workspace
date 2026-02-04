-- 查看主表與細節表的總筆數
USE traffic_111_db;
SELECT 
	'Main' as Table_Name, 
     COUNT(*) as Total 
FROM accident_main
UNION ALL
SELECT '
	Detail', 
    COUNT(*) 
FROM accident_details;

-- 查看各個順位的當事者數量 (確認順位 1 是否符合預期)
USE traffic_111_db;
SELECT party_sequence, COUNT(*) as Count
FROM accident_details
GROUP BY party_sequence
ORDER BY party_sequence;

USE traffic_111_db;

-- 透過 accident_id 將 main & details table 關聯，查詢A1前十筆
SELECT m.*, d.*
FROM accident_main m
JOIN 
	accident_details d ON m.accident_id = d.accident_id
WHERE d.accident_category = 'A1'
ORDER BY 
	m.accident_date ASC, 
    m.accident_id ASC
LIMIT 10;

-- 透過 accident_id 將 main & details table 關聯，查詢A2前十筆
SELECT m.*, d.*
FROM accident_main m
JOIN 
	accident_details d ON m.accident_id = d.accident_id
WHERE d.accident_category = 'A2'
ORDER BY 
	m.accident_date ASC, 
    m.accident_id ASC
LIMIT 10;

-- 查詢A1 和 A2 1~12月, 每個月的筆數共有幾筆
USE traffic_111_db;
SELECT 
    IFNULL(m.accident_month, '總計') AS '月份',
    COUNT(CASE WHEN d.accident_category LIKE 'A1%' THEN 1 END) AS 'A1筆數',
    COUNT(CASE WHEN d.accident_category LIKE 'A2%' THEN 1 END) AS 'A2筆數',
    COUNT(DISTINCT m.accident_id) AS '該月事故總件數'
FROM 
    traffic_111_db.accident_main m
JOIN 
    traffic_111_db.accident_details d ON m.accident_id = d.accident_id
WHERE 
    d.accident_category LIKE 'A1%' OR d.accident_category LIKE 'A2%'
GROUP BY 
    m.accident_month WITH ROLLUP;