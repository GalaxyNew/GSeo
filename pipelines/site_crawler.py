#!/usr/bin/env python3
"""SEO Site Crawler - 檢測死鏈/title/meta/h1/canonical 問題，寫入 PostgreSQL"""

import os, sys, json, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from loguru import logger
import psycopg2

TARGET_URL = os.environ.get("TARGET_URL", "https://igoriptv2.com")
DATABASE_URL = os.environ.get("DATABASE_URL",
    "postgresql://seo_user:changeme_in_production@127.0.0.1:5432/seo_db")
MAX_DEPTH = int(os.environ.get("CRAWLER_DEPTH", "2"))

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; SEO-Crawler/1.0)"})
session.timeout = 15

def get_db_conn():
    return psycopg2.connect(DATABASE_URL)

def crawl_page(url):
    result = {"url": url, "status": 0, "issues": []}
    try:
        resp = session.get(url, allow_redirects=True)
        result["status"] = resp.status_code
        result["final_url"] = resp.url
        if resp.status_code != 200:
            result["issues"].append({"issue_type": "http_error",
                "severity": "critical" if resp.status_code >= 500 else "high",
                "description": f"HTTP {resp.status_code}"})
            return result
        soup = BeautifulSoup(resp.text, "lxml")
        parsed = urlparse(url)
        # Title
        title_tag = soup.find("title")
        if not title_tag or not title_tag.string or len(title_tag.string.strip()) == 0:
            result["issues"].append({"issue_type": "missing_title",
                "severity": "critical", "description": "缺少 <title>"})
        elif len(title_tag.string.strip()) > 60:
            result["issues"].append({"issue_type": "title_too_long",
                "severity": "low",
                "description": f"Title 過長 ({len(title_tag.string.strip())}字符)"})
        # Meta Description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc or not meta_desc.get("content", "").strip():
            result["issues"].append({"issue_type": "missing_meta_description",
                "severity": "high", "description": "缺少 meta description"})
        # H1
        h1_tags = soup.find_all("h1")
        if not h1_tags:
            result["issues"].append({"issue_type": "missing_h1",
                "severity": "high", "description": "缺少 H1"})
        elif len(h1_tags) > 1:
            result["issues"].append({"issue_type": "multiple_h1",
                "severity": "low", "description": f"{len(h1_tags)} 個 H1"})
        # H2
        if not soup.find_all("h2"):
            result["issues"].append({"issue_type": "missing_h2",
                "severity": "low", "description": "缺少 H2"})
        # Canonical
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if canonical and canonical.get("href"):
            cu = urljoin(url, canonical["href"])
            if cu.rstrip("/") != url.rstrip("/"):
                result["issues"].append({"issue_type": "canonical_mismatch",
                    "severity": "low", "description": f"Canonical 不匹配: {cu}"})
        # Alt
        images = soup.find_all("img")
        missing_alt = sum(1 for img in images if not img.get("alt", "").strip())
        if missing_alt > 0:
            result["issues"].append({"issue_type": "missing_alt",
                "severity": "low",
                "description": f"{missing_alt}/{len(images)} 圖片缺 alt"})
        # OG Title
        if not soup.find("meta", attrs={"property": "og:title"}):
            result["issues"].append({"issue_type": "missing_og_title",
                "severity": "low", "description": "缺少 og:title"})
        # HTML lang
        html_tag = soup.find("html")
        if html_tag and not html_tag.get("lang"):
            result["issues"].append({"issue_type": "missing_html_lang",
                "severity": "high", "description": "<html> 缺 lang"})
        # 內部鏈接
        internal_links = set()
        for a in soup.find_all("a", href=True):
            full = urljoin(url, a["href"])
            if urlparse(full).netloc == parsed.netloc:
                internal_links.add(full.split("#")[0].split("?")[0])
        result["internal_links"] = list(internal_links)
    except requests.RequestException as e:
        result["issues"].append({"issue_type": "connection_error",
            "severity": "critical", "description": f"連接失敗: {str(e)[:200]}"})
    return result

def crawl_site(start_url, max_depth=2):
    visited, all_results, queue = set(), [], [(start_url, 0)]
    while queue:
        url, depth = queue.pop(0)
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        logger.info(f"爬取 [{depth}/{max_depth}] {url}")
        result = crawl_page(url)
        all_results.append(result)
        if depth < max_depth and "internal_links" in result:
            for link in result["internal_links"]:
                if link not in visited:
                    queue.append((link, depth + 1))
    return all_results

def save_to_db(results):
    conn = get_db_conn()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    for page in results:
        url = page.get("final_url", page["url"])
        for issue in page.get("issues", []):
            cur.execute(
                "INSERT INTO audits (url, issue_type, severity, description, created_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (url, issue["issue_type"], issue["severity"], issue["description"], now))
    conn.commit()
    count = cur.rowcount
    cur.close()
    conn.close()
    return count

def main():
    logger.info(f"開始爬取 {TARGET_URL}，深度 {MAX_DEPTH}")
    results = crawl_site(TARGET_URL, MAX_DEPTH)
    total_issues = sum(len(p.get("issues", [])) for p in results)
    logger.info(f"完成：{len(results)} 頁，{total_issues} 問題")
    if "--dry-run" not in sys.argv:
        c = save_to_db(results)
        logger.info(f"寫入 {c} 條")
    else:
        logger.info("DRY RUN")
        print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
