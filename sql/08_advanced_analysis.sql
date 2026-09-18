USE bilibili_project;

-- 时长分组播放量
SELECT
    CASE
        WHEN duration_sec < 300 THEN '5分钟以下'
        WHEN duration_sec < 600 THEN '5-10分钟'
        WHEN duration_sec < 1200 THEN '10-20分钟'
        ELSE '20分钟以上'
    END AS duration_group,
    COUNT(*) AS video_cnt,
    ROUND(AVG(play_count), 0) AS avg_play
FROM videos
GROUP BY duration_group
ORDER BY avg_play DESC;

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
