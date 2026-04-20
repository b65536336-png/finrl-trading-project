#!/usr/bin/env python3
"""统计《光明日报》历史新闻中关键词出现词频（按年汇总）。

默认关键词：气候风险
默认时间范围：2000-01-01 到 2024-12-31

说明：
- 脚本基于光明日报电子版页面结构（epaper.gmw.cn）抓取。
- 若网络环境无法访问站点，可在可联网机器运行同一脚本。
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

BASE = "https://epaper.gmw.cn/gmrb/html/{ym}/{d}/nbs.D110000gmrb_01.htm"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


@dataclass
class FetchStats:
    issue_pages_ok: int = 0
    issue_pages_fail: int = 0
    article_pages_ok: int = 0
    article_pages_fail: int = 0


def daterange(start: dt.date, end: dt.date) -> Iterable[dt.date]:
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def fetch_text(url: str, timeout: int = 20, retries: int = 2, sleep_s: float = 0.3) -> str | None:
    req = urllib.request.Request(url, headers=HEADERS)
    for i in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
            # 页面通常是 utf-8，失败时忽略非法字符
            return raw.decode("utf-8", "ignore")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            if i == retries:
                return None
            time.sleep(sleep_s * (i + 1))
    return None


def extract_article_urls(issue_html: str, issue_url: str) -> list[str]:
    # 新版文章链接模式：nw.D110000gmrb_YYYYMMDD_1-08.htm
    rels = set(re.findall(r'href=["\']([^"\']*nw\.D110000gmrb_[^"\']+\.htm)["\']', issue_html))
    if not rels:
        return []

    base = issue_url.rsplit("/", 1)[0] + "/"
    urls = []
    for rel in sorted(rels):
        abs_u = urllib.parse.urljoin(base, rel)
        urls.append(abs_u)
    return urls


def strip_html(html: str) -> str:
    text = re.sub(r"<script[\\s\\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\\s\\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_keyword_occurrences(text: str, keyword: str) -> int:
    return text.count(keyword)


def crawl(keyword: str, start: dt.date, end: dt.date, max_days: int | None = None) -> tuple[dict[int, int], FetchStats]:
    year_counts: dict[int, int] = defaultdict(int)
    stats = FetchStats()

    days = list(daterange(start, end))
    if max_days is not None:
        days = days[:max_days]

    for d in days:
        issue_url = BASE.format(ym=d.strftime("%Y-%m"), d=d.strftime("%d"))
        issue_html = fetch_text(issue_url)
        if issue_html is None:
            stats.issue_pages_fail += 1
            continue

        stats.issue_pages_ok += 1
        article_urls = extract_article_urls(issue_html, issue_url)

        for aurl in article_urls:
            ahtml = fetch_text(aurl)
            if ahtml is None:
                stats.article_pages_fail += 1
                continue
            stats.article_pages_ok += 1

            plain = strip_html(ahtml)
            c = count_keyword_occurrences(plain, keyword)
            if c:
                year_counts[d.year] += c

        time.sleep(0.1)

    return dict(sorted(year_counts.items())), stats


def write_outputs(year_counts: dict[int, int], stats: FetchStats, out_prefix: str) -> None:
    csv_path = f"{out_prefix}.csv"
    json_path = f"{out_prefix}.json"

    years = list(range(2000, 2025))
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "keyword_count"])
        for y in years:
            w.writerow([y, year_counts.get(y, 0)])

    payload = {
        "keyword": "气候风险",
        "range": ["2000-01-01", "2024-12-31"],
        "year_counts": {str(y): year_counts.get(y, 0) for y in years},
        "fetch_stats": stats.__dict__,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="统计光明日报新闻关键词词频（按年）")
    p.add_argument("--keyword", default="气候风险", help="统计关键词，默认：气候风险")
    p.add_argument("--start", default="2000-01-01", help="开始日期，YYYY-MM-DD")
    p.add_argument("--end", default="2024-12-31", help="结束日期，YYYY-MM-DD")
    p.add_argument("--out-prefix", default="results/gmrb_climate_risk_2000_2024", help="输出文件前缀")
    p.add_argument("--max-days", type=int, default=None, help="仅用于调试，限制抓取天数")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    year_counts, stats = crawl(args.keyword, start, end, args.max_days)
    write_outputs(year_counts, stats, args.out_prefix)

    print("抓取完成。")
    print(f"关键词: {args.keyword}")
    print(f"范围: {args.start} ~ {args.end}")
    print(f"版面页成功/失败: {stats.issue_pages_ok}/{stats.issue_pages_fail}")
    print(f"文章页成功/失败: {stats.article_pages_ok}/{stats.article_pages_fail}")
    print("按年词频（仅展示>0）：")
    non_zero = {y: c for y, c in year_counts.items() if c > 0}
    print(non_zero if non_zero else "无（可能受网络或源站访问限制影响）")


if __name__ == "__main__":
    main()
