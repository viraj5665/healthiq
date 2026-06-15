import { useEffect, useState, useCallback, useMemo } from 'react'
import { fetchAlerts, runAlertCheck } from '../lib/api'
import type { Alert } from '../types'

type SevFilter = 'all' | 'critical' | 'urgent' | 'warning'

const SEV_COLOR: Record<string, string> = {
  critical: '#F0997B',
  urgent:   '#F5C97A',
  warning:  '#5DCAA5',
}
const SEV_BG: Record<string, string> = {
  critical: 'rgba(240,153,123,0.10)',
  urgent:   'rgba(245,201,122,0.10)',
  warning:  'rgba(93,202,165,0.10)',
}

const TYPE_LABEL: Record<string, string> = {
  'risk-threshold': 'Risk Threshold',
  'bed_capacity':   'Bed Capacity',
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins  = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days  = Math.floor(diff / 86400000)
  if (mins < 1)   return 'just now'
  if (mins < 60)  return `${mins}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

function PulsingDot() {
  return (
    <span style={{ position: 'relative', display: 'inline-flex', width: 8, height: 8, flexShrink: 0 }}>
      <span style={{
        position: 'absolute', inset: 0, borderRadius: '50%',
        background: '#F0997B', opacity: 0.6,
        animation: 'ping 1.4s cubic-bezier(0,0,0.2,1) infinite',
      }} />
      <span style={{
        position: 'relative', display: 'inline-flex',
        width: 8, height: 8, borderRadius: '50%',
        background: '#F0997B',
      }} />
      <style>{`@keyframes ping { 75%,100% { transform: scale(2); opacity: 0; } }`}</style>
    </span>
  )
}

interface CheckResult { created: number; skipped_duplicates: number }

export default function Alerts() {
  const [data, setData]           = useState<Alert[]>([])
  const [loading, setLoading]     = useState(true)
  const [checking, setChecking]   = useState(false)
  const [checkResult, setCheckResult] = useState<CheckResult | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const [filter, setFilter]       = useState<SevFilter>('all')

  const load = useCallback(async () => {
    try {
      const rows = await fetchAlerts(200)
      setData(rows)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const counts = useMemo(() => ({
    all:      data.length,
    critical: data.filter(d => d.severity === 'critical').length,
    urgent:   data.filter(d => d.severity === 'urgent').length,
    warning:  data.filter(d => d.severity === 'warning').length,
  }), [data])

  const filtered = useMemo(() =>
    filter === 'all' ? data : data.filter(d => d.severity === filter),
    [data, filter]
  )

  async function handleCheck() {
    setChecking(true)
    setCheckResult(null)
    try {
      const r = await runAlertCheck()
      setCheckResult(r)
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setChecking(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, gap: 10 }}>
      <div style={{
        width: 18, height: 18, borderRadius: '50%',
        border: '2px solid #1D2940', borderTopColor: '#F0997B',
        animation: 'spin 0.8s linear infinite',
      }} />
      <span style={{ color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>
        Loading alerts...
      </span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1100, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#E2EAF8', marginBottom: 4 }}>
            Active Alerts
          </div>
          <div style={{ fontSize: 12, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
            Real-time clinical alert feed · status=active
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
          <button
            onClick={handleCheck}
            disabled={checking}
            style={{
              background: checking ? '#1D2940' : 'rgba(240,153,123,0.08)',
              border: '1px solid #F0997B',
              borderRadius: 6,
              padding: '8px 18px',
              color: checking ? '#5C6B8A' : '#F0997B',
              fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace",
              cursor: checking ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
              transition: 'all 0.15s',
            }}
          >
            {checking ? (
              <>
                <span style={{
                  display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
                  border: '1.5px solid #3A4B6A', borderTopColor: '#F0997B',
                  animation: 'spin 0.8s linear infinite',
                }} />
                Checking...
              </>
            ) : '⚡  Run alert check'}
          </button>
          {checkResult && (
            <span style={{ fontSize: 11, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
              +{checkResult.created} new · {checkResult.skipped_duplicates} skipped
            </span>
          )}
        </div>
      </div>

      {error && (
        <div style={{ marginBottom: 16, padding: '10px 14px', background: 'rgba(240,153,123,0.08)', border: '1px solid #F0997B', borderRadius: 6, color: '#F0997B', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          {error}
        </div>
      )}

      {/* Summary filter cards */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 24, flexWrap: 'wrap' }}>
        {([
          { key: 'all',      label: 'All Alerts',  color: '#8FA3C8', count: counts.all },
          { key: 'critical', label: 'Critical',     color: '#F0997B', count: counts.critical },
          { key: 'urgent',   label: 'Urgent',       color: '#F5C97A', count: counts.urgent },
          { key: 'warning',  label: 'Warning',      color: '#5DCAA5', count: counts.warning },
        ] as const).map(({ key, label, color, count }) => {
          const active = filter === key
          return (
            <button
              key={key}
              onClick={() => setFilter(key)}
              style={{
                flex: 1, minWidth: 120,
                background: active ? `rgba(${hexToRgb(color)},0.10)` : '#121929',
                border: `1px solid ${active ? color : '#1D2940'}`,
                borderRadius: 8,
                padding: '14px 18px',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s',
                boxShadow: active ? `0 0 12px rgba(${hexToRgb(color)},0.12)` : 'none',
              }}
            >
              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 24, fontWeight: 500, color, lineHeight: 1.1,
              }}>
                {count}
              </div>
              <div style={{
                fontSize: 10, color: '#5C6B8A', marginTop: 4,
                textTransform: 'uppercase', letterSpacing: '0.06em',
              }}>
                {label}
              </div>
            </button>
          )
        })}
      </div>

      {/* Alert feed */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {filtered.length === 0 && (
          <div style={{
            background: '#121929', border: '1px solid #1D2940', borderRadius: 8,
            padding: '40px 24px', textAlign: 'center', color: '#3A4B6A', fontSize: 13,
          }}>
            No {filter !== 'all' ? filter : ''} alerts at this time.
          </div>
        )}

        {filtered.map((alert) => {
          const col = SEV_COLOR[alert.severity] ?? '#8FA3C8'
          const bg  = SEV_BG[alert.severity]  ?? 'rgba(143,163,200,0.06)'
          const isCritical = alert.severity === 'critical'

          return (
            <div
              key={alert.id}
              style={{
                background: '#121929',
                border: `1px solid #1D2940`,
                borderLeft: `3px solid ${col}`,
                borderRadius: 8,
                padding: '14px 18px',
                display: 'flex',
                gap: 14,
                alignItems: 'flex-start',
              }}
            >
              {/* Severity indicator */}
              <div style={{ paddingTop: 2, flexShrink: 0 }}>
                {isCritical ? <PulsingDot /> : (
                  <span style={{
                    display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: col,
                  }} />
                )}
              </div>

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                  {/* Severity badge */}
                  <span style={{
                    display: 'inline-flex', alignItems: 'center',
                    padding: '2px 7px', borderRadius: 4,
                    background: bg, color: col,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 9, fontWeight: 500, letterSpacing: '0.08em',
                    flexShrink: 0,
                  }}>
                    {alert.severity.toUpperCase()}
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 500, color: '#E2EAF8' }}>
                    {alert.title}
                  </span>
                </div>

                <div style={{ fontSize: 12, color: '#8FA3C8', marginBottom: 8, lineHeight: 1.5 }}>
                  {alert.message}
                </div>

                <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  {alert.patient_id && (
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10, color: '#5C6B8A',
                    }}>
                      Patient {alert.patient_id.slice(0, 8)}…
                    </span>
                  )}
                  <span style={{ fontSize: 10, color: '#3A4B6A' }}>
                    {TYPE_LABEL[alert.alert_type] ?? alert.alert_type}
                  </span>
                  <span style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10, color: '#3A4B6A', marginLeft: 'auto',
                  }}>
                    {relativeTime(alert.triggered_at)}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

    </div>
  )
}

function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r},${g},${b}`
}
