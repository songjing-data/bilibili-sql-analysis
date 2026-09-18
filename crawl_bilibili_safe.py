"""Low-rate, resumable Bilibili video search collector.

Uses public web endpoints only. It does not bypass access controls. If Bilibili
returns a risk-control response, the collector backs off and records the error.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests


SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"
VIEW_URL = "https://api.bilibili.com/x/web-interface/view"
DEFAULT_KEYWORDS = {
    1: ("科学科普", ["科普", "科学", "天文", "物理"]),
    2: ("社科人文", ["历史", "人文", "社会学", "哲学"]),
    3: ("财经商业", ["财经", "商业", "经济", "投资"]),
    4: ("校园学习", ["考研", "学习", "大学", "课程"]),
    5: ("职业职场", ["职场", "求职", "面试", "职业规划"]),
    6: ("设计创意", ["设计", "创意", "平面设计", "工业设计"]),
}

RAW_FIELDS = [
    "video_id", "bvid", "title", "category_id", "category_name", "keyword",
    "author", "play_count", "like_count", "coin_count", "favorite_count",
    "danmaku_count", "duration_sec", "publish_time", "detail_status",
]
FINAL_FIELDS = [
    "video_id", "title", "category_id", "category_name", "author",
    "play_count", "like_count", "coin_count", "favorite_count",
    "danmaku_count", "duration_sec", "publish_time",
]


class ApiError(RuntimeError):
    def __init__(self, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


def clean_title(value: Any) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    return html.unescape(text).strip()


def as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def format_timestamp(value: Any) -> str:
    timestamp = as_int(value)
    if not timestamp:
        return ""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json, text/plain, */*",
    })
    # Optional: set BILIBILI_COOKIE in the terminal. Never paste it into code.
    cookie = os.environ.get("BILIBILI_COOKIE", "").strip()
    if cookie:
        session.headers["Cookie"] = cookie
    return session


def request_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    retries: int,
    backoff: float,
) -> dict[str, Any]:
    last_error = "unknown error"
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, params=params, timeout=(10, 25))
            if response.status_code in {412, 418, 429}:
                raise ApiError(f"HTTP {response.status_code} (访问受限/请求过快)")
            if 500 <= response.status_code:
                raise ApiError(f"HTTP {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            code = as_int(payload.get("code"))
            if code != 0:
                message = payload.get("message") or payload.get("msg") or "无说明"
                # -412 is commonly a request/risk-control rejection.
                retryable = code in {-412, -509, -500, -503}
                raise ApiError(f"API code={code}, message={message}", retryable)
            return payload
        except (requests.RequestException, ValueError, ApiError) as exc:
            last_error = str(exc)
            retryable = not isinstance(exc, ApiError) or exc.retryable
            if attempt >= retries or not retryable:
                break
            delay = backoff * (2 ** (attempt - 1)) + random.uniform(0, backoff)
            print(f"    请求失败：{exc}；{delay:.1f} 秒后重试 ({attempt}/{retries})")
            time.sleep(delay)
    raise ApiError(last_error, retryable=False)


def load_rows(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            row["bvid"]: row
            for row in csv.DictReader(handle)
            if row.get("bvid")
        }


def save_rows(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows.values())
    temp.replace(path)


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")).get("completed", []))
    except (OSError, ValueError, TypeError):
        return set()


def save_state(path: Path, completed: set[str]) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps({"completed": sorted(completed)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def pause(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def search(
    session: requests.Session,
    rows: dict[str, dict[str, Any]],
    completed: set[str],
    raw_path: Path,
    state_path: Path,
    pages: int,
    retries: int,
    backoff: float,
    min_delay: float,
    max_delay: float,
) -> None:
    for category_id, (category_name, keywords) in DEFAULT_KEYWORDS.items():
        for keyword in keywords:
            print(f"\n[{category_name}] 关键词：{keyword}")
            for page in range(1, pages + 1):
                task_key = f"{category_id}|{keyword}|{page}"
                if task_key in completed:
                    print(f"  第 {page} 页已完成，跳过")
                    continue
                try:
                    payload = request_json(
                        session,
                        SEARCH_URL,
                        {"search_type": "video", "keyword": keyword, "page": page},
                        retries,
                        backoff,
                    )
                except ApiError as exc:
                    print(f"  第 {page} 页停止：{exc}")
                    print("  已保存进度；建议稍后再运行，不要连续重启猛刷。")
                    break

                results = (payload.get("data") or {}).get("result") or []
                if not results:
                    print(f"  第 {page} 页无结果，该关键词结束")
                    completed.add(task_key)
                    save_state(state_path, completed)
                    break

                before = len(rows)
                for video in results:
                    bvid = str(video.get("bvid") or "").strip()
                    if not bvid:
                        continue
                    # Keep the first category assignment when keywords overlap.
                    if bvid not in rows:
                        rows[bvid] = {
                            "video_id": video.get("aid") or "",
                            "bvid": bvid,
                            "title": clean_title(video.get("title")),
                            "category_id": category_id,
                            "category_name": category_name,
                            "keyword": keyword,
                            "author": video.get("author") or "",
                            "play_count": as_int(video.get("play")),
                            "like_count": 0,
                            "coin_count": 0,
                            "favorite_count": 0,
                            "danmaku_count": as_int(video.get("video_review")),
                            "duration_sec": 0,
                            "publish_time": format_timestamp(video.get("pubdate")),
                            "detail_status": "pending",
                        }
                completed.add(task_key)
                save_rows(raw_path, rows)
                save_state(state_path, completed)
                print(
                    f"  第 {page} 页完成：新增 {len(rows) - before} 条，"
                    f"去重后共 {len(rows)} 条"
                )
                pause(min_delay, max_delay)


def enrich_details(
    session: requests.Session,
    rows: dict[str, dict[str, Any]],
    raw_path: Path,
    retries: int,
    backoff: float,
    min_delay: float,
    max_delay: float,
) -> None:
    pending = [row for row in rows.values() if row.get("detail_status") != "ok"]
    print(f"\n准备补全 {len(pending)} 条真实指标。")
    for index, row in enumerate(pending, start=1):
        bvid = str(row["bvid"])
        try:
            payload = request_json(
                session, VIEW_URL, {"bvid": bvid}, retries, backoff
            )
        except ApiError as exc:
            row["detail_status"] = f"error: {exc}"
            save_rows(raw_path, rows)
            print(f"  [{index}/{len(pending)}] {bvid} 失败：{exc}")
            # A refusal likely affects following requests too; stop safely.
            if "412" in str(exc) or "429" in str(exc) or "-412" in str(exc):
                print("  检测到访问限制，已保存进度并停止详情补全。")
                break
            continue

        data = payload.get("data") or {}
        stat = data.get("stat") or {}
        owner = data.get("owner") or {}
        row.update({
            "video_id": data.get("aid") or row.get("video_id", ""),
            "title": data.get("title") or row.get("title", ""),
            "author": owner.get("name") or row.get("author", ""),
            "play_count": as_int(stat.get("view")),
            "like_count": as_int(stat.get("like")),
            "coin_count": as_int(stat.get("coin")),
            "favorite_count": as_int(stat.get("favorite")),
            "danmaku_count": as_int(stat.get("danmaku")),
            "duration_sec": as_int(data.get("duration")),
            "publish_time": format_timestamp(data.get("pubdate")),
            "detail_status": "ok",
        })
        if index % 10 == 0 or index == len(pending):
            save_rows(raw_path, rows)
        print(f"  [{index}/{len(pending)}] {bvid} 完成")
        pause(min_delay, max_delay)
    save_rows(raw_path, rows)


def export_final(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINAL_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows.values())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="低速、可续跑的 B 站搜索数据采集器")
    parser.add_argument("--pages", type=int, default=10, help="每个关键词最多页数，默认 10")
    parser.add_argument("--output-dir", type=Path, default=Path("bilibili_data"))
    parser.add_argument("--details", action="store_true", help="补全真实点赞、投币、收藏和时长")
    parser.add_argument("--details-only", action="store_true", help="只补全已有 raw CSV 的详情")
    parser.add_argument("--min-delay", type=float, default=3.0)
    parser.add_argument("--max-delay", type=float, default=6.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--backoff", type=float, default=15.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.pages < 1 or args.retries < 1:
        print("pages 和 retries 必须大于 0", file=sys.stderr)
        return 2
    if args.min_delay < 0 or args.max_delay < args.min_delay:
        print("延迟参数不合法", file=sys.stderr)
        return 2

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "bilibili_raw.csv"
    final_path = output_dir / "bilibili_final.csv"
    state_path = output_dir / "crawl_state.json"
    rows = load_rows(raw_path)
    completed = load_state(state_path)
    session = build_session()

    print(f"已载入 {len(rows)} 条历史数据；输出目录：{output_dir.resolve()}")
    if not args.details_only:
        search(
            session, rows, completed, raw_path, state_path,
            args.pages, args.retries, args.backoff,
            args.min_delay, args.max_delay,
        )
    if args.details or args.details_only:
        enrich_details(
            session, rows, raw_path, args.retries, args.backoff,
            args.min_delay, args.max_delay,
        )
    export_final(final_path, rows)
    print(f"\n完成：去重后 {len(rows)} 条")
    print(f"原始/断点数据：{raw_path.resolve()}")
    print(f"SQL 兼容数据：{final_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
