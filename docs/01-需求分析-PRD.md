# GSeo · SEO 指挥中心 需求分析（PRD）v1.0

> 产品：igoriptv2.com SEO/GEO 自主运营系统（代号 GSeo）
> 干系人：用户746879（Owner/唯一审批人）、Hermes（总经理）、OpenClaw 执行团队
> 更新：2026-07-08

## 1. 背景与问题

igoriptv2.com 是已上线的西语 IPTV 销售站（西班牙节点，Cloudflare 前置）。SEO 运营目前依赖人工与零散讨论：数据看不到、计划无载体、变更无审批闭环、进度不透明。任务分散在多张卡与多个群，无统一管理。

## 2. 北极星目标（Owner 原话，2026-07-08）

> Agent 自主获取 GSC 数据 → 结合 DataForSEO 等外部数据优化站点 → 自主在系统后台记录运维 → Owner 作为监督者通过报表/大屏/飞书掌握全局并协同指挥。

两条铁律：① 任何实装到前端站点的变更，操作前必须备份；② 生产变更必须经审批页分类审批，未经审批冻结。

## 3. 用户与场景

| 角色 | 场景 | 诉求 |
|---|---|---|
| Owner | 每天打开大屏/收飞书日报 | 30 秒看懂：流量趋势、计划进度、项目状态、待我审批什么 |
| Owner | 收到发布审批请求 | 分类批量审批安全项、逐项确认敏感项、一键驳回危险项 |
| SEO agent | 每日取数分析 | 数据自动入库、写分析事件、生成优化提案 |
| 全栈/DevOps agent | 交付功能 | PR 合并即上线即进 CHANGELOG，进度自动可见 |
| Hermes | 巡检推进 | 计划树/事件账本作为派单与验收依据 |

## 4. 功能需求（按模块，P0=必须）

### M-A 观测大屏 /dashboard（P0，已上线 v1 于 2026-07-08 05:46）
- A1 GSC 核心指标卡：点击/曝光/平均排名/收录，日环比 ✅v1 部分
- A2 项目总览板块：里程碑进度条、当前进行项+负责人、最近交付（GitHub API 实时）
- A3 渠道数据：DataForSEO 关键词排名、站点健康（M2 接入）
- A4 告警横幅：Critical 事件置顶

### M-B 计划中枢 /plans（P0）
- B1 计划树：年→月→日三层，可折叠
- B2 条目分类：keyword / backlink / article / tech-seo，每条含负责人、状态、关联任务卡/issue
- B3 es-ES 首批关键词库导入为 keyword 条目
- B4 进度自动汇总到父层

### M-C 发布中心 /release（P0，解冻生产的前提）
- C1 ReleasePlan→ChangeItem 审批流（复用已验收对象模型：三级分类 batch_ok/manual_confirm/blocker + 三态 normal/blocked/audit）
- C2 强制前置：BackupRecord 存在才允许执行（铁律①）
- C3 执行→健康检查→异常自动回滚（RollbackPlan 必须 dry-run 验证过）
- C4 审计视图：已发布计划只读（audit 态）

### M-D 事件账本 /events（P1）
- D1 统一事件 ID（EV-日期-序号），actor/action/input/output/evidence
- D2 按任务卡/agent/日期筛选；敏感信息 [REDACTED] 规则

### 非功能
- 部署广州（43.139.233.184），西班牙站零改动直到 M-C 可用
- Agent API token 鉴权；审批动作仅 Owner
- 页面加载 <2s；大屏 60s 自动刷新

## 5. 明确不做（本期）

- 多站点支持（只服务 igoriptv2.com）
- 用户系统/多人权限（Owner 单人 + agent token）
- 移动端适配（大屏优先，响应式够用即可）

## 6. 里程碑与验收

| 里程碑 | 范围 | 验收 |
|---|---|---|
| M1 | A2/B1/B2/D1 + 骨架四路由 | Owner 打开大屏见实时项目总览 |
| M2 | 数据管道转正（GSC cron/日报/告警）+ A1/A3 全量 | 运维群每日真实日报 |
| M3 | M-C 全量 → 解冻生产 | 首个真实 SEO 变更经审批上线并演练回滚 |
| M4 | 自主优化循环（提案→审批→发布→效果回填） | 北极星达成 |
