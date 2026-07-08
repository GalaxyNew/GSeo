#!/usr/bin/env python3
"""
GSC Data Collector — T13-S1
Reads Google Search Console data via Service Account and writes to PostgreSQL.

Usage:
    python3 gsc_collector.py --property igoriptv2.com --days 7
    python3 gsc_collector.py --property igoriptv2.com --days 3 --dimension country

Credentials: GOOGLE_APPLICATION_CREDENTIALS env var (Service Account JSON path)
PostgreSQL: PG_HOST, PG_PORT, PG_USER, PG_PASSWORD, PG_DB env vars
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime, timedelta, date

# Silence noisy HTTP libraries
logging.getLogger("googleapiclient").setLevel(logging.WARNING)
logging.getLogger("google_auth_httplib2").setLevel(logging.WARNING)

logger = logging.getLogger("gsc_collector")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)

# ---------- Config from environment ----------
SA_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/opt/seo-system/secrets/gsc-service-account.json")
PG_CONFIG = {
    "host": os.environ.get("PG_HOST", "127.0.0.1"),
    "port": int(os.environ.get("PG_PORT", "5432")),
    "user": os.environ.get("PG_USER", "seo_user"),
    "password": os.environ.get("PG_PASSWORD", "changeme_in_production"),
    "dbname": os.environ.get("PG_DB", "seo_db"),
}

def get_gsc_service():
    """Authenticate and return GSC API service."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        if not os.path.exists(SA_PATH):
            raise FileNotFoundError(f"Service Account file not found: {SA_PATH}")

        credentials = service_account.Credentials.from_service_account_file(
            SA_PATH,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        service = build("searchconsole", "v1", credentials=credentials)
        logger.info("GSC Service Account authenticated successfully")
        return service
    except Exception as e:
        logger.error(f"GSC authentication failed: {e}")
        # Update data source status
        update_source_status("auth_failed", str(e))
        raise

def get_pg_conn():
    """Get PostgreSQL connection."""
    import psycopg2
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = False
        return conn
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        raise

def update_source_status(status, error=None, rows=0):
    """Update data source status in PG."""
    try:
        import psycopg2
        conn = psycopg2.connect(**PG_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            UPDATE gsc.data_source_status
            SET status = %s, last_error = %s, rows_synced = %s, updated_at = NOW()
            WHERE source_name = %s
        """, (status, error, rows, "gsc_igoriptv2"))
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to update source status: {e}")

def fetch_gsc_data(service, property_url, start_date, end_date, dimensions=None):
    """Fetch GSC data for given date range and dimensions."""
    if dimensions is None:
        dimensions = ["query", "page"]

    all_rows = []
    start_row = 0
    batch_size = 25000

    while True:
        try:
            request = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": dimensions,
                "rowLimit": batch_size,
                "startRow": start_row,
            }
            response = service.searchanalytics().query(
                siteUrl=f"sc-domain:{property_url}",
                body=request
            ).execute()

            rows = response.get("rows", [])
            if not rows:
                break

            for row in rows:
                record = {
                    "property_url": property_url,
                    "date": start_date,  # simplified: use start_date for all
                }
                for i, dim in enumerate(dimensions):
                    record[dim] = row["keys"][i] if i < len(row["keys"]) else None
                record["clicks"] = row.get("clicks", 0)
                record["impressions"] = row.get("impressions", 0)
                record["ctr"] = row.get("ctr", 0)
                record["position"] = row.get("position", 0)
                all_rows.append(record)

            if len(rows) < batch_size:
                break
            start_row += batch_size

        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "permission" in error_msg.lower():
                logger.error(f"GSC permission denied for {property_url}: {e}")
                update_source_status("permission_denied", error_msg)
                raise
            elif "not found" in error_msg.lower():
                logger.error(f"GSC property not found: {property_url}: {e}")
                update_source_status("property_not_found", error_msg)
                raise
            else:
                logger.error(f"GSC query error: {e}")
                raise

    return all_rows

def insert_gsc_data(conn, records, sync_date):
    """Insert GSC raw data into PostgreSQL."""
    cur = conn.cursor()
    inserted = 0

    for rec in records:
        cur.execute("""
            INSERT INTO gsc.gsc_raw
                (property_url, query, page, device, country,
                 clicks, impressions, ctr, position, date, sync_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            rec["property_url"],
            rec.get("query"),
            rec.get("page"),
            rec.get("device", "desktop"),
            rec.get("country", "gbr"),
            rec["clicks"],
            rec["impressions"],
            round(rec["ctr"], 6),
            round(rec["position"], 2),
            rec["date"],
            sync_date,
        ))
        inserted += cur.rowcount

    conn.commit()
    return inserted

def aggregate_daily_metrics(conn, property_url, metric_date):
    """Aggregate raw data into daily metrics by dimension."""
    cur = conn.cursor()

    # By query
    cur.execute("""
        INSERT INTO gsc.metrics_daily (property_url, metric_date, dimension, dimension_value,
            total_clicks, total_impressions, avg_ctr, avg_position)
        SELECT %s, %s::date, 'query', query,
            SUM(clicks), SUM(impressions),
            CASE WHEN SUM(impressions) > 0 THEN SUM(clicks)::decimal / SUM(impressions) ELSE 0 END,
            CASE WHEN COUNT(*) > 0 THEN AVG(position) ELSE 0 END
        FROM gsc.gsc_raw
        WHERE property_url = %s AND date = %s AND query IS NOT NULL
        GROUP BY query
        ON CONFLICT (property_url, metric_date, dimension, dimension_value) DO UPDATE SET
            total_clicks = EXCLUDED.total_clicks,
            total_impressions = EXCLUDED.total_impressions,
            avg_ctr = EXCLUDED.avg_ctr,
            avg_position = EXCLUDED.avg_position
    """, (property_url, metric_date, property_url, metric_date))

    # By page
    cur.execute("""
        INSERT INTO gsc.metrics_daily (property_url, metric_date, dimension, dimension_value,
            total_clicks, total_impressions, avg_ctr, avg_position)
        SELECT %s, %s::date, 'page', page,
            SUM(clicks), SUM(impressions),
            CASE WHEN SUM(impressions) > 0 THEN SUM(clicks)::decimal / SUM(impressions) ELSE 0 END,
            CASE WHEN COUNT(*) > 0 THEN AVG(position) ELSE 0 END
        FROM gsc.gsc_raw
        WHERE property_url = %s AND date = %s AND page IS NOT NULL
        GROUP BY page
        ON CONFLICT (property_url, metric_date, dimension, dimension_value) DO UPDATE SET
            total_clicks = EXCLUDED.total_clicks,
            total_impressions = EXCLUDED.total_impressions,
            avg_ctr = EXCLUDED.avg_ctr,
            avg_position = EXCLUDED.avg_position
    """, (property_url, metric_date, property_url, metric_date))

    # By country (use 'country' field)
    cur.execute("""
        INSERT INTO gsc.metrics_daily (property_url, metric_date, dimension, dimension_value,
            total_clicks, total_impressions, avg_ctr, avg_position)
        SELECT %s, %s::date, 'country', country,
            SUM(clicks), SUM(impressions),
            CASE WHEN SUM(impressions) > 0 THEN SUM(clicks)::decimal / SUM(impressions) ELSE 0 END,
            CASE WHEN COUNT(*) > 0 THEN AVG(position) ELSE 0 END
        FROM gsc.gsc_raw
        WHERE property_url = %s AND date = %s
        GROUP BY country
        ON CONFLICT (property_url, metric_date, dimension, dimension_value) DO UPDATE SET
            total_clicks = EXCLUDED.total_clicks,
            total_impressions = EXCLUDED.total_impressions,
            avg_ctr = EXCLUDED.avg_ctr,
            avg_position = EXCLUDED.avg_position
    """, (property_url, metric_date, property_url, metric_date))

    # By device
    cur.execute("""
        INSERT INTO gsc.metrics_daily (property_url, metric_date, dimension, dimension_value,
            total_clicks, total_impressions, avg_ctr, avg_position)
        SELECT %s, %s::date, 'device', device,
            SUM(clicks), SUM(impressions),
            CASE WHEN SUM(impressions) > 0 THEN SUM(clicks)::decimal / SUM(impressions) ELSE 0 END,
            CASE WHEN COUNT(*) > 0 THEN AVG(position) ELSE 0 END
        FROM gsc.gsc_raw
        WHERE property_url = %s AND date = %s
        GROUP BY device
        ON CONFLICT (property_url, metric_date, dimension, dimension_value) DO UPDATE SET
            total_clicks = EXCLUDED.total_clicks,
            total_impressions = EXCLUDED.total_impressions,
            avg_ctr = EXCLUDED.avg_ctr,
            avg_position = EXCLUDED.avg_position
    """, (property_url, metric_date, property_url, metric_date))

    conn.commit()
    logger.info(f"Aggregated metrics for {metric_date}")

def print_sample_data(conn, limit=5):
    """Print sanitized sample data for verification."""
    cur = conn.cursor()

    logger.info(f"=== Sample gsc_raw (top {limit}) ===")
    cur.execute("""
        SELECT property_url, LEFT(query, 30) as query_preview,
               LEFT(page, 40) as page_preview,
               device, country, clicks, impressions,
               ROUND(ctr::numeric, 4) as ctr, ROUND(position::numeric, 1) as pos,
               date, sync_date
        FROM gsc.gsc_raw
        ORDER BY impressions DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    if rows:
        print(f"{'Property':<20} {'Query':<32} {'Clicks':>7} {'Impr':>7} {'CTR':>8} {'Pos':>6}")
        print("-" * 90)
        for r in rows:
            print(f"{r[0]:<20} {(r[1] or 'NULL'):<32} {r[5]:>7} {r[6]:>7} {float(r[7] or 0):>8.4f} {float(r[8] or 0):>6.1f}")
    else:
        print("No data in gsc_raw")

    logger.info(f"=== Sample metrics_daily (top {limit}) ===")
    cur.execute("""
        SELECT property_url, metric_date, dimension, LEFT(dimension_value, 30) as value,
               total_clicks, total_impressions
        FROM gsc.metrics_daily
        ORDER BY total_impressions DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    if rows:
        print(f"{'Property':<20} {'Date':<12} {'Dim':<10} {'Value':<32} {'Clicks':>7} {'Impr':>7}")
        print("-" * 100)
        for r in rows:
            print(f"{r[0]:<20} {str(r[1]):<12} {r[2]:<10} {(r[3] or 'NULL'):<32} {r[4]:>7} {r[5]:>7}")
    else:
        print("No data in metrics_daily")

    logger.info(f"=== Data source status ===")
    cur.execute("SELECT * FROM gsc.data_source_status")
    for r in cur.fetchall():
        logger.info(f"  {r}")

def main():
    parser = argparse.ArgumentParser(description="GSC Data Collector")
    parser.add_argument("--property", required=True, help="GSC property URL (e.g. igoriptv2.com)")
    parser.add_argument("--days", type=int, default=7, help="Days of data to fetch")
    parser.add_argument("--dimension", default="query,page", help="Dimensions (query,page,device,country)")
    parser.add_argument("--dry-run", action="store_true", help="Only fetch, don't write to PG")
    args = parser.parse_args()

    logger.info(f"GSC Collector starting: property={args.property}, days={args.days}, dims={args.dimension}")

    # 1. Authenticate
    service = get_gsc_service()
    update_source_status("authenticating")

    # 2. Fetch data day by day
    dimensions = [d.strip() for d in args.dimension.split(",")]
    all_records = []
    today = date.today()

    for i in range(args.days):
        d = today - timedelta(days=i)
        d_str = d.isoformat()
        try:
            records = fetch_gsc_data(service, args.property, d_str, d_str, dimensions)
            all_records.extend(records)
            logger.info(f"Fetched {len(records)} records for {d_str}")
        except Exception as e:
            logger.error(f"Failed to fetch {d_str}: {e}")
            # Continue with other days (degraded mode)
            continue

    logger.info(f"Total records fetched: {len(all_records)}")

    if args.dry_run:
        logger.info("Dry-run mode: skipping PG write")
        if all_records:
            print(f"\nSample record (dry-run):")
            r = all_records[0]
            for k, v in r.items():
                val = str(v)[:50] if v else "NULL"
                print(f"  {k}: {val}")
        update_source_status("dry_run_complete", rows=len(all_records))
        return

    if not all_records:
        logger.warning("No records fetched — nothing to write")
        update_source_status("no_data")
        return

    # 3. Write to PG
    conn = get_pg_conn()
    sync_date = today.isoformat()

    inserted = insert_gsc_data(conn, all_records, sync_date)
    logger.info(f"Inserted {inserted} records into gsc.gsc_raw")

    # 4. Aggregate
    for i in range(args.days):
        d = today - timedelta(days=i)
        try:
            aggregate_daily_metrics(conn, args.property, d.isoformat())
        except Exception as e:
            logger.error(f"Aggregation failed for {d.isoformat()}: {e}")

    # 5. Update status
    update_source_status("synced", rows=inserted)
    logger.info(f"Data source status updated: synced, {inserted} rows")

    # 6. Print sample
    print_sample_data(conn)

    conn.close()
    logger.info("GSC Collector completed successfully")

if __name__ == "__main__":
    main()
