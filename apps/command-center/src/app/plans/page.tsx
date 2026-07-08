import pg from 'pg'

const pool = new pg.Pool({
  host: '127.0.0.1',
  port: 5432,
  database: 'seo_db',
  user: 'seo_user',
  password: 'changeme_in_production',
})

interface Plan {
  id: string
  title: string
  description: string | null
  period: string
  year_val: number | null
  month_val: number | null
  day_val: number | null
  status: string
  priority: string
  created_at: string
  keywords: { id: string; term: string; esTerm: string; category: string }[]
}

interface Keyword {
  id: string
  term: string
  esTerm: string
  category: string
  searchVolume: number
  difficulty: number
  cpc: number
  priority: string
  complianceRisk: string
}

async function getPlans(): Promise<Plan[]> {
  const { rows } = await pool.query(`
    SELECT p.*, COALESCE(json_agg(json_build_object(
      'id', k.id, 'term', k.term, 'esTerm', k.es_term, 'category', k.category
    )) FILTER (WHERE k.id IS NOT NULL), '[]') as keywords
    FROM seo_plan p
    LEFT JOIN seo_plan_keyword pk ON p.id = pk.plan_id
    LEFT JOIN seo_keyword k ON pk.keyword_id = k.id
    GROUP BY p.id
    ORDER BY p.year_val DESC NULLS LAST, p.month_val DESC NULLS LAST, p.day_val DESC NULLS LAST
  `)
  return rows
}

async function getKeywords(): Promise<Keyword[]> {
  const { rows } = await pool.query(`
    SELECT id, term, es_term as "esTerm", category, search_volume as "searchVolume",
           difficulty, cpc, priority, compliance_risk as "complianceRisk"
    FROM seo_keyword ORDER BY priority, category
  `)
  return rows
}

const STATUS_COLORS: Record<string, string> = {
  draft: '#64748b',
  active: '#22d3ee',
  completed: '#34d399',
  paused: '#fbbf24',
}

const CATEGORY_LABELS: Record<string, string> = {
  branded: '🏷️ 品牌词',
  informational: '📖 教程词',
  transactional: '💰 转化词',
  navigational: '❓ 问题词',
}

const PRIORITY_COLORS: Record<string, string> = {
  P0: '#f87171',
  P1: '#fb923c',
  P2: '#fbbf24',
  P3: '#64748b',
}

const COMPLIANCE_COLORS: Record<string, { color: string; bg: string }> = {
  low: { color: '#34d399', bg: 'rgba(52,211,153,0.12)' },
  medium: { color: '#fbbf24', bg: 'rgba(251,191,36,0.12)' },
  high: { color: '#fb7185', bg: 'rgba(251,113,133,0.12)' },
}

export default async function PlansPage() {
  const [plans, keywords] = await Promise.all([getPlans(), getKeywords()])

  // Group plans by year → month → day
  const yearGroups = new Map<number, Map<number, Plan[]>>()
  for (const p of plans) {
    const y = p.year_val ?? 2026
    const m = p.month_val ?? 0
    if (!yearGroups.has(y)) yearGroups.set(y, new Map())
    const monthMap = yearGroups.get(y)!
    if (!monthMap.has(m)) monthMap.set(m, [])
    monthMap.get(m)!.push(p)
  }

  // Group keywords by category
  const kwGroups = new Map<string, Keyword[]>()
  for (const kw of keywords) {
    if (!kwGroups.has(kw.category)) kwGroups.set(kw.category, [])
    kwGroups.get(kw.category)!.push(kw)
  }

  return (
    <div className="p-4 md:p-8 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-extrabold mb-2">
          <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
            计划中枢
          </span>
        </h1>
        <p className="text-slate-400 text-sm">SEO 计划管理 · 年→月→日三级视图 · 关键词库</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 mb-8">
        {[
          { label: '总计划', value: plans.length, icon: '📋' },
          { label: '总关键词', value: keywords.length, icon: '🔑' },
          { label: 'P0 关键词', value: keywords.filter(k => k.priority === 'P0').length, icon: '🔴' },
          { label: '活跃计划', value: plans.filter(p => p.status === 'active').length, icon: '⚡' },
        ].map((s, i) => (
          <div key={i} className="bg-[#101622] border border-[#253247] rounded-2xl p-4 md:p-5">
            <div className="text-2xl mb-2">{s.icon}</div>
            <div className="text-3xl md:text-4xl font-extrabold text-cyan-400">{s.value}</div>
            <div className="text-xs text-slate-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <PlansClient
        yearGroups={yearGroups}
        kwGroups={kwGroups}
        allKeywords={keywords}
      />
    </div>
  )
}

function PlansClient({
  yearGroups,
  kwGroups,
  allKeywords,
}: {
  yearGroups: Map<number, Map<number, Plan[]>>
  kwGroups: Map<string, Keyword[]>
  allKeywords: Keyword[]
}) {
  return (
    <div>
      {/* Plans Section */}
      <div className="mb-10">
        <h2 className="text-lg font-bold text-slate-200 mb-4">📅 SEO 计划</h2>
        {yearGroups.size === 0 ? (
          <div className="bg-[#101622] border border-[#253247] rounded-xl p-8 text-center">
            <div className="text-slate-500 text-sm">暂无计划数据。通过 API POST /api/plans 创建计划。</div>
          </div>
        ) : (
          <div className="space-y-6">
            {Array.from(yearGroups.entries())
              .sort(([a], [b]) => b - a)
              .map(([year, months]) => (
                <div key={year}>
                  <div className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2">
                    <span>📅</span> {year} 年
                  </div>
                  <div className="space-y-3 ml-4">
                    {Array.from(months.entries())
                      .sort(([a], [b]) => b - a)
                      .map(([month, planItems]) => (
                        <div key={month}>
                          <div className="text-xs font-medium text-slate-400 mb-2">
                            {month > 0 ? `${month} 月` : '未指定月份'}
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 ml-4">
                            {planItems.map(p => (
                              <div key={p.id} className="bg-[#101622] border border-[#253247] rounded-xl p-4">
                                <div className="flex justify-between items-start mb-2">
                                  <span
                                    className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                                    style={{ color: PRIORITY_COLORS[p.priority] || '#64748b', background: (PRIORITY_COLORS[p.priority] || '#64748b') + '18', border: '1px solid ' + (PRIORITY_COLORS[p.priority] || '#64748b') + '33' }}
                                  >
                                    {p.priority}
                                  </span>
                                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ color: STATUS_COLORS[p.status] || '#64748b', background: (STATUS_COLORS[p.status] || '#64748b') + '18' }}>
                                    {p.status}
                                  </span>
                                </div>
                                <h3 className="text-sm font-semibold text-slate-100 mb-1">{p.title}</h3>
                                {p.description && <p className="text-xs text-slate-400 mb-2">{p.description}</p>}
                                <div className="text-[10px] text-slate-500">
                                  {p.period} · {p.day_val ? `Day ${p.day_val}` : '—'}
                                </div>
                                {p.keywords && p.keywords.length > 0 && (
                                  <div className="mt-2 flex flex-wrap gap-1">
                                    {p.keywords.map((kw: { id: string; term: string }) => (
                                      <span key={kw.id} className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-800/50 text-slate-400 border border-slate-700/50">{kw.term}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* Keywords Section */}
      <div>
        <h2 className="text-lg font-bold text-slate-200 mb-4">🔑 关键词库</h2>
        <div className="space-y-6">
          {Array.from(kwGroups.entries()).map(([cat, kws]) => (
            <div key={cat}>
              <div className="text-sm font-semibold text-cyan-400 mb-3">{CATEGORY_LABELS[cat] || cat}</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#253247]">
                      <th className="text-left py-2 px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">关键词</th>
                      <th className="text-left py-2 px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">西语</th>
                      <th className="text-left py-2 px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">优先级</th>
                      <th className="text-left py-2 px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">难度</th>
                      <th className="text-left py-2 px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">搜索量</th>
                      <th className="text-left py-2 px-3 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">合规</th>
                    </tr>
                  </thead>
                  <tbody>
                    {kws.map(kw => {
                      const cc = COMPLIANCE_COLORS[kw.complianceRisk] || COMPLIANCE_COLORS.low
                      return (
                        <tr key={kw.id} className="border-b border-[#253247]/50 hover:bg-[#101622]/50">
                          <td className="py-2 px-3 font-medium text-slate-200">{kw.term}</td>
                          <td className="py-2 px-3 text-slate-400">{kw.esTerm}</td>
                          <td className="py-2 px-3">
                            <span className="font-bold" style={{ color: PRIORITY_COLORS[kw.priority] }}>{kw.priority}</span>
                          </td>
                          <td className="py-2 px-3 text-slate-400">{kw.difficulty}/100</td>
                          <td className="py-2 px-3 text-slate-400">{kw.searchVolume.toLocaleString()}</td>
                          <td className="py-2 px-3">
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ color: cc.color, background: cc.bg }}>
                              {kw.complianceRisk}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
