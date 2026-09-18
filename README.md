# B站知识区UP主视频数据分析（SQL版）

## 项目背景
分析B站知识区视频数据，找出影响播放量和弹幕数的因素，为内容运营提供建议。

## 数据说明
- 数据来源：B站搜索接口
- 数据量：2890条
- 覆盖分区：科学科普、财经商业、校园学习、职业职场、设计创意

## 技术栈
- 数据库：MySQL
- 语言：Python + SQL
- SQL：JOIN、GROUP BY、CASE WHEN、窗口函数、CTE

## 分析问题
1. 哪个分区平均播放量最高？
2. 哪个分区平均弹幕数最高？
3. 时长和播放量有什么关系？
4. 各分区播放量Top3是哪些？
5. 哪些UP主播放量最高？

## 目录结构
- `mysql/01_create_database.sql`：建数据库
- `mysql/02_create_table.sql`：建表
- `mysql/03_import_data.sql`：导入数据
- `mysql/04_clean_data.sql`：清洗数据
- `mysql/05_basic_analysis.sql`：数据概览
- `mysql/06_content_analysis.sql`：分区播放量、弹幕分析
- `mysql/07_creator_analysis.sql`：UP主分析
- `mysql/08_advanced_analysis.sql`：时长、爆款、Top3分析

## 主要发现
1. 社科人文分区平均播放量最高，达到1155714。
2. 科学科普分区平均弹幕数最高，达到26513条。
3. 时长5分钟以下的视频平均播放量最高。
4. 各分区Top3见 mysql/08_advanced_analysis.sql。

## 爬虫代码
`bilibili_crawler.py`：低频可续爬的B站搜索采集器，支持断点续爬、限速、重试。
