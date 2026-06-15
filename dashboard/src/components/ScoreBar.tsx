interface Props {
  score: number
  level: string
}

const BAR_COLOR: Record<string, string> = {
  critical: '#F0997B',
  high:     '#F0875C',
  moderate: '#F5C97A',
  low:      '#5DCAA5',
}

export function ScoreBar({ score, level }: Props) {
  const pct = Math.round(score * 100)
  const color = BAR_COLOR[level] ?? '#5DCAA5'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        flex: 1,
        height: 4,
        background: '#1D2940',
        borderRadius: 2,
        overflow: 'hidden',
        minWidth: 80,
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: color,
          borderRadius: 2,
          boxShadow: `0 0 4px ${color}60`,
          transition: 'width 0.3s ease',
        }} />
      </div>
      <span style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12,
        color: color,
        minWidth: 32,
        textAlign: 'right',
      }}>
        {pct}%
      </span>
    </div>
  )
}
