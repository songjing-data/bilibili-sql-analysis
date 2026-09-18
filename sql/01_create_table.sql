CREATE DATABASE IF NOT EXISTS bilibili_project
DEFAULT CHARACTER SET utf8mb4;

USE bilibili_project;

CREATE TABLE categories (
    category_id INT PRIMARY KEY,
    category_name VARCHAR(50)
);

CREATE TABLE videos (
    video_id VARCHAR(30) PRIMARY KEY,
    title VARCHAR(300),
    category_id INT,
    category_name VARCHAR(50),
    author VARCHAR(100),
    play_count INT,
    like_count INT,
    coin_count INT,
    favorite_count INT,
    danmaku_count INT,
    duration_sec INT,
    publish_time VARCHAR(30)
);
