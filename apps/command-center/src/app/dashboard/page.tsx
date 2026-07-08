import { readFile } from 'fs/promises'

interface Task {
  id: string
  title: string
  status: string
  priority: string
  owner: string
  deadline: string
  created: string
  tags: string[]
}

interface GitHubMilestone {
  title: string
  state: string
  openIssues: number
  closedIssues: number
  progress: number
}

interface GitHubIssue {
  number: number
  title: string
  state: string
  labels: string[]
  updated_at: string
}

interface OverviewData {
  github: {
    milestones: GitHubMilestone[]
    recentIssues: GitHubIssue[]
    latestRelease: { tag: string; name: string; date: string } | null
  } | null
  local: {
    plans: number
    keywords: number
    events: number
  }
  timestamp: string
  cached?: boolean
}

async function getTasks(): Promise<Task[]> {
  try {
    const raw = await readFile('/opt/seo-system/data/task-ledger/all.json', 'utf-8')
    return JSON.parse(raw)
  } catch {
    return []
  }
}

async function getOverview(): Promise<OverviewData> {
  try {
    const res = await fetch('http://127.0.0.1:3000/api/overview', { cache: 'no-store' })
    if (!res.ok) throw new Error('overview fetch failed')
    return await res.json()
  } catch {
    return { github: null, local: { plans: 0, keywords: 0, events: 0 }, timestamp: new Date().toISOString() }
  }
}

const STATUS_CONFIG: Record<string, { label: string; color: string; border: string }> = {
  PENDING:     { label: '待处理', color: '#64748b', border: 'rgba(100,116,139,0.25)' },
  ASSIGNED:    { label: '已分配', color: '#94a3b8', border: 'rgba(148,163,184,0.25)' },
  IN_PROGRESS: { label: '进行中', color: '#22d3ee', border: 'rgba(34,211,238,0.25)' },
  REVIEW:      { label: '待审核', color: '#a78bfa', border: 'rgba(167,139,250,0.25)' },
  PASSED:      { label: '已通过', color: '#34d399', border: 'rgba(52,211,153,0.25)' },
  BLOCKED:     { label: '已阻塞', color: '#fb7185', border: 'rgba(251,113,133,0.25)' },
  REJECTED:    { label: '已拒绝', color: '#f87171', border: 'rgba(248,113,113,0.25)' },
  PAUSED:      { label: '已暂停', color: '#fbbf24', border: 'rgba(251,191,36,0.25)' },
}

const PRIORITY_CONFIG: Record<string, { label: string; color: string }> = {
  P0: { label: 'P0', color: '#f87171' },
  P1: { label: 'P1', color: '#fb923c' },
  P2: { label: 'P2', color: '#fbbf24' },
  P3: { label: 'P3', color: '#64748b' },
}

const BOARD_COLUMNS = ['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'REVIEW', 'PASSED', 'BLOCKED'] as const

export default async function DashboardPage() {
  const [tasks, overview] = await Promise.all([getTasks(), getOverview()])

  const stats = {
    total: tasks.length,
    pending: tasks.filter((t: Task) => t.status === 'PENDING').length,
    inProgress: tasks.filter((t: Task) => t.status === 'IN_PROGRESS').length,
    passed: tasks.filter((t: Task) => t.status === 'PASSED').length,
    blocked: tasks.filter((t: Task) => t.status === 'BLOCKED').length,
  }

  const gh = overview.github

  return (
    <div className="p-4 md:p-8 max-w-[1600px] mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-extrabold mb-2">
          <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
            SEO 指挥中心
          </span>
        </h1>
        <p className="text-slate-400 text-sm">观测大屏 · GitHub 项目总览 · 数据来自 GSeo</p>
      </div>

      {/* GitHub Project Overview */}
      {gh && (
        <div className="mb-8">
          <h2 className="text-lg font-bold text-slate-200 mb-4">🐙 GitHub 项目总览</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Milestones */}
            <div className="bg-[#101622] border border-[#253247] rounded-xl p-5">
              <h3 className="text-sm font-semibold text-purple-400 mb-4">里程碑进度</h3>
              <div className="space-y-3">
                {gh.milestones.map((m: GitHubMilestone) => (
                  <div key={m.title}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs text-slate-200">{m.title}</span>
                      <span className="text-[10px] text-slate-400">{m.progress}%</span>
                    </div>
                    <div className="w-full bg-slate-800/50 rounded-full h-2">
                      <div
                        className="h-2 rounded-full transition-all"
                        style={{
                          width: `${m.progress}%`,
                          background: m.state === 'closed'
                            ? 'linear-gradient(90deg, #34d399, #22d3ee)'
                            : 'linear-gradient(90deg, #22d3ee, #a78bfa)',
                        }}
                      />
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{m.closedIssues} done · {m.openIssues} open</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Issues + Local Stats */}
            <div className="space-y-4">
              {/* Local module stats */}
              <div className="bg-[#101622] border border-[#253247] rounded-xl p-5">
                <h3 className="text-sm font-semibold text-cyan-400 mb-3">📊 模块统计</h3>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: '计划', value: overview.local.plans, icon: '📅' },
                    { label: '关键词', value: overview.local.keywords, icon: '🔑' },
                    { label: '事件', value: overview.local.events, icon: '📋' },
                  ].map((s, i) => (
                    <div key={i} className="text-center">
                      <div className="text-xl mb-1">{s.icon}</div>
                      <div className="text-2xl font-extrabold text-cyan-400">{s.value}</div>
                      <div className="text-[10px] text-slate-400">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent issues */}
              <div className="bg-[#101622] border border-[#253247] rounded-xl p-5">
                <h3 className="text-sm font-semibold text-purple-400 mb-3">最近 Issues</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {gh.recentIssues.slice(0, 6).map((i: GitHubIssue) => (
                    <div key={i.number} className="flex items-center gap-2 text-xs">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${i.state === 'open' ? 'bg-green-400' : 'bg-slate-500'}`} />
                      <span className="text-slate-500 font-mono">#{i.number}</span>
                      <span className="text-slate-200 truncate flex-1">{i.title}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-4 mb-8">
        {[
          { label: '总任务', value: stats.total, icon: '📦' },
          { label: '待处理', value: stats.pending, icon: '⏳' },
          { label: '进行中', value: stats.inProgress, icon: '⚡' },
          { label: '已通过', value: stats.passed, icon: '✅' },
          { label: '已阻塞', value: stats.blocked, icon: '🚫' },
        ].map((s, i) => (
          <div key={i} className="bg-[#101622] border border-[#253247] rounded-2xl p-4 md:p-5">
            <div className="text-2xl mb-2">{s.icon}</div>
            <div className="text-3xl md:text-4xl font-extrabold text-cyan-400">{s.value}</div>
            <div className="text-xs text-slate-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {BOARD_COLUMNS.map((col) => {
          const sc = STATUS_CONFIG[col]
          const colTasks = tasks.filter((t: Task) => t.status === col)
          return (
            <div key={col}>
              <div className="flex items-center gap-2 mb-3 pb-2 border-b-2" style={{ borderColor: sc.border }}>
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: sc.color }} />
                <span className="text-sm font-semibold whitespace-nowrap" style={{ color: sc.color }}>{sc.label}</span>
                <span className="text-xs text-slate-500 ml-auto">{colTasks.length}</span>
              </div>
              {colTasks.map((t: Task) => (
                <div key={t.id} className="bg-[#101622] border border-[#253247] rounded-xl p-3 mb-3 hover:border-cyan-800/50 transition-colors">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ color: (PRIORITY_CONFIG[t.priority] || PRIORITY_CONFIG.P3).color, background: (PRIORITY_CONFIG[t.priority] || PRIORITY_CONFIG.P3).color + '18', border: '1px solid ' + (PRIORITY_CONFIG[t.priority] || PRIORITY_CONFIG.P3).color + '33' }}>
                      {(PRIORITY_CONFIG[t.priority] || PRIORITY_CONFIG.P3).label}
                    </span>
                    <span className="text-[10px] text-slate-500">{t.id}</span>
                  </div>
                  <h3 className="text-sm font-semibold text-slate-100 leading-snug mb-2">{t.title}</h3>
                  <div className="flex flex-wrap gap-1.5 items-center mb-2">
                    <span className="text-xs text-slate-400">👤 {t.owner}</span>
                    {t.deadline && <span className="text-xs text-slate-500">📅 {t.deadline}</span>}
                  </div>
                  {t.tags && t.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {t.tags.slice(0, 4).map((tag: string) => (
                        <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800/50 text-slate-400 border border-slate-700/50">{tag}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {colTasks.length === 0 && <div className="text-center text-slate-600 text-xs py-8">暂无</div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
