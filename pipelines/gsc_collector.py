#!/usr/bin/env python3
"""GSC dry-run for igoriptv2.com.
Reads Google Search Console data and writes a redacted dry-run report.
Does not print or log service-account private key material.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession


def encode_site_url(site_url: str) -> str:
    return site_url.replace(":", "%3A").replace("/", "%2F")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--credentials", default="/opt/seo-automation/secrets/gsc-key.json")
    ap.add_argument("--property", default="sc-domain:igoriptv2.com")
    ap.add_argument("--log-dir", default="/opt/seo-system/logs")
    ap.add_argument("--days", type=int, default=10)
    args = ap.parse_args()

    key_path = Path(args.credentials)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Guangzhou server currently reaches Google APIs through the local SOCKS tunnel.
    # Use env vars only; never log proxy credentials or secret contents.
    os.environ.setdefault("HTTPS_PROXY", "socks5h://127.0.0.1:1080")
    os.environ.setdefault("HTTP_PROXY", "socks5h://127.0.0.1:1080")
    os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")

    today = dt.date.today()
    end = today - dt.timedelta(days=3)  # avoid GSC data delay
    start = today - dt.timedelta(days=args.days)

    scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
    creds = service_account.Credentials.from_service_account_file(str(key_path), scopes=scopes)
    session = AuthorizedSession(creds)
    # Some proxy exits return generic Google 403 HTML on www.googleapis.com. Use the
    # webmasters.googleapis.com endpoint, which is equivalent for Search Console API
    # and works through the current Guangzhou SOCKS route.
    base_url = "https://webmasters.googleapis.com/webmasters/v3"

    result = {
        "mode": "dry-run",
        "property": args.property,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "serviceAccount": creds.service_account_email,
        "dataSource": "Google Search Console",
        "dataforseoStatus": "missing/degraded",
        "queries": {},
    }

    site_resp = session.get(f"{base_url}/sites", timeout=30)
    result["sitesStatus"] = site_resp.status_code
    site_resp.raise_for_status()
    entries = site_resp.json().get("siteEntry", [])
    result["accessibleSites"] = [
        {"siteUrl": e.get("siteUrl"), "permissionLevel": e.get("permissionLevel")}
        for e in entries
    ]

    endpoint = f"{base_url}/sites/{encode_site_url(args.property)}/searchAnalytics/query"
    for dims in (["date"], ["query"], ["page"]):
        body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": dims, "rowLimit": 10}
        resp = session.post(endpoint, json=body, timeout=30)
        resp.raise_for_status()
        rows = resp.json().get("rows", [])
        safe_rows = []
        for r in rows[:10]:
            safe_rows.append({
                "keys": r.get("keys"),
                "clicks": r.get("clicks"),
                "impressions": r.get("impressions"),
                "ctr": r.get("ctr"),
                "position": r.get("position"),
            })
        result["queries"]["+".join(dims)] = {"rowCount": len(rows), "sampleRows": safe_rows}

    out = log_dir / ("gsc-dry-run-%s.json" % today.isoformat())
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({
        "ok": True,
        "mode": "dry-run",
        "property": args.property,
        "startDate": result["startDate"],
        "endDate": result["endDate"],
        "serviceAccount": result["serviceAccount"],
        "output": str(out),
        "dateRows": result["queries"].get("date", {}).get("rowCount"),
        "queryRows": result["queries"].get("query", {}).get("rowCount"),
        "pageRows": result["queries"].get("page", {}).get("rowCount"),
        "dataforseoStatus": result["dataforseoStatus"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
