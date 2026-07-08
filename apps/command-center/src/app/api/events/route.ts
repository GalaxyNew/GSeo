import { NextResponse } from 'next/server'
import pg from 'pg'

const pool = new pg.Pool({
  host: '127.0.0.1',
  port: 5432,
  database: 'seo_db',
  user: 'seo_user',
  password: process.env.DB_PASSWORD || 'changeme_in_production',
})

export async function GET(request: Request) {
  try {
    const url = new URL(request.url)
    const actor = url.searchParams.get('actor') || ''
    const action = url.searchParams.get('action') || ''
    const taskId = url.searchParams.get('taskId') || ''
    const limit = Math.min(parseInt(url.searchParams.get('limit') || '50'), 200)
    const offset = parseInt(url.searchParams.get('offset') || '0')

    let sql = `SELECT id, ts, actor, action, task_id as "taskId", input, output, evidence, created_at as "createdAt"
               FROM seo_event WHERE 1=1`
    const params: string[] = []
    let idx = 1

    if (actor) { sql += ` AND actor = $${idx++}`; params.push(actor) }
    if (action) { sql += ` AND action = $${idx++}`; params.push(action) }
    if (taskId) { sql += ` AND task_id = $${idx++}`; params.push(taskId) }

    sql += ` ORDER BY ts DESC LIMIT $${idx++} OFFSET $${idx++}`
    params.push(limit.toString(), offset.toString())

    const { rows } = await pool.query(sql, params)
    return NextResponse.json(rows)
  } catch (err) {
    console.error('Events GET error:', err)
    return NextResponse.json({ error: 'Failed to fetch events' }, { status: 500 })
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { actor, action, taskId, input, output, evidence } = body

    if (!actor || !action) {
      return NextResponse.json({ error: 'actor and action are required' }, { status: 400 })
    }

    const { rows } = await pool.query(
      `INSERT INTO seo_event (id, actor, action, task_id, input, output, evidence)
       VALUES (next_ev_id(), $1, $2, $3, $4, $5, $6) RETURNING *`,
      [actor, action, taskId || null, input || null, output || null, evidence || null]
    )
    return NextResponse.json(rows[0], { status: 201 })
  } catch (err) {
    console.error('Events POST error:', err)
    return NextResponse.json({ error: 'Failed to create event' }, { status: 500 })
  }
}
