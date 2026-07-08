# GSeo · SEO 指挥中心

igoriptv2.com SEO/GEO 自主运营系统——Agent 自主取数（GSC/DataForSEO）→ 数据驱动优化 → 审批发布 → 全程可观测。Owner 通过大屏/报表/飞书监督指挥。

## 架构总览

```text
[法国节点] Collector ──artifact──▶ [广州节点] SEO 指挥中心 ◀── Agent API ── OpenClaw 执行团队
   GSC / DataForSEO                 Next.js + PostgreSQL16          （Hermes 总经理调度）
                                    ├ /dashboard 观测大屏+项目总览
                                    ├ /plans     计划中枢（年→月→日）
                                    ├ /release   发布中心（审批+备份+回滚）
                                    └ /events    事件账本（EV-ID 全程留痕）
                                          │ 审批通过+备份后
                                          ▼
                              [西班牙节点] igoriptv2.com 生产站（改动冻结，经发布中心解冻）
```

## 文档

| 文档 | 说明 |
|---|---|
| [docs/01-需求分析-PRD.md](docs/01-需求分析-PRD.md) | 北极星、用户故事、功能清单、里程碑验收 |
| [docs/02-架构设计.md](docs/02-架构设计.md) | 六面合一重构方案（v1.1） |
| [docs/03-数据契约.md](docs/03-数据契约.md) | Schema/artifact/API 契约——**实现验收基准** |
| [docs/04-开发文档.md](docs/04-开发文档.md) | 环境、开发流程、部署与回滚 |
| [Wiki](../../wiki) | 运行 SOP、服务器台账、FAQ |

## 当前状态

- 里程碑：M1 进行中（观测大屏 v1 已上线广州节点 2026-07-08）
- 项目总览：广州后台 /dashboard（实时里程碑进度）
- 生产站：SEO 变更冻结中，待 M3 发布中心解冻

## 规则速记

分支 `feat/T{任务卡号}-{短名}`；PR 必须关联 issue 并附验证输出；涉西班牙站先跑 backup.sh 贴证据；**完成 = PR 合并 + 部署可访问 + CHANGELOG + 关 issue**，缺一不算。完整规则见任务账本治理规范（agent-vault）。
