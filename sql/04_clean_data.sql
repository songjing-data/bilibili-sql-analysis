USE bilibili_project;

DELETE FROM videos WHERE play_count = 0;

SELECT COUNT(*) FROM videos;
