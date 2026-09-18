USE bilibili_project;

-- 1. 各分区视频数与平均播放量
SELECT
    c.category_name,
    COUNT(*) AS video_cnt,
    ROUND(AVG(v.play_count), 0) AS avg_play,
    MAX(v.play_count) AS max_play
FROM videos v
JOIN categories c ON v.category_id = c.category_id
GROUP BY c.category_name
ORDER BY avg_play DESC;

-- 2. 播放量 Top 10
SELECT title, author, play_count
FROM videos
ORDER BY play_count DESC
LIMIT 10;

-- 3. 各分区平均弹幕数
SELECT
    c.category_name,
    ROUND(AVG(v.danmaku_count), 0) AS avg_danmaku
FROM videos v
JOIN categories c ON v.category_id = c.category_id
GROUP BY c.category_name
ORDER BY avg_danmaku DESC;

-- 4. 时长分组播放量
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
