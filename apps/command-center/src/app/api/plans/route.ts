import { NextResponse } from 'next/server'
import pg from 'pg'

const pool = new pg.Pool({
  host: '127.0.0.1',
  port: 5432,
  database: 'seo_db',
  user: 'seo_user',
  password: 'changeme_in_production',
})

export async function GET() {
  try {
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
    return NextResponse.json(rows)
  } catch (err) {
    console.error('Plans API error:', err)
    return NextResponse.json({ error: 'Failed to fetch plans' }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { title, description, period, year, month, day, status, priority } = body

    if (!title || !period) {
      return NextResponse.json({ error: 'title and period are required' }, { status: 400 })
    }

    const { rows } = await pool.query(
      `INSERT INTO seo_plan (title, description, period, year_val, month_val, day_val, status, priority)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *`,
      [title, description || null, period, year || null, month || null, day || null, status || 'draft', priority || 'P2']
    )
    return NextResponse.json(rows[0], { status: 201 })
  } catch (err) {
    console.error('Plan create error:', err)
    return NextResponse.json({ error: 'Failed to create plan' }, { status: 500 })
  }
}
