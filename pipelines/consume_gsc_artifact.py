#!/usr/bin/env python3
"""Consume a GSC collector artifact and generate a Guangzhou dry-run report.
This script does not call Google APIs and does not require GSC credentials.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--artifact', required=True)
    ap.add_argument('--out-dir', default='/opt/seo-system/logs')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    artifact_path = Path(args.artifact)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    artifact = json.loads(artifact_path.read_text())
    checksum = sha256_file(artifact_path)

    required = ['property', 'startDate', 'endDate', 'source_status', 'collector_node', 'generated_at', 'queries']
    missing = [k for k in required if k not in artifact]
    if missing:
        raise SystemExit(f'missing required artifact fields: {missing}')

    queries = artifact.get('queries', {})
    report = {
        'mode': 'dry-run' if args.dry_run else 'manual',
        'generated_at': dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'consumer_node': 'guangzhou-seo-system',
        'artifact_path': str(artifact_path),
        'artifact_sha256': checksum,
        'property': artifact.get('property'),
        'startDate': artifact.get('startDate'),
        'endDate': artifact.get('endDate'),
        'source_status': artifact.get('source_status'),
        'collector_node': artifact.get('collector_node'),
        'collector_generated_at': artifact.get('generated_at'),
        'dataSource': artifact.get('dataSource', 'Google Search Console'),
        'dataforseoStatus': artifact.get('dataforseoStatus', 'missing/degraded'),
        'summary': {
            'dateRows': queries.get('date', {}).get('rowCount', 0),
            'queryRows': queries.get('query', {}).get('rowCount', 0),
            'pageRows': queries.get('page', {}).get('rowCount', 0),
        },
        'guardrails': {
            'formal_push_enabled': False,
            'scheduler_enabled': False,
            'frontend_site_modified': False,
            'dataforseo_real_data_available': False,
        },
        'notes': [
            'GSC data came from a collector artifact; Guangzhou did not call Google APIs in this run.',
            'DataForSEO is still missing/degraded; do not output keyword volume, CPC, SERP rank, or competitor data as real data.',
            'This is not production enablement; no crontab/systemd/APScheduler is enabled.'
        ]
    }

    out = out_dir / f"gsc-consumer-dry-run-{dt.date.today().isoformat()}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({
        'ok': True,
        'output': str(out),
        'artifact_sha256': checksum,
        'property': report['property'],
        'source_status': report['source_status'],
        **report['summary'],
        'scheduler_enabled': report['guardrails']['scheduler_enabled'],
        'formal_push_enabled': report['guardrails']['formal_push_enabled'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
