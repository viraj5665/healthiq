interface Props {
  label: string
  value: number | string
  color?: string
  pct?: number
  onClick?: () => void
  active?: boolean
}

export function StatCard({ label, value, color = '#5DCAA5', pct, onClick, active }: Props) {
  return (
    <button
      onClick={onClick}
      style={{
        background: active ? `rgba(${hexToRgb(color)},0.08)` : '#121929',
        border: `1px solid ${active ? color : '#1D2940'}`,
        borderRadius: 8,
        padding: '16px 20px',
        cursor: onClick ? 'pointer' : 'default',
        textAlign: 'left',
        flex: 1,
        minWidth: 140,
        transition: 'border-color 0.15s, background 0.15s',
        boxShadow: active ? `0 0 12px rgba(${hexToRgb(color)},0.15)` : 'none',
      }}
    >
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 26,
        fontWeight: 500,
        color,
        lineHeight: 1.1,
      }}>
        {value}
      </div>
      <div style={{
        fontSize: 11,
        color: '#5C6B8A',
        marginTop: 4,
        fontWeight: 500,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
      }}>
        {label}
      </div>
      {pct !== undefined && (
        <div style={{ fontSize: 11, color: '#3A4B6A', marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
          {pct.toFixed(1)}%
        </div>
      )}
    </button>
  )
}

function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r},${g},${b}`
}
