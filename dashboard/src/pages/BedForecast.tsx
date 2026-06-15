import { useEffect, useState, useCallback } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, defs, linearGradient, stop,
} from 'recharts'
import { fetchBedForecasts, runForecast } from '../lib/api'
import type { BedForecast as BedForecastType } from '../types'

const STATUS_COLOR: Record<string, string> = {
  normal:   '#5DCAA5',
  warning:  '#F5C97A',
  critical: '#F0997B',
}

const STATUS_BG: Record<string, string> = {
  normal:   'rgba(93,202,165,0.1)',
  warning:  'rgba(245,201,122,0.1)',
  critical: 'rgba(240,153,123,0.1)',
}

function fmt(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}

function fmtShort(dateStr: string) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { weekday: 'short', month: 'numeric', day: 'numeric' })
}

function overallStatus(data: BedForecastType[]): string {
  if (data.some(d => d.status === 'critical')) return 'critical'
  if (data.some(d => d.status === 'warning'))  return 'warning'
  return 'normal'
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ value: number; dataKey: string }>
  label?: string
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null
  const occ = payload.find(p => p.dataKey === 'predicted_occupancy')?.value ?? 0
  const cap = payload.find(p => p.dataKey === 'capacity')?.value ?? 0
  const pct = cap > 0 ? ((occ / cap) * 100).toFixed(1) : '—'
  return (
    <div style={{
      background: '#172035',
      border: '1px solid #1D2940',
      borderRadius: 6,
      padding: '10px 14px',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 12,
    }}>
      <div style={{ color: '#8FA3C8', marginBottom: 6 }}>{label}</div>
      <div style={{ color: '#5DCAA5' }}>Occupancy: <strong>{occ}</strong> beds</div>
      <div style={{ color: '#5C6B8A' }}>Capacity:  {cap} beds</div>
      <div style={{ color: '#E2EAF8', marginTop: 4 }}>{pct}% utilisation</div>
    </div>
  )
}

export default function BedForecast() {
  const [data, setData]       = useState<BedForecastType[]>([])
  const [loading, setLoading] = useState(true)
  const [rerunning, setRerunning] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const rows = await fetchBedForecasts()
      setData(rows.sort((a, b) => a.forecast_date.localeCompare(b.forecast_date)))
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleRerun() {
    setRerunning(true)
    try {
      await runForecast()
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setRerunning(false)
    }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, gap: 10 }}>
      <div style={{
        width: 18, height: 18, borderRadius: '50%',
        border: '2px solid #1D2940', borderTopColor: '#5DCAA5',
        animation: 'spin 0.8s linear infinite',
      }} />
      <span style={{ color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>
        Loading forecast...
      </span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )

  if (error) return (
    <div style={{ padding: 32, color: '#F0997B', fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>
      Error: {error}
    </div>
  )

  if (!data.length) return (
    <div style={{ padding: 32, color: '#5C6B8A', fontSize: 13 }}>
      No forecast data. Click "Re-run forecast" to generate.
    </div>
  )

  const avgOcc = data.reduce((s, d) => s + d.predicted_occupancy, 0) / data.length
  const peakDay = [...data].sort((a, b) => b.predicted_occupancy - a.predicted_occupancy)[0]
  const capacity = data[0].capacity
  const status = overallStatus(data)
  const statusColor = STATUS_COLOR[status]

  // Chart data — add a display label
  const chartData = data.map(d => ({
    ...d,
    label: fmtShort(d.forecast_date),
  }))

  // For gradient stop color we need the dominant status
  const gradId = 'occGradient'

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#E2EAF8', marginBottom: 4 }}>
            Bed Forecast
          </div>
          <div style={{ fontSize: 12, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
            7-day census · moving average · capacity {capacity} beds
          </div>
        </div>
        <button
          onClick={handleRerun}
          disabled={rerunning}
          style={{
            background: rerunning ? '#1D2940' : 'rgba(93,202,165,0.08)',
            border: '1px solid #5DCAA5',
            borderRadius: 6,
            padding: '8px 18px',
            color: rerunning ? '#5C6B8A' : '#5DCAA5',
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            cursor: rerunning ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            transition: 'all 0.15s',
          }}
        >
          {rerunning ? (
            <>
              <span style={{
                display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
                border: '1.5px solid #3A4B6A', borderTopColor: '#5DCAA5',
                animation: 'spin 0.8s linear infinite',
              }} />
              Running...
            </>
          ) : '↻  Re-run forecast'}
        </button>
      </div>

      {/* Summary stat bar */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 28, flexWrap: 'wrap' }}>
        {[
          {
            label: '7-Day Avg Occupancy',
            value: avgOcc.toFixed(1),
            sub: `${((avgOcc / capacity) * 100).toFixed(1)}% capacity`,
            color: statusColor,
          },
          {
            label: 'Peak Day',
            value: peakDay.predicted_occupancy.toFixed(1),
            sub: fmtShort(peakDay.forecast_date),
            color: STATUS_COLOR[peakDay.status],
          },
          {
            label: 'Bed Capacity',
            value: String(capacity),
            sub: 'total beds',
            color: '#8FA3C8',
          },
          {
            label: '7-Day Status',
            value: status.toUpperCase(),
            sub: `${data.filter(d => d.status === status).length}/7 days`,
            color: statusColor,
          },
        ].map(({ label, value, sub, color }) => (
          <div key={label} style={{
            flex: 1, minWidth: 150,
            background: '#121929',
            border: `1px solid #1D2940`,
            borderRadius: 8,
            padding: '16px 20px',
          }}>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 24,
              fontWeight: 500,
              color,
              lineHeight: 1.1,
            }}>
              {value}
            </div>
            <div style={{ fontSize: 11, color: '#5C6B8A', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {label}
            </div>
            <div style={{ fontSize: 11, color: '#3A4B6A', marginTop: 2, fontFamily: "'JetBrains Mono', monospace" }}>
              {sub}
            </div>
          </div>
        ))}
      </div>

      {/* Area chart */}
      <div style={{
        background: '#121929',
        border: '1px solid #1D2940',
        borderRadius: 8,
        padding: '24px 16px 16px',
        marginBottom: 20,
      }}>
        <div style={{ fontSize: 11, color: '#3A4B6A', fontFamily: "'JetBrains Mono', monospace", marginBottom: 16, paddingLeft: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Predicted Occupancy — Next 7 Days
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={chartData} margin={{ top: 8, right: 20, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={statusColor} stopOpacity={0.25} />
                <stop offset="95%" stopColor={statusColor} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1D2940" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: '#5C6B8A', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={{ stroke: '#1D2940' }}
              tickLine={false}
            />
            <YAxis
              domain={[0, capacity + 2]}
              tick={{ fill: '#5C6B8A', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#1D2940', strokeWidth: 1 }} />
            <ReferenceLine
              y={capacity}
              stroke="#F0997B"
              strokeDasharray="6 3"
              strokeWidth={1.5}
              label={{
                value: `Capacity (${capacity})`,
                fill: '#F0997B',
                fontSize: 10,
                fontFamily: "'JetBrains Mono', monospace",
                position: 'insideTopRight',
              }}
            />
            <Area
              type="monotone"
              dataKey="predicted_occupancy"
              stroke={statusColor}
              strokeWidth={2}
              fill={`url(#${gradId})`}
              dot={{ fill: statusColor, strokeWidth: 0, r: 4 }}
              activeDot={{ fill: statusColor, stroke: '#0A0E17', strokeWidth: 2, r: 6 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Day cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 10 }}>
        {data.map((day) => {
          const pct = ((day.predicted_occupancy / day.capacity) * 100).toFixed(0)
          const col = STATUS_COLOR[day.status]
          return (
            <div key={day.forecast_date} style={{
              background: '#121929',
              border: `1px solid #1D2940`,
              borderRadius: 8,
              padding: '14px 12px',
            }}>
              <div style={{ fontSize: 10, color: '#5C6B8A', marginBottom: 10, fontWeight: 500 }}>
                {fmt(day.forecast_date)}
              </div>

              {/* Mini bar */}
              <div style={{ height: 3, background: '#1D2940', borderRadius: 2, marginBottom: 12, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pct}%`, background: col, borderRadius: 2 }} />
              </div>

              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 20,
                fontWeight: 500,
                color: col,
                lineHeight: 1,
                marginBottom: 4,
              }}>
                {day.predicted_occupancy.toFixed(1)}
              </div>
              <div style={{ fontSize: 10, color: '#3A4B6A', marginBottom: 10, fontFamily: "'JetBrains Mono', monospace" }}>
                of {day.capacity} beds · {pct}%
              </div>

              {/* Status badge */}
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '2px 7px',
                borderRadius: 4,
                background: STATUS_BG[day.status],
                color: col,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 9,
                fontWeight: 500,
                letterSpacing: '0.08em',
              }}>
                {day.status.toUpperCase()}
              </span>
            </div>
          )
        })}
      </div>

    </div>
  )
}
