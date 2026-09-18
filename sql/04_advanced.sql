USE bilibili_project;

-- 各分区播放量 Top3（窗口函数）
WITH ranked AS (
    SELECT
        c.category_name,
        v.title,
        v.play_count,
        ROW_NUMBER() OVER (
            PARTITION BY c.category_name
            ORDER BY v.play_count DESC
        ) AS rn
    FROM videos v
    JOIN categories c ON v.category_id = c.category_id
)
SELECT * FROM ranked WHERE rn <= 3;
