# CHANGELOG

## [2026-07-08] T13-S1 GSC 只读接入工程化

### Added
- `pipelines/gsc_collector.py` — GSC 数据采集脚本（Service Account → PostgreSQL）
- PostgreSQL schema `gsc`: gsc_raw / metrics_daily / data_source_status
- HTTP CONNECT proxy 管线（广州 → 西班牙 VPS → Google API）

### Infrastructure
- 广州服务器 Python 依赖：google-api-python-client, psycopg2-binary, pysocks
- GSC Service Account 凭证安全存储：`/opt/seo-system/secrets/`

### Technical Notes
- GSC property URL 格式：`sc-domain:igoriptv2.com`（非 `sc-data:`）
- 代理架构：西班牙 VPS mini_proxy.py:8888 + SSH tunnel → 广州 127.0.0.1:18888

## [2026-07-08] T12-S2 广州后端代码纳入

### Added
- `apps/command-center/` — seo-dashboard Next.js 项目源码
- `pipelines/` — gsc_collector.py, site_crawler.py, gsc_consumer.py, lighthouse_audit.py
- `deploy/docker-compose.yml` — PostgreSQL + Redis compose

## [2026-07-08] T12-S1 前端站抢救

### Added
- speniptv 仓库：160 文件同步（生产站快照）
