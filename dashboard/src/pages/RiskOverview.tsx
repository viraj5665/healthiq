import { useEffect, useState, useMemo, useRef, useCallback } from 'react'
import { fetchRiskScores, RISK_ORDER, createManualPatient } from '../lib/api'
import type { RiskScore, RiskLevel, SortField, SortDir, ManualPatientIn } from '../types'
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

const EMPTY_FORM: ManualPatientIn = {
  date_of_birth: '',
  gender: 'male',
  num_encounters: 0,
  num_er_visits: 0,
  conditions: '',
}

// ── Modal ──────────────────────────────────────────────────────────────────────

interface ModalProps {
  onClose: () => void
  onSuccess: (patientId: string) => void
}

function AddPatientModal({ onClose, onSuccess }: ModalProps) {
  const [form, setForm] = useState<ManualPatientIn>(EMPTY_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Ref guard: state updates are async, so use a ref to synchronously block
  // duplicate submissions before the disabled button re-renders.
  const inFlight = useRef(false)

  function set(k: keyof ManualPatientIn, v: string | number) {
    setForm(prev => ({ ...prev, [k]: v }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (inFlight.current) return
    if (!form.date_of_birth) { setError('Date of birth is required'); return }
    if (form.num_er_visits > form.num_encounters) {
      setError('ER visits cannot exceed total encounters'); return
    }
    setError(null)
    inFlight.current = true
    setSubmitting(true)
    try {
      const result = await createManualPatient(form)
      onSuccess(result.patient_id)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Submission failed')
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    background: '#0F1725',
    border: '1px solid #1D2940',
    borderRadius: 6,
    padding: '8px 12px',
    color: '#E2EAF8',
    fontSize: 13,
    width: '100%',
    outline: 'none',
    fontFamily: 'inherit',
  }
  const labelStyle: React.CSSProperties = {
    fontSize: 11,
    color: '#5C6B8A',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    display: 'block',
    marginBottom: 6,
  }

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(5, 8, 16, 0.75)',
          backdropFilter: 'blur(3px)',
          zIndex: 100,
        }}
      />
      {/* Panel */}
      <div style={{
        position: 'fixed',
        top: '50%', left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 101,
        width: '100%', maxWidth: 480,
        background: '#121929',
        border: '1px solid #1D2940',
        borderRadius: 10,
        boxShadow: '0 24px 48px rgba(0,0,0,0.6)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid #1D2940',
        }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600, color: '#E2EAF8' }}>Add patient</div>
            <div style={{ fontSize: 11, color: '#5C6B8A', marginTop: 2, fontFamily: "'JetBrains Mono', monospace" }}>
              XGBoost scores in ~2 seconds
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none',
              color: '#5C6B8A', fontSize: 18, cursor: 'pointer', lineHeight: 1, padding: 4,
            }}
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Row 1: DOB + Gender */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Date of Birth</label>
              <input
                type="date"
                value={form.date_of_birth}
                max={new Date().toISOString().slice(0, 10)}
                onChange={e => set('date_of_birth', e.target.value)}
                style={{ ...inputStyle, colorScheme: 'dark' }}
                required
              />
            </div>
            <div>
              <label style={labelStyle}>Gender</label>
              <select
                value={form.gender}
                onChange={e => set('gender', e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other / Unknown</option>
              </select>
            </div>
          </div>

          {/* Row 2: Encounters + ER visits */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Prior Encounters</label>
              <input
                type="number"
                min={0}
                max={500}
                value={form.num_encounters}
                onChange={e => set('num_encounters', Math.max(0, parseInt(e.target.value) || 0))}
                style={inputStyle}
              />
            </div>
            <div>
              <label style={labelStyle}>ER Visits (last 6 mo)</label>
              <input
                type="number"
                min={0}
                max={form.num_encounters}
                value={form.num_er_visits}
                onChange={e => set('num_er_visits', Math.max(0, parseInt(e.target.value) || 0))}
                style={inputStyle}
              />
            </div>
          </div>

          {/* Conditions */}
          <div>
            <label style={labelStyle}>Known Conditions (optional)</label>
            <textarea
              value={form.conditions}
              onChange={e => set('conditions', e.target.value)}
              placeholder="e.g. Type 2 diabetes, hypertension, COPD"
              rows={2}
              style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5 }}
            />
          </div>

          {/* Age preview */}
          {form.date_of_birth && (
            <div style={{
              background: 'rgba(93,202,165,0.06)', border: '1px solid rgba(93,202,165,0.15)',
              borderRadius: 6, padding: '8px 12px',
              fontSize: 12, color: '#5DCAA5',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              Age: {Math.floor((Date.now() - new Date(form.date_of_birth).getTime()) / 31557600000)} years
            </div>
          )}

          {/* Error */}
          {error && (
            <div style={{
              background: 'rgba(240,153,123,0.08)', border: '1px solid rgba(240,153,123,0.3)',
              borderRadius: 6, padding: '8px 12px',
              fontSize: 12, color: '#F0997B',
            }}>
              {error}
            </div>
          )}

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', paddingTop: 4 }}>
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              style={{
                background: 'none', border: '1px solid #1D2940',
                borderRadius: 6, padding: '8px 16px',
                color: '#5C6B8A', fontSize: 13, cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              style={{
                background: submitting ? '#1D2940' : 'rgba(93,202,165,0.12)',
                border: '1px solid #5DCAA5',
                borderRadius: 6, padding: '8px 20px',
                color: submitting ? '#5C6B8A' : '#5DCAA5',
                fontSize: 13, cursor: submitting ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', gap: 8,
                fontWeight: 500,
              }}
            >
              {submitting ? (
                <>
                  <span style={{
                    display: 'inline-block', width: 12, height: 12, borderRadius: '50%',
                    border: '1.5px solid #3A4B6A', borderTopColor: '#5DCAA5',
                    animation: 'spin 0.8s linear infinite',
                  }} />
                  Scoring patient…
                </>
              ) : 'Add & score →'}
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </button>
          </div>
        </form>
      </div>
    </>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function RiskOverview() {
  const [data, setData]           = useState<RiskScore[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [filter, setFilter]       = useState<RiskLevel>('all')
  const [sortField, setSortField] = useState<SortField>('score')
  const [sortDir, setSortDir]     = useState<SortDir>('desc')
  const [expanded, setExpanded]   = useState<Set<string>>(new Set())
  const [search, setSearch]       = useState('')
  const [showModal, setShowModal] = useState(false)
  const [highlightId, setHighlightId] = useState<string | null>(null)

  const rowRefs = useRef<Map<string, HTMLDivElement>>(new Map())

  const loadData = useCallback(async () => {
    const scores = await fetchRiskScores(700)
    setData(scores)
  }, [])

  useEffect(() => {
    loadData()
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [loadData])

  // Scroll + brief highlight after new patient appears in table
  useEffect(() => {
    if (!highlightId) return
    const el = rowRefs.current.get(highlightId)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      const t = setTimeout(() => setHighlightId(null), 3000)
      return () => clearTimeout(t)
    }
  }, [highlightId, data])

  async function handlePatientAdded(patientId: string) {
    setShowModal(false)
    setFilter('all')
    setSearch('')
    setSortField('score')
    setSortDir('desc')
    await loadData()
    setHighlightId(patientId)
  }

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
    return [...rows].sort((a, b) => {
      let diff = 0
      if (sortField === 'score')      diff = a.score - b.score
      if (sortField === 'risk_level') diff = (RISK_ORDER[a.risk_level] ?? 0) - (RISK_ORDER[b.risk_level] ?? 0)
      if (sortField === 'age')        diff = (a.features?.age ?? 0) - (b.features?.age ?? 0)
      return sortDir === 'desc' ? -diff : diff
    })
  }, [data, filter, search, sortField, sortDir])

  function toggleSort(field: SortField) {
    if (sortField === field) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortField(field); setSortDir('desc') }
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
    return [...row.explanation].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))[0]?.feature ?? '—'
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, gap: 10 }}>
      <div style={{
        width: 18, height: 18, borderRadius: '50%',
        border: '2px solid #1D2940', borderTopColor: '#5DCAA5',
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
    <>
      {showModal && (
        <AddPatientModal
          onClose={() => setShowModal(false)}
          onSuccess={handlePatientAdded}
        />
      )}

      <div style={{ padding: '28px 32px', maxWidth: 1400, margin: '0 auto' }}>

        {/* Page header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 600, color: '#E2EAF8', marginBottom: 4 }}>
              Patient Risk Overview
            </div>
            <div style={{ fontSize: 12, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
              LACE readmission risk · {data.length} patients · XGBoost v1.0
            </div>
          </div>
          <button
            onClick={() => setShowModal(true)}
            style={{
              background: 'rgba(93,202,165,0.08)',
              border: '1px solid #5DCAA5',
              borderRadius: 6,
              padding: '8px 18px',
              color: '#5DCAA5',
              fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace",
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            + Add patient
          </button>
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
              background: '#121929', border: '1px solid #1D2940',
              borderRadius: 6, padding: '7px 12px',
              color: '#E2EAF8', fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace",
              width: 240, outline: 'none',
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
                  borderRadius: 5, padding: '5px 10px',
                  color: sortField === key ? '#5DCAA5' : '#5C6B8A',
                  fontSize: 11, cursor: 'pointer',
                  fontFamily: "'JetBrains Mono', monospace",
                  display: 'flex', alignItems: 'center', gap: 4,
                }}
              >
                {label}
                {sortField === key && <span style={{ fontSize: 9 }}>{sortDir === 'desc' ? '↓' : '↑'}</span>}
              </button>
            ))}
          </div>
          <span style={{ marginLeft: 'auto', fontSize: 11, color: '#3A4B6A', fontFamily: "'JetBrains Mono', monospace" }}>
            {filtered.length} rows
          </span>
        </div>

        {/* Table */}
        <div style={{ background: '#121929', border: '1px solid #1D2940', borderRadius: 8, overflow: 'hidden' }}>
          {/* Header */}
          <div style={{
            display: 'grid', gridTemplateColumns: '2fr 60px 180px 110px 1fr 28px',
            padding: '10px 20px', borderBottom: '1px solid #1D2940',
            fontSize: 10, color: '#3A4B6A', letterSpacing: '0.08em',
            fontWeight: 600, textTransform: 'uppercase',
          }}>
            <span>Patient ID</span><span>Age</span><span>Risk Score</span>
            <span>Level</span><span>Top Driver</span><span />
          </div>

          {filtered.length === 0 && (
            <div style={{ padding: '32px 20px', textAlign: 'center', color: '#3A4B6A', fontSize: 13 }}>
              No patients match the current filter.
            </div>
          )}

          {filtered.map((row, i) => {
            const isExpanded  = expanded.has(row.id)
            const isHighlight = row.patient_id === highlightId
            const age = row.features?.age != null ? Math.round(row.features.age) : '—'
            const sorted3 = [...(row.explanation ?? [])]
              .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
              .slice(0, 3)

            return (
              <div
                key={row.id}
                ref={(el) => {
                  if (el) rowRefs.current.set(row.patient_id, el)
                  else rowRefs.current.delete(row.patient_id)
                }}
                style={{
                  borderBottom: i < filtered.length - 1 ? '1px solid #151E30' : 'none',
                  transition: 'box-shadow 0.4s',
                  boxShadow: isHighlight
                    ? 'inset 0 0 0 1px #5DCAA5, 0 0 20px rgba(93,202,165,0.18)'
                    : 'none',
                  borderRadius: isHighlight ? 4 : 0,
                }}
              >
                {/* Main row */}
                <div
                  onClick={() => toggleExpand(row.id)}
                  style={{
                    display: 'grid', gridTemplateColumns: '2fr 60px 180px 110px 1fr 28px',
                    padding: '12px 20px', alignItems: 'center',
                    cursor: 'pointer', transition: 'background 0.1s',
                    background: isExpanded ? '#172035' : isHighlight ? 'rgba(93,202,165,0.04)' : 'transparent',
                  }}
                  onMouseEnter={e => { if (!isExpanded) (e.currentTarget as HTMLElement).style.background = 'rgba(23,32,53,0.6)' }}
                  onMouseLeave={e => { if (!isExpanded) (e.currentTarget as HTMLElement).style.background = isHighlight ? 'rgba(93,202,165,0.04)' : 'transparent' }}
                >
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                    color: isHighlight ? '#5DCAA5' : '#8FA3C8',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 12,
                  }}>
                    {row.patient_id}
                    {isHighlight && (
                      <span style={{ marginLeft: 8, fontSize: 9, color: '#5DCAA5', opacity: 0.7 }}>NEW</span>
                    )}
                  </span>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: '#E2EAF8' }}>
                    {age}
                  </span>
                  <div style={{ paddingRight: 16 }}>
                    <ScoreBar score={row.score} level={row.risk_level} />
                  </div>
                  <div><RiskLevelBadge level={row.risk_level} /></div>
                  <span style={{
                    fontSize: 11, color: '#5C6B8A',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 8,
                  }}>
                    {topFeature(row)}
                  </span>
                  <span style={{
                    fontSize: 12, color: '#3A4B6A',
                    transform: isExpanded ? 'rotate(90deg)' : 'none',
                    transition: 'transform 0.15s', display: 'inline-block', textAlign: 'center',
                  }}>›</span>
                </div>

                {/* Expanded SHAP panel */}
                {isExpanded && sorted3.length > 0 && (
                  <div style={{
                    padding: '16px 24px 20px 24px',
                    background: '#0F1725', borderTop: '1px solid #151E30',
                  }}>
                    <div style={{
                      fontSize: 10, color: '#3A4B6A', fontWeight: 600,
                      letterSpacing: '0.08em', textTransform: 'uppercase',
                      marginBottom: 14, fontFamily: "'JetBrains Mono', monospace",
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
    </>
  )
}
