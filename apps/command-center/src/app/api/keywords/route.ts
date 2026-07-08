import { NextResponse } from 'next/server'
import pg from 'pg'

const pool = new pg.Pool({
  host: '127.0.0.1',
  port: 5432,
  database: 'seo_db',
  user: 'seo_user',
  password: process.env.DB_PASSWORD || 'changeme_in_production',
})

export async function GET() {
  try {
    const { rows } = await pool.query(`
      SELECT id, term, es_term as "esTerm", category, search_volume as "searchVolume",
             difficulty, cpc, priority, active, compliance_risk as "complianceRisk",
             created_at as "createdAt"
      FROM seo_keyword ORDER BY priority, category
    `)
    return NextResponse.json(rows)
  } catch (err) {
    console.error('Keywords API error:', err)
    return NextResponse.json({ error: 'Failed to fetch keywords' }, { status: 500 })
  }
}
