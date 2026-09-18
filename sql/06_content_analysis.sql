USE bilibili_project;

-- 各分区视频数与平均播放量
SELECT
    c.category_name,
    COUNT(*) AS video_cnt,
    ROUND(AVG(v.play_count), 0) AS avg_play,
    MAX(v.play_count) AS max_play
FROM videos v
JOIN categories c ON v.category_id = c.category_id
GROUP BY c.category_name
ORDER BY avg_play DESC;

-- 各分区平均弹幕数
SELECT
    c.category_name,
    ROUND(AVG(v.danmaku_count), 0) AS avg_danmaku
FROM videos v
JOIN categories c ON v.category_id = c.category_id
GROUP BY c.category_name
ORDER BY avg_danmaku DESC;
