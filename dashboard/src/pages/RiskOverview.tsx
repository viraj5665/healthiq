import { useEffect, useState, useMemo } from 'react'
import { fetchRiskScores, RISK_ORDER } from '../lib/api'
import type { RiskScore, RiskLevel, SortField, SortDir } from '../types'
import { StatCard } from '../components/StatCard'
import { RiskLevelBadge } from '../components/RiskLevelBadge'
import { ScoreBar } from '../components/ScoreBar'
import { ShapBar } from '../components/ShapBar'

const LEVELS: { key: RiskLevel; label: string; color: string }[] = [
  { key: 'all',      label: 'All Patients', color: '#8FA3C8' },
  { key: 'critical', label: 'Critical',     color: '#F0997B' },
  { key: 'high',     label: 'High',         color: '#F0875C' },
  { key: 'moderate', label: 'Moderate',     color: '#F5C97A' },
  { key: 'low',      label: 'Low',          color: '#5DCAA5' },
]

const COLS: { key: SortField; label: string }[] = [
  { key: 'score',      label: 'Risk Score' },
  { key: 'risk_level', label: 'Risk Level' },
  { key: 'age',        label: 'Age' },
]

export default function RiskOverview() {
  const [data, setData]           = useState<RiskScore[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [filter, setFilter]       = useState<RiskLevel>('all')
  const [sortField, setSortField] = useState<SortField>('score')
  const [sortDir, setSortDir]     = useState<SortDir>('desc')
  const [expanded, setExpanded]   = useState<Set<string>>(new Set())
  const [search, setSearch]       = useState('')

  useEffect(() => {
    fetchRiskScores()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const counts = useMemo(() => ({
    all:      data.length,
    critical: data.filter(d => d.risk_level === 'critical').length,
    high:     data.filter(d => d.risk_level === 'high').length,
    moderate: data.filter(d => d.risk_level === 'moderate').length,
    low:      data.filter(d => d.risk_level === 'low').length,
  }), [data])

  const filtered = useMemo(() => {
    let rows = filter === 'all' ? data : data.filter(d => d.risk_level === filter)
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      rows = rows.filter(d => d.patient_id.toLowerCase().includes(q))
    }
    rows = [...rows].sort((a, b) => {
      let diff = 0
      if (sortField === 'score')      diff = a.score - b.score
      if (sortField === 'risk_level') diff = (RISK_ORDER[a.risk_level] ?? 0) - (RISK_ORDER[b.risk_level] ?? 0)
      if (sortField === 'age')        diff = (a.features?.age ?? 0) - (b.features?.age ?? 0)
      return sortDir === 'desc' ? -diff : diff
    })
    return rows
  }, [data, filter, search, sortField, sortDir])

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  function toggleExpand(id: string) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const topFeature = (row: RiskScore) => {
    if (!row.explanation?.length) return '—'
    const top = [...row.explanation].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))[0]
    return top?.feature ?? '—'
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, gap: 10 }}>
      <div style={{
        width: 18, height: 18, borderRadius: '50%',
        border: '2px solid #1D2940',
        borderTopColor: '#5DCAA5',
        animation: 'spin 0.8s linear infinite',
      }} />
      <span style={{ color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>
        Loading patient data...
      </span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )

  if (error) return (
    <div style={{ padding: 32, color: '#F0997B', fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>
      Error: {error}
    </div>
  )

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1400, margin: '0 auto' }}>

      {/* Page header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 18, fontWeight: 600, color: '#E2EAF8', marginBottom: 4 }}>
          Patient Risk Overview
        </div>
        <div style={{ fontSize: 12, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
          LACE readmission risk · {data.length} patients · XGBoost v1.0
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' }}>
        {LEVELS.map(({ key, label, color }) => (
          <StatCard
            key={key}
            label={label}
            value={counts[key]}
            color={color}
            pct={key !== 'all' ? (counts[key] / counts.all) * 100 : undefined}
            active={filter === key}
            onClick={() => setFilter(key)}
          />
        ))}
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Search patient ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            background: '#121929',
            border: '1px solid #1D2940',
            borderRadius: 6,
            padding: '7px 12px',
            color: '#E2EAF8',
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            width: 240,
            outline: 'none',
          }}
        />
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: '#5C6B8A' }}>Sort:</span>
          {COLS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => toggleSort(key)}
              style={{
                background: sortField === key ? 'rgba(93,202,165,0.1)' : '#121929',
                border: `1px solid ${sortField === key ? '#5DCAA5' : '#1D2940'}`,
                borderRadius: 5,
                padding: '5px 10px',
                color: sortField === key ? '#5DCAA5' : '#5C6B8A',
                fontSize: 11,
                cursor: 'pointer',
                fontFamily: "'JetBrains Mono', monospace",
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              {label}
              {sortField === key && (
                <span style={{ fontSize: 9 }}>{sortDir === 'desc' ? '↓' : '↑'}</span>
              )}
            </button>
          ))}
        </div>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#3A4B6A', fontFamily: "'JetBrains Mono', monospace" }}>
          {filtered.length} rows
        </span>
      </div>

      {/* Table */}
      <div style={{
        background: '#121929',
        border: '1px solid #1D2940',
        borderRadius: 8,
        overflow: 'hidden',
      }}>
        {/* Table header */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 60px 180px 110px 1fr 28px',
          padding: '10px 20px',
          borderBottom: '1px solid #1D2940',
          fontSize: 10,
          color: '#3A4B6A',
          letterSpacing: '0.08em',
          fontWeight: 600,
          textTransform: 'uppercase',
        }}>
          <span>Patient ID</span>
          <span>Age</span>
          <span>Risk Score</span>
          <span>Level</span>
          <span>Top Driver</span>
          <span />
        </div>

        {/* Rows */}
        {filtered.length === 0 && (
          <div style={{ padding: '32px 20px', textAlign: 'center', color: '#3A4B6A', fontSize: 13 }}>
            No patients match the current filter.
          </div>
        )}

        {filtered.map((row, i) => {
          const isExpanded = expanded.has(row.id)
          const age = row.features?.age != null ? Math.round(row.features.age) : '—'
          const explanation = row.explanation ?? []
          const sorted3 = [...explanation]
            .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
            .slice(0, 3)

          return (
            <div
              key={row.id}
              style={{
                borderBottom: i < filtered.length - 1 ? '1px solid #151E30' : 'none',
              }}
            >
              {/* Main row */}
              <div
                onClick={() => toggleExpand(row.id)}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '2fr 60px 180px 110px 1fr 28px',
                  padding: '12px 20px',
                  alignItems: 'center',
                  cursor: 'pointer',
                  transition: 'background 0.1s',
                  background: isExpanded ? '#172035' : 'transparent',
                }}
                onMouseEnter={e => { if (!isExpanded) (e.currentTarget as HTMLElement).style.background = 'rgba(23,32,53,0.6)' }}
                onMouseLeave={e => { if (!isExpanded) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
              >
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  color: '#8FA3C8',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  paddingRight: 12,
                }}>
                  {row.patient_id}
                </span>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12,
                  color: '#E2EAF8',
                }}>
                  {age}
                </span>
                <div style={{ paddingRight: 16 }}>
                  <ScoreBar score={row.score} level={row.risk_level} />
                </div>
                <div>
                  <RiskLevelBadge level={row.risk_level} />
                </div>
                <span style={{
                  fontSize: 11,
                  color: '#5C6B8A',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  paddingRight: 8,
                }}>
                  {topFeature(row)}
                </span>
                <span style={{
                  fontSize: 12,
                  color: '#3A4B6A',
                  transform: isExpanded ? 'rotate(90deg)' : 'none',
                  transition: 'transform 0.15s',
                  display: 'inline-block',
                  textAlign: 'center',
                }}>
                  ›
                </span>
              </div>

              {/* Expanded SHAP panel */}
              {isExpanded && sorted3.length > 0 && (
                <div style={{
                  padding: '16px 24px 20px 24px',
                  background: '#0F1725',
                  borderTop: '1px solid #151E30',
                }}>
                  <div style={{
                    fontSize: 10,
                    color: '#3A4B6A',
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    marginBottom: 14,
                    fontFamily: "'JetBrains Mono', monospace",
                  }}>
                    SHAP Feature Contributions (top 3)
                  </div>
                  <ShapBar features={sorted3} />
                  <div style={{ marginTop: 14, fontSize: 10, color: '#3A4B6A', fontFamily: "'JetBrains Mono', monospace" }}>
                    Computed at {new Date(row.computed_at).toLocaleString()} · Model {row.model_version}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
