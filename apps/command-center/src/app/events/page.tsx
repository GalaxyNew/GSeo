import pg from 'pg'

const pool = new pg.Pool({
  host: '127.0.0.1',
  port: 5432,
  database: 'seo_db',
  user: 'seo_user',
  password: 'changeme_in_production',
})

interface Event {
  id: string
  ts: string
  actor: string
  action: string
  taskId: string | null
  input: string | null
  output: string | null
  evidence: string | null
  createdAt: string
}

async function getEvents(): Promise<Event[]> {
  const { rows } = await pool.query(`
    SELECT id, ts, actor, action, task_id as "taskId", input, output, evidence, created_at as "createdAt"
    FROM seo_event ORDER BY ts DESC LIMIT 100
  `)
  return rows
}

const ACTION_LABELS: Record<string, string> = {
  sync: '🔄 同步',
  analyze: '📊 分析',
  propose: '💡 提案',
  approve: '✅ 审批',
  execute: '⚡ 执行',
  alert: '🚨 告警',
  rollback: '⏪ 回滚',
  note: '📝 备注',
}

const ACTION_COLORS: Record<string, string> = {
  sync: '#22d3ee',
  analyze: '#a78bfa',
  propose: '#fbbf24',
  approve: '#34d399',
  execute: '#22d3ee',
  alert: '#fb7185',
  rollback: '#f97316',
  note: '#94a3b8',
}

export default async function EventsPage() {
  const events = await getEvents()

  const stats = {
    total: events.length,
    today: events.filter((e: Event) => {
      const d = new Date(e.ts)
      const now = new Date()
      return d.toDateString() === now.toDateString()
    }).length,
    actors: new Set(events.map((e: Event) => e.actor)).size,
  }

  return (
    <div className="p-4 md:p-8 max-w-[1600px] mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-extrabold mb-2">
          <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
            事件账本
          </span>
        </h1>
        <p className="text-slate-400 text-sm">Agent 操作记录 · EV-ID 统一标识 · 时间线视图</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4 mb-8">
        {[
          { label: '总事件', value: stats.total, icon: '📋' },
          { label: '今日事件', value: stats.today, icon: '📅' },
          { label: '参与 Agent', value: stats.actors, icon: '🤖' },
        ].map((s, i) => (
          <div key={i} className="bg-[#101622] border border-[#253247] rounded-2xl p-4 md:p-5">
            <div className="text-2xl mb-2">{s.icon}</div>
            <div className="text-3xl md:text-4xl font-extrabold text-cyan-400">{s.value}</div>
            <div className="text-xs text-slate-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        <h2 className="text-sm font-semibold text-slate-200 mr-2">动作筛选：</h2>
        {Object.entries(ACTION_LABELS).map(([key, label]) => (
          <span key={key} className="text-[10px] font-semibold px-2 py-0.5 rounded-full border" style={{ color: ACTION_COLORS[key], background: ACTION_COLORS[key] + '18', borderColor: ACTION_COLORS[key] + '33' }}>
            {label}
          </span>
        ))}
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        {events.length === 0 ? (
          <div className="bg-[#101622] border border-[#253247] rounded-xl p-8 text-center text-slate-500 text-sm">
            暂无事件记录。通过 API POST /api/events 写入事件。
          </div>
        ) : (
          events.map((e: Event) => {
            const ts = new Date(e.ts)
            const color = ACTION_COLORS[e.action] || '#64748b'
            const label = ACTION_LABELS[e.action] || e.action
            return (
              <div key={e.id} className="bg-[#101622] border border-[#253247] rounded-xl p-4 hover:border-cyan-800/50 transition-colors">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span className="text-[10px] font-mono text-slate-500">{e.id}</span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ color, background: color + '18', border: '1px solid ' + color + '33' }}>
                    {label}
                  </span>
                  <span className="text-[10px] text-slate-400">👤 {e.actor}</span>
                  {e.taskId && <span className="text-[10px] text-slate-500">📎 {e.taskId}</span>}
                  <span className="text-[10px] text-slate-600 ml-auto">{ts.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                {e.input && (
                  <p className="text-sm text-slate-200 mb-1">{e.input}</p>
                )}
                {e.output && (
                  <p className="text-xs text-slate-400 mb-1 italic">{e.output}</p>
                )}
                {e.evidence && (
                  <div className="mt-1 text-[10px] text-slate-500 bg-slate-800/50 rounded p-1.5 font-mono break-all">{e.evidence}</div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
