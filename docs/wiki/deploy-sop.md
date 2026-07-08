# Deploy SOP

## Overview
SEO Command Center standard deployment procedure.

## Servers
| Name | IP | Purpose |
|------|-----|------|
| Guangzhou | 43.139.233.184 | SEO Dashboard / PG16 / Redis |
| Spain | 65.20.105.127 | igoriptv2.com production |

## Deploy Flow (Guangzhou)
1. SSH ubuntu@43.139.233.184
2. cd /opt/seo-system/seo-dashboard/
3. Update files
4. NODE_OPTIONS="--max-old-space-size=512" npm run build
5. sudo systemctl restart seo-dashboard
6. Verify all routes HTTP 200

## Database (PG16 Docker)
- Container: seo-postgres
- Connection: 127.0.0.1:5432 / seo_db / seo_user
- DDL: SCP SQL file -> docker exec -i seo-postgres psql -U seo_user -d seo_db < file.sql

## Verification
```bash
curl -s -o /dev/null -w "%%{http_code}" http://43.139.233.184/dashboard
curl -s -o /dev/null -w "%%{http_code}" http://43.139.233.184/plans
curl -s -o /dev/null -w "%%{http_code}" http://43.139.233.184/events
curl -s -o /dev/null -w "%%{http_code}" http://43.139.233.184/release
```
