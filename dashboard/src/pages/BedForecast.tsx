import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
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
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
  })
}
function fmtShort(dateStr: string) {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short', month: 'numeric', day: 'numeric',
  })
}

function simStatus(occ: number, cap: number): string {
  const util = occ / cap
  if (util >= 1.00) return 'critical'
  if (util >= 0.80) return 'warning'
  return 'normal'
}

function overallSimStatus(data: BedForecastType[], cap: number): string {
  const statuses = data.map(d => simStatus(d.predicted_occupancy, cap))
  if (statuses.includes('critical')) return 'critical'
  if (statuses.includes('warning'))  return 'warning'
  return 'normal'
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ value: number; dataKey: string }>
  label?: string
  simCapacity: number
}

function CustomTooltip({ active, payload, label, simCapacity }: TooltipProps) {
  if (!active || !payload?.length) return null
  const occ = payload.find(p => p.dataKey === 'predicted_occupancy')?.value ?? 0
  const pct = simCapacity > 0 ? ((occ / simCapacity) * 100).toFixed(1) : '—'
  const st  = simStatus(occ, simCapacity)
  return (
    <div style={{
      background: '#172035', border: '1px solid #1D2940',
      borderRadius: 6, padding: '10px 14px',
      fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
    }}>
      <div style={{ color: '#8FA3C8', marginBottom: 6 }}>{label}</div>
      <div style={{ color: STATUS_COLOR[st] }}>Occupancy: <strong>{typeof occ === 'number' ? occ.toFixed(1) : occ}</strong> beds</div>
      <div style={{ color: '#5C6B8A' }}>Capacity:  {simCapacity} beds</div>
      <div style={{ color: '#E2EAF8', marginTop: 4 }}>{pct}% utilisation</div>
    </div>
  )
}

export default function BedForecast() {
  const [data, setData]         = useState<BedForecastType[]>([])
  const [loading, setLoading]   = useState(true)
  const [rerunning, setRerunning] = useState(false)
  const [error, setError]       = useState<string | null>(null)
  const [simCapacity, setSimCapacity] = useState(20)

  const load = useCallback(async () => {
    try {
      const rows = await fetchBedForecasts()
      const sorted = rows.sort((a, b) => a.forecast_date.localeCompare(b.forecast_date))
      setData(sorted)
      setSimCapacity(sorted[0]?.capacity ?? 20)
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

  const status      = useMemo(() => overallSimStatus(data, simCapacity), [data, simCapacity])
  const statusColor = STATUS_COLOR[status]
  const avgOcc      = data.length ? data.reduce((s, d) => s + d.predicted_occupancy, 0) / data.length : 0
  const peakDay     = data.length ? [...data].sort((a, b) => b.predicted_occupancy - a.predicted_occupancy)[0] : null

  const chartData = data.map(d => ({ ...d, label: fmtShort(d.forecast_date) }))
  const gradId    = 'occGradient'

  const simDayCount = data.filter(d => simStatus(d.predicted_occupancy, simCapacity) === status).length

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, gap: 10 }}>
      <div style={{
        width: 18, height: 18, borderRadius: '50%',
        border: '2px solid #1D2940', borderTopColor: '#5DCAA5',
        animation: 'spin 0.8s linear infinite',
      }} />
      <span style={{ color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>Loading forecast...</span>
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

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1200, margin: '0 auto' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#E2EAF8', marginBottom: 4 }}>Bed Forecast</div>
          <div style={{ fontSize: 12, color: '#5C6B8A', fontFamily: "'JetBrains Mono', monospace" }}>
            7-day census · day-of-week variance · capacity {simCapacity} beds
          </div>
        </div>
        <button
          onClick={handleRerun}
          disabled={rerunning}
          style={{
            background: rerunning ? '#1D2940' : 'rgba(93,202,165,0.08)',
            border: '1px solid #5DCAA5', borderRadius: 6,
            padding: '8px 18px',
            color: rerunning ? '#5C6B8A' : '#5DCAA5',
            fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
            cursor: rerunning ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
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
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {[
          {
            label: '7-Day Avg Occupancy',
            value: avgOcc.toFixed(1),
            sub: `${((avgOcc / simCapacity) * 100).toFixed(1)}% of sim. capacity`,
            color: statusColor,
          },
          {
            label: 'Peak Day',
            value: peakDay ? peakDay.predicted_occupancy.toFixed(1) : '—',
            sub: peakDay ? fmtShort(peakDay.forecast_date) : '',
            color: peakDay ? STATUS_COLOR[simStatus(peakDay.predicted_occupancy, simCapacity)] : '#8FA3C8',
          },
          {
            label: 'Sim. Capacity',
            value: String(simCapacity),
            sub: 'drag slider below →',
            color: '#8FA3C8',
          },
          {
            label: '7-Day Status',
            value: status.toUpperCase(),
            sub: `${simDayCount}/7 days at ${status}`,
            color: statusColor,
          },
        ].map(({ label, value, sub, color }) => (
          <div key={label} style={{
            flex: 1, minWidth: 150,
            background: '#121929', border: '1px solid #1D2940',
            borderRadius: 8, padding: '16px 20px',
          }}>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 24, fontWeight: 500, color, lineHeight: 1.1,
            }}>{value}</div>
            <div style={{ fontSize: 11, color: '#5C6B8A', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {label}
            </div>
            <div style={{ fontSize: 11, color: '#3A4B6A', marginTop: 2, fontFamily: "'JetBrains Mono', monospace" }}>
              {sub}
            </div>
          </div>
        ))}
      </div>

      {/* Capacity slider */}
      <div style={{
        background: '#121929', border: '1px solid #1D2940',
        borderRadius: 8, padding: '14px 20px',
        marginBottom: 20,
        display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <span style={{ fontSize: 11, color: '#5C6B8A', whiteSpace: 'nowrap', minWidth: 160 }}>
          Simulate capacity change
        </span>
        <input
          type="range"
          min={10}
          max={50}
          value={simCapacity}
          onChange={e => setSimCapacity(Number(e.target.value))}
          style={{ flex: 1, accentColor: '#5DCAA5', cursor: 'pointer' }}
        />
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 14, fontWeight: 500,
          color: statusColor,
          minWidth: 60, textAlign: 'right',
        }}>
          {simCapacity} beds
        </span>
        <span style={{ fontSize: 10, color: '#3A4B6A', minWidth: 40 }}>10 – 50</span>
      </div>

      {/* Area chart */}
      <div style={{
        background: '#121929', border: '1px solid #1D2940',
        borderRadius: 8, padding: '24px 16px 16px',
        marginBottom: 20,
      }}>
        <div style={{
          fontSize: 11, color: '#3A4B6A', fontFamily: "'JetBrains Mono', monospace",
          marginBottom: 16, paddingLeft: 8, textTransform: 'uppercase', letterSpacing: '0.06em',
        }}>
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
              domain={[0, Math.max(simCapacity, ...data.map(d => d.predicted_occupancy)) + 2]}
              tick={{ fill: '#5C6B8A', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
              axisLine={false} tickLine={false} width={32}
            />
            <Tooltip
              content={(props) => (
                <CustomTooltip
                  active={props.active}
                  payload={props.payload as Array<{ value: number; dataKey: string }> | undefined}
                  label={props.label as string | undefined}
                  simCapacity={simCapacity}
                />
              )}
              cursor={{ stroke: '#1D2940', strokeWidth: 1 }}
            />
            <ReferenceLine
              y={simCapacity}
              stroke="#F0997B"
              strokeDasharray="6 3"
              strokeWidth={1.5}
              label={{
                value: `Cap. (${simCapacity})`,
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
          const st  = simStatus(day.predicted_occupancy, simCapacity)
          const col = STATUS_COLOR[st]
          const pct = Math.min(100, (day.predicted_occupancy / simCapacity) * 100)
          return (
            <div key={day.forecast_date} style={{
              background: '#121929', border: '1px solid #1D2940',
              borderRadius: 8, padding: '14px 12px',
            }}>
              <div style={{ fontSize: 10, color: '#5C6B8A', marginBottom: 10, fontWeight: 500 }}>
                {fmt(day.forecast_date)}
              </div>
              <div style={{ height: 3, background: '#1D2940', borderRadius: 2, marginBottom: 12, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pct}%`, background: col, borderRadius: 2, transition: 'width 0.2s' }} />
              </div>
              <div style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 20, fontWeight: 500, color: col,
                lineHeight: 1, marginBottom: 4,
              }}>
                {day.predicted_occupancy.toFixed(1)}
              </div>
              <div style={{ fontSize: 10, color: '#3A4B6A', marginBottom: 10, fontFamily: "'JetBrains Mono', monospace" }}>
                of {simCapacity} beds · {pct.toFixed(0)}%
              </div>
              <span style={{
                display: 'inline-flex', alignItems: 'center',
                padding: '2px 7px', borderRadius: 4,
                background: STATUS_BG[st], color: col,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 9, fontWeight: 500, letterSpacing: '0.08em',
              }}>
                {st.toUpperCase()}
              </span>
            </div>
          )
        })}
      </div>

    </div>
  )
}
