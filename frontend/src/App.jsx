import { useEffect, useState } from 'react'

// Plain-English meaning of each reason, shown when you hover over it.
const REASON_HELP = {
  MISSING_IN_B: 'System A has this record but System B has no entry for it',
  ORPHAN_IN_B: 'System B has an entry for a record that System A does not have',
  DUPLICATE_IN_B: 'System B has several entries that do not add up to the A total',
  VALUE_MISMATCH: 'The amounts differ (or B left the amount blank)',
  LOCATION_MISMATCH: 'A and B put this record at different locations',
  DATE_MISMATCH: 'A and B give different dates',
  VOIDED_IN_A: 'System A says this record is voided, but B still has an entry',
}

async function getJson(url) {
  const res = await fetch(url)
  const body = await res.json()
  if (!res.ok) throw new Error(body.error || `Request failed (${res.status})`)
  return body
}

// An empty cell for "no value" (never 0, never the word null).
function Money({ value, hidden }) {
  if (hidden) return <span className="note">hidden (other org)</span>
  return value === null ? '' : value
}

export default function App() {
  const [orgs, setOrgs] = useState([])
  const [reasons, setReasons] = useState([])
  const [org, setOrg] = useState('')
  const [reason, setReason] = useState('')
  const [sort, setSort] = useState('') // e.g. "a_value" (smallest first) or "-a_value" (biggest first)
  const [rows, setRows] = useState(null) // null = still loading the first answer
  const [error, setError] = useState('')

  // Once, when the page opens: load the list of orgs and reasons for the dropdowns.
  useEffect(() => {
    Promise.all([getJson('/api/orgs/'), getJson('/api/reasons/')])
      .then(([o, r]) => {
        setOrgs(o)
        setReasons(r)
        setOrg(o[0] || '')
      })
      .catch((e) => setError(e.message))
  }, [])

  // Every time the org, the reason filter or the sort changes: ask the API again.
  useEffect(() => {
    if (!org) return
    const params = new URLSearchParams({ org })
    if (reason) params.set('reason', reason)
    if (sort) params.set('sort', sort)
    let stale = false // ignore an old answer that arrives after a newer request
    getJson(`/api/disagreements/?${params}`)
      .then((data) => { if (!stale) { setRows(data); setError('') } })
      .catch((e) => { if (!stale) { setRows([]); setError(e.message) } })
    return () => { stale = true }
  }, [org, reason, sort])

  // Click a header: first click = smallest first, second = biggest first, third = no sorting.
  function clickHeader(column) {
    if (sort === column) setSort('-' + column)
    else if (sort === '-' + column) setSort('')
    else setSort(column)
  }

  function arrow(column) {
    if (sort === column) return ' ▲'
    if (sort === '-' + column) return ' ▼'
    return ''
  }

  // A clickable column heading.
  function sortHeader(column, label) {
    return (
      <th className="sortable num" onClick={() => clickHeader(column)}>
        {label}{arrow(column)}
      </th>
    )
  }

  return (
    <div>
      <h1>DealerOS: where System A and System B disagree</h1>

      <div className="controls">
        <label>
          Org:{' '}
          <select value={org} onChange={(e) => setOrg(e.target.value)}>
            {orgs.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>
        <label>
          Reason:{' '}
          <select value={reason} onChange={(e) => setReason(e.target.value)}>
            <option value="">All reasons</option>
            {reasons.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <span className="note">Click a value heading to sort.</span>
      </div>

      {error && <p className="error">{error}</p>}

      <table>
        <thead>
          <tr>
            <th>Reason</th>
            <th>Record ID</th>
            <th>Location</th>
            {sortHeader('a_value', 'System A value')}
            {sortHeader('b_value', 'System B value')}
            {sortHeader('difference', 'Difference')}
          </tr>
        </thead>
        <tbody>
          {(rows || []).map((r, i) => (
            <tr key={`${r.reason}-${r.record_id}-${i}`}>
              <td title={REASON_HELP[r.reason]}>{r.reason}</td>
              <td>{r.record_id}</td>
              <td>{r.location}</td>
              <td className="num"><Money value={r.a_value} /></td>
              <td className="num"><Money value={r.b_value} hidden={r.b_hidden} /></td>
              <td className="num"><Money value={r.difference} /></td>
            </tr>
          ))}
        </tbody>
      </table>

      {rows !== null && !error && rows.length === 0 && <p className="note">No disagreements to show.</p>}
    </div>
  )
}