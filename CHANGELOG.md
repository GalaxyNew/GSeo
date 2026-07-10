## 2026-07-11 - SEO P0 Meta/Title/Redirect Fix
- 修复 PageSeo.es metaDescription 脏前缀 `Description：`
- 补齐 3 篇西语博客缺失 metaDescription
- 缩短 3 篇过长 Title/metaTitle
- proxy.ts: `/es/*` 软跳转由默认 307 改为 301 永久重定向
- 生产验证：首页 description、博客 title/description、/es/* 301 已通过
- 同步服务器源码到 `apps/igortv/`（不含 node_modules/.next/.env/dev.db/uploads）

# Changelog
