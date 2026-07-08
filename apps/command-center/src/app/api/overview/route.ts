import { NextResponse } from 'next/server'
import pg from 'pg'

const pool = new pg.Pool({
  host: '127.0.0.1',
  port: 5432,
  database: 'seo_db',
  user: 'seo_user',
  password: 'changeme_in_production',
})

// GitHub API cache
let ghCache: { data: any; ts: number } | null = null
const CACHE_TTL = 60_000 // 60s

async function fetchGitHub() {
  const token = process.env.GITHUB_PAT
  if (!token) return null

  const [milestonesRes, issuesRes, releasesRes] = await Promise.all([
    fetch('https://api.github.com/repos/GalaxyNew/GSeo/milestones?state=all&per_page=10', {
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github.v3+json' },
    }),
    fetch('https://api.github.com/repos/GalaxyNew/GSeo/issues?state=all&per_page=10&sort=updated&direction=desc', {
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github.v3+json' },
    }),
    fetch('https://api.github.com/repos/GalaxyNew/GSeo/releases?per_page=5', {
      headers: { Authorization: `Bearer ${token}`, Accept: 'application/vnd.github.v3+json' },
    }),
  ])

  const milestones = await milestonesRes.json()
  const issues = await issuesRes.json()
  const releases = await releasesRes.json()

  return { milestones, issues, releases }
}

async function getLocalStats() {
  const [plans, keywords, events] = await Promise.all([
    pool.query('SELECT COUNT(*) as cnt FROM seo_plan'),
    pool.query('SELECT COUNT(*) as cnt FROM seo_keyword'),
    pool.query('SELECT COUNT(*) as cnt FROM seo_event'),
  ])
  return {
    plans: parseInt(plans.rows[0].cnt),
    keywords: parseInt(keywords.rows[0].cnt),
    events: parseInt(events.rows[0].cnt),
  }
}

export async function GET() {
  try {
    const now = Date.now()
    if (ghCache && now - ghCache.ts < CACHE_TTL) {
      return NextResponse.json({ ...ghCache.data, cached: true })
    }

    const [github, local] = await Promise.all([fetchGitHub(), getLocalStats()])

    const data = {
      github: github ? {
        milestones: github.milestones.map((m: any) => ({
          title: m.title,
          state: m.state,
          openIssues: m.open_issues,
          closedIssues: m.closed_issues,
          progress: m.open_issues + m.closed_issues > 0
            ? Math.round((m.closed_issues / (m.open_issues + m.closed_issues)) * 100)
            : 0,
        })),
        recentIssues: github.issues.slice(0, 8).map((i: any) => ({
          number: i.number,
          title: i.title,
          state: i.state,
          labels: (i.labels || []).map((l: any) => l.name),
          updated_at: i.updated_at,
        })),
        latestRelease: github.releases[0] ? {
          tag: github.releases[0].tag_name,
          name: github.releases[0].name,
          date: github.releases[0].published_at,
        } : null,
      } : null,
      local,
      timestamp: new Date().toISOString(),
    }

    ghCache = { data, ts: now }
    return NextResponse.json(data)
  } catch (err) {
    console.error('Overview API error:', err)
    return NextResponse.json({ error: 'Failed to fetch overview' }, { status: 500 })
  }
}
