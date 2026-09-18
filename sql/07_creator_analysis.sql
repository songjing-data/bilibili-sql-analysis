USE bilibili_project;

SELECT
    author,
    COUNT(*) AS video_cnt,
    SUM(play_count) AS total_play,
    ROUND(AVG(play_count), 0) AS avg_play
FROM videos
GROUP BY author
ORDER BY total_play DESC
LIMIT 20;
