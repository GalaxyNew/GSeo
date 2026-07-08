#!/usr/bin/env python3
"""Lighthouse Audit - 執行 headless Lighthouse 審計，寫入 PostgreSQL"""

import json, subprocess, sys, os
from datetime import datetime, timezone
import psycopg2

TARGET_URL = os.environ.get("TARGET_URL", "https://igoriptv2.com")
DATABASE_URL = os.environ.get("DATABASE_URL",
    "postgresql://seo_user:changeme_in_production@127.0.0.1:5432/seo_db")
CHROME_FLAGS = "--headless --no-sandbox --disable-gpu --disable-dev-shm-usage"
OUTPUT_DIR = "/tmp"

def run_lighthouse(url, form_factor="desktop"):
    preset = "desktop" if form_factor == "desktop" else "desktop"
    extra_flags = ""
    if form_factor == "mobile":
        extra_flags = "--emulated-form-factor=mobile --chrome-flags='--headless --no-sandbox --disable-gpu --disable-dev-shm-usage --emulated-form-factor=mobile'"
    else:
        extra_flags = f"--chrome-flags='{CHROME_FLAGS}'"

    outpath = os.path.join(OUTPUT_DIR, f"lh-{form_factor}.json")
    cmd = f"lighthouse {url} {extra_flags} --output=json --output-path={outpath} --quiet --no-save-artifacts"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"Lighthouse stderr: {result.stderr}", file=sys.stderr)
        return None, result.stderr
    with open(outpath) as f:
        return json.load(f), None

def extract_scores(report):
    cats = report.get("categories", {})
    audits = report.get("audits", {})
    scores = {}
    for k, col in [("performance", "performance"), ("accessibility", "accessibility"),
                    ("best-practices", "best_practices"), ("seo", "seo")]:
        v = cats.get(k, {}).get("score")
        scores[col] = round(v * 100, 1) if v is not None else None

    for audit_key, col in [("largest-contentful-paint", "lcp"),
                            ("total-blocking-time", "fid"),
                            ("cumulative-layout-shift", "cls")]:
        a = audits.get(audit_key, {})
        nv = a.get("numericValue")
        if col == "cls":
            scores[col] = round(nv, 2) if nv is not None else None
        else:
            scores[col] = round(nv) if nv is not None else None
    return scores

def save_to_db(url, device, scores):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    cur.execute(
        "INSERT INTO lighthouse_scores (url, device, performance, accessibility, best_practices, seo, lcp, fid, cls, checked_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (url, device, scores.get("performance"), scores.get("accessibility"),
         scores.get("best_practices"), scores.get("seo"),
         scores.get("lcp"), scores.get("fid"), scores.get("cls"), now))
    conn.commit()
    cnt = cur.rowcount
    cur.close()
    conn.close()
    return cnt

def main():
    dry_run = "--dry-run" in sys.argv

    for device in ["desktop", "mobile"]:
        print(f"=== {device} ===")
        report, err = run_lighthouse(TARGET_URL, device)
        if report is None:
            print(f"FAILED: {err}")
            continue
        scores = extract_scores(report)
        for k, v in scores.items():
            print(f"  {k}: {v}")
        if not dry_run:
            cnt = save_to_db(TARGET_URL, device, scores)
            print(f"  DB: {cnt} row inserted")
        else:
            print("  DRY RUN")

if __name__ == "__main__":
    main()
