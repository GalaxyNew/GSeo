import pg from 'pg'

const pool = new pg.Pool({
  host: '127.0.0.1',
  port: 5432,
  database: 'seo_db',
  user: 'seo_user',
  password: 'changeme_in_production',
})

interface Release {
  id: string
  title: string
  plan: string | null
  status: string
  createdAt: string
  updatedAt: string
  changeItemCount: number
  backupCount: number
  verifiedCount: number
  totalChecks: number
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  draft: { label: '草稿', color: '#64748b', icon: '📝' },
  approved: { label: '已审批', color: '#fbbf24', icon: '✅' },
  executing: { label: '执行中', color: '#22d3ee', icon: '⚡' },
  done: { label: '已完成', color: '#34d399', icon: '🎯' },
  rolledback: { label: '已回滚', color: '#fb7185', icon: '⏪' },
}

const TYPE_LABELS: Record<string, string> = {
  content: '📄 内容',
  code: '💻 代码',
  config: '⚙️ 配置',
  database: '🗄️ 数据库',
}

async function getReleases(): Promise<Release[]> {
  const { rows } = await pool.query(`
    SELECT r.*,
      COALESCE(c.cnt, 0)::int as "changeItemCount",
      COALESCE(b.cnt, 0)::int as "backupCount",
      COALESCE(v.ok::int, 0) as "verifiedCount",
      COALESCE(v.total::int, 0) as "totalChecks"
    FROM seo_release r
    LEFT JOIN (SELECT release_id, COUNT(*) as cnt FROM seo_change_item GROUP BY release_id) c ON r.id = c.release_id
    LEFT JOIN (SELECT release_id, COUNT(*) as cnt FROM seo_backup_record GROUP BY release_id) b ON r.id = b.release_id
    LEFT JOIN (SELECT release_id, COUNT(*) FILTER (WHERE status = 'passed') as ok, COUNT(*) as total FROM seo_verification_check GROUP BY release_id) v ON r.id = v.release_id
    ORDER BY r.created_at DESC
  `)
  return rows
}

export default async function ReleasePage() {
  const releases = await getReleases()

  const stats = {
    total: releases.length,
    active: releases.filter(r => ['approved', 'executing'].includes(r.status)).length,
    done: releases.filter(r => r.status === 'done').length,
  }

  return (
    <div className="p-4 md:p-8 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-extrabold mb-2">
          <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
            发布中心
          </span>
        </h1>
        <p className="text-slate-400 text-sm">发布管理 · 备份记录 · 回滚清单 · 验证检查</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4 mb-8">
        {[
          { label: '总发布', value: stats.total, icon: '📦' },
          { label: '进行中', value: stats.active, icon: '⚡' },
          { label: '已完成', value: stats.done, icon: '🎯' },
        ].map((s, i) => (
          <div key={i} className="bg-[#101622] border border-[#253247] rounded-2xl p-4 md:p-5">
            <div className="text-2xl mb-2">{s.icon}</div>
            <div className="text-3xl md:text-4xl font-extrabold text-cyan-400">{s.value}</div>
            <div className="text-xs text-slate-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Status filter badges */}
      <div className="flex flex-wrap gap-2 mb-6">
        <h2 className="text-sm font-semibold text-slate-200 mr-2">状态筛选：</h2>
        {Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
          const count = releases.filter(r => r.status === key).length
          if (count === 0) return null
          return (
            <span key={key} className="text-[10px] font-semibold px-2 py-0.5 rounded-full border" style={{ color: cfg.color, background: cfg.color + '18', borderColor: cfg.color + '33' }}>
              {cfg.icon} {cfg.label} ({count})
            </span>
          )
        })}
      </div>

      {/* Release cards */}
      <div className="space-y-4">
        {releases.length === 0 ? (
          <div className="bg-[#101622] border border-[#253247] rounded-xl p-8 text-center text-slate-500 text-sm">
            暂无发布记录。通过 API POST /api/releases 创建。
          </div>
        ) : (
          releases.map(r => {
            const cfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.draft
            const date = new Date(r.createdAt)
            return (
              <div key={r.id} className="bg-[#101622] border border-[#253247] rounded-xl p-5 hover:border-cyan-800/50 transition-colors">
                <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-100">{r.title}</h3>
                    {r.plan && <p className="text-xs text-slate-400 mt-1">{r.plan}</p>}
                  </div>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0" style={{ color: cfg.color, background: cfg.color + '18', border: '1px solid ' + cfg.color + '33' }}>
                    {cfg.icon} {cfg.label}
                  </span>
                </div>

                {/* Meta row */}
                <div className="flex flex-wrap gap-3 mb-3 text-[10px] text-slate-500">
                  <span>📋 变更 {r.changeItemCount}</span>
                  <span>💾 备份 {r.backupCount}</span>
                  <span>✅ 验证 {r.verifiedCount}/{r.totalChecks}</span>
                  <span className="ml-auto">{date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                </div>

                {/* Progress bar */}
                {r.totalChecks > 0 && (
                  <div className="w-full bg-slate-800/50 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full transition-all"
                      style={{ width: `${(r.verifiedCount / r.totalChecks) * 100}%`, background: cfg.color }}
                    />
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* API hint */}
      <div className="mt-8 bg-[#101622] border border-[#253247] rounded-xl p-4">
        <h3 className="text-xs font-semibold text-slate-400 mb-2">🔗 API 操作</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[10px] text-slate-500 font-mono">
          <div>GET /api/releases — 查询发布列表</div>
          <div>POST /api/releases — 创建发布</div>
          <div>GET /api/releases/[id] — 发布详情</div>
          <div>PATCH /api/releases/[id] — 更新状态</div>
        </div>
      </div>
    </div>
  )
}
