import { NextResponse } from 'next/server'
import { readFile } from 'fs/promises'

export async function GET() {
  try {
    const raw = await readFile('/opt/seo-system/data/task-ledger/all.json', 'utf-8')
    const tasks = JSON.parse(raw)
    return NextResponse.json(tasks)
  } catch (err) {
    console.error('Failed to read task ledger:', err)
    return NextResponse.json([], { status: 200 })
  }
}
