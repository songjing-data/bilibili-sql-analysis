USE bilibili_project;

SELECT
    COUNT(*) AS total_videos,
    SUM(play_count) AS total_play,
    ROUND(AVG(play_count), 0) AS avg_play,
    MAX(play_count) AS max_play
FROM videos;
