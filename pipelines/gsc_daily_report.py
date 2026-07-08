#!/usr/bin/env python3
"""
SEO Daily Report Generator — T13-S2
Reads GSC data from PostgreSQL and formats a daily/weekly report.

Usage:
    python3 gsc_daily_report.py --dry-run          # Print to stdout, don't send
    python3 gsc_daily_report.py --mode daily       # Send daily report to Feishu
    python3 gsc_daily_report.py --mode weekly      # Send weekly report to Feishu
    python3 gsc_daily_report.py --collect-and-report  # Run GSC collector then generate report

Environment:
    PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB
    FEISHU_CHAT_ID (or --chat-id arg)
    GSC_PROXY (optional, http proxy for GSC API)
"""

import argparse
import json
import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta, date

logger = logging.getLogger("gsc_daily_report")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)

# ---------- Config ----------
PG_CONFIG = {
    "host": os.environ.get("PG_HOST", "127.0.0.1"),
    "port": int(os.environ.get("PG_PORT", "5432")),
    "user": os.environ.get("PG_USER", "seo_user"),
    "password": os.environ.get("PG_PASSWORD", "changeme_in_production"),
    "dbname": os.environ.get("PG_DB", "seo_db"),
}

FEISHU_CHAT_ID = os.environ.get("FEISHU_CHAT_ID", "oc_b8ace6e204d5cf6f7762c728cfd65e6d")

def get_pg_conn():
    import psycopg2
    return psycopg2.connect(**PG_CONFIG)

def fetch_report_data(conn, start_date, end_date):
    """Fetch aggregated GSC data for report period."""
    cur = conn.cursor()

    # Overall summary
    cur.execute("""
        SELECT
            SUM(clicks) as total_clicks,
            SUM(impressions) as total_impressions,
            CASE WHEN SUM(impressions) > 0
                THEN ROUND(SUM(clicks)::numeric / SUM(impressions), 4)
                ELSE 0 END as avg_ctr,
            CASE WHEN COUNT(*) > 0
                THEN ROUND(AVG(position)::numeric, 2)
                ELSE 0 END as avg_position,
            COUNT(DISTINCT date) as days_with_data
        FROM gsc.gsc_raw
        WHERE date >= %s AND date <= %s
    """, (start_date, end_date))
    summary = cur.fetchone()

    # Top queries
    cur.execute("""
        SELECT query, SUM(clicks) as clicks, SUM(impressions) as impressions,
            CASE WHEN SUM(impressions) > 0
                THEN ROUND(SUM(clicks)::numeric / SUM(impressions), 4)
                ELSE 0 END as ctr
        FROM gsc.gsc_raw
        WHERE date >= %s AND date <= %s AND query IS NOT NULL
        GROUP BY query
        ORDER BY clicks DESC
        LIMIT 10
    """, (start_date, end_date))
    top_queries = cur.fetchall()

    # Top pages
    cur.execute("""
        SELECT page, SUM(clicks) as clicks, SUM(impressions) as impressions,
            CASE WHEN SUM(impressions) > 0
                THEN ROUND(SUM(clicks)::numeric / SUM(impressions), 4)
                ELSE 0 END as ctr
        FROM gsc.gsc_raw
        WHERE date >= %s AND date <= %s AND page IS NOT NULL
        GROUP BY page
        ORDER BY clicks DESC
        LIMIT 10
    """, (start_date, end_date))
    top_pages = cur.fetchall()

    # Device breakdown
    cur.execute("""
        SELECT device, SUM(clicks) as clicks, SUM(impressions) as impressions
        FROM gsc.gsc_raw
        WHERE date >= %s AND date <= %s
        GROUP BY device
        ORDER BY clicks DESC
    """, (start_date, end_date))
    devices = cur.fetchall()

    # Country breakdown
    cur.execute("""
        SELECT country, SUM(clicks) as clicks, SUM(impressions) as impressions
        FROM gsc.gsc_raw
        WHERE date >= %s AND date <= %s
        GROUP BY country
        ORDER BY clicks DESC
        LIMIT 10
    """, (start_date, end_date))
    countries = cur.fetchall()

    # Data source status
    cur.execute("""
        SELECT source_name, status, last_sync_at, rows_synced, updated_at
        FROM gsc.data_source_status
    """)
    source_status = cur.fetchall()

    # Previous period comparison (if available)
    prev_start = (date.fromisoformat(start_date) - timedelta(days=(date.fromisoformat(end_date) - date.fromisoformat(start_date)).days + 1)).isoformat()
    prev_end = (date.fromisoformat(start_date) - timedelta(days=1)).isoformat()
    cur.execute("""
        SELECT SUM(clicks), SUM(impressions)
        FROM gsc.gsc_raw
        WHERE date >= %s AND date <= %s
    """, (prev_start, prev_end))
    prev = cur.fetchone()
    prev_clicks = prev[0] or 0
    prev_impressions = prev[1] or 0

    return {
        "summary": {
            "total_clicks": summary[0] or 0,
            "total_impressions": summary[1] or 0,
            "avg_ctr": float(summary[2] or 0),
            "avg_position": float(summary[3] or 0),
            "days_with_data": summary[4] or 0,
        },
        "top_queries": [{"query": q, "clicks": c, "impressions": i, "ctr": float(t)} for q, c, i, t in top_queries],
        "top_pages": [{"page": p, "clicks": c, "impressions": i, "ctr": float(t)} for p, c, i, t in top_pages],
        "devices": [{"device": d, "clicks": c, "impressions": i} for d, c, i in devices],
        "countries": [{"country": c, "clicks": k, "impressions": i} for c, k, i in countries],
        "source_status": source_status,
        "prev_clicks": prev_clicks,
        "prev_impressions": prev_impressions,
        "period": {"start": start_date, "end": end_date},
    }

def detect_anomalies(data):
    """Detect anomalies and generate actionable insights."""
    anomalies = []
    suggestions = []

    clicks = data["summary"]["total_clicks"]
    impressions = data["summary"]["total_impressions"]
    prev_clicks = data["prev_clicks"]
    prev_impressions = data["prev_impressions"]

    # Clicks trend
    if prev_clicks > 0:
        change = (clicks - prev_clicks) / prev_clicks * 100
        if change > 50:
            anomalies.append(f"📈 点击量环比上涨 +{change:.1f}%（{prev_clicks} → {clicks}）")
        elif change < -30:
            anomalies.append(f"📉 点击量环比下降 {change:.1f}%（{prev_clicks} → {clicks}）")
            suggestions.append("建议：检查是否有索引被移除或页面不可访问")

    # Impressions trend
    if prev_impressions > 0:
        imp_change = (impressions - prev_impressions) / prev_impressions * 100
        if imp_change > 30:
            anomalies.append(f"📈 展示量环比上涨 +{imp_change:.1f}%（{prev_impressions} → {impressions}）")
        elif imp_change < -20:
            anomalies.append(f"📉 展示量环比下降 {imp_change:.1f}%（{prev_impressions} → {impressions}）")

    # CTR
    ctr = data["summary"]["avg_ctr"]
    if ctr < 0.01 and impressions > 100:
        anomalies.append(f"⚠️ CTR 偏低 {ctr:.2%}（展示 {impressions} 次但点击仅 {clicks}）")
        suggestions.append("建议：优化 title 和 meta description 以提高点击率")

    # Position
    pos = data["summary"]["avg_position"]
    if pos > 20:
        anomalies.append(f"⚠️ 平均排名 {pos:.1f}（低于前 20）")
        suggestions.append("建议：聚焦长尾关键词内容优化，提升核心页面排名")

    # Data freshness
    for status in data["source_status"]:
        name, st, last_sync, rows, updated = status
        if st != "synced":
            anomalies.append(f"🔴 数据源 {name} 状态异常: {st}")
        elif last_sync:
            hours_ago = (datetime.utcnow() - last_sync.replace(tzinfo=None)).total_seconds() / 3600
            if hours_ago > 24:
                anomalies.append(f"⚠️ 数据源 {name} 上次同步 {hours_ago:.0f} 小时前，可能过时")

    # Low data warning
    if data["summary"]["days_with_data"] == 0:
        anomalies.append("🔴 报告周期内无数据")

    if not anomalies:
        anomalies.append("✅ 数据正常，无异常指标")

    return anomalies, suggestions

def format_report(data, mode="daily"):
    """Format report as Feishu-compatible markdown."""
    period = data["period"]
    summary = data["summary"]

    if mode == "weekly":
        title = f"📊 **SEO 周报 | {period['start']} ~ {period['end']}"
    else:
        title = f"📊 **SEO 日报 | {period['end']}"

    lines = [title, ""]

    # Summary
    lines.append("**📈 核心指标**")
    lines.append(f"- 点击量: **{summary['total_clicks']}** | 展示量: **{summary['total_impressions']}**")
    lines.append(f"- 平均 CTR: **{summary['avg_ctr']:.2%}** | 平均排名: **{summary['avg_position']:.1f}**")
    lines.append(f"- 数据天数: {summary['days_with_data']}")

    # Trend
    if data["prev_clicks"] > 0 or data["prev_impressions"] > 0:
        lines.append("")
        lines.append("**📋 环比变化**")
        c_prev = data["prev_clicks"]
        i_prev = data["prev_impressions"]
        c_now = summary["total_clicks"]
        i_now = summary["total_impressions"]
        c_arrow = "↑" if c_now >= c_prev else "↓"
        i_arrow = "↑" if i_now >= i_prev else "↓"
        lines.append(f"- 点击: {c_prev} → {c_now} {c_arrow} | 展示: {i_prev} → {i_now} {i_arrow}")

    # Top queries
    if data["top_queries"]:
        lines.append("")
        lines.append("**🔍 热门搜索词 TOP10**")
        for i, q in enumerate(data["top_queries"], 1):
            lines.append(f"{i}. `{q['query']}` — {q['clicks']} clicks / {q['impressions']} impr / CTR {q['ctr']:.2%}")

    # Top pages
    if data["top_pages"]:
        lines.append("")
        lines.append("**📄 热门页面 TOP10**")
        for i, p in enumerate(data["top_pages"], 1):
            # Truncate long URLs
            page_display = p["page"] if len(p["page"]) <= 60 else p["page"][:57] + "..."
            lines.append(f"{i}. {page_display} — {p['clicks']} clicks / {p['impressions']} impr")

    # Device breakdown
    if data["devices"]:
        lines.append("")
        lines.append("**💻 设备分布**")
        for d in data["devices"]:
            pct = d["clicks"] / summary["total_clicks"] * 100 if summary["total_clicks"] > 0 else 0
            lines.append(f"- {d['device'].capitalize()}: {d['clicks']} clicks ({pct:.0f}%) / {d['impressions']} impr")

    # Country breakdown
    if data["countries"]:
        lines.append("")
        lines.append("**🌍 地区分布**")
        for c in data["countries"]:
            lines.append(f"- {c['country'].upper()}: {c['clicks']} clicks / {c['impressions']} impr")

    # Anomalies
    anomalies, suggestions = detect_anomalies(data)
    lines.append("")
    lines.append("**⚠️ 异常检测**")
    for a in anomalies:
        lines.append(f"- {a}")

    if suggestions:
        lines.append("")
        lines.append("**💡 行动建议**")
        for s in suggestions:
            lines.append(f"- {s}")

    lines.append("")
    lines.append(f"🕐 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')} | 数据源: GSC Service Account")

    return "\n".join(lines)

def send_feishu_report(report_text, chat_id=None):
    """Send report to Feishu group via lark-cli."""
    chat_id = chat_id or FEISHU_CHAT_ID
    logger.info(f"Sending report to Feishu chat: {chat_id}")

    try:
        env = os.environ.copy()
        env["LARK_CLI_WORKSPACE"] = "hermes"
        result = subprocess.run(
            ["lark-cli", "im", "+messages-send",
             "--as", "bot",
             "--chat-id", chat_id,
             "--markdown", report_text],
            capture_output=True, text=True, timeout=30, env=env
        )
        if result.returncode == 0:
            logger.info("Report sent to Feishu ✅")
        else:
            logger.error(f"Failed to send: {result.stderr[:200]}")
    except FileNotFoundError:
        logger.error("lark-cli not found on this server")
    except Exception as e:
        logger.error(f"Send failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="SEO Daily/Weekly Report")
    parser.add_argument("--dry-run", action="store_true", help="Print report without sending")
    parser.add_argument("--mode", default="daily", choices=["daily", "weekly"])
    parser.add_argument("--days", type=int, default=1, help="Days to report (default: 1 for daily)")
    parser.add_argument("--chat-id", help="Feishu chat ID override")
    parser.add_argument("--collect-and-report", action="store_true", help="Run collector then generate report")
    args = parser.parse_args()

    # Collect fresh data if requested
    if args.collect_and_report:
        logger.info("Running GSC collector...")
        try:
            env = os.environ.copy()
            env["GOOGLE_APPLICATION_CREDENTIALS"] = "/opt/seo-system/secrets/gsc-service-account.json"
            env.setdefault("https_proxy", "http://127.0.0.1:18888")
            result = subprocess.run(
                [sys.executable, "/opt/seo-system/pipelines/gsc_collector.py",
                 "--property", "igoriptv2.com", "--days", "7"],
                capture_output=True, text=True, timeout=120, env=env
            )
            logger.info(result.stdout[-500:] if result.stdout else "(no output)")
            if result.returncode != 0:
                logger.error(f"Collector failed: {result.stderr[:200]}")
        except Exception as e:
            logger.error(f"Collector error: {e}")

    # Determine date range
    today = date.today()
    if args.mode == "weekly":
        start_date = (today - timedelta(days=6)).isoformat()
        end_date = today.isoformat()
        args.days = 7
    else:
        start_date = (today - timedelta(days=max(args.days - 1, 0))).isoformat()
        end_date = today.isoformat()

    logger.info(f"Generating {args.mode} report: {start_date} ~ {end_date}")

    # Fetch data from PG
    conn = get_pg_conn()
    data = fetch_report_data(conn, start_date, end_date)
    conn.close()

    # Format report
    report = format_report(data, args.mode)

    if args.dry_run:
        print(report)
        logger.info("Dry-run complete (no Feishu send)")
    else:
        send_feishu_report(report, args.chat_id)

if __name__ == "__main__":
    main()
